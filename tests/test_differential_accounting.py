"""Tests for differential accounting -- the second-accountant release gate.

The gate exists because a grey-box audit of twelve DP libraries found thirteen guarantee
violations (Cebere et al., arXiv 2602.17454, 2026). Its whole value is that it fires when the
two accountants disagree in the unsafe direction, so the test that matters is the one that
proves it fires -- not the one that proves it stays quiet.

The `unavailable`/`unsupported` cases get their own tests for the same reason the auditor has a
negative control: an absent check must never be reportable as a passed one.
"""

from dataclasses import FrozenInstanceError, replace

import pytest

from synthproof.accounting.differential import (
    AccountantAgreement,
    AccountantDisagreement,
    cross_check,
    cross_check_spends,
    enforce,
)
from synthproof.accounting.types import MechanismSpec, PrivacySpend

pytest.importorskip("autodp", reason="autodp is the second accountant under test")


# --------------------------------------------------------------- agreement on real parameters


@pytest.mark.parametrize("sigma", [1.0, 2.0, 5.0, 10.0])
@pytest.mark.parametrize("steps", [1, 5, 20])
def test_the_two_accountants_agree_on_gaussian_composition(sigma, steps):
    """Agreement is the expected case; if this breaks, one of the libraries changed."""
    a = cross_check(sigma, 1e-5, "gaussian", 1.0, steps)
    assert a.verdict == "agree", a.detail
    assert not a.blocks_release
    assert a.secondary_epsilon is not None
    assert a.relative_difference <= a.tolerance


def test_agreement_survives_a_sensitivity_other_than_one():
    """autodp takes sigma in units of sensitivity; getting that wrong would fake a disagreement."""
    a = cross_check(4.0, 1e-5, "gaussian", sensitivity=2.0, steps=3)
    assert a.verdict == "agree", a.detail


# --------------------------------------------------------------- the gate must actually fire


def test_under_reporting_blocks_the_release():
    """The case the gate exists for.

    Constructed by hand rather than by breaking the accountant, because we need a genuine
    under-report to assert on and both libraries currently agree. `blocks_release` is the
    property the pipeline branches on, so it is what is asserted.
    """
    bad = AccountantAgreement(
        primary="dp_accounting",
        primary_epsilon=1.0,
        secondary="autodp",
        secondary_epsilon=2.0,
        relative_difference=0.5,
        tolerance=0.01,
        verdict="under_report",
        detail="constructed",
    )
    assert bad.blocks_release
    with pytest.raises(AccountantDisagreement):
        enforce(bad)


@pytest.mark.parametrize("verdict", ["agree", "conservative", "unavailable", "unsupported"])
def test_only_under_reporting_blocks(verdict):
    """Reporting MORE loss than the reference is conservative and must not stop a release."""
    a = AccountantAgreement(
        primary="dp_accounting",
        primary_epsilon=1.0,
        secondary="autodp",
        secondary_epsilon=1.0,
        relative_difference=0.0,
        tolerance=0.01,
        verdict=verdict,
        detail="constructed",
    )
    assert not a.blocks_release
    assert enforce(a) is a


def test_a_real_under_report_is_detected_end_to_end():
    """Reintroduce the failure for real: claim an epsilon the second accountant contradicts.

    A spend history whose recorded total is half what the noise scales actually compose to is
    exactly audit finding F4 (the old subsampling bound under-reported by ~2x). The gate must
    catch it from the spend history alone.
    """
    spec = MechanismSpec(name="gaussian", sensitivity=1.0, noise_scale=1.0, steps=1)
    honest = cross_check_spends(
        [PrivacySpend(mechanism=spec, computed_eps=4.72851, delta=1e-5)], 1e-5
    )
    assert honest.verdict == "agree", honest.detail

    understated = cross_check_spends(
        [PrivacySpend(mechanism=spec, computed_eps=honest.secondary_epsilon / 2, delta=1e-5)], 1e-5
    )
    assert understated.verdict == "under_report", understated.detail
    assert understated.blocks_release
    with pytest.raises(AccountantDisagreement):
        enforce(understated)


# --------------------------------------------------------------- absence is never agreement


@pytest.mark.parametrize("b,steps", [(1.0, 1), (2.0, 5), (0.5, 3)])
def test_laplace_is_cross_checked_too(b, steps):
    """Both families this project charges are covered, so real releases get checked.

    Before Laplace was added, every `pairwise` and `aim` release reported `unsupported` --
    honest, but useless, because those mechanisms charge Laplace for selection alongside
    Gaussian for measurement. Worst observed disagreement across this grid is 0.28%.
    """
    a = cross_check(b, 1e-5, "laplace", 1.0, steps)
    assert a.verdict == "agree", a.detail
    assert a.secondary_epsilon is not None


def test_a_mixed_gaussian_laplace_release_is_actually_checked():
    """The realistic case: `pairwise` charges both families in one release."""
    spends = [
        PrivacySpend(
            mechanism=MechanismSpec(name="gaussian", sensitivity=1.0, noise_scale=1.0, steps=1),
            computed_eps=1.0,
        ),
        PrivacySpend(
            mechanism=MechanismSpec(name="laplace", sensitivity=1.0, noise_scale=1.0, steps=1),
            computed_eps=99.0,  # deliberately over-stated: conservative, never fatal
        ),
    ]
    a = cross_check_spends(spends, 1e-5)
    assert a.verdict in {"agree", "conservative"}, a.detail
    assert a.secondary_epsilon is not None
    assert not a.blocks_release


def test_a_mechanism_the_accountant_knows_but_we_cannot_check_reads_unsupported():
    """Silently comparing the wrong thing would be the defect class this module exists to catch.

    `dpsgd` is the live example: `Accountant` accounts it (via a subsampled Gaussian event) but
    this cross-check has no counterpart for it. That gap must read `unsupported`, never
    `agree`. Names the accountant does not know at all are refused earlier, by
    `Accountant.to_dp_event` -- a stronger guard than this one, and tested separately.
    """
    a = cross_check(1.0, 1e-5, "dpsgd", 1.0, 3)
    assert a.verdict == "unsupported"
    assert a.secondary_epsilon is None
    assert "NOT cross-checked" in a.detail
    assert not a.blocks_release

    spends = [
        PrivacySpend(
            mechanism=MechanismSpec(name="gaussian", sensitivity=1.0, noise_scale=1.0, steps=1),
            computed_eps=1.0,
        ),
        PrivacySpend(
            mechanism=MechanismSpec(name="dpsgd", sensitivity=1.0, noise_scale=1.0, steps=1),
            computed_eps=2.0,
        ),
    ]
    mixed = cross_check_spends(spends, 1e-5)
    assert mixed.verdict == "unsupported"
    assert "dpsgd" in mixed.detail


def test_a_mechanism_the_accountant_rejects_never_reaches_the_cross_check():
    """The outer guard. An unknown name must fail loudly, not be accounted as Gaussian."""
    with pytest.raises(ValueError, match="Unknown mechanism"):
        cross_check(1.0, 1e-5, "exponential", 1.0, 3)


def test_an_empty_spend_history_is_unavailable_not_agreed():
    a = cross_check_spends([], 1e-5)
    assert a.verdict == "unavailable"
    assert not a.blocks_release


# --------------------------------------------------------------- it reaches the certificate


def test_the_verdict_is_serialisable_and_therefore_signable():
    """The verdict has to survive into the signed payload or it protects nobody."""
    a = cross_check(2.0, 1e-5, "gaussian", 1.0, 5)
    d = a.to_dict()
    assert d["verdict"] == "agree"
    assert d["primary"] == "dp_accounting"
    assert d["secondary"] == "autodp"
    assert isinstance(d["primary_epsilon"], float)
    # A frozen dataclass keeps a verdict from being edited after the gate ran.
    with pytest.raises(FrozenInstanceError):
        a.verdict = "agree"  # type: ignore[misc]
    assert replace(a, verdict="under_report").blocks_release
