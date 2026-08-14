"""Tests for the one-run audit (Steinke, Nasr & Jagielski 2023).

The estimator is the load-bearing part: it converts a count of correct guesses into a claimed
privacy lower bound. If it is wrong in the optimistic direction the project publishes an
epsilon it cannot support, so the tests below pin the mathematics before touching any data.
"""

import numpy as np
import pytest

from synthproof.audit.steinke import (
    SteinkeAuditor,
    canaries_needed_for,
    compare_auditors,
    default_delta_correction,
    epsilon_lower_bound,
    max_provable_epsilon,
)
from synthproof.data.dataset import TabularDataset
from synthproof.generators.leaky import LeakyGenerator

# ------------------------------------------------------------------ the estimator

def test_chance_level_evidence_certifies_nothing():
    """Half the guesses correct is exactly what a perfectly private mechanism produces."""
    assert epsilon_lower_bound(30, 60) == 0.0
    assert epsilon_lower_bound(50, 100) == 0.0
    assert epsilon_lower_bound(5, 10) == 0.0


def test_worse_than_chance_certifies_nothing():
    assert epsilon_lower_bound(10, 60) == 0.0
    assert epsilon_lower_bound(0, 60) == 0.0


def test_bound_is_monotone_in_correct_guesses():
    """More evidence can never certify less."""
    vals = [epsilon_lower_bound(c, 60) for c in range(30, 61)]
    assert vals == sorted(vals)


def test_bound_is_monotone_in_sample_size_for_a_perfect_adversary():
    """A perfect adversary with more canaries must certify more."""
    vals = [epsilon_lower_bound(r, r) for r in (10, 25, 50, 100, 400, 800)]
    assert vals == sorted(vals)


def test_a_perfect_adversary_certifies_exactly_the_ceiling():
    """The ceiling is defined by the all-correct case, so the two must agree."""
    for r in (10, 60, 200, 800):
        assert epsilon_lower_bound(r, r) == pytest.approx(max_provable_epsilon(r), abs=1e-6)


def test_tiny_samples_cannot_certify_anything():
    """3 correct out of 3 happens with probability 0.125 by chance — above alpha=0.05."""
    assert epsilon_lower_bound(3, 3) == 0.0
    # 5 of 5 is 0.031, which does clear it.
    assert epsilon_lower_bound(5, 5) > 0.0


def test_the_ceiling_matches_its_closed_form():
    """eps_max = log(a/(1-a)) with a = alpha^(1/r). Guards against a silent regression."""
    import math
    for r in (10, 60, 500):
        a = 0.05 ** (1.0 / r)
        assert max_provable_epsilon(r) == pytest.approx(math.log(a / (1 - a)), rel=1e-9)


def test_certifying_a_large_epsilon_needs_exponentially_many_canaries():
    """The result that disqualifies canary auditing at this project's proved epsilons.

    Roughly ln(1/alpha)*e^eps canaries are required, so the cost of certification grows
    exponentially in the epsilon being certified.
    """
    assert canaries_needed_for(1.0) < 20
    assert canaries_needed_for(4.0) < 250
    # The proved epsilon in the H1 experiments is 7.36.
    assert canaries_needed_for(7.36) > 4000
    # Exponential, not linear: doubling epsilon does far more than double the requirement.
    assert canaries_needed_for(8.0) > 20 * canaries_needed_for(4.0)


def test_delta_is_absorbed_conservatively():
    """A delta large enough to consume alpha must collapse the bound, not inflate it."""
    strong = epsilon_lower_bound(60, 60, alpha=0.05, delta=0.0)
    weakened = epsilon_lower_bound(60, 60, alpha=0.05, delta=1e-3)
    assert weakened <= strong
    # delta * r >= alpha leaves no confidence budget at all.
    assert epsilon_lower_bound(60, 60, alpha=0.05, delta=0.01) == 0.0


def test_delta_correction_warns_only_when_it_matters():
    assert default_delta_correction(60, 1e-5) is None       # negligible
    assert default_delta_correction(60, 1e-3) is not None   # consumes >10% of alpha


# ------------------------------------------------------------------ planting

def test_inclusion_is_randomised_and_only_included_canaries_are_planted():
    ds = TabularDataset.create_synthetic_toy(num_rows=500)
    auditor = SteinkeAuditor(num_canaries=100, seed=0)
    aug, cset = auditor.plant_canaries(ds)

    assert len(cset.canaries) == 100
    # Roughly half included at p=0.5; a wide band, this is only guarding against 0 or all.
    assert 25 < cset.num_included < 75
    # The augmented table grew by exactly the number included, not by all 100.
    assert aug.num_rows == ds.num_rows + cset.num_included
    assert aug.schema is not None, "planting must not drop the schema"


def test_planting_never_produces_a_degenerate_inclusion_vector():
    """All-in or all-out carries no signal in one direction and makes the audit vacuous."""
    ds = TabularDataset.create_synthetic_toy(num_rows=200)
    for seed in range(10):
        _, cset = SteinkeAuditor(num_canaries=4, seed=seed, inclusion_prob=0.9).plant_canaries(ds)
        assert 0 < cset.num_included < 4


def test_constructor_validates_its_arguments():
    with pytest.raises(ValueError, match="num_canaries"):
        SteinkeAuditor(num_canaries=1)
    with pytest.raises(ValueError, match="inclusion_prob"):
        SteinkeAuditor(inclusion_prob=0.0)
    with pytest.raises(ValueError, match="abstain_frac"):
        SteinkeAuditor(abstain_frac=1.0)


# ------------------------------------------------------------------ controls

def test_positive_control_a_verbatim_release_is_detected():
    """THE control. An auditor that cannot see this has no standing to report a null."""
    ds = TabularDataset.create_synthetic_toy(num_rows=800)
    auditor = SteinkeAuditor(num_canaries=100, seed=0)
    aug, cset = auditor.plant_canaries(ds)

    gen = LeakyGenerator(seed=0, leak_fraction=1.0)
    gen.fit(aug, None, None, 0.0)
    res = auditor.audit(gen.generate(aug.num_rows), cset)

    assert res.audited_eps > 0.0, "one-run auditor is blind to a verbatim release"
    assert res.p_value < 0.05
    assert res.accuracy > 0.5
    assert "detected" in res.interpretation().lower()


def test_negative_control_a_release_with_no_real_records_does_not_fire():
    """Marginals are preserved exactly and no individual is present, so nothing may be
    certified. A metric that fires here measures similarity, not disclosure."""
    ds = TabularDataset.create_synthetic_toy(num_rows=800)
    auditor = SteinkeAuditor(num_canaries=100, seed=3)
    aug, cset = auditor.plant_canaries(ds)

    gen = LeakyGenerator(seed=3, leak_fraction=0.0)
    gen.fit(aug, None, None, 0.0)
    res = auditor.audit(gen.generate(aug.num_rows), cset)

    assert res.audited_eps == 0.0, f"false positive: eps={res.audited_eps:.3f}"


def test_a_reported_bound_never_exceeds_its_own_ceiling():
    """An epsilon above the ceiling would be arithmetically impossible."""
    ds = TabularDataset.create_synthetic_toy(num_rows=600)
    for m in (20, 60, 150):
        auditor = SteinkeAuditor(num_canaries=m, seed=1)
        aug, cset = auditor.plant_canaries(ds)
        gen = LeakyGenerator(seed=1, leak_fraction=1.0)
        gen.fit(aug, None, None, 0.0)
        res = auditor.audit(gen.generate(aug.num_rows), cset)
        assert res.audited_eps <= res.ceiling + 1e-9
        assert res.ceiling == pytest.approx(max_provable_epsilon(res.guesses))


def test_saturation_is_flagged_rather_than_reported_as_a_finding():
    """A saturated bound means 'at least this much', not 'exactly this much'."""
    ds = TabularDataset.create_synthetic_toy(num_rows=400)
    auditor = SteinkeAuditor(num_canaries=30, seed=2)
    aug, cset = auditor.plant_canaries(ds)
    gen = LeakyGenerator(seed=2, leak_fraction=1.0)
    gen.fit(aug, None, None, 0.0)
    res = auditor.audit(gen.generate(aug.num_rows), cset)

    if res.saturated:
        assert "may be far higher" in res.interpretation()


def test_interpretation_explains_a_null_instead_of_leaving_a_bare_zero():
    ds = TabularDataset.create_synthetic_toy(num_rows=400)
    auditor = SteinkeAuditor(num_canaries=40, seed=5)
    aug, cset = auditor.plant_canaries(ds)
    gen = LeakyGenerator(seed=5, leak_fraction=0.0)
    gen.fit(aug, None, None, 0.0)
    res = auditor.audit(gen.generate(aug.num_rows), cset)

    text = res.interpretation()
    assert "rules out nothing" in text
    assert f"{res.ceiling:.2f}" in text


def test_auditor_comparison_reports_the_canary_cost_of_each_epsilon():
    c = compare_auditors(100)
    assert c["one_run_guesses"] == 100
    assert c["one_run_ceiling"] == pytest.approx(max_provable_epsilon(100), abs=1e-4)
    # The paired auditor spends two canaries per comparison; the one-run construction spends one.
    assert c["paired_effective_canaries"] == 50
    assert c["canaries_for_eps_8"] > c["canaries_for_eps_4"] > c["canaries_for_eps_1"]


def test_detection_improves_on_average_with_more_canaries():
    """More evidence certifies more — but only in expectation, not seed by seed.

    The bound is monotone in `correct` at fixed `r`, and monotone in `r` for a PERFECT
    adversary (both asserted above). With a REAL adversary, accuracy varies with which
    canaries happen to be drawn, so a single seed can certify less at m=60 than at m=20.
    Measured: [1.82, 1.61, 2.61] for seed 7. That is sampling noise in the adversary, not a
    defect in the estimator, and asserting per-seed monotonicity would be asserting something
    the mathematics does not promise.
    """
    ds = TabularDataset.create_synthetic_toy(num_rows=1200)
    means = []
    for m in (20, 60, 150):
        per_seed = []
        for seed in range(5):
            auditor = SteinkeAuditor(num_canaries=m, seed=seed)
            aug, cset = auditor.plant_canaries(ds)
            gen = LeakyGenerator(seed=seed, leak_fraction=1.0)
            gen.fit(aug, None, None, 0.0)
            per_seed.append(auditor.audit(gen.generate(aug.num_rows), cset).audited_eps)
        means.append(float(np.mean(per_seed)))

    assert means == sorted(means), f"mean bound not increasing in canary count: {means}"
    assert means[-1] > means[0] * 1.2, f"more canaries bought too little: {means}"
