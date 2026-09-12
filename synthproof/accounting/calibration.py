"""Noise calibration: invert the composition theorem to hit a target epsilon.

Without this, a "target epsilon" is only a knob that influences the noise scale, and the
epsilon that actually gets composed is whatever falls out. SynthProof previously set
``noise_scale = sqrt(num_columns) / target_eps`` by hand, which drifted badly: a target
of 8.0 composed to 70.49. See brutal_project_audit.md, finding F2.

``calibrate_noise_scale`` binary-searches the noise scale so that composing the requested
mechanism the requested number of times yields the requested epsilon. Epsilon is strictly
decreasing in the noise scale, which is what makes the search well-posed.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Sequence

from synthproof.accounting.accountant import Accountant
from synthproof.accounting.types import MechanismSpec

# Bracketing limits. A noise scale outside these is a configuration error, not a
# search failure — epsilon targets that need them are unusable in practice.
_MIN_SCALE = 1e-9
_MAX_SCALE = 1e12


def epsilon_for_noise_scale(
    noise_scale: float,
    target_delta: float,
    name: str = "gaussian",
    sensitivity: float = 1.0,
    steps: int = 1,
    sampling_rate: Optional[float] = None,
    orders: Optional[Sequence[float]] = None,
) -> float:
    """Epsilon obtained by composing `steps` copies of the mechanism at `noise_scale`."""
    spec = MechanismSpec(
        name=name,
        sensitivity=sensitivity,
        noise_scale=noise_scale,
        sampling_rate=sampling_rate,
        steps=steps,
    )
    # Budget is irrelevant here; we only use the accountant's composition.
    return Accountant(budget_eps=float("inf"), budget_delta=target_delta, orders=orders).dry_run(
        spec
    )


def calibrate_noise_scale(
    target_eps: float,
    target_delta: float = 1e-5,
    name: str = "gaussian",
    sensitivity: float = 1.0,
    steps: int = 1,
    sampling_rate: Optional[float] = None,
    orders: Optional[Sequence[float]] = None,
    tol: float = 1e-4,
    max_iter: int = 200,
) -> float:
    """Finds the noise scale whose composed epsilon equals `target_eps`.

    Args:
        target_eps: Desired total epsilon after composing all `steps`.
        target_delta: Delta at which epsilon is evaluated.
        name: Mechanism name ("gaussian" or "laplace").
        sensitivity: Mechanism sensitivity.
        steps: Number of compositions to calibrate for.
        sampling_rate: Poisson subsampling rate, if any.
        orders: RDP orders; defaults to the standard grid.
        tol: Relative tolerance on the achieved epsilon.
        max_iter: Bisection iteration cap.

    Returns:
        The calibrated noise scale. The achieved epsilon is <= target_eps (the search
        returns the conservative side of the bracket), so the calibration never
        overspends the requested budget.

    Raises:
        ValueError: if the target is non-positive or cannot be bracketed.
    """
    if target_eps <= 0:
        raise ValueError(f"target_eps must be positive, got {target_eps}")
    if steps < 1:
        raise ValueError(f"steps must be at least 1, got {steps}")

    def eps_at(scale: float) -> float:
        return epsilon_for_noise_scale(
            scale, target_delta, name, sensitivity, steps, sampling_rate, orders
        )

    # Epsilon decreases as noise grows. Bracket [lo, hi] with eps(lo) >= target >= eps(hi).
    lo = hi = float(sensitivity)

    while eps_at(hi) > target_eps:
        hi *= 2.0
        if hi > _MAX_SCALE:
            raise ValueError(
                f"Cannot reach eps={target_eps} at delta={target_delta} with "
                f"{steps} step(s): required noise exceeds {_MAX_SCALE:g}."
            )

    while eps_at(lo) < target_eps:
        lo /= 2.0
        if lo < _MIN_SCALE:
            # Even almost-zero noise composes to less than the target, so the target is
            # trivially satisfiable; return the smallest sane scale.
            return _MIN_SCALE

    # Converge on the bracket width rather than on |eps(mid) - target|. Terminating on
    # the epsilon gap is unsafe here: if the final probe lands just *above* the target it
    # updates `lo`, leaving `hi` at its stale initial value, and returning `hi` then
    # overshoots badly (Laplace/5 steps/target 2.0 returned a scale achieving eps=1.25).
    # The invariant eps(hi) <= target < eps(lo) holds at every iteration, so shrinking
    # the bracket and returning `hi` is both correct and conservative.
    for _ in range(max_iter):
        if hi - lo <= tol * hi:
            break
        mid = 0.5 * (lo + hi)
        if eps_at(mid) > target_eps:
            lo = mid  # too little noise
        else:
            hi = mid  # enough noise

    return hi


# ── the under-spend, diagnosed 2026-08-23 ────────────────────────────────────────────────
#
# Releases compose to roughly 0.92 of their target epsilon, and AIM to 0.79. The cause is NOT
# the bisection below, which lands within 0.01% of target on a single stage:
#
#     single-stage  target 0.5 -> 0.499967   target 8.0 -> 7.999605     ratio 1.0000
#     two-stage     target 1.0 -> 0.832346   target 8.0 -> 6.715220     ratio 0.83
#
# The loss is entirely in `BudgetPlan`, and it is structural. The plan splits the total
# LINEARLY across stages and calibrates each stage against its own share, but RDP composition
# is SUBLINEAR -- composing two stages calibrated to 0.2e and 0.8e yields materially less than
# e. Every stage added widens the gap, which is why AIM, with the most charged operations,
# leaves the most on the table.
#
# THE FIX IS NOW IMPLEMENTED, and it is OFF BY DEFAULT. `BudgetPlan.split(tighten=True)`
# bisects an outer multiplier k on the stage shares until the COMPOSED total meets the target,
# returning the conservative side exactly as the inner search does. Composition is monotone in
# k, so the search is well-posed and the never-overspend invariant is preserved -- which is
# asserted directly in tests/test_budget_tightening.py rather than argued here.
#
# It stays off because turning it on changes EVERY PUBLISHED EPSILON -- proved 7.356 becomes
# ~8.0 -- and every committed result would be invalid until the full grid is re-run (~4h per
# dataset). That is a costed decision rather than an oversight, and the cost belongs to
# whoever decides to pay it. The current default remains conservative in the safe direction:
# the release is MORE private than the operator asked for, never less.
#
# To adopt it: flip the default, run `make reproduce-all`, read the diff, then `make manifest`.
# Tracked as M3.7. See ../SYNTHPROOF-COMPLETION-PLAN.md Phase 4.


@dataclass(frozen=True)
class BudgetPlan:
    """A split of one release's total epsilon across the pipeline stages.

    Every stage that touches the sensitive data draws from the same total, so the
    composed epsilon of a complete release approximates `total_eps` rather than
    exceeding it by whatever the earlier stages happened to spend.
    """

    total_eps: float
    delta: float
    profile_eps: float
    synthesis_eps: float
    # 1.0 when the shares are a plain linear split; >1 when they were scaled up so the
    # COMPOSED total meets the target. Recorded rather than inferred, so a reader of a plan
    # can tell which calibration produced it without re-deriving anything.
    tightening: float = 1.0

    @property
    def composed_eps(self) -> float:
        """What the two stages actually compose to, asked of the accountant.

        This is the number that matters and the one nothing used to report: `total_eps` is
        what was REQUESTED, and under a linear split the composition of the stages lands
        below it. Computing it here means the gap can be inspected instead of discovered.
        """
        from synthproof.accounting.accountant import Accountant
        from synthproof.accounting.types import MechanismSpec

        acct = Accountant(budget_eps=float("inf"), budget_delta=self.delta)
        for stage_eps in (self.profile_eps, self.synthesis_eps):
            scale = calibrate_noise_scale(stage_eps, self.delta, "gaussian", 1.0, 1)
            acct.charge(MechanismSpec(name="gaussian", noise_scale=scale, sensitivity=1.0))
        return float(acct.total(self.delta))

    @classmethod
    def split(
        cls,
        total_eps: float,
        delta: float = 1e-5,
        profile_frac: float = 0.1,
        tighten: bool = False,
    ) -> "BudgetPlan":
        """Splits `total_eps` between domain profiling and synthesis.

        Args:
            total_eps: Total epsilon for the whole release.
            delta: Target delta.
            profile_frac: Fraction reserved for DP domain profiling. Profiling only
                needs coarse range estimates, so it gets the smaller share.
            tighten: When True, scale both shares by a common multiplier so that their
                COMPOSED epsilon meets `total_eps` instead of falling short of it. See the
                under-spend note above for why this is off by default: it changes every
                published epsilon in this repository. It never overspends -- the search
                returns the conservative side of the bracket, exactly as the inner
                calibration does.
        """
        if total_eps <= 0:
            raise ValueError(f"total_eps must be positive, got {total_eps}")
        if not (0.0 < profile_frac < 1.0):
            raise ValueError(f"profile_frac must be in (0, 1), got {profile_frac}")

        # Routed through the Allocator so budget splitting has one implementation.
        from synthproof.ledger.allocator import Allocator

        shares: Dict[str, float] = Allocator.allocate_weighted(
            total_eps, {"profile": profile_frac, "synthesis": 1.0 - profile_frac}
        )
        plan = cls(
            total_eps=total_eps,
            delta=delta,
            profile_eps=shares["profile"],
            synthesis_eps=shares["synthesis"],
        )
        if not tighten:
            return plan

        # Bisect the outer multiplier k. `composed(k)` is monotone increasing in k, so the
        # bracket [1, hi] with composed(1) <= target <= composed(hi) is well-posed. `hi`
        # returns the conservative side: the last k whose composition is still within budget.
        def composed(k: float) -> float:
            return cls(
                total_eps=total_eps,
                delta=delta,
                profile_eps=shares["profile"] * k,
                synthesis_eps=shares["synthesis"] * k,
                tightening=k,
            ).composed_eps

        lo, hi = 1.0, 1.0
        while composed(hi) < total_eps:
            hi *= 1.5
            if hi > 64.0:  # far past any plausible sublinearity; something else is wrong
                break
        for _ in range(60):
            if hi - lo <= 1e-4 * hi:
                break
            mid = 0.5 * (lo + hi)
            if composed(mid) <= total_eps:
                lo = mid  # still within budget, push further
            else:
                hi = mid
        k = lo  # the largest multiplier that does NOT overspend

        return cls(
            total_eps=total_eps,
            delta=delta,
            profile_eps=shares["profile"] * k,
            synthesis_eps=shares["synthesis"] * k,
            tightening=k,
        )


def calibrate_weighted_scales(
    weights: Sequence[float],
    target_eps: float,
    target_delta: float = 1e-5,
    name: str = "gaussian",
    sensitivity: float = 1.0,
    orders: Optional[Sequence[float]] = None,
    tol: float = 1e-4,
    max_iter: int = 200,
) -> list:
    """Per-query noise scales that spend `target_eps` in total, split by `weights`.

    This is what makes a NON-UNIFORM budget allocation possible without any hand-derived
    composition. Hypothesis H3 asks whether spending more of a fixed budget on the columns an
    analyst cares about buys downstream utility; answering it needs each query to carry its
    own noise scale while the composed total still lands on `target_eps`.

    The shape of the split is fixed analytically — for Gaussian mechanisms under RDP the
    per-query cost goes as `1/scale^2`, so a query with weight `w` gets
    `scale ∝ 1/sqrt(w)` — but the SIZE of the split is found by bisecting against the
    accountant, exactly as `calibrate_noise_scale` does. No epsilon here is computed by this
    module: the returned scales are the ones the accountant agrees compose to at most
    `target_eps`, and a caller that charges them gets that verified again on the way through.

    A uniform weight vector reproduces `calibrate_noise_scale` to within the bisection
    tolerance, which is asserted in the tests rather than assumed.

    Args:
        weights: One positive weight per query. Relative size is what matters, not scale.
        target_eps: Total epsilon after composing every query.

    Returns:
        One noise scale per weight, in the same order.

    Raises:
        ValueError: on a non-positive target, an empty weight vector, or any weight <= 0.
    """
    if target_eps <= 0:
        raise ValueError(f"target_eps must be positive, got {target_eps}")
    w = [float(x) for x in weights]
    if not w:
        raise ValueError("weights must not be empty")
    if any(x <= 0 for x in w):
        raise ValueError(f"every weight must be positive, got {w}")

    k = len(w)
    total_w = sum(w)
    # Shape of the allocation: scale_i proportional to 1/sqrt(w_i), normalised so a uniform
    # vector leaves every scale equal to the multiplier.
    shape = [((total_w / (x * k)) ** 0.5) for x in w]

    def eps_at(mult: float) -> float:
        acct = Accountant(budget_eps=float("inf"), budget_delta=target_delta, orders=orders)
        events = [
            (
                acct.to_dp_event(
                    MechanismSpec(name=name, sensitivity=sensitivity, noise_scale=mult * s, steps=1)
                ),
                1,
            )
            for s in shape
        ]
        return acct._epsilon_for(events, target_delta)

    lo = hi = float(sensitivity)
    while eps_at(hi) > target_eps:
        hi *= 2.0
        if hi > _MAX_SCALE:
            raise ValueError(
                f"Cannot reach eps={target_eps} at delta={target_delta} with {k} weighted "
                f"queries: required noise exceeds {_MAX_SCALE:g}."
            )
    while eps_at(lo) < target_eps:
        lo /= 2.0
        if lo < _MIN_SCALE:
            return [_MIN_SCALE * s for s in shape]

    # Same invariant as calibrate_noise_scale: eps(hi) <= target < eps(lo). Return `hi`, the
    # conservative side, so the calibration never overspends.
    for _ in range(max_iter):
        if hi - lo <= tol * hi:
            break
        mid = 0.5 * (lo + hi)
        if eps_at(mid) > target_eps:
            lo = mid
        else:
            hi = mid

    return [hi * s for s in shape]
