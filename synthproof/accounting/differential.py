"""Differential accounting: check the release budget against a SECOND implementation.

WHY THIS EXISTS, AND WHY IT IS NOT PARANOIA. In February 2026 a grey-box audit of twelve
open-source differential privacy libraries -- SmartNoise SDK, Opacus and Diffprivlib among them
-- found thirteen violations of their stated guarantees (Cebere et al., "Privacy in Theory, Bugs
in Practice", arXiv 2602.17454). The field's response has been to audit the library. The
unexplored response is the one taken here: **do not rest a published privacy claim on a single
implementation.**

AND THE PERSON RECEIVING THE RELEASE WILL NOT CATCH IT. Song, Sarathy, Shoemate & Vadhan
(CSCW 2024, arXiv 2410.09721) interviewed 5 DP library developers and 17 data analysts and found
that practitioners do not verify DP guarantees at all -- they trust the library implicitly. Their
title is a participant quote: "I inherently just trust that it works." So the two facts compose:
implementations lose guarantees, and nobody downstream checks. A cross-check that runs at release
time and ships its verdict is the response to both.

This project already had the ingredients. `tests/test_accounting_properties.py` cross-checks
composition against `autodp` (Wang, Zhu & Dong) as a unit test. A test that runs in CI protects
the developers; it does not protect the person receiving the release, because nothing about the
released artefact records that the check was ever made. This module promotes that cross-check
from a test into a **release gate whose verdict travels inside the signed Privacy Data Sheet.**

THE ASYMMETRY THAT MAKES THIS SAFE TO ACT ON. Disagreement matters in only one direction.
Reporting MORE privacy loss than an independent implementation is conservative -- the release is
at least as private as claimed. Reporting LESS means the guarantee we publish is not one we can
support, which is exactly the failure that made the hand-rolled accountant unusable (audit
finding F4: the old subsampling bound under-reported epsilon by roughly 2x at q = 0.01).
So `UNDER_REPORT` is fatal and `CONSERVATIVE` is not.

WHAT THIS DOES NOT DO. Two implementations agreeing is evidence, not proof: they could share an
upstream error, and both delegate to the same underlying theory. It also cannot detect a
mechanism that is charged but never applied -- that is standing rule 3, enforced elsewhere. The
claim made here is narrow and is printed on the certificate as such: *two independent
accountants were asked, and this is what each said.*
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

from synthproof.accounting.calibration import epsilon_for_noise_scale

# Relative tolerance below which the two accountants are treated as agreeing. The measured
# spread across the CI grid is ~0.05%; 1% leaves room for their differing discretisation of the
# RDP order grid without admitting a real disagreement.
DEFAULT_TOLERANCE = 0.01

# Reporting slightly less than the reference is numerical noise, not a violation. Anything
# beyond this is treated as under-reporting and refused.
UNDER_REPORT_MARGIN = 0.999


# autodp's zoo covers both mechanism families this project charges. `b` for LaplaceMechanism and
# `sigma` for GaussianMechanism are both expressed in units of sensitivity, which is the same
# convention dp_accounting uses -- getting that wrong would manufacture a disagreement out of a
# unit error, so it is asserted by test_agreement_survives_a_sensitivity_other_than_one.
SUPPORTED_MECHANISMS = ("gaussian", "laplace")


def _autodp_mechanism(spec_name: str, noise_scale: float, sensitivity: float, index: int = 0):
    """Translate one charged mechanism into its autodp counterpart."""
    from autodp.mechanism_zoo import GaussianMechanism, LaplaceMechanism

    scaled = float(noise_scale) / float(sensitivity)
    if spec_name == "gaussian":
        return GaussianMechanism(sigma=scaled, name=f"g{index}")
    if spec_name == "laplace":
        return LaplaceMechanism(b=scaled, name=f"l{index}")
    raise ValueError(f"unsupported mechanism for cross-check: {spec_name}")


@dataclass(frozen=True)
class AccountantAgreement:
    """What two independent accountants said about the same release, and whether it ships."""

    primary: str
    primary_epsilon: float
    secondary: Optional[str]
    secondary_epsilon: Optional[float]
    relative_difference: Optional[float]
    tolerance: float
    verdict: str  # "agree" | "conservative" | "under_report" | "unavailable" | "unsupported"
    detail: str

    @property
    def blocks_release(self) -> bool:
        """Only under-reporting is fatal. See the module docstring for the asymmetry."""
        return self.verdict == "under_report"

    def to_dict(self) -> dict:
        return asdict(self)


class AccountantDisagreement(RuntimeError):
    """Raised when the second accountant says the release leaks more than we claim."""

    def __init__(self, agreement: AccountantAgreement):
        self.agreement = agreement
        super().__init__(agreement.detail)


def cross_check(
    noise_scale: float,
    target_delta: float,
    name: str = "gaussian",
    sensitivity: float = 1.0,
    steps: int = 1,
    tolerance: float = DEFAULT_TOLERANCE,
) -> AccountantAgreement:
    """Compose the same release through `dp_accounting` and `autodp`, and compare.

    Never raises for a missing or incapable second accountant -- absence of a check is
    reported as `unavailable`/`unsupported` rather than being silently dropped or mistaken
    for agreement. Only `verdict == "under_report"` should stop a release.
    """
    ours = epsilon_for_noise_scale(noise_scale, target_delta, name, sensitivity, steps)

    try:
        from autodp.transformer_zoo import Composition
    except ImportError:
        return AccountantAgreement(
            primary="dp_accounting",
            primary_epsilon=ours,
            secondary=None,
            secondary_epsilon=None,
            relative_difference=None,
            tolerance=tolerance,
            verdict="unavailable",
            detail=(
                "autodp is not installed, so this epsilon rests on a single implementation. "
                "Install autodp to have the release cross-checked."
            ),
        )

    # Say so rather than silently comparing the wrong thing -- naming an unchecked release
    # "agree" would be the exact class of defect this module exists to catch.
    if name not in SUPPORTED_MECHANISMS:
        return AccountantAgreement(
            primary="dp_accounting",
            primary_epsilon=ours,
            secondary="autodp",
            secondary_epsilon=None,
            relative_difference=None,
            tolerance=tolerance,
            verdict="unsupported",
            detail=(
                f"mechanism '{name}' has no directly comparable autodp construction here, so "
                "this release was NOT cross-checked. The epsilon is unaffected; the assurance "
                "is weaker."
            ),
        )

    composed = Composition()([_autodp_mechanism(name, noise_scale, sensitivity)], [int(steps)])
    theirs = float(composed.get_approxDP(target_delta))

    rel = abs(ours - theirs) / theirs if theirs > 0 else 0.0

    if ours < theirs * UNDER_REPORT_MARGIN:
        verdict = "under_report"
        detail = (
            f"REFUSING: dp_accounting reports eps={ours:.6f} but autodp reports "
            f"eps={theirs:.6f}. We would be publishing a guarantee we cannot support. "
            "Reporting less privacy loss than an independent implementation is the failure "
            "mode of audit finding F4 and must not ship."
        )
    elif rel <= tolerance:
        verdict = "agree"
        detail = (
            f"two independent accountants agree within {tolerance:.1%} "
            f"(dp_accounting {ours:.6f}, autodp {theirs:.6f})"
        )
    else:
        verdict = "conservative"
        detail = (
            f"dp_accounting reports eps={ours:.6f} against autodp's {theirs:.6f}, a "
            f"{rel:.2%} difference above the {tolerance:.1%} tolerance. We report the LARGER "
            "value, so the release is at least as private as claimed, but the gap is worth "
            "investigating."
        )

    return AccountantAgreement(
        primary="dp_accounting",
        primary_epsilon=ours,
        secondary="autodp",
        secondary_epsilon=theirs,
        relative_difference=rel,
        tolerance=tolerance,
        verdict=verdict,
        detail=detail,
    )


def enforce(agreement: AccountantAgreement) -> AccountantAgreement:
    """Raise if the cross-check says the release under-reports. Returns it otherwise."""
    if agreement.blocks_release:
        raise AccountantDisagreement(agreement)
    return agreement


def cross_check_spends(
    spends,
    target_delta: float,
    tolerance: float = DEFAULT_TOLERANCE,
) -> AccountantAgreement:
    """Cross-check an ACTUAL composed release, from the accountant's own spend history.

    This is the version that matters. `cross_check` compares a single hypothetical mechanism;
    this walks what the release really charged -- every profiling query, every marginal
    measurement, every selection step -- and recomposes the lot under `autodp`.

    A release that mixes mechanism families is reported `unsupported` rather than partially
    checked. Cross-checking only the Gaussian half and calling the result "agree" would be a
    claim wider than the evidence, which is the defect class this module exists to catch.
    """
    specs = [s.mechanism for s in spends]
    if not specs:
        return AccountantAgreement(
            primary="dp_accounting",
            primary_epsilon=0.0,
            secondary=None,
            secondary_epsilon=None,
            relative_difference=None,
            tolerance=tolerance,
            verdict="unavailable",
            detail="no charges recorded, so there is nothing to cross-check",
        )

    ours = float(spends[-1].computed_eps)

    unsupported = sorted({s.name for s in specs if s.name not in SUPPORTED_MECHANISMS})
    if unsupported:
        return AccountantAgreement(
            primary="dp_accounting",
            primary_epsilon=ours,
            secondary="autodp",
            secondary_epsilon=None,
            relative_difference=None,
            tolerance=tolerance,
            verdict="unsupported",
            detail=(
                f"release charges {', '.join(unsupported)}, which has no counterpart in "
                "this cross-check, so the release was NOT independently checked. The epsilon "
                "is unaffected; the assurance is weaker."
            ),
        )

    try:
        from autodp.transformer_zoo import Composition
    except ImportError:
        return AccountantAgreement(
            primary="dp_accounting",
            primary_epsilon=ours,
            secondary=None,
            secondary_epsilon=None,
            relative_difference=None,
            tolerance=tolerance,
            verdict="unavailable",
            detail=(
                "autodp is not installed, so this epsilon rests on a single implementation. "
                "Install autodp to have the release cross-checked."
            ),
        )

    mechanisms, counts = [], []
    for i, spec in enumerate(specs):
        mechanisms.append(_autodp_mechanism(spec.name, spec.noise_scale, spec.sensitivity, i))
        counts.append(int(getattr(spec, "steps", 1) or 1))

    theirs = float(Composition()(mechanisms, counts).get_approxDP(target_delta))
    rel = abs(ours - theirs) / theirs if theirs > 0 else 0.0

    if ours < theirs * UNDER_REPORT_MARGIN:
        verdict, detail = "under_report", (
            f"REFUSING: this release composes to eps={ours:.6f} under dp_accounting but "
            f"eps={theirs:.6f} under autodp, across {len(specs)} charges. We would be "
            "publishing a guarantee we cannot support."
        )
    elif rel <= tolerance:
        verdict, detail = "agree", (
            f"two independent accountants agree within {tolerance:.1%} across {len(specs)} "
            f"charges (dp_accounting {ours:.6f}, autodp {theirs:.6f})"
        )
    else:
        verdict, detail = "conservative", (
            f"dp_accounting reports eps={ours:.6f} against autodp's {theirs:.6f} across "
            f"{len(specs)} charges, a {rel:.2%} difference above the {tolerance:.1%} "
            "tolerance. We report the LARGER value, so the release is at least as private "
            "as claimed, but the gap is worth investigating."
        )

    return AccountantAgreement(
        primary="dp_accounting",
        primary_epsilon=ours,
        secondary="autodp",
        secondary_epsilon=theirs,
        relative_difference=rel,
        tolerance=tolerance,
        verdict=verdict,
        detail=detail,
    )
