"""The audit-range verdict: could this audit have certified this claim?

Until 2026-09-13 the capsule, CLI, API and console each carried their own copy of
`lod_safe = audited_eps < audit_ceiling`, shown as a green tick. It never compared the PROVED
epsilon with the ceiling -- the comparison this project's central finding is about -- so a
release proving eps = 7.36 against a 2.97 ceiling came out green. It also let two demo capsules
ship signed with ceilings their own declared audits cannot produce.

These tests pin the replacement against the cases that matter: the project's own H1 numbers,
the real CLI release, the two fabricated demo sheets, and the priority order between checks.
"""

import pytest

from synthproof.audit.ceiling import range_verdict, recompute_ceiling
from synthproof.audit.steinke import max_provable_epsilon

H1_CEILING = max_provable_epsilon(60, 0.05)  # 2.972...
CLI_CEILING = max_provable_epsilon(30, 0.05)  # 2.254..., the CLI's default 30 canaries


def _one_run(proved, audited, ceiling, budget):
    return range_verdict(proved, audited, ceiling, estimator="one_run", budget=budget, alpha=0.05)


# ------------------------------------------------------------------ the cases that matter


def test_h1_is_reported_as_a_claim_the_audit_could_not_certify():
    """The project's own disqualified result. The old check rendered this green."""
    v = _one_run(7.36, 0.0, H1_CEILING, 60)
    assert v.code == "CLAIM_EXCEEDS_AUDIT_RANGE"
    assert v.tone == "warn"
    assert v.claim_in_audit_range is False
    assert "not evidence of no leakage" in v.explanation


def test_the_real_cli_release_at_eps_1_is_in_range_and_not_detected():
    """Numbers copied from an actual `synthproof run --eps 1.0` sheet (ceiling at 30 canaries)."""
    v = _one_run(0.9122542470732562, 0.0, 2.2536643625605906, 30)
    assert v.code == "IN_RANGE_NOT_DETECTED"
    assert v.tone == "ok" and v.claim_in_audit_range is True
    assert "absence of evidence" in v.explanation


def test_the_real_cli_release_at_eps_8_exceeds_the_audit_range():
    v = _one_run(7.356, 0.0, CLI_CEILING, 30)
    assert v.code == "CLAIM_EXCEEDS_AUDIT_RANGE"


@pytest.mark.parametrize(
    "ceiling, budget",
    [(3.50, 60), (4.00, 100)],
    ids=["adult-demo-capsule", "acs-demo-capsule"],
)
def test_the_fabricated_demo_ceilings_are_caught(ceiling, budget):
    """The shipped demo sheets declared one_run / budget / alpha=0.05 and a ceiling that audit
    cannot produce. Both verified as authentic, because the signature covers what was written,
    not whether it was true."""
    v = _one_run(1.0, 0.384, ceiling, budget)
    assert v.code == "CEILING_MISMATCH"
    assert v.tone == "fail"
    assert v.recomputed_ceiling == pytest.approx(max_provable_epsilon(budget, 0.05))


def test_in_range_with_a_nonzero_audit_is_consistent_not_undetected():
    """The old badge called an audited 0.5 under a 2.0 ceiling "NOT DETECTED". It is a detection."""
    v = range_verdict(1.5, 0.5, 2.0)
    assert v.code == "IN_RANGE_CONSISTENT"
    assert "NOT DETECTED" not in v.label


# ------------------------------------------------------------------ priority order


def test_an_audit_above_the_proof_outranks_everything():
    """Lower bound > upper bound means the accounting or the audit is wrong. Nothing else about
    the sheet can be interpreted until that is resolved, so it wins even over a mismatch."""
    v = _one_run(2.0, 3.0, 99.0, 60)
    assert v.code == "AUDIT_CONTRADICTS_PROOF" and v.tone == "fail"


def test_a_ceiling_mismatch_outranks_a_range_judgement():
    """A range judgement made from an invented ceiling would itself be invented."""
    v = _one_run(7.36, 0.0, 10.0, 60)  # would read "in range" if 10.0 were trusted
    assert v.code == "CEILING_MISMATCH"


def test_no_ceiling_is_uninterpretable_rather_than_fine():
    for ceiling in (None, 0.0):
        v = range_verdict(1.0, 0.0, ceiling)
        assert v.code == "NO_CEILING" and v.claim_in_audit_range is False


def test_a_mu_gdp_ceiling_is_not_compared_with_an_epsilon():
    v = range_verdict(1.0, 0.0, 5.36, estimator="gdp", budget=1000, alpha=0.05)
    assert v.code == "CEILING_UNITS"


def test_a_missing_proved_epsilon_is_reported():
    assert range_verdict(None, 0.0, 2.0).code == "NO_CLAIM"


# ------------------------------------------------------------------ recomputation


def test_a_real_float_ceiling_passes_the_consistency_check():
    """The check must not misfire on the exact value the pipeline itself wrote."""
    v = _one_run(1.0, 0.0, max_provable_epsilon(60, 0.05), 60)
    assert v.code != "CEILING_MISMATCH"


def test_an_underivable_ceiling_is_not_treated_as_a_mismatch():
    """ "Cannot recompute" and "does not match" are different outcomes and must stay different."""
    assert recompute_ceiling(None, 60, 0.05) is None
    assert recompute_ceiling("paired_cp", 61, 0.05) is None  # unmeasured paired budget
    assert recompute_ceiling("gdp", 100, 0.05) is None  # mu, not epsilon
    v = range_verdict(1.0, 0.0, 3.2, estimator="paired_cp", budget=61, alpha=0.05)
    assert v.code == "IN_RANGE_NOT_DETECTED"


def test_no_verdict_ever_calls_a_release_safe():
    """There is deliberately no `safe` outcome. Pinned so one is not added back."""
    cases = [
        range_verdict(2.0, 3.0, 2.5),
        range_verdict(1.0, 0.0, None),
        _one_run(7.36, 0.0, H1_CEILING, 60),
        range_verdict(1.0, 0.0, 2.0),
        range_verdict(1.0, 0.5, 2.0),
        _one_run(1.0, 0.0, 3.5, 60),
    ]
    for v in cases:
        assert "safe" not in v.label.lower() and "safe" not in v.to_dict()
        assert "Bounded under MIQE" not in v.explanation
