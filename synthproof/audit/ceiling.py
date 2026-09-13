"""One place to ask "what is the most this auditor could possibly have reported?".

WHY THIS MODULE EXISTS. An audited epsilon is uninterpretable without the reach of the instrument
that produced it. This project reported ``eps_audited = 0.000`` against ``eps_proved = 7.36`` and
read it as a fact about the mechanism; with 60 canaries at alpha = 0.05 the auditor could not have
exceeded **2.97** even against a release that was 100% verbatim training data. The zero was the
floor, not a finding.

THE HAZARD THIS MODULE IS BUILT TO PREVENT. There is more than one ceiling here, they are in
**different units**, and two of them are numerically close enough to look interchangeable:

    paired Clopper-Pearson (measured)   m=800 -> 5.377   epsilon
    one-run (closed form)               r=800 -> 5.586   epsilon
    GDP / f-DP (closed form)            runs  -> mu, NOT epsilon

Quoting the paired 5.377 next to the one-run 2.972 silently crosses instruments, and comparing a
mu-ceiling against an epsilon bound is a units error. Both are checkable by an examiner
recomputing a single cell, and this project has already made the first mistake once. So the only
supported way to obtain a ceiling is `ceiling_for`, which refuses anything it cannot source, and
returns a `Ceiling` that carries its own unit, estimator and provenance.

NONE OF THE UNDERLYING QUANTITIES ARE OURS. The one-run ceiling is a corollary of Steinke, Nasr &
Jagielski (2023) Thm 2.1 / Eq. (3). The concept has a published name in this exact sub-domain --
**"maximum auditable epsilon"**, Annamalai, Ganev & De Cristofaro, USENIX Security 2024
([arXiv:2405.10994](https://arxiv.org/abs/2405.10994)) S2.2, who also compute it numerically in
S7.5 for their own configuration. Keinan, Shenfeld & Ligett
([arXiv:2503.07199](https://arxiv.org/abs/2503.07199), NeurIPS 2025) Thm 5.2 formalise the maximum
achievable efficacy of one-run auditing. The GDP analogue's attributions are in
`gdp.max_provable_mu`. What this module contributes is that the quantity is **required, sourced
and unit-tagged at the point of release**, not that it exists.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional, Tuple

from synthproof.audit.gdp import max_provable_mu
from synthproof.audit.steinke import DEFAULT_ALPHA, max_provable_epsilon

__all__ = [
    "Ceiling",
    "ESTIMATORS",
    "RangeVerdict",
    "ceiling_for",
    "measured_paired_budgets",
    "range_verdict",
    "recompute_ceiling",
]


#: The estimator families this project can source a ceiling for. Anything else must raise,
#: because a guessed ceiling is worse than an absent one -- it is a wrong number that looks right.
ESTIMATORS: Tuple[str, ...] = ("one_run", "paired_cp", "gdp")


# The paired Clopper-Pearson series is MEASURED, not closed-form: it is the audited epsilon this
# project's paired auditor actually returned against a fully verbatim release (leak_fraction=1.0),
# which is the empirical definition of "the most it could report". Copied from the committed
# results/detection_floor.json (dataset uci_adult, rows 3000, alpha 0.05, 5 seeds per cell).
# There is deliberately NO interpolation: a budget that was not measured has no measured ceiling.
_PAIRED_CP_MEASURED_ALPHA = 0.05
_PAIRED_CP_MEASURED: Dict[int, float] = {
    10: 0.807154865248952,
    25: 1.8388684705889868,
    50: 2.5695846830164917,
    100: 3.2813463490987878,
    200: 3.983758252165089,
    400: 4.681527163123462,
    800: 5.376982551119489,
}
_PAIRED_CP_SOURCE = "results/detection_floor.json (leak_fraction=1.0, uci_adult, n=3000, 5 seeds)"


@dataclass(frozen=True)
class Ceiling:
    """The most an auditor could have reported, with everything needed to not misuse it.

    `unit` is load-bearing. A `mu` ceiling must never be compared against an epsilon bound, and
    `exceeds` refuses to try.
    """

    value: float
    unit: str  # "epsilon" | "mu"
    estimator: str
    budget: int
    alpha: float
    source: str
    measured: bool

    def exceeds(self, proved: float, proved_unit: str = "epsilon") -> bool:
        """True if the instrument could have confirmed `proved`. Refuses a units mismatch."""
        if proved_unit != self.unit:
            raise ValueError(
                f"units mismatch: ceiling is in {self.unit!r} but the bound is in "
                f"{proved_unit!r}. Convert explicitly, or audit in the same unit. Comparing a "
                f"mu-GDP ceiling against an epsilon bound is not a rounding error, it is a "
                f"different quantity."
            )
        return self.value >= proved

    def is_underpowered_for(self, proved: float, proved_unit: str = "epsilon") -> bool:
        """True if a null from this instrument says nothing about a mechanism proved at `proved`."""
        return not self.exceeds(proved, proved_unit)

    def describe(self) -> str:
        how = "measured" if self.measured else "closed form"
        return (
            f"{self.value:.4f} {self.unit} (estimator={self.estimator}, budget={self.budget}, "
            f"alpha={self.alpha}, {how}, source={self.source})"
        )


def measured_paired_budgets() -> Tuple[int, ...]:
    """The budgets at which a paired Clopper-Pearson ceiling was actually measured."""
    return tuple(sorted(_PAIRED_CP_MEASURED))


def ceiling_for(
    estimator: str,
    budget: int,
    alpha: float = DEFAULT_ALPHA,
    *,
    negatives: Optional[int] = None,
) -> Ceiling:
    """The ceiling for one estimator family, or an error. Never a guess.

    Args:
        estimator: one of `ESTIMATORS`. See the module docstring for why this cannot default.
        budget: canaries (`m`) for the canary estimators, or runs per world for `gdp`.
        alpha: confidence level of the reported lower bound.
        negatives: `gdp` only -- runs in the negative world, if it differs from `budget`.

    Raises:
        ValueError: on an unknown estimator, a non-positive budget, or -- for `paired_cp` -- a
            budget or alpha this project has not measured. Refusing is the point: an
            interpolated "measurement" is a fabricated number.
    """
    if estimator not in ESTIMATORS:
        raise ValueError(
            f"unknown estimator {estimator!r}; supported: {', '.join(ESTIMATORS)}. "
            f"A ceiling must be sourced to the estimator that produced the audit -- the series "
            f"are not interchangeable (see the module docstring)."
        )
    if budget < 1:
        raise ValueError(f"budget must be >= 1, got {budget}")
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha must be in (0, 1), got {alpha}")

    if estimator == "one_run":
        return Ceiling(
            value=max_provable_epsilon(budget, alpha),
            unit="epsilon",
            estimator="one_run",
            budget=budget,
            alpha=alpha,
            source="steinke.max_provable_epsilon (corollary of Steinke et al. Thm 2.1)",
            measured=False,
        )

    if estimator == "paired_cp":
        if alpha != _PAIRED_CP_MEASURED_ALPHA:
            raise ValueError(
                f"the paired Clopper-Pearson ceiling is MEASURED, only at "
                f"alpha={_PAIRED_CP_MEASURED_ALPHA}; got alpha={alpha}. Re-run "
                f"scripts/run_detection_floor.py at that alpha, or use estimator='one_run', "
                f"whose ceiling is closed form."
            )
        if budget not in _PAIRED_CP_MEASURED:
            raise ValueError(
                f"no measured paired ceiling at budget={budget}; measured at "
                f"{measured_paired_budgets()}. This series is not interpolated -- an "
                f"interpolated measurement is a fabricated number."
            )
        return Ceiling(
            value=_PAIRED_CP_MEASURED[budget],
            unit="epsilon",
            estimator="paired_cp",
            budget=budget,
            alpha=alpha,
            source=_PAIRED_CP_SOURCE,
            measured=True,
        )

    # estimator == "gdp"
    neg = budget if negatives is None else negatives
    if neg < 1:
        raise ValueError(f"negatives must be >= 1, got {neg}")
    return Ceiling(
        value=max_provable_mu(budget, neg, alpha),
        unit="mu",
        estimator="gdp",
        budget=budget,
        alpha=alpha,
        source="gdp.max_provable_mu (Koskela & Mohammadi SaTML 2025 estimator, zero errors)",
        measured=False,
    )


# =============================================================================================
# Could this audit have certified this claim?
# =============================================================================================
#
# ONE verdict, used by the capsule, the CLI, the API and (through the API) the console. Until
# 2026-09-13 each of those four surfaces carried its own copy of a check that was WRONG in the
# direction that matters most for this project:
#
#   `lod_safe = audited_eps < audit_ceiling`, rendered as a green tick, "NOT DETECTED (< LoD)",
#   and in the capsule "Bounded under MIQE 2.0".
#
# Three defects in one line. (1) It never compared the PROVED epsilon with the ceiling, which
# is the comparison this project's central finding is about -- a sheet proving eps = 7.36
# against a ceiling of 2.97 came out green. (2) The ceiling is an UPPER limit on what an audit
# can certify, not a lower limit of detection, so an audited 1.5 under a 2.97 ceiling is a
# detection, yet it was labelled "not detected". (3) A field named `safe` presented absence of
# evidence as assurance -- the "privacy theater" failure Dibia et al.'s experts describe, in the
# artefact built to answer it. And nothing checked that the reported ceiling was the one the
# declared audit produces, which is how two demo capsules shipped signed with invented ceilings.

_TOL = 1e-9


@dataclass(frozen=True)
class RangeVerdict:
    """What an (eps_proved, eps_audited, ceiling) triple does and does not support.

    `tone` is for colour only: "ok", "warn" or "fail". There is deliberately no field called
    `safe` -- no outcome of this function is a statement that a release is safe.
    """

    code: str
    label: str
    tone: str
    claim_in_audit_range: bool
    explanation: str
    recomputed_ceiling: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def recompute_ceiling(
    estimator: Optional[str], budget: Optional[int], alpha: Optional[float]
) -> Optional[float]:
    """The epsilon ceiling the declared audit actually produces, or None if it cannot be derived.

    None is returned -- not raised -- for an absent field, an unmeasured paired budget, or a
    mu-GDP audit, because "cannot recompute" is a different outcome from "does not match" and a
    verifier must be able to report the two separately.
    """
    if estimator is None or budget is None or alpha is None:
        return None
    try:
        c = ceiling_for(str(estimator), int(budget), float(alpha))
    except (TypeError, ValueError):
        return None
    return c.value if c.unit == "epsilon" else None


def range_verdict(
    proved: Optional[float],
    audited: Optional[float],
    ceiling: Optional[float],
    *,
    estimator: Optional[str] = None,
    budget: Optional[int] = None,
    alpha: Optional[float] = None,
    rel_tol: float = 1e-6,
) -> RangeVerdict:
    """Classifies a release's audit against its own claim. Checks run in priority order.

    1. audited > proved       -> the lower bound exceeds the upper bound; one of them is wrong.
    2. gdp estimator          -> the ceiling is in mu and cannot be compared with an epsilon.
    3. ceiling != recomputed  -> the reported ceiling is not the one the declared audit gives.
    4. no ceiling             -> the audited value is uninterpretable.
    5. no proved epsilon      -> nothing to compare the audit with.
    6. proved > ceiling       -> the audit could not have certified the claim (H1's situation).
    7. in range, audited 0    -> nothing detected, within the audit's reach.
    8. in range, audited > 0  -> audit and proof are consistent.
    """
    if proved is not None and audited is not None and audited > proved + _TOL:
        return RangeVerdict(
            "AUDIT_CONTRADICTS_PROOF",
            "AUDIT EXCEEDS PROOF",
            "fail",
            False,
            f"The audit's lower bound (audited ε = {audited:.3f}) is larger than the proved upper "
            f"bound (ε = {proved:.3f}). Both cannot hold: either the privacy accounting or the "
            "audit is wrong, and the release should not be relied on until that is resolved.",
        )

    if estimator == "gdp":
        return RangeVerdict(
            "CEILING_UNITS",
            "CEILING IN μ, NOT ε",
            "warn",
            False,
            "This is a μ-GDP audit, so its ceiling is in μ. Comparing it with an ε bound is a "
            "units error, not a rounding difference; convert explicitly.",
        )

    recomputed = recompute_ceiling(estimator, budget, alpha)
    if (
        recomputed is not None
        and ceiling is not None
        and not math.isclose(ceiling, recomputed, rel_tol=rel_tol, abs_tol=_TOL)
    ):
        return RangeVerdict(
            "CEILING_MISMATCH",
            "CEILING DOES NOT MATCH ITS AUDIT",
            "fail",
            False,
            f"The sheet reports an audit ceiling of {ceiling:.3f}, but a {estimator} audit with a "
            f"budget of {budget} at α = {alpha} can certify at most {recomputed:.3f}. The reported "
            "ceiling is not the one this audit produces, so no judgement about the audit's reach "
            "can be made from it.",
            recomputed,
        )

    if ceiling is None or ceiling <= _TOL:
        return RangeVerdict(
            "NO_CEILING",
            "NO CEILING REPORTED",
            "warn",
            False,
            "No audit ceiling is reported, so the audited value cannot be interpreted: a zero "
            "could mean no leakage, or an instrument that could not have seen any.",
            recomputed,
        )

    if proved is None:
        return RangeVerdict(
            "NO_CLAIM",
            "NO PROVED ε REPORTED",
            "warn",
            False,
            "The sheet carries an audit but no proved ε to compare it with.",
            recomputed,
        )

    if proved > ceiling + _TOL:
        shown = 0.0 if audited is None else audited
        return RangeVerdict(
            "CLAIM_EXCEEDS_AUDIT_RANGE",
            "CLAIM EXCEEDS AUDIT RANGE",
            "warn",
            False,
            f"The proved ε = {proved:.3f} is above the most this audit could certify "
            f"({ceiling:.3f}). The audit can neither confirm nor refute the claim: an audited "
            f"value of {shown:.3f} is not evidence that the claim is tight, and a zero is not "
            "evidence of no leakage.",
            recomputed,
        )

    if audited is None or audited <= _TOL:
        return RangeVerdict(
            "IN_RANGE_NOT_DETECTED",
            "IN RANGE · NOT DETECTED",
            "ok",
            True,
            f"The audit could certify up to ε = {ceiling:.3f}, which covers the claim "
            f"(ε = {proved:.3f}), and it detected no leakage. That is absence of evidence within "
            "the audit's reach, not proof of absence: the auditor's detection floor still limits "
            "how small a leak it could see.",
            recomputed,
        )

    return RangeVerdict(
        "IN_RANGE_CONSISTENT",
        "IN RANGE · CONSISTENT",
        "ok",
        True,
        f"The audit could certify up to ε = {ceiling:.3f}, covering the claim (ε = {proved:.3f}), "
        f"and its lower bound (audited ε = {audited:.3f}) does not exceed the proof. Audit and "
        "proof agree.",
        recomputed,
    )
