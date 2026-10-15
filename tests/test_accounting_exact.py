"""Exact-value tests for the accounting core, written against its surviving mutants.

Mutation testing (scripts/mutation.sh, 2026-10-16) found 127 mutants of synthproof/accounting/
that no test noticed: a changed boundary, a dropped field, a swapped message. Most lived in the
second-accountant cross-check, the weighted calibration and the budget-tightening search. Each
test below pins one thing those mutants changed -- an exact value, a boundary, or a field that
travels in the signed sheet -- rather than only a verdict.
"""

import builtins
import math
import re

import pytest

from synthproof.accounting import differential
from synthproof.accounting.accountant import Accountant
from synthproof.accounting.calibration import (
    _MAX_SCALE,
    _MIN_SCALE,
    BudgetPlan,
    calibrate_noise_scale,
    calibrate_weighted_scales,
    epsilon_for_noise_scale,
)
from synthproof.accounting.differential import (
    DEFAULT_TOLERANCE,
    UNDER_REPORT_MARGIN,
    AccountantDisagreement,
    cross_check,
    enforce,
)
from synthproof.accounting.noise import em_noise_scale
from synthproof.accounting.types import BudgetExceededError, MechanismSpec

pytest.importorskip("autodp")

# ------------------------------------------------------------------ the cross-check, per branch


def test_agree_reports_both_accountants_exactly():
    a = cross_check(3.0, 1e-5, "gaussian", 1.0, 4)
    ours = epsilon_for_noise_scale(3.0, 1e-5, "gaussian", 1.0, 4)
    assert a.verdict == "agree"
    assert (a.primary, a.secondary) == ("dp_accounting", "autodp")
    assert a.primary_epsilon == ours
    assert a.secondary_epsilon is not None and a.secondary_epsilon > 0
    assert a.relative_difference == pytest.approx(
        abs(ours - a.secondary_epsilon) / a.secondary_epsilon, rel=1e-12
    )
    assert a.tolerance == DEFAULT_TOLERANCE
    assert f"{ours:.6f}" in a.detail and f"{a.secondary_epsilon:.6f}" in a.detail
    assert "agree" in a.detail
    assert not a.blocks_release
    assert a.to_dict()["verdict"] == "agree"


def test_a_difference_above_the_tolerance_is_conservative_not_agree():
    a = cross_check(3.0, 1e-5, "gaussian", 1.0, 4, tolerance=0.0)
    if a.relative_difference == 0.0:
        pytest.skip("the two accountants agree exactly here; no conservative gap to test")
    assert a.verdict == "conservative"
    assert "LARGER" in a.detail and f"{a.relative_difference:.2%}" in a.detail
    assert not a.blocks_release


def test_a_difference_exactly_at_the_tolerance_still_agrees():
    probe = cross_check(3.0, 1e-5, "gaussian", 1.0, 4)
    a = cross_check(3.0, 1e-5, "gaussian", 1.0, 4, tolerance=probe.relative_difference)
    assert a.verdict == "agree"


def test_under_reporting_is_refused_and_says_so(monkeypatch):
    real = differential.epsilon_for_noise_scale
    monkeypatch.setattr(
        differential, "epsilon_for_noise_scale", lambda *a, **k: 0.5 * real(*a, **k)
    )
    a = cross_check(3.0, 1e-5, "gaussian", 1.0, 4)
    assert a.verdict == "under_report"
    assert a.blocks_release
    assert a.detail.startswith("REFUSING")
    assert f"{a.primary_epsilon:.6f}" in a.detail
    with pytest.raises(AccountantDisagreement) as err:
        enforce(a)
    assert err.value.agreement is a
    assert str(err.value) == a.detail


def test_reporting_just_inside_the_margin_is_not_under_reporting(monkeypatch):
    """`ours < theirs * 0.999` is the line. Exactly at it is numerical noise, not a violation."""
    probe = cross_check(3.0, 1e-5, "gaussian", 1.0, 4)
    at_margin = probe.secondary_epsilon * UNDER_REPORT_MARGIN
    monkeypatch.setattr(differential, "epsilon_for_noise_scale", lambda *a, **k: at_margin)
    assert cross_check(3.0, 1e-5, "gaussian", 1.0, 4).verdict != "under_report"
    monkeypatch.setattr(
        differential, "epsilon_for_noise_scale", lambda *a, **k: at_margin * (1 - 1e-6)
    )
    assert cross_check(3.0, 1e-5, "gaussian", 1.0, 4).verdict == "under_report"


def test_an_unsupported_mechanism_is_reported_unchecked_not_agreed():
    # A name the accountant knows but autodp has no construction for here.
    a = cross_check(3.0, 1e-5, "dpsgd", 1.0, 1)
    assert a.verdict == "unsupported"
    assert a.secondary == "autodp" and a.secondary_epsilon is None
    assert a.relative_difference is None
    assert "NOT cross-checked" in a.detail and "dpsgd" in a.detail
    assert not a.blocks_release


def test_a_missing_second_accountant_is_reported_not_hidden(monkeypatch):
    real_import = builtins.__import__

    def no_autodp(name, *a, **k):
        if name.startswith("autodp"):
            raise ImportError("no autodp")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", no_autodp)
    a = cross_check(3.0, 1e-5, "gaussian", 1.0, 4)
    assert a.verdict == "unavailable"
    assert a.secondary is None and a.secondary_epsilon is None and a.relative_difference is None
    assert a.primary == "dp_accounting"
    assert "single implementation" in a.detail
    assert not a.blocks_release


@pytest.mark.parametrize("name", ["gaussian", "laplace", "exponential"])
def test_sensitivity_is_divided_out_for_every_mechanism(name):
    """A sensitivity other than one must not manufacture a disagreement (unit error)."""
    unit = cross_check(2.0, 1e-5, name, 1.0, 3)
    scaled = cross_check(2.0 * 7.0, 1e-5, name, 7.0, 3)
    assert scaled.secondary_epsilon == pytest.approx(unit.secondary_epsilon, rel=1e-9)
    assert scaled.verdict == unit.verdict


# ------------------------------------------------------------------ weighted calibration


def test_weighted_scales_have_exactly_the_inverse_sqrt_weight_shape():
    w = [1.0, 4.0, 9.0, 0.25]
    s = calibrate_weighted_scales(w, 2.0)
    for i in range(len(w)):
        for j in range(len(w)):
            assert s[i] / s[j] == pytest.approx(math.sqrt(w[j] / w[i]), rel=1e-12)


def test_weighted_scales_spend_the_target_and_never_more():
    w = [1.0, 2.0, 5.0]
    s = calibrate_weighted_scales(w, 1.5)
    acct = Accountant(float("inf"), 1e-5)
    for x in s:
        acct.charge(MechanismSpec("gaussian", 1.0, x))
    spent = acct.total(1e-5)
    assert spent <= 1.5
    assert spent >= 1.5 * (1 - 1e-3)


def test_uniform_weights_equal_the_scalar_calibration():
    s = calibrate_weighted_scales([3.0, 3.0, 3.0], 2.0)
    ref = calibrate_noise_scale(2.0, 1e-5, "gaussian", 1.0, 3)
    assert all(x == pytest.approx(ref, rel=2e-4) for x in s)


def test_weighted_laplace_calibration_also_lands_on_target():
    s = calibrate_weighted_scales([1.0, 3.0], 1.0, name="laplace")
    acct = Accountant(float("inf"), 1e-5)
    for x in s:
        acct.charge(MechanismSpec("laplace", 1.0, x))
    assert 1.0 * (1 - 1e-3) <= acct.total(1e-5) <= 1.0


def test_a_tighter_tolerance_lands_closer_to_the_target():
    loose = calibrate_weighted_scales([1.0, 2.0], 1.0, tol=1e-2)
    tight = calibrate_weighted_scales([1.0, 2.0], 1.0, tol=1e-8)

    def spent(scales):
        acct = Accountant(float("inf"), 1e-5)
        for x in scales:
            acct.charge(MechanismSpec("gaussian", 1.0, x))
        return acct.total(1e-5)

    assert spent(loose) <= 1.0 and spent(tight) <= 1.0
    assert 1.0 - spent(tight) <= 1.0 - spent(loose)
    assert 1.0 - spent(tight) < 1e-5


def test_a_trivially_satisfiable_target_returns_the_minimum_scale_shape():
    w = [1.0, 4.0]
    s = calibrate_weighted_scales(w, 1e40)
    shape = [math.sqrt(sum(w) / (x * len(w))) for x in w]
    assert s == pytest.approx([_MIN_SCALE * x for x in shape], rel=1e-12)


def test_an_unreachable_target_is_refused_with_the_reason():
    with pytest.raises(ValueError, match=re.escape(f"exceeds {_MAX_SCALE:g}")):
        calibrate_weighted_scales([1.0] * 3, 1e-12, target_delta=1e-300)


@pytest.mark.parametrize(
    "weights,target,msg",
    [
        ([1.0], 0.0, "target_eps must be positive"),
        ([], 1.0, "must not be empty"),
        ([1.0, 0.0], 1.0, "every weight must be positive"),
        ([1.0, -2.0], 1.0, "positive"),
    ],
)
def test_weighted_calibration_rejects_bad_inputs(weights, target, msg):
    with pytest.raises(ValueError, match=msg):
        calibrate_weighted_scales(weights, target)


# ------------------------------------------------------------------ budget split and tightening


def test_the_linear_split_is_exact_and_records_no_tightening():
    p = BudgetPlan.split(4.0, 1e-5, profile_frac=0.25)
    assert (p.total_eps, p.delta) == (4.0, 1e-5)
    assert p.profile_eps == pytest.approx(1.0, rel=1e-12)
    assert p.synthesis_eps == pytest.approx(3.0, rel=1e-12)
    assert p.tightening == 1.0
    assert p.composed_eps < 4.0


def test_tightening_meets_the_target_from_below_and_keeps_the_ratio():
    p = BudgetPlan.split(4.0, 1e-5, profile_frac=0.25, tighten=True)
    assert p.tightening > 1.0
    assert p.composed_eps <= 4.0
    assert p.composed_eps >= 4.0 * (1 - 1e-3)
    assert p.profile_eps / p.synthesis_eps == pytest.approx(1.0 / 3.0, rel=1e-12)
    assert p.profile_eps == pytest.approx(1.0 * p.tightening, rel=1e-12)


def test_tightening_is_the_largest_multiplier_that_does_not_overspend():
    p = BudgetPlan.split(2.0, 1e-5, tighten=True)
    k = p.tightening
    bigger = BudgetPlan(
        total_eps=2.0, delta=1e-5, profile_eps=0.2 * k * 1.002, synthesis_eps=1.8 * k * 1.002
    )
    assert bigger.composed_eps > 2.0  # a hair more would overspend


@pytest.mark.parametrize(
    "total,frac,msg",
    [
        (0.0, 0.1, "total_eps must be positive"),
        (-1.0, 0.1, "total_eps must be positive"),
        (1.0, 0.0, r"profile_frac must be in \(0, 1\)"),
        (1.0, 1.0, r"profile_frac must be in"),
    ],
)
def test_the_split_rejects_bad_inputs(total, frac, msg):
    with pytest.raises(ValueError, match=msg):
        BudgetPlan.split(total, 1e-5, profile_frac=frac)


# ------------------------------------------------------------------ small exact values


def test_the_exponential_mechanism_is_charged_at_two_delta_over_epsilon():
    assert em_noise_scale(0.5, 3.0) == pytest.approx(12.0, rel=1e-15)
    assert em_noise_scale(2.0, 1.0) == pytest.approx(1.0, rel=1e-15)


def test_budget_exceeded_carries_its_numbers():
    e = BudgetExceededError(1.23456, 0.5, 1e-5)
    assert (e.requested_eps, e.remaining_eps, e.delta) == (1.23456, 0.5, 1e-5)
    assert str(e) == (
        "Privacy spend of epsilon=1.2346 exceeds remaining epsilon=0.5000 at delta=1.00e-05"
    )


def test_a_snapshot_is_a_copy_not_a_view():
    acct = Accountant(10.0, 1e-5)
    acct.charge(MechanismSpec("gaussian", 1.0, 5.0), run_id="a")
    snap = acct.snapshot()
    events_before, spends_before = len(snap[0]), len(snap[1])
    acct.charge(MechanismSpec("gaussian", 1.0, 5.0), run_id="b")
    assert (len(snap[0]), len(snap[1])) == (events_before, spends_before)
    acct.restore(snap)
    assert acct.total(1e-5) == pytest.approx(
        epsilon_for_noise_scale(5.0, 1e-5, "gaussian", 1.0, 1), rel=1e-12
    )
    acct.charge(MechanismSpec("gaussian", 1.0, 5.0), run_id="c")
    assert (len(snap[0]), len(snap[1])) == (events_before, spends_before)
