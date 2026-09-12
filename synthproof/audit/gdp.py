"""Gaussian Differential Privacy auditing: measure privacy on the FPR/FNR tradeoff curve.

WHY THIS EXISTS. Every audit this project has run reports `eps_audited = 0.000`, and the
project's own write-up treated that as an information-theoretic ceiling. That reading is
**partly wrong, and the correction is published**.

Ganev, Annamalai & Kulynych, *Tight Auditing of Differential Privacy in MST and AIM*, TPDP 2026
([arXiv:2604.18352](https://arxiv.org/abs/2604.18352)) — verified against the arXiv abstract on
2026-08-25 — obtain **mu_emp ~ 0.43 against an implied mu = 0.45** at `(eps, delta) = (1, 1e-2)`
on exactly the mechanism family this project uses. Their diagnosis of the zeros is explicit:
unstable threshold-selection criteria pick overly small thresholds, inflating FPR and collapsing
the empirical lower bound to zero, which is why prior work reports `eps_emp = 0` in the
strong-privacy regime.

So the zero is substantially an **estimator artefact**, not only an instrument ceiling. The fix
is to stop reducing the audit to a single `(eps, delta)` point estimated from a paired
Clopper-Pearson interval, and instead measure the whole tradeoff curve and fit one parameter to
it.

WHAT GDP GIVES US. A mechanism is `mu`-GDP (Dong, Roth & Su, JRSS-B 2022) when distinguishing
neighbouring datasets is at least as hard as distinguishing `N(0,1)` from `N(mu,1)`. Its
tradeoff curve is

    FNR(FPR) = Phi( Phi^-1(1 - FPR) - mu )

which rearranges to a per-threshold estimate

    mu_emp = Phi^-1(1 - FPR) - Phi^-1(FNR)

One scalar summarises the whole curve, and a single unlucky threshold cannot collapse it,
because every threshold yields an estimate and the audit takes the best supported one.

HONEST DIFFERENCES FROM THE PAPER, stated because this is a replication and must not be
presented as a reproduction:

  * They use an **XGBoost** adversary over query-based MIA features plus white-box noisy
    marginal counts. `xgboost` is not installed here; `scripts/run_gdp_audit.py` uses a
    scikit-learn gradient-boosting classifier. A weaker adversary yields a **smaller**
    `mu_emp`, so this errs toward under-claiming.
  * They use a **Bayesian joint estimator** (after Zanella-Beguelin et al.) taking the `mu_emp`
    whose GDP region holds 90% posterior mass, and state it "does not necessarily yield valid
    frequentist coverage". This module instead uses one-sided **Clopper-Pearson** bounds on FPR
    and FNR and reports the resulting conservative `mu`. That is a different, more conservative
    estimator, and the number it produces is not directly comparable to their 0.43.
  * They audit a **restricted configuration**: the dependency graph is fixed, only one-way
    marginals are measured, and domain compression is disabled, so MST and AIM both reduce to
    an independent-marginal model. **This is not a tight audit of AIM as deployed**, and any
    text implying otherwise is wrong.
  * Their audit is **not one-run**. It uses 10,000 independent models (5,000 per world) against
    a single target record on a worst-case 11-record dataset. Thesis text describing it as a
    one-run audit of full AIM would be wrong twice over.

A NUMBER THAT MUST NOT BE MISQUOTED. Their "implied mu = 0.45" is the MECHANISM's GDP parameter
(a single Gaussian at sigma ~ 2.2 gives sqrt(1)/2.2 = 0.4545), not the result of inverting the
released `(eps, delta) = (1, 1e-2)`. Inverting that pair gives **0.5325**, because the pair is
not tight -- a 0.45-GDP mechanism only spends `delta = 0.0033` at `eps = 1`. Use
`mu_from_gaussian_composition` for the mechanism's own parameter and `mu_from_eps_delta` only as
the looser fallback, and never present the latter as reproducing their figure.

WHAT THIS MODULE DOES NOT DO. It does not replace `audit/steinke.py`. The one-run construction
answers "what epsilon can I certify from one training run"; this answers "what mu does the
FPR/FNR curve support across many runs". Both are reported; neither is dropped.
"""

import math
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import numpy as np
from scipy import optimize, stats

# Standard normal CDF and its inverse, named for the formulae above.
_PHI = stats.norm.cdf
_PHI_INV = stats.norm.ppf

DEFAULT_ALPHA = 0.05


def delta_for_mu(mu: float, eps: float) -> float:
    """Delta of a `mu`-GDP mechanism at a given epsilon.

    Dong, Roth & Su (2022), the (eps, delta) profile of Gaussian DP:

        delta(eps) = Phi(-eps/mu + mu/2) - e^eps * Phi(-eps/mu - mu/2)

    Delegated arithmetic only -- no bound is invented here.
    """
    if mu <= 0:
        return 0.0
    return float(_PHI(-eps / mu + mu / 2.0) - math.exp(eps) * _PHI(-eps / mu - mu / 2.0))


def mu_from_gaussian_composition(steps: int, noise_multiplier: float) -> float:
    """The exact `mu` of `steps` compositions of a Gaussian mechanism at `noise_multiplier`.

    A Gaussian mechanism with noise multiplier `sigma` is exactly `(1/sigma)`-GDP, and GDP
    composes by root-sum-square (Dong, Roth & Su 2022, Corollary 3.3), so `k` of them give
    `mu = sqrt(k) / sigma`.

    **Prefer this over `mu_from_eps_delta` when the noise is known.** It is the mechanism's
    own parameter rather than a bound reconstructed from a released `(eps, delta)` pair, and it
    is strictly tighter -- which makes any comparison against an empirical `mu` a stronger test.
    """
    if steps < 1:
        raise ValueError(f"steps must be at least 1, got {steps}")
    if noise_multiplier <= 0:
        raise ValueError(f"noise multiplier must be positive, got {noise_multiplier}")
    return math.sqrt(steps) / noise_multiplier


def mu_from_eps_delta(eps: float, delta: float) -> float:
    """The `mu` whose GDP profile passes through `(eps, delta)` exactly.

    **This is an UPPER BOUND on the mechanism's true `mu`, not the mechanism's `mu`**, and the
    difference is large enough to matter. It answers "if this `(eps, delta)` were tight, what
    `mu` would that be?" A released `(eps, delta)` is usually NOT tight, so the answer comes
    out larger than the mechanism's actual parameter.

    Worked example, checked against the literature on 2026-08-25. Ganev et al.
    ([arXiv:2604.18352](https://arxiv.org/abs/2604.18352)) report an implied `mu = 0.45` at
    `(eps, delta) = (1, 1e-2)`. This function returns **0.5325** for those inputs, and the
    round trip is exact (`delta_for_mu(0.5325, 1) = 0.01`). Both numbers are right and they are
    not the same quantity:

      * `0.45` is their MECHANISM's parameter -- a single Gaussian at `sigma ~ 2.2` gives
        `sqrt(1)/2.2 = 0.4545`. It satisfies `(1, 1e-2)`-DP with room to spare:
        `delta_for_mu(0.45, 1) = 0.0033`, well under `1e-2`.
      * `0.5325` is the largest `mu` consistent with the released pair.

    So **this function does not reproduce their 0.45 and must not be presented as doing so.**
    Use `mu_from_gaussian_composition` when the noise multiplier is known; fall back to this
    only when all that is available is a released `(eps, delta)`, and label it as the
    conservative comparator that it is.

    Solved by bisection: `delta_for_mu` is monotone increasing in `mu` at fixed `eps`.

    Raises:
        ValueError: if the target cannot be bracketed, rather than returning a wrong number.
    """
    if eps < 0:
        raise ValueError(f"epsilon must be non-negative, got {eps}")
    if not (0.0 < delta < 1.0):
        raise ValueError(f"delta must be in (0, 1), got {delta}")

    lo, hi = 1e-9, 1.0
    while delta_for_mu(hi, eps) < delta:
        hi *= 2.0
        if hi > 1e6:
            raise ValueError(
                f"Cannot bracket mu for (eps={eps}, delta={delta}). The requested delta is "
                "larger than any GDP mechanism attains at this epsilon."
            )
    return float(optimize.brentq(lambda m: delta_for_mu(m, eps) - delta, lo, hi, xtol=1e-10))


def mu_from_rates(fpr: float, fnr: float) -> float:
    """Point estimate of `mu` from one (FPR, FNR) operating point.

    `mu = Phi^-1(1 - FPR) - Phi^-1(FNR)`, the GDP tradeoff curve rearranged.

    Returns 0.0 when the point is at or above the diagonal (the adversary did no better than
    guessing). A negative `mu` is not meaningful as a privacy lower bound and is clamped rather
    than reported, because a negative lower bound would read as evidence of MORE privacy than
    the mechanism has.
    """
    if not (0.0 <= fpr <= 1.0 and 0.0 <= fnr <= 1.0):
        raise ValueError(f"FPR and FNR must be probabilities, got ({fpr}, {fnr})")
    if fpr <= 0.0 or fnr <= 0.0:
        # A zero rate makes Phi^-1 infinite. The caller should pass CONFIDENCE-CORRECTED rates
        # (see `mu_lower_bound`), which are never exactly zero; an uncorrected zero here means
        # an unbounded estimate from finite data, which is exactly the instability this module
        # exists to avoid.
        raise ValueError(
            "FPR or FNR is exactly zero, which makes the estimate unbounded. Pass "
            "confidence-corrected rates -- use `mu_lower_bound`, not this function, on raw counts."
        )
    return max(0.0, float(_PHI_INV(1.0 - fpr) - _PHI_INV(fnr)))


def _clopper_pearson_upper(successes: int, trials: int, alpha: float) -> float:
    """One-sided upper confidence bound on a binomial rate."""
    if trials <= 0:
        return 1.0
    if successes >= trials:
        return 1.0
    return float(stats.beta.ppf(1.0 - alpha, successes + 1, trials - successes))


@dataclass
class GDPAuditResult:
    """One audited operating point, with everything needed to check it."""

    mu_emp: float
    fpr: float
    fnr: float
    fpr_upper: float
    fnr_upper: float
    threshold: float
    n_positive: int
    n_negative: int
    alpha: float
    implied_mu: Optional[float] = None
    proved_eps: Optional[float] = None
    delta: Optional[float] = None

    @property
    def is_informative(self) -> bool:
        """False when the audit could not distinguish the two worlds at all."""
        return self.mu_emp > 0.0

    @property
    def exceeds_implied(self) -> bool:
        """True when the empirical mu EXCEEDS what the proof allows.

        This is the outcome that matters most: a lower bound above the implied bound is
        evidence of a VIOLATION -- either in the mechanism, the accounting, or this audit.
        It must never be reported as a good result.
        """
        return self.implied_mu is not None and self.mu_emp > self.implied_mu


def mu_lower_bound(
    scores_in: Sequence[float],
    scores_out: Sequence[float],
    alpha: float = DEFAULT_ALPHA,
    thresholds: Optional[Sequence[float]] = None,
) -> GDPAuditResult:
    """Best-supported `mu` lower bound over all thresholds on the adversary's scores.

    Args:
        scores_in: Adversary scores from runs where the target record WAS present.
        scores_out: Scores from runs where it was ABSENT.
        alpha: One-sided error probability. Split across the two rates by Bonferroni, so the
            reported bound holds jointly at `alpha`.
        thresholds: Candidate thresholds. Defaults to every midpoint between observed scores.

    Returns:
        The `GDPAuditResult` with the largest `mu_emp`.

    The confidence correction is what makes this a LOWER BOUND rather than a point estimate:
    FPR and FNR are each replaced by a one-sided upper confidence bound, so the resulting `mu`
    is the smallest the data supports. Taking the maximum over thresholds is why a single
    unlucky threshold cannot collapse the result to zero -- the failure mode Ganev et al.
    identify as the cause of published `eps_emp = 0` results.
    """
    a = np.asarray(scores_in, dtype=float)
    b = np.asarray(scores_out, dtype=float)
    if a.size == 0 or b.size == 0:
        raise ValueError("Both score sets must be non-empty.")

    grid: np.ndarray
    if thresholds is None:
        allv = np.unique(np.concatenate([a, b]))
        grid = (
            (allv[:-1] + allv[1:]) / 2.0
            if allv.size > 1
            else np.array([allv[0] - 1e-9, allv[0] + 1e-9])
        )
    else:
        grid = np.atleast_1d(np.asarray(thresholds, dtype=float))

    half = alpha / 2.0
    best: Optional[GDPAuditResult] = None
    for t in grid:
        # Predict "in" when score > t.
        fp = int(np.sum(b > t))  # out-runs called in
        fn = int(np.sum(a <= t))  # in-runs called out
        fpr_u = _clopper_pearson_upper(fp, b.size, half)
        fnr_u = _clopper_pearson_upper(fn, a.size, half)
        if fpr_u >= 1.0 or fnr_u >= 1.0:
            continue
        mu = max(0.0, float(_PHI_INV(1.0 - fpr_u) - _PHI_INV(fnr_u)))
        if best is None or mu > best.mu_emp:
            best = GDPAuditResult(
                mu_emp=mu,
                fpr=fp / b.size,
                fnr=fn / a.size,
                fpr_upper=fpr_u,
                fnr_upper=fnr_u,
                threshold=float(t),
                n_positive=int(a.size),
                n_negative=int(b.size),
                alpha=alpha,
            )

    if best is None:
        # Every threshold left a rate at its trivial bound. Report a zero explicitly rather
        # than raising: "the audit could not distinguish the worlds" is a result.
        best = GDPAuditResult(
            mu_emp=0.0,
            fpr=float("nan"),
            fnr=float("nan"),
            fpr_upper=1.0,
            fnr_upper=1.0,
            threshold=float("nan"),
            n_positive=int(a.size),
            n_negative=int(b.size),
            alpha=alpha,
        )
    return best


def audit_against_proof(
    scores_in: Sequence[float],
    scores_out: Sequence[float],
    proved_eps: float,
    delta: float,
    alpha: float = DEFAULT_ALPHA,
) -> GDPAuditResult:
    """`mu_lower_bound`, annotated with the mu the proved `(eps, delta)` implies."""
    res = mu_lower_bound(scores_in, scores_out, alpha=alpha)
    res.implied_mu = mu_from_eps_delta(proved_eps, delta)
    res.proved_eps = float(proved_eps)
    res.delta = float(delta)
    return res


def max_provable_mu(n_positive: int, n_negative: int, alpha: float = DEFAULT_ALPHA) -> float:
    """Ceiling: the largest `mu` this many runs could certify against a PERFECT adversary.

    The GDP analogue of `steinke.max_provable_epsilon`, and it exists for the same reason: an
    audited number is uninterpretable without the range the instrument could have reported.
    A perfect adversary makes zero errors, so the bound is set entirely by the confidence
    correction on two zero counts.

    **NOT OURS, AND NOT NOVEL.** This is `mu_lower_bound`'s published estimator with both error
    counts set to zero -- a one-line substitution. Attributions, all verified 2026-09-03:

      * The estimator: Koskela & Mohammadi, SaTML 2025 ([arXiv:2406.04827](https://arxiv.org/abs/2406.04827)),
        `mu_emp = Phi^-1(1 - alpha_bar) - Phi^-1(beta_bar)` with Clopper-Pearson or Jeffreys
        upper bounds on the two rates.
      * The ceiling in mu-GDP: Mitchell, Andrew, Ganesh, McMahan & Kairouz,
        [arXiv:2606.10481](https://arxiv.org/abs/2606.10481) (Google, Jun 2026), verified from
        the full text: "We use n=3000 unique canaries per set, so the estimated mu of a perfect
        classifier is 7.17." (They use a Jeffreys point estimate; this uses a one-sided
        Clopper-Pearson confidence bound, so the two are not numerically identical.)
      * The ceiling in epsilon: Liu & Xiong, UniAud ([arXiv:2507.04457](https://arxiv.org/abs/2507.04457))
        S III-B; Heller & Fetaya ([arXiv:2110.05057](https://arxiv.org/abs/2110.05057)) S V-B;
        Zanella-Beguelin et al. ([arXiv:2206.05199](https://arxiv.org/abs/2206.05199)).

    What this project contributes is the RUNNABLE PRE-AUDIT TOOL (`synthproof audit-power
    --gdp`), not the quantity. Never present it as a finding -- this project already made
    exactly that mistake once with the canary ceiling, which turned out to be a corollary of
    Steinke et al. Thm 2.1.
    """
    half = alpha / 2.0
    fpr_u = _clopper_pearson_upper(0, n_negative, half)
    fnr_u = _clopper_pearson_upper(0, n_positive, half)
    if fpr_u >= 1.0 or fnr_u >= 1.0:
        return 0.0
    return max(0.0, float(_PHI_INV(1.0 - fpr_u) - _PHI_INV(fnr_u)))


def runs_needed_for_mu(mu: float, alpha: float = DEFAULT_ALPHA) -> int:
    """Runs per world needed before `mu` is certifiable at all, against a perfect adversary."""
    if mu <= 0:
        return 0
    n = 8
    while n < 10_000_000:
        if max_provable_mu(n, n, alpha) >= mu:
            return n
        n = int(n * 1.5) + 1
    raise ValueError(f"mu = {mu} is not reachable below 10M runs per world at alpha = {alpha}.")


def tradeoff_curve(mu: float, points: int = 101) -> List[Tuple[float, float]]:
    """The theoretical (FPR, FNR) curve of a `mu`-GDP mechanism, for plotting against data."""
    fprs = np.linspace(1e-4, 1 - 1e-4, points)
    return [(float(f), float(_PHI(_PHI_INV(1.0 - f) - mu))) for f in fprs]
