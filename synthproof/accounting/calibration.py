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
    return Accountant(budget_eps=float("inf"), budget_delta=target_delta,
                      orders=orders).dry_run(spec)


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
            lo = mid          # too little noise
        else:
            hi = mid          # enough noise

    return hi


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

    @classmethod
    def split(cls, total_eps: float, delta: float = 1e-5,
              profile_frac: float = 0.1) -> "BudgetPlan":
        """Splits `total_eps` between domain profiling and synthesis.

        Args:
            total_eps: Total epsilon for the whole release.
            delta: Target delta.
            profile_frac: Fraction reserved for DP domain profiling. Profiling only
                needs coarse range estimates, so it gets the smaller share.
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
        return cls(
            total_eps=total_eps,
            delta=delta,
            profile_eps=shares["profile"],
            synthesis_eps=shares["synthesis"],
        )
