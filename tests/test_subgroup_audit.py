"""Tests for the per-subgroup auditor — the instrument behind H2.

H2's headline is a null, and a null is only publishable if the instrument provably works.
These tests pin the design decisions the null rests on: equal allocation, the per-group
ceiling, and the fact that a subgroup canary really does belong to its subgroup.
"""

import numpy as np
import pandas as pd
import pytest

from synthproof.audit.steinke import max_provable_epsilon
from synthproof.audit.subgroup import (
    SubgroupAudit,
    SubgroupAuditResult,
    SubgroupCanaryAuditor,
    summarise,
)
from synthproof.data.dataset import TabularDataset


def _skewed(n=2000, seed=0):
    """A table whose `race` mirrors Adult's skew: one group is well under 1%."""
    rng = np.random.default_rng(seed)
    race = rng.choice(
        ["White", "Black", "Asian", "Amer-Indian", "Other"],
        size=n,
        p=[0.855, 0.10, 0.03, 0.008, 0.007],
    )
    return TabularDataset(
        df=pd.DataFrame(
            {
                "age": rng.integers(18, 90, n).astype(float),
                "hours": rng.integers(1, 99, n).astype(float),
                "race": race,
                "sex": rng.choice(["Male", "Female"], n),
                "income": rng.choice(["<=50K", ">50K"], n),
            }
        ),
        name="skewed",
    )


def _audit(subgroup, share, m, correct):
    """A SubgroupAudit with a hand-set outcome, for testing the reporting logic alone."""
    from synthproof.audit.steinke import epsilon_lower_bound

    eps = epsilon_lower_bound(correct, m, alpha=0.05)
    return SubgroupAudit(
        subgroup=subgroup,
        population_share=share,
        num_canaries=m,
        num_included=m // 2,
        guesses=m,
        correct=correct,
        accuracy=correct / m,
        audited_eps=eps,
        ceiling=max_provable_epsilon(m, 0.05),
        p_value=0.5,
        saturated=False,
    )


# ------------------------------------------------------------------ allocation


def test_equal_allocation_gives_every_group_the_same_canary_count():
    """The core H2 design decision.

    Proportional allocation would hand the rare groups H2 is *about* the weakest instrument.
    Equal allocation deliberately oversamples them.
    """
    alloc = SubgroupCanaryAuditor(
        "race", num_canaries=400, balanced=True, min_per_group=20
    ).allocate(_skewed())
    assert len(set(alloc.values())) == 1, alloc
    assert sum(alloc.values()) <= 400


def test_proportional_allocation_starves_the_rare_groups_which_is_why_it_is_not_default():
    """The contrast that justifies `balanced=True`. If this ever flips, the default is wrong."""
    ds = _skewed()
    prop = SubgroupCanaryAuditor(
        "race", num_canaries=400, balanced=False, min_per_group=1
    ).allocate(ds)
    bal = SubgroupCanaryAuditor("race", num_canaries=400, balanced=True, min_per_group=1).allocate(
        ds
    )
    assert prop["Amer-Indian"] < bal["Amer-Indian"]
    assert prop["White"] > bal["White"]


def test_a_group_too_small_to_certify_anything_is_dropped_not_audited_as_zero():
    """An epsilon of 0 from 3 canaries is noise, and reporting it beside 0 from 200 would
    invite reading them as the same finding."""
    alloc = SubgroupCanaryAuditor(
        "race", num_canaries=30, balanced=True, min_per_group=20
    ).allocate(_skewed())
    assert alloc == {}, "30 canaries over 5 groups is 6 each; none should qualify"


def test_a_missing_attribute_fails_loudly():
    with pytest.raises(KeyError, match="not in the table"):
        SubgroupCanaryAuditor("ethnicity").allocate(_skewed())


def test_too_few_canaries_is_rejected_at_construction():
    with pytest.raises(ValueError, match="must be >= 2"):
        SubgroupCanaryAuditor("race", num_canaries=1)


# ------------------------------------------------------------------ the ceiling


def test_the_per_group_ceiling_falls_as_the_attribute_gains_levels():
    """Pins the cross-dataset caveat documented in scripts/run_h2.py.

    A fixed canary budget split equally means more levels -> fewer canaries each -> a lower
    ceiling. Adult's `race` has 5 levels and ACS's `RAC1P` has 9, so ACS's race instrument is
    genuinely weaker BEFORE any mechanism runs. Any Adult-vs-ACS H2 comparison has to say so.
    """
    adult_race = max_provable_epsilon(400 // 5, 0.05)
    acs_race = max_provable_epsilon(400 // 9, 0.05)
    assert adult_race == pytest.approx(3.2661, abs=1e-3)
    assert acs_race == pytest.approx(2.6528, abs=1e-3)
    assert acs_race < adult_race


def test_every_subgroup_reports_its_own_ceiling_not_a_shared_one():
    """Comparing eps=0 in a group of 8 against eps=0 in a group of 300 is meaningless; the
    per-group ceiling is what makes that visible in the output."""
    ds = _skewed()
    auditor = SubgroupCanaryAuditor("race", num_canaries=200, seed=1, min_per_group=20)
    aug, sets = auditor.plant_stratified(ds)
    res = auditor.audit_release(ds, aug.df, sets)
    for s in res.subgroups:
        assert s.ceiling == pytest.approx(max_provable_epsilon(s.num_canaries, 0.05))


# ------------------------------------------------------------------ planting


def test_a_subgroup_canary_actually_belongs_to_its_subgroup():
    """Without the forced assignment, a canary would join its group only by chance and the
    per-group audit would be measuring nothing at all."""
    ds = _skewed()
    auditor = SubgroupCanaryAuditor("race", num_canaries=200, seed=3, min_per_group=20)
    _, sets = auditor.plant_stratified(ds)
    for level, cset in sets.items():
        assert set(cset.canaries["race"]) == {level}


def test_the_inclusion_vector_is_never_degenerate():
    """All-in or all-out makes the binomial test vacuous. Checked across many seeds because
    it is a rare random event, not a deterministic one."""
    ds = _skewed()
    for seed in range(15):
        auditor = SubgroupCanaryAuditor("sex", num_canaries=60, seed=seed, min_per_group=20)
        _, sets = auditor.plant_stratified(ds)
        for cset in sets.values():
            assert 0 < int(cset.included.sum()) < len(cset.included)


def test_only_the_included_canaries_reach_the_augmented_table():
    """The whole one-run construction rests on this: excluded canaries must never be fitted."""
    ds = _skewed()
    auditor = SubgroupCanaryAuditor("sex", num_canaries=100, seed=5, min_per_group=20)
    aug, sets = auditor.plant_stratified(ds)
    expected = sum(int(c.included.sum()) for c in sets.values())
    assert aug.num_rows == ds.num_rows + expected


def test_planting_is_reproducible_under_a_seed():
    ds = _skewed()
    a, sa = SubgroupCanaryAuditor("sex", num_canaries=80, seed=11).plant_stratified(ds)
    b, sb = SubgroupCanaryAuditor("sex", num_canaries=80, seed=11).plant_stratified(ds)
    assert a.num_rows == b.num_rows
    for lv in sa:
        assert np.array_equal(sa[lv].included, sb[lv].included)


def test_planting_raises_rather_than_returning_an_empty_audit():
    """Silently returning nothing would read downstream as 'no leakage found'."""
    with pytest.raises(ValueError, match="No subgroup"):
        SubgroupCanaryAuditor("race", num_canaries=30, min_per_group=20).plant_stratified(_skewed())


# ------------------------------------------------------------------ reporting


def test_leakage_gap_is_rarest_minus_most_common_so_positive_supports_h2():
    """The sign convention is the whole claim. Inverted, a null would read as confirmation."""
    res = SubgroupAuditResult(
        attribute="race",
        subgroups=[
            _audit("Amer-Indian", 0.008, 80, 62),  # rare, leaks more
            _audit("White", 0.855, 80, 41),
        ],
    )
    assert res.rarest.subgroup == "Amer-Indian"
    assert res.most_common.subgroup == "White"
    assert res.leakage_gap() > 0


def test_an_unmeasurable_result_says_so_instead_of_reading_as_no_difference():
    """Standing rule 5: a null is a result, but it must be framed as instrument limitation
    when that is what it is."""
    res = SubgroupAuditResult(
        attribute="race",
        subgroups=[
            _audit("Amer-Indian", 0.008, 80, 40),  # chance accuracy -> eps 0
            _audit("White", 0.855, 80, 40),
        ],
    )
    text = res.interpretation()
    assert "UNMEASURABLE" in text
    assert res.leakage_gap() == 0.0
    # It must name the ceiling, or a reader cannot tell a weak instrument from a real null.
    assert "ceiling" in text.lower()


def test_a_single_measurable_subgroup_refuses_to_report_a_comparison():
    res = SubgroupAuditResult(attribute="sex", subgroups=[_audit("Female", 0.33, 200, 160)])
    assert res.leakage_gap() is None
    assert "no comparison" in res.interpretation().lower()


def test_summarise_prints_every_subgroup_with_its_ceiling():
    res = SubgroupAuditResult(
        attribute="race",
        subgroups=[_audit("Amer-Indian", 0.008, 80, 62), _audit("White", 0.855, 80, 41)],
    )
    out = summarise([res])
    assert "Amer-Indian" in out and "White" in out
    assert "ceiling" in out
