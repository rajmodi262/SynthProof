"""The classifier must refuse a bad row rather than produce a plausible wrong class.

Every rule tested here is fixed in `docs/CEILING_SURVEY_PROTOCOL.md`, which was committed before
any paper was read. If a test here disagrees with that document, the document wins and the test
is the bug.
"""

import pytest

from synthproof.survey.ceiling_audit import (
    NOT_REPORTED,
    ProtocolViolation,
    Row,
    classify,
    classify_all,
    summarise,
    wilson_interval,
)


def _row(**over):
    kw = dict(
        paper_id="arXiv:0000.00000",
        config_label="Table 3, eps=8",
        estimator_family="one_run",
        budget=60,
        alpha=0.05,
        eps_emp=0.0,
        emp_unit="epsilon",
        eps_proved=7.36,
        proved_unit="epsilon",
        acknowledged_limit="no",
        extractor="rm",
        source_depth="full text",
        locators={"budget": "S5.2", "alpha": "S5.2", "eps_emp": "Tab.3", "eps_proved": "Tab.3"},
    )
    kw.update(over)
    return Row(**kw)


class TestClassification:
    def test_this_projects_own_h1_configuration_is_underpowered(self):
        """The worked example: m=60 caps the auditor at 2.97 against a proved 7.36."""
        c = classify(_row())
        assert c.klass == "UNDERPOWERED"
        assert c.ceiling == pytest.approx(2.972, abs=5e-4)
        assert c.counts_toward_k is True

    def test_a_generous_budget_against_a_small_bound_is_interpretable(self):
        c = classify(_row(budget=800, eps_proved=2.0, eps_emp=1.0))
        assert c.klass == "INTERPRETABLE"

    def test_an_estimate_pinned_at_the_ceiling_is_saturated(self):
        c = classify(_row(budget=800, eps_proved=2.0, eps_emp=5.5))
        assert c.klass == "SATURATED"
        assert "pinned at the top" in c.reason

    def test_a_missing_budget_is_not_reported_not_a_guess(self):
        c = classify(_row(budget=None, locators={"alpha": "S5", "eps_emp": "T3", "eps_proved": "T3"}))
        assert c.klass == "NOT REPORTED"
        assert c.ceiling is None


class TestRefusals:
    @pytest.mark.parametrize("fam", ["other", NOT_REPORTED, "clopper", ""])
    def test_an_unreadable_estimator_is_excluded_never_guessed(self, fam):
        """Protocol S5. Three ceiling series in two units; guessing is a checkable error."""
        c = classify(_row(estimator_family=fam))
        assert c.klass == "EXCLUDED"
        assert "excluded rather than" in c.reason

    def test_a_number_without_a_locator_is_inadmissible(self):
        """Protocol S4. This is what makes the table credible rather than contestable."""
        with pytest.raises(ProtocolViolation, match="no locator"):
            classify(_row(locators={"alpha": "S5", "eps_emp": "T3", "eps_proved": "T3"}))

    def test_comparing_mu_against_epsilon_raises(self):
        """A units error, not a rounding one."""
        with pytest.raises(ProtocolViolation, match="units error"):
            classify(_row(estimator_family="gdp", budget=2500, proved_unit="epsilon"))

    def test_gdp_compares_fine_within_mu(self):
        c = classify(_row(estimator_family="gdp", budget=2500, emp_unit="mu",
                          proved_unit="mu", eps_proved=0.4547, eps_emp=0.4014))
        assert c.klass in ("INTERPRETABLE", "UNDERPOWERED", "SATURATED")
        assert c.ceiling_unit == "mu"

    @pytest.mark.parametrize("bad", ["maybe", "true", ""])
    def test_acknowledged_limit_must_be_yes_no_or_not_reported(self, bad):
        with pytest.raises(ProtocolViolation, match="acknowledged_limit"):
            classify(_row(acknowledged_limit=bad))

    def test_an_unmeasured_paired_budget_is_excluded_not_interpolated(self):
        c = classify(_row(estimator_family="paired_cp", budget=60))
        assert c.klass == "EXCLUDED"
        assert "no sourced ceiling" in c.reason


class TestK:
    def test_a_paper_that_acknowledged_its_limit_does_not_count_toward_k(self):
        """Protocol S8: a self-disclosed limit is a restatement, not a finding."""
        silent = classify(_row(paper_id="a", acknowledged_limit="no"))
        candid = classify(_row(paper_id="b", acknowledged_limit="yes"))
        assert silent.counts_toward_k is True
        assert candid.counts_toward_k is False

        s = summarise([silent, candid])
        assert s.n_papers_included == 2
        assert s.k == 1
        assert s.n_underpowered_but_acknowledged == 1

    def test_a_papers_class_is_its_most_favourable_configuration(self):
        """Protocol S3: the reading most generous to the paper."""
        rows = [
            _row(paper_id="p", config_label="weak", budget=60, eps_proved=7.36),
            _row(paper_id="p", config_label="strong", budget=800, eps_proved=2.0, eps_emp=1.0),
        ]
        s = summarise(classify_all(rows))
        assert s.n_papers_included == 1
        assert s.by_class["INTERPRETABLE"] == 1
        assert s.k == 0

    def test_excluded_rows_do_not_enter_the_denominator(self):
        rows = [_row(paper_id="a"), _row(paper_id="b", estimator_family="other")]
        s = summarise(classify_all(rows))
        assert s.n_papers_included == 1
        assert s.n_excluded_undeterminable_estimator == 1

    def test_the_null_is_reported_as_the_finding(self):
        """Protocol S10 declares this acceptable in advance so it cannot later be avoided."""
        s = summarise(classify_all([_row(paper_id="a", budget=800, eps_proved=2.0, eps_emp=1.0)]))
        assert s.k == 0
        assert "K = 0" in s.headline()
        assert "reports its own limits" in s.headline()

    def test_headline_carries_a_wilson_interval(self):
        rows = [_row(paper_id=f"p{i}") for i in range(10)]
        s = summarise(classify_all(rows))
        assert s.k == 10
        assert "Wilson CI" in s.headline()


class TestWilson:
    def test_it_does_not_produce_a_degenerate_interval_at_the_extremes(self):
        """The reason for choosing Wilson over the normal approximation: K may be 0 or n."""
        lo, hi = wilson_interval(0, 20)
        assert lo == 0.0 and 0.0 < hi < 0.5
        lo, hi = wilson_interval(20, 20)
        assert hi == 1.0 and 0.5 < lo < 1.0

    def test_no_trials_is_not_a_crash(self):
        assert wilson_interval(0, 0) == (0.0, 0.0)
