"""Tests for the GDP auditing module.

The tests that matter here are the ones pinning the DISTINCTION between the mechanism's own
`mu` and the `mu` implied by a released `(eps, delta)`. Conflating those two is how a project
ends up claiming it reproduced a published figure when it computed something else, and this
module's docstring exists because that nearly happened.
"""

import json
import math

import pytest

from synthproof.audit.gdp import (
    audit_against_proof,
    delta_for_mu,
    max_provable_mu,
    mu_from_eps_delta,
    mu_from_gaussian_composition,
    mu_from_rates,
    mu_lower_bound,
    runs_needed_for_mu,
    tradeoff_curve,
)

# --------------------------------------------------------------------------- the conversions


def test_eps_delta_round_trip_is_exact():
    """`mu_from_eps_delta` must invert `delta_for_mu`, or every comparison built on it is wrong."""
    for eps, delta in ((1.0, 1e-2), (1.0, 1e-5), (7.36, 1e-5), (0.5, 1e-3)):
        mu = mu_from_eps_delta(eps, delta)
        assert delta_for_mu(mu, eps) == pytest.approx(delta, rel=1e-6)


def test_gaussian_composition_matches_the_published_mechanism_parameter():
    """VALIDATION AGAINST THE LITERATURE. Ganev et al. (arXiv:2604.18352) report an implied
    `mu = 0.45`. A single Gaussian at sigma ~ 2.2 is exactly that, which is what identifies
    their number as the MECHANISM's parameter rather than an inverted (eps, delta)."""
    assert mu_from_gaussian_composition(1, 2.2) == pytest.approx(0.4545, abs=1e-3)
    # GDP composes by root-sum-square.
    assert mu_from_gaussian_composition(4, 2.0) == pytest.approx(1.0, abs=1e-9)
    assert mu_from_gaussian_composition(9, 3.0) == pytest.approx(1.0, abs=1e-9)


def test_the_two_routes_are_different_quantities_and_that_is_pinned():
    """THE distinction. Inverting `(1, 1e-2)` gives 0.5325, NOT the paper's 0.45, because that
    released pair is not tight. If this test ever starts passing with them equal, someone has
    changed a definition and every mu comparison in the project needs re-checking."""
    inverted = mu_from_eps_delta(1.0, 1e-2)
    mechanism = mu_from_gaussian_composition(1, 2.2)
    assert inverted == pytest.approx(0.5325, abs=1e-3)
    assert mechanism < inverted, "the mechanism's mu must be tighter than the inverted pair"
    # The mechanism spends far less delta than the released pair permits.
    assert delta_for_mu(mechanism, 1.0) < 1e-2


def test_larger_mu_means_larger_delta():
    """Monotonicity, which is what makes the bisection in `mu_from_eps_delta` well-posed."""
    ds = [delta_for_mu(m, 1.0) for m in (0.1, 0.5, 1.0, 2.0)]
    assert ds == sorted(ds)


def test_bad_inputs_raise_rather_than_returning_a_wrong_number():
    with pytest.raises(ValueError):
        mu_from_eps_delta(1.0, 0.0)
    with pytest.raises(ValueError):
        mu_from_eps_delta(-1.0, 1e-5)
    with pytest.raises(ValueError):
        mu_from_gaussian_composition(0, 1.0)
    with pytest.raises(ValueError):
        mu_from_gaussian_composition(1, 0.0)
    with pytest.raises(ValueError):
        mu_from_rates(0.0, 0.5)  # an exact zero makes the estimate unbounded


# --------------------------------------------------------------------------- the estimator


def test_separable_worlds_give_a_positive_mu():
    """POSITIVE CONTROL. Two clearly different score distributions must produce mu > 0."""
    ins = [3.0 + 0.01 * i for i in range(400)]
    outs = [0.0 + 0.01 * i for i in range(400)]
    res = mu_lower_bound(ins, outs)
    assert res.is_informative
    assert res.mu_emp > 1.0


def test_identical_worlds_give_zero():
    """NEGATIVE CONTROL, and the one that matters. If the two worlds are the same, the audit
    must report nothing -- not a small positive number it could be tempted to publish."""
    vals = [0.01 * i for i in range(400)]
    res = mu_lower_bound(vals, list(vals))
    assert res.mu_emp == pytest.approx(0.0, abs=0.35)


def test_the_bound_never_exceeds_what_the_run_count_could_certify():
    """A lower bound above the instrument's own ceiling would be a bug, not a discovery."""
    ins = [10.0] * 200
    outs = [-10.0] * 200
    res = mu_lower_bound(ins, outs)
    assert res.mu_emp <= max_provable_mu(200, 200) + 1e-9


def test_the_ceiling_grows_with_runs():
    """The GDP analogue of the canary ceiling: more runs buy a larger certifiable mu."""
    mus = [max_provable_mu(n, n) for n in (50, 200, 1000, 5000)]
    assert mus == sorted(mus)
    assert runs_needed_for_mu(0.45) < runs_needed_for_mu(3.0)


def test_a_perfect_adversary_at_tiny_n_still_cannot_certify_much():
    """The point of reporting a ceiling: with 20 runs per world, even perfect separation
    certifies only a modest mu, so a small result there is uninformative rather than reassuring."""
    assert max_provable_mu(20, 20) < max_provable_mu(2000, 2000)


def test_audit_against_proof_attaches_the_comparator():
    ins = [2.0] * 300
    outs = [0.0] * 300
    res = audit_against_proof(ins, outs, proved_eps=1.0, delta=1e-2)
    assert res.implied_mu == pytest.approx(mu_from_eps_delta(1.0, 1e-2))
    assert res.proved_eps == 1.0


def test_exceeding_the_implied_mu_is_flagged_as_a_violation():
    """SAFETY-CRITICAL. An empirical mu above the proved bound is evidence of a violation
    somewhere -- mechanism, accounting, or audit. It must be surfaced, never celebrated."""
    ins = [50.0] * 4000
    outs = [-50.0] * 4000
    res = audit_against_proof(ins, outs, proved_eps=0.01, delta=1e-10)
    assert res.exceeds_implied, "a perfect adversary against a tiny epsilon must flag"


def test_mu_from_rates_clamps_below_the_diagonal():
    """An adversary doing worse than chance is not evidence of extra privacy."""
    assert mu_from_rates(0.6, 0.6) == 0.0


def test_tradeoff_curve_matches_the_estimator():
    """The curve and the point estimator must be the same formula, or plots will not line up."""
    mu = 0.75
    for fpr, fnr in tradeoff_curve(mu, points=11):
        if 0 < fpr < 1 and 0 < fnr < 1:
            assert mu_from_rates(fpr, fnr) == pytest.approx(mu, abs=1e-6)


def test_empty_input_is_refused():
    with pytest.raises(ValueError):
        mu_lower_bound([], [1.0, 2.0])


def test_alpha_is_honoured():
    """A stricter alpha must give a smaller (more conservative) bound."""
    ins = [1.0] * 500
    outs = [0.0] * 500
    strict = mu_lower_bound(ins, outs, alpha=0.001).mu_emp
    loose = mu_lower_bound(ins, outs, alpha=0.2).mu_emp
    assert strict < loose


def test_result_carries_everything_needed_to_recheck_it():
    res = mu_lower_bound([2.0] * 100, [0.0] * 100)
    for field in ("fpr", "fnr", "fpr_upper", "fnr_upper", "threshold", "n_positive", "n_negative"):
        assert getattr(res, field) is not None
    assert math.isfinite(res.mu_emp)


# --------------------------------------------------------------------------- the power analysis

# `audit-power --gdp` answers, BEFORE an audit is run, whether it could certify the target at
# all. The canary version of this command already exists; these pin the GDP mode, and in
# particular that it cannot silently claim more reach than the arithmetic supports.


def _cli(*args):
    from click.testing import CliRunner

    from synthproof.cli import main

    return CliRunner().invoke(main, ["audit-power", *args])


def test_gdp_power_reports_a_ceiling_and_a_requirement():
    res = _cli("--gdp", "--mu", "0.4547", "--runs", "2500", "--json")
    assert res.exit_code == 0, res.output
    d = json.loads(res.output)
    assert d["metric"] == "mu-GDP"
    assert d["target_mu"] == pytest.approx(0.4547)
    assert d["runs_required_per_world"] >= 1
    assert d["ceiling_mu"] > d["target_mu"]
    assert d["can_certify_target"] is True


def test_gdp_power_refuses_a_budget_that_cannot_reach_the_target():
    """The whole point: say NO before the run, not after a zero comes back."""
    res = _cli("--gdp", "--mu", "6.0", "--runs", "10", "--json")
    assert res.exit_code == 0, res.output
    d = json.loads(res.output)
    assert d["can_certify_target"] is False
    assert d["ceiling_mu"] < 6.0


def test_gdp_power_converts_from_eps_delta_and_labels_it_loose():
    """Inverting a released (eps, delta) gives the LOOSE comparator, and the report must say
    so -- conflating it with the mechanism's own mu is the error this module was built around."""
    res = _cli("--gdp", "--eps", "7.36", "--delta", "1e-5", "--json")
    assert res.exit_code == 0, res.output
    d = json.loads(res.output)
    assert d["target_mu"] == pytest.approx(1.5546, abs=1e-3)
    assert "LOOSE" in d["target_mu_source"]


def test_mu_and_runs_require_gdp():
    """NEGATIVE CONTROL. Silently ignoring --mu in canary mode would answer a different
    question from the one asked."""
    assert _cli("--eps", "1.0", "--mu", "0.5").exit_code != 0
    assert _cli("--eps", "1.0", "--runs", "100").exit_code != 0


def test_eps_is_still_required_in_canary_mode():
    assert _cli("--canaries", "60").exit_code != 0


def test_canary_mode_is_unchanged():
    """The existing behaviour must not shift: 60 canaries cannot certify eps = 7.36."""
    res = _cli("--eps", "7.36", "--canaries", "60", "--json")
    assert res.exit_code == 0, res.output
    d = json.loads(res.output)
    assert d["can_certify_target"] is False
    assert d["ceiling"] == pytest.approx(2.972, abs=1e-2)
    assert d["canaries_required_total"] == 4711


def test_the_two_estimators_disagree_at_the_same_numeric_budget():
    """The result the planner reports: at a numeric budget of 60, the canary estimator cannot
    reach this project's own target and the GDP estimator can.

    This is a statement about STATISTICAL REACH at equal numeric budget. It is NOT a speed-up:
    60 canaries live inside one model fit, 60 GDP runs per world are 120 separate fits.
    """
    from synthproof.audit.steinke import max_provable_epsilon

    target_eps, delta = 7.36, 1e-5
    target_mu = mu_from_eps_delta(target_eps, delta)
    assert max_provable_epsilon(60) < target_eps, "canary auditor should fall short"
    assert max_provable_mu(60, 60) > target_mu, "GDP auditor should reach it"
