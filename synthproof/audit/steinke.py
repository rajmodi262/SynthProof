"""One-run privacy audit after Steinke, Nasr & Jagielski (2023).

WHY THIS REPLACES THE PAIRED AUDITOR. `audit/canary.py` splits canaries into a planted group
and a held-out group, estimates TPR and FPR separately, and reports
``log(TPR_lower / FPR_upper)`` from two Clopper-Pearson intervals. That works, but it spends
two canaries to learn about one and the two intervals compound, so the bound saturates early:
measured ceiling 2.57 at m=50 and only 5.38 at m=800 (see results/DETECTION_FLOOR.md).

The one-run construction instead includes **each canary independently at random**, trains once,
and derives epsilon from a single binomial tail over the adversary's correct guesses. Every
canary carries a bit of evidence, and there is one interval rather than two.

THE ESTIMATOR. Under epsilon-DP, an adversary guessing the membership of a single canary is
correct with probability at most

    p(eps) = e^eps / (1 + e^eps)

which is the randomised-response view of the guarantee. Guesses over independently included
canaries are (conditionally) independent, so with `r` guesses and `v` correct we can reject the
hypothesis "this mechanism is eps-DP" at level alpha whenever

    P[Binomial(r, p(eps)) >= v] <= alpha

`p` is increasing in eps, so the tail probability is too, and the rejectable set is an interval
[0, eps*]. The audited lower bound is that eps* — the largest epsilon the evidence rules out.

THE CEILING IS INFORMATION-THEORETIC, NOT AN IMPLEMENTATION LIMIT. With a *perfect* adversary
(v = r) the bound solves p^r = alpha, giving

    eps_max(r) = log( a / (1 - a) ),   a = alpha^(1/r)

which for large r is approximately ``log(r / ln(1/alpha))``. Certifying a given epsilon
therefore needs roughly ``ln(1/alpha) * e^eps`` canaries — **exponential in epsilon**. At
alpha = 0.05, proving eps = 7.36 requires about 4,700 perfectly-detected canaries. No canary
audit at the scales this project runs can certify epsilon anywhere near its proved bound, and
that is a property of auditing rather than of our code. `max_provable_epsilon` computes it, and
every result reports it alongside the estimate.

DEVIATIONS FROM THE PAPER, stated rather than glossed:

  * Delta is handled by a union bound (``alpha_effective = alpha - r*delta``) rather than the
    paper's tighter treatment. At delta = 1e-5 and r = 60 the correction is 6e-4 against an
    alpha of 0.05, so it costs almost nothing and is conservative in the safe direction.
  * The adversary is the same nearest-neighbour similarity score used by the paired auditor,
    not a mechanism-specific one. A stronger adversary would raise the audited epsilon; this
    bound is therefore a lower bound on a lower bound.
"""

import math
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats

from synthproof.audit.canary import CanaryAuditor
from synthproof.data.dataset import TabularDataset

DEFAULT_ALPHA = 0.05


# --------------------------------------------------------------------------- the estimator

def _p_correct(eps: float) -> float:
    """Max per-guess success probability under eps-DP (randomised-response view)."""
    return math.exp(eps) / (1.0 + math.exp(eps))


def max_provable_epsilon(num_guesses: int, alpha: float = DEFAULT_ALPHA) -> float:
    """Largest epsilon this many guesses could ever certify, with a PERFECT adversary.

    Solves ``p^r = alpha``. This is the instrument's ceiling: an audit reporting a value at
    or near it is saturated, and the true epsilon may be far higher.
    """
    if num_guesses < 1:
        return 0.0
    a = alpha ** (1.0 / num_guesses)
    if a >= 1.0:
        return float("inf")
    return math.log(a / (1.0 - a))


def canaries_needed_for(epsilon: float, alpha: float = DEFAULT_ALPHA) -> int:
    """Guesses required to certify `epsilon`, assuming a perfect adversary.

    Roughly ``ln(1/alpha) * e^epsilon`` — exponential in epsilon, which is why certifying a
    large proved bound by auditing is impractical rather than merely expensive.
    """
    if epsilon <= 0:
        return 1
    p = _p_correct(epsilon)
    return max(1, math.ceil(math.log(alpha) / math.log(p)))


def epsilon_lower_bound(correct: int, guesses: int, alpha: float = DEFAULT_ALPHA,
                        delta: float = 0.0, max_eps: float = 30.0) -> float:
    """Largest epsilon ruled out by `correct` correct guesses out of `guesses`.

    Returns 0.0 when the evidence rules out nothing — which is the honest answer, not a
    failure. Bisects on epsilon because the binomial tail is monotone in it.
    """
    if guesses <= 0 or correct <= 0:
        return 0.0
    correct = min(correct, guesses)

    # Union bound over guesses absorbs the delta term. If delta is large enough to consume
    # alpha outright, no epsilon can be rejected at this confidence.
    alpha_eff = alpha - guesses * delta
    if alpha_eff <= 0:
        return 0.0

    def rejects(eps: float) -> bool:
        """True when the observed count is too unlikely for this epsilon to hold."""
        return stats.binom.sf(correct - 1, guesses, _p_correct(eps)) <= alpha_eff

    if not rejects(0.0):
        return 0.0                      # even a perfectly private mechanism explains this
    if rejects(max_eps):
        return max_eps                  # saturated; report the cap rather than extrapolating

    lo, hi = 0.0, max_eps
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if rejects(mid):
            lo = mid
        else:
            hi = mid
    return lo


# --------------------------------------------------------------------------- results

@dataclass
class SteinkeResult:
    """Outcome of a one-run audit."""

    audited_eps: float          # epsilon lower bound from the confusion counts
    ceiling: float              # most this many guesses could ever certify
    saturated: bool             # the bound hit the ceiling, so the true value may be higher
    correct: int
    guesses: int
    abstained: int
    num_canaries: int
    num_included: int
    accuracy: float             # correct / guesses; 0.5 is chance
    alpha: float
    delta: float
    p_value: float              # P[at least this many correct | mechanism is perfectly private]

    def interpretation(self) -> str:
        """One sentence a reader can act on, rather than a bare number."""
        if self.audited_eps <= 0.0:
            return (
                f"No leakage detected. With {self.guesses} guesses the audit could have "
                f"certified at most eps={self.ceiling:.2f}, so this result rules out nothing "
                "above that and is consistent with any mechanism."
            )
        if self.saturated:
            return (
                f"Saturated at eps>={self.audited_eps:.2f}: the adversary was perfect, so the "
                f"true epsilon may be far higher. More canaries would be needed to say more."
            )
        return (
            f"Leakage detected: eps >= {self.audited_eps:.3f} at {1 - self.alpha:.0%} "
            f"confidence, against a ceiling of {self.ceiling:.2f} for {self.guesses} guesses."
        )


@dataclass
class OneRunCanarySet:
    """Canaries plus the randomised inclusion vector that decided which were planted."""

    canaries: pd.DataFrame
    included: np.ndarray        # bool[m]; True for canaries actually added to the training set

    @property
    def num_included(self) -> int:
        return int(self.included.sum())

    # `members` / `holdout` mirror the paired auditor's CanarySet so consumers that only need
    # "which canaries were planted" work with either. The meaning is not quite the same: here
    # the split is a random draw rather than a fixed partition, and every canary contributes
    # evidence, so `holdout` is "not planted" rather than "a control group".
    @property
    def members(self) -> pd.DataFrame:
        """Canaries that were actually planted into the training data."""
        return self.canaries.loc[self.included].reset_index(drop=True)

    @property
    def holdout(self) -> pd.DataFrame:
        """Canaries the inclusion draw left out."""
        return self.canaries.loc[~self.included].reset_index(drop=True)


# --------------------------------------------------------------------------- the auditor

class SteinkeAuditor:
    """Plants canaries under a randomised inclusion vector and audits from one run."""

    def __init__(self, num_canaries: int = 100, seed: int = 42,
                 alpha: float = DEFAULT_ALPHA, inclusion_prob: float = 0.5,
                 abstain_frac: float = 0.0):
        """
        Args:
            num_canaries: Total canaries generated. Unlike the paired auditor, ALL of them
                carry evidence — there is no held-out half.
            inclusion_prob: Probability each canary is planted. 0.5 maximises the information
                per canary.
            abstain_frac: Fraction of the middle-ranked canaries the adversary declines to
                guess on. Abstaining raises accuracy on the remainder but lowers `r`, and the
                ceiling falls with `r`, so the default guesses on everything.
        """
        if num_canaries < 2:
            raise ValueError(f"num_canaries must be >= 2, got {num_canaries}")
        if not (0.0 < inclusion_prob < 1.0):
            raise ValueError(f"inclusion_prob must be in (0, 1), got {inclusion_prob}")
        if not (0.0 <= abstain_frac < 1.0):
            raise ValueError(f"abstain_frac must be in [0, 1), got {abstain_frac}")

        self.num_canaries = num_canaries
        self.seed = seed
        self.alpha = alpha
        self.inclusion_prob = inclusion_prob
        self.abstain_frac = abstain_frac
        # Canary construction is shared with the paired auditor, so the two differ only in
        # the estimator and not in what a canary looks like.
        self._maker = CanaryAuditor(num_canaries=num_canaries, seed=seed)

    def plant_canaries(self, dataset: TabularDataset) -> Tuple[TabularDataset, OneRunCanarySet]:
        """Generates m canaries, includes each independently at random, and plants those."""
        rng = np.random.default_rng(self.seed)
        canaries = self._maker._make_canaries(dataset, self.num_canaries, rng)
        included = rng.random(self.num_canaries) < self.inclusion_prob

        # Degenerate draws carry no signal in one direction and make the audit meaningless.
        if included.all():
            included[int(rng.integers(0, self.num_canaries))] = False
        if not included.any():
            included[int(rng.integers(0, self.num_canaries))] = True

        planted = canaries.loc[included].reset_index(drop=True)
        augmented = pd.concat([dataset.df, planted], ignore_index=True)
        return (
            TabularDataset(df=augmented, name=f"{dataset.name}_canary",
                           schema=dataset.schema),
            OneRunCanarySet(canaries=canaries, included=included),
        )

    def audit(self, synthetic_df: pd.DataFrame,
              canary_set: OneRunCanarySet,
              delta: float = 0.0) -> SteinkeResult:
        """Scores every canary, guesses membership, and converts the count into an epsilon."""
        scores = self._maker._similarity_scores(canary_set.canaries, synthetic_df)
        m = len(scores)
        included = canary_set.included

        # Rank by score and guess the top half IN, the bottom half OUT. Ties are broken
        # stably, so the result does not depend on row order.
        order = np.argsort(-scores, kind="stable")
        n_abstain = int(round(m * self.abstain_frac))
        n_guess = m - n_abstain
        k_high = n_guess // 2
        k_low = n_guess - k_high

        guessed_in = order[:k_high]
        guessed_out = order[m - k_low:]

        correct = int(included[guessed_in].sum() + (~included[guessed_out]).sum())
        guesses = len(guessed_in) + len(guessed_out)

        eps = epsilon_lower_bound(correct, guesses, alpha=self.alpha, delta=delta)
        ceiling = max_provable_epsilon(guesses, self.alpha)

        return SteinkeResult(
            audited_eps=eps,
            ceiling=ceiling,
            saturated=eps > 0.0 and eps >= ceiling - 1e-6,
            correct=correct,
            guesses=guesses,
            abstained=m - guesses,
            num_canaries=m,
            num_included=canary_set.num_included,
            accuracy=correct / max(1, guesses),
            alpha=self.alpha,
            delta=delta,
            # Probability of doing this well by chance alone, i.e. against a mechanism that
            # reveals nothing. Reported so a null is legible without reading the epsilon.
            p_value=float(stats.binom.sf(correct - 1, guesses, 0.5)) if guesses else 1.0,
        )


def compare_auditors(num_canaries: int, alpha: float = DEFAULT_ALPHA) -> dict:
    """Ceilings of the two estimators at the same canary budget, for the results chapter.

    The paired auditor needs 2m canaries (m planted, m held out) to make m comparisons; the
    one-run construction uses all m. This reports what each can certify from the SAME total
    canary budget, which is the comparison that matters to a practitioner.
    """
    return {
        "num_canaries": num_canaries,
        "one_run_guesses": num_canaries,
        "one_run_ceiling": round(max_provable_epsilon(num_canaries, alpha), 4),
        "paired_effective_canaries": num_canaries // 2,
        "canaries_for_eps_1": canaries_needed_for(1.0, alpha),
        "canaries_for_eps_4": canaries_needed_for(4.0, alpha),
        "canaries_for_eps_8": canaries_needed_for(8.0, alpha),
    }


def default_delta_correction(guesses: int, delta: float,
                             alpha: float = DEFAULT_ALPHA) -> Optional[str]:
    """Warns when delta is large enough to matter against the chosen alpha."""
    if guesses * delta > 0.1 * alpha:
        return (
            f"delta={delta:g} over {guesses} guesses consumes "
            f"{guesses * delta / alpha:.0%} of alpha={alpha}. The union-bound correction is "
            "no longer negligible; the reported epsilon is conservative but loose."
        )
    return None
