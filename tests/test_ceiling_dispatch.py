"""The dispatcher exists to make one specific mistake impossible.

Two ceiling series live in this repo and they are close enough to look interchangeable: at m=800
the paired Clopper-Pearson series measured 5.377 and the one-run formula gives 5.586. Quoting one
where the other belongs is a checkable error -- an examiner recomputes a single cell and finds it.
A third ceiling is in mu, not epsilon, so comparing it against a proved epsilon is a units error.

These tests pin all three behaviours. The regression test at the bottom was verified by
reintroducing the bug (making the dispatcher fall through to `one_run`) and watching it fail.
"""

import pytest

from synthproof.audit.ceiling import (
    ESTIMATORS,
    ceiling_for,
    measured_paired_budgets,
)
from synthproof.audit.steinke import max_provable_epsilon


class TestOneRun:
    def test_it_matches_the_pinned_formula_exactly(self):
        for r in (10, 60, 100, 400, 800):
            got = ceiling_for("one_run", r)
            assert got.value == pytest.approx(max_provable_epsilon(r), rel=1e-12)
            assert got.unit == "epsilon"
            assert got.measured is False

    def test_the_committed_h1_figure(self):
        """results/AUDITOR_COMPARISON.md reports 2.972 at 60 canaries."""
        assert ceiling_for("one_run", 60).value == pytest.approx(2.972, abs=5e-4)


class TestPairedClopperPearson:
    def test_it_returns_the_measured_value_not_the_formula(self):
        """THE POINT OF THE WHOLE MODULE. At m=800 these differ in the first decimal."""
        paired = ceiling_for("paired_cp", 800)
        one_run = ceiling_for("one_run", 800)
        assert paired.value == pytest.approx(5.376982551119489, rel=1e-12)
        assert one_run.value == pytest.approx(5.5856, abs=1e-3)
        assert paired.value != pytest.approx(one_run.value, abs=1e-3)
        assert paired.measured is True

    def test_it_refuses_an_unmeasured_budget_rather_than_interpolating(self):
        assert 60 not in measured_paired_budgets()
        with pytest.raises(ValueError, match="not interpolated"):
            ceiling_for("paired_cp", 60)

    def test_it_refuses_an_alpha_it_did_not_measure(self):
        with pytest.raises(ValueError, match="MEASURED"):
            ceiling_for("paired_cp", 800, alpha=0.01)


class TestGdpIsADifferentUnit:
    def test_it_reports_mu_not_epsilon(self):
        got = ceiling_for("gdp", 2500)
        assert got.unit == "mu"

    def test_comparing_mu_against_a_proved_epsilon_raises(self):
        """A units error is not a rounding error. Refuse rather than silently mislead."""
        mu_ceiling = ceiling_for("gdp", 2500)
        with pytest.raises(ValueError, match="units mismatch"):
            mu_ceiling.exceeds(7.36)  # proved_unit defaults to "epsilon"

    def test_it_compares_fine_within_its_own_unit(self):
        mu_ceiling = ceiling_for("gdp", 2500)
        assert mu_ceiling.exceeds(0.4547, proved_unit="mu") is True


class TestRefusals:
    @pytest.mark.parametrize("bad", ["", "clopper", "one-run", "GDP", "steinke", None])
    def test_an_unknown_estimator_raises_and_names_the_supported_set(self, bad):
        with pytest.raises(ValueError, match="unknown estimator"):
            ceiling_for(bad, 100)

    def test_the_error_lists_every_supported_estimator(self):
        with pytest.raises(ValueError) as exc:
            ceiling_for("nope", 100)
        for name in ESTIMATORS:
            assert name in str(exc.value)

    @pytest.mark.parametrize("budget", [0, -1])
    def test_a_nonpositive_budget_raises(self, budget):
        with pytest.raises(ValueError, match="budget must be"):
            ceiling_for("one_run", budget)

    @pytest.mark.parametrize("alpha", [0.0, 1.0, -0.1, 1.5])
    def test_an_out_of_range_alpha_raises(self, alpha):
        with pytest.raises(ValueError, match="alpha must be"):
            ceiling_for("one_run", 100, alpha=alpha)


class TestUnderpoweredClassification:
    def test_this_projects_own_h1_grid_is_underpowered(self):
        """m=60 against eps_proved 7.36: the null could never have been anything else."""
        c = ceiling_for("one_run", 60)
        assert c.is_underpowered_for(7.36) is True
        assert c.value < 7.36

    def test_a_large_budget_is_interpretable_at_a_small_proved_bound(self):
        c = ceiling_for("one_run", 800)
        assert c.exceeds(2.0) is True
        assert c.is_underpowered_for(2.0) is False

    def test_describe_carries_the_provenance(self):
        text = ceiling_for("paired_cp", 400).describe()
        assert "paired_cp" in text and "measured" in text
        assert "detection_floor.json" in text
