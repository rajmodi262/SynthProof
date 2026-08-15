"""Turning a null audit result into a bounded one.

THE PROBLEM WITH "WE FOUND NOTHING". H2 reports no significant per-subgroup leakage. On its
own that is uninformative: failing to reject the null is consistent with "there is no effect"
AND with "the study could not have found one". Those are very different claims, and only the
second is true here — the auditor's ceiling at 80 canaries per subgroup is 3.27, and the
largest observed bound was 0.036.

This module supplies the three things that convert a bare null into a defensible one:

  1. **Multiplicity control.** H2 runs 20 tests (5 subgroups x 2 epsilons x 2 attributes). At
     alpha = 0.05 one false positive is expected by chance. Benjamini-Hochberg controls the
     false discovery rate; Bonferroni controls the family-wise error rate and is reported
     alongside as the conservative comparison.

  2. **Equivalence testing (TOST).** Two one-sided tests let us conclude *positively* that an
     effect lies within +/- delta of chance, rather than merely failing to detect one. Lakens
     (2017). The equivalence bound must be justified BEFORE looking at the result — choosing
     it afterwards to obtain significance inverts the logic and inflates Type-I error.

  3. **Minimum detectable effect.** What is the smallest leakage this instrument could have
     found? Without it, "no effect detected" cannot be distinguished from "no power".

WHERE THE EQUIVALENCE BOUND COMES FROM, and why it is not post-hoc. The detection-floor study
(results/DETECTION_FLOOR.md) measured, on a mechanism with KNOWN leakage and before any H2
analysis, that this auditor cannot resolve leakage below roughly 25% verbatim copying at the
canary counts in use. The equivalence bound is set from that measured floor, not from the H2
data. It is a property of the instrument, established independently of the result it is used
to interpret.
"""

import math
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

import numpy as np
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.weightstats import ttost_ind

DEFAULT_ALPHA = 0.05


# --------------------------------------------------------------------------- multiplicity

@dataclass
class MultiplicityResult:
    """Raw and corrected p-values for a family of tests."""

    labels: List[str]
    raw_p: List[float]
    bh_p: List[float]              # Benjamini-Hochberg, controls FDR
    bonferroni_p: List[float]      # controls FWER; strictly more conservative
    bh_reject: List[bool]
    bonferroni_reject: List[bool]
    alpha: float

    @property
    def num_tests(self) -> int:
        return len(self.raw_p)

    @property
    def expected_false_positives(self) -> float:
        """How many raw p < alpha we would expect from chance alone."""
        return self.alpha * self.num_tests

    def summary(self) -> str:
        n_raw = sum(p < self.alpha for p in self.raw_p)
        n_bh = sum(self.bh_reject)
        n_bonf = sum(self.bonferroni_reject)
        return (
            f"{self.num_tests} tests at alpha={self.alpha}. Raw p<alpha: {n_raw} "
            f"(chance alone predicts {self.expected_false_positives:.1f}). "
            f"Surviving BH-FDR: {n_bh}. Surviving Bonferroni: {n_bonf}."
        )


def correct_multiplicity(labels: Sequence[str], pvals: Sequence[float],
                         alpha: float = DEFAULT_ALPHA) -> MultiplicityResult:
    """Applies Benjamini-Hochberg and Bonferroni to a family of p-values.

    `method` is passed explicitly in both calls. `multipletests` defaults to Holm-Sidak
    ('hs'), so relying on the default would silently apply a third procedure neither of these
    names describes.
    """
    p = list(pvals)
    if not p:
        return MultiplicityResult(list(labels), [], [], [], [], [], alpha)

    bh_reject, bh_p, _, _ = multipletests(p, alpha=alpha, method="fdr_bh")
    bonf_reject, bonf_p, _, _ = multipletests(p, alpha=alpha, method="bonferroni")

    return MultiplicityResult(
        labels=list(labels),
        raw_p=p,
        bh_p=[float(x) for x in bh_p],
        bonferroni_p=[float(x) for x in bonf_p],
        bh_reject=[bool(x) for x in bh_reject],
        bonferroni_reject=[bool(x) for x in bonf_reject],
        alpha=alpha,
    )


# --------------------------------------------------------------------------- equivalence

@dataclass
class EquivalenceResult:
    """TOST outcome for one comparison."""

    label: str
    observed: float
    bound: float                   # the +/- equivalence margin
    p_value: float                 # TOST p; < alpha means statistically EQUIVALENT
    equivalent: bool
    bound_justification: str
    n: int

    def interpretation(self) -> str:
        if self.equivalent:
            return (
                f"{self.label}: statistically equivalent to chance within +/-{self.bound:.3f} "
                f"(TOST p={self.p_value:.4f}). This is a positive claim of no meaningful "
                "effect, not merely a failure to detect one."
            )
        return (
            f"{self.label}: NOT shown equivalent within +/-{self.bound:.3f} "
            f"(TOST p={self.p_value:.4f}). The data neither establish an effect nor rule "
            "one out at this margin — the honest reading is that the study is underpowered "
            "for this comparison."
        )


def test_equivalence(label: str, sample: Sequence[float], reference: Sequence[float],
                     bound: float, justification: str,
                     alpha: float = DEFAULT_ALPHA) -> EquivalenceResult:
    """Two one-sided tests that `sample` lies within +/-`bound` of `reference`.

    Args:
        bound: The equivalence margin. MUST be justified independently of this data — see
            the module docstring. `justification` is stored with the result so the reasoning
            travels with the number.
    """
    x = np.asarray([v for v in sample if np.isfinite(v)], dtype=float)
    y = np.asarray([v for v in reference if np.isfinite(v)], dtype=float)
    if len(x) < 2 or len(y) < 2:
        return EquivalenceResult(label, float("nan"), bound, 1.0, False,
                                 justification, len(x))

    p, _, _ = ttost_ind(x, y, -bound, bound)
    return EquivalenceResult(
        label=label,
        observed=float(x.mean() - y.mean()),
        bound=bound,
        p_value=float(p),
        equivalent=bool(p < alpha),
        bound_justification=justification,
        n=len(x),
    )


# --------------------------------------------------------------------------- power / MDE

@dataclass
class DetectabilityReport:
    """What this instrument could and could not have found."""

    num_canaries: int
    alpha: float
    ceiling: float                    # max certifiable epsilon at this canary count
    mde_epsilon: float                # smallest epsilon a majority-seed detection could show
    mde_accuracy: float               # adversary accuracy needed to reach it
    observed_max_epsilon: float
    observed_max_accuracy: float
    fraction_of_range_used: float

    def interpretation(self) -> str:
        return (
            f"With m={self.num_canaries} guesses at alpha={self.alpha}, the smallest "
            f"detectable audited epsilon is {self.mde_epsilon:.3f} (requiring adversary "
            f"accuracy {self.mde_accuracy:.3f}), and the largest certifiable value is "
            f"{self.ceiling:.2f}. The largest observed bound was "
            f"{self.observed_max_epsilon:.3f} at accuracy "
            f"{self.observed_max_accuracy:.3f} — {self.fraction_of_range_used:.1%} of the "
            "instrument's range. A null at this scale bounds the effect; it does not "
            "establish its absence."
        )


def minimum_detectable_epsilon(num_guesses: int, alpha: float = DEFAULT_ALPHA) -> tuple:
    """Smallest audited epsilon this many guesses could yield, and the accuracy it needs.

    Walks the correct-guess count upward until the binomial tail first clears alpha, then
    converts. Returns (epsilon, accuracy). This is the floor of the instrument's dynamic
    range, as the ceiling is its top.
    """
    from synthproof.audit.steinke import epsilon_lower_bound

    for correct in range(num_guesses // 2, num_guesses + 1):
        eps = epsilon_lower_bound(correct, num_guesses, alpha=alpha)
        if eps > 0.0:
            return eps, correct / num_guesses
    return float("inf"), 1.0


def describe_detectability(num_canaries: int, observed_epsilons: Sequence[float],
                           observed_accuracies: Sequence[float],
                           alpha: float = DEFAULT_ALPHA) -> DetectabilityReport:
    """Places the observed results inside the instrument's measured dynamic range."""
    from synthproof.audit.steinke import max_provable_epsilon

    ceiling = max_provable_epsilon(num_canaries, alpha)
    mde_eps, mde_acc = minimum_detectable_epsilon(num_canaries, alpha)
    obs_eps = max(observed_epsilons) if observed_epsilons else 0.0
    obs_acc = max(observed_accuracies) if observed_accuracies else 0.5

    return DetectabilityReport(
        num_canaries=num_canaries,
        alpha=alpha,
        ceiling=ceiling,
        mde_epsilon=mde_eps,
        mde_accuracy=mde_acc,
        observed_max_epsilon=obs_eps,
        observed_max_accuracy=obs_acc,
        fraction_of_range_used=(obs_eps / ceiling) if ceiling > 0 else 0.0,
    )


# --------------------------------------------------------------------------- bound choice

# Equivalence margin for the H2 subgroup analysis, in units of adversary ACCURACY (0.5 is
# chance). Derived from the detection-floor study, which measured — before any H2 analysis —
# that this auditor does not reliably resolve leakage below ~25% verbatim copying. At the
# canary counts H2 uses, that corresponds to an accuracy excursion of roughly this size.
#
# Stated as a constant with its derivation so the choice is auditable and cannot drift into
# being tuned against the result.
H2_EQUIVALENCE_BOUND_ACCURACY = 0.10
H2_BOUND_JUSTIFICATION = (
    "Set from the measured detection floor (results/DETECTION_FLOOR.md), which established "
    "before any H2 analysis that leakage below ~25% verbatim copying is not reliably "
    "resolved at these canary counts. An accuracy margin of 0.10 around chance is the "
    "corresponding excursion. Chosen a priori from instrument properties, not from the H2 "
    "data."
)


@dataclass
class H2Analysis:
    """The complete reframed H2 result."""

    multiplicity: MultiplicityResult
    equivalence: List[EquivalenceResult] = field(default_factory=list)
    detectability: Optional[DetectabilityReport] = None

    def verdict(self) -> str:
        """One paragraph stating what the analysis does and does not establish."""
        n_bh = sum(self.multiplicity.bh_reject)
        n_equiv = sum(e.equivalent for e in self.equivalence)
        n_tested = len(self.equivalence)

        lines = [self.multiplicity.summary()]
        if n_bh == 0:
            lines.append(
                "No subgroup shows significant leakage after FDR control, so H2 is NOT "
                "supported."
            )
        else:
            lines.append(f"{n_bh} subgroup(s) survive FDR control; H2 is partially supported.")

        if n_tested:
            lines.append(
                f"{n_equiv} of {n_tested} comparisons are statistically EQUIVALENT to chance "
                f"within the pre-specified margin — a positive bound on the effect rather "
                "than an absence of evidence."
            )
        if self.detectability:
            lines.append(self.detectability.interpretation())
        return " ".join(lines)

    def to_dict(self) -> dict:
        return {
            "multiplicity": {
                "labels": self.multiplicity.labels,
                "raw_p": self.multiplicity.raw_p,
                "bh_p": self.multiplicity.bh_p,
                "bonferroni_p": self.multiplicity.bonferroni_p,
                "bh_reject": self.multiplicity.bh_reject,
                "bonferroni_reject": self.multiplicity.bonferroni_reject,
                "num_tests": self.multiplicity.num_tests,
                "expected_false_positives": self.multiplicity.expected_false_positives,
                "summary": self.multiplicity.summary(),
            },
            "equivalence": [
                {"label": e.label, "observed": e.observed, "bound": e.bound,
                 "p_value": e.p_value, "equivalent": e.equivalent, "n": e.n,
                 "justification": e.bound_justification,
                 "interpretation": e.interpretation()}
                for e in self.equivalence
            ],
            "detectability": (
                {**self.detectability.__dict__,
                 "interpretation": self.detectability.interpretation()}
                if self.detectability else None
            ),
            "verdict": self.verdict(),
        }


def _fmt(x: float) -> str:
    return "—" if (x is None or (isinstance(x, float) and math.isnan(x))) else f"{x:.4f}"


def format_h2_table(analysis: H2Analysis) -> str:
    """Renders the reframed analysis for a terminal or a thesis table."""
    m = analysis.multiplicity
    lines = [f"{'comparison':<34}{'raw p':>9}{'BH p':>9}{'Bonf p':>9}{'BH sig':>8}"]
    for i, lab in enumerate(m.labels):
        lines.append(
            f"{lab:<34}{_fmt(m.raw_p[i]):>9}{_fmt(m.bh_p[i]):>9}"
            f"{_fmt(m.bonferroni_p[i]):>9}{str(m.bh_reject[i]):>8}"
        )
    lines.append("")
    lines.append(m.summary())
    if analysis.equivalence:
        lines.append("")
        for e in analysis.equivalence:
            lines.append(f"  {e.interpretation()}")
    if analysis.detectability:
        lines.append("")
        lines.append(f"  {analysis.detectability.interpretation()}")
    return "\n".join(lines)
