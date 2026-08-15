"""Tests for attribute inference and, more importantly, its baselines.

Jayaraman & Evans (CCS 2022) showed a naive imputation attacker outperforming three published
state-of-the-art attribute-inference attacks. Reporting raw attack accuracy as "leakage"
therefore measures how PREDICTABLE an attribute is, not how much a release LEAKED. These tests
pin the baselines that make the difference meaningful.
"""

import numpy as np
import pandas as pd
import pytest

from synthproof.attacks.attribute_inference import AttributeInferenceAttack
from synthproof.data.dataset import TabularDataset
from synthproof.data.schema import CATEGORICAL, NUMERICAL, ColumnSpec, Schema
from synthproof.generators.leaky import LeakyGenerator


def _population(n=2400, seed=0):
    """A table where the sensitive column is largely predictable from the others.

    Deliberately predictable: that is the regime where a naive attacker scores well and a
    careless evaluation would mistake predictability for leakage.
    """
    rng = np.random.default_rng(seed)
    age = rng.uniform(18, 80, n)
    hours = rng.uniform(10, 60, n)
    # Threshold 4.2 gives a ~75/25 class split, matching UCI Adult's imbalance. That
    # imbalance is what makes the point: a naive attacker scores ~0.75 on prevalence alone.
    high = (0.03 * age + 0.05 * hours + rng.normal(0, 1.2, n)) > 4.2
    df = pd.DataFrame({"age": age, "hours": hours,
                       "income": np.where(high, ">50K", "<=50K")})
    schema = Schema([
        ColumnSpec("age", NUMERICAL, lower=18.0, upper=80.0),
        ColumnSpec("hours", NUMERICAL, lower=10.0, upper=60.0),
        ColumnSpec("income", CATEGORICAL, categories=["<=50K", ">50K"]),
    ])
    third = n // 3
    return (TabularDataset(df.iloc[:third].reset_index(drop=True), schema=schema),
            df.iloc[:400].reset_index(drop=True),             # targets (in the fit set)
            df.iloc[third:2 * third].reset_index(drop=True))  # reference (unseen)


def _release(fit_ds, leak, seed=0):
    gen = LeakyGenerator(seed=seed, leak_fraction=leak)
    gen.fit(fit_ds, None, None, 0.0)
    return gen.generate(fit_ds.num_rows)


# ------------------------------------------------------------------ the central point

def test_a_release_with_no_real_records_shows_no_leakage_despite_high_raw_accuracy():
    """THE test. Raw attack accuracy is not leakage.

    A shuffled release preserves every marginal and contains no real record, so it cannot
    have leaked anything. The attack still scores well above chance — because the attribute
    is predictable — and only the comparison against an attacker who never saw the release
    reveals that nothing was leaked. Measured on UCI Adult: the attack reached 0.730 on a
    shuffled release, which reads as alarming until set against a baseline of 0.828.
    """
    fit_ds, targets, reference = _population()
    res = AttributeInferenceAttack("income", seed=0).evaluate(
        _release(fit_ds, 0.0), targets, reference)

    assert res.attack_accuracy > 0.65, (
        f"the attack scored only {res.attack_accuracy:.3f}; it should look non-trivially "
        "good here, because that is exactly what makes raw accuracy misleading"
    )
    assert res.leakage_vs_conditional <= 0.02, (
        f"false leakage {res.leakage_vs_conditional:+.3f} on a release with no real records"
    )
    assert not res.leaks
    assert "No individual-level leakage" in res.interpretation()


def test_a_verbatim_release_shows_real_leakage():
    """The positive control: a release that IS the training data must beat the baseline."""
    fit_ds, targets, reference = _population()
    res = AttributeInferenceAttack("income", seed=0).evaluate(
        _release(fit_ds, 1.0), targets, reference)

    assert res.leakage_vs_conditional > 0.02, (
        f"no leakage detected on a verbatim release ({res.leakage_vs_conditional:+.3f})"
    )
    assert res.leaks
    assert "Leakage of" in res.interpretation()


def test_leakage_is_monotone_in_memorisation():
    fit_ds, targets, reference = _population()
    atk = AttributeInferenceAttack("income", seed=0)
    leaks = [atk.evaluate(_release(fit_ds, lf), targets, reference).leakage_vs_conditional
             for lf in (0.0, 1.0)]
    assert leaks[0] < leaks[1]


def test_a_dp_release_does_not_leak_beyond_the_population():
    from synthproof.accounting.accountant import Accountant
    from synthproof.accounting.calibration import BudgetPlan
    from synthproof.data.profiler import DPDomainProfiler
    from synthproof.frontier.experiment import MECHANISMS

    fit_ds, targets, reference = _population()
    plan = BudgetPlan.split(1.0, 1e-5, 0.1)
    acc = Accountant(1.02, 1e-5)
    profile = DPDomainProfiler(acc, eps_budget=plan.profile_eps).profile(fit_ds, seed=0)
    gen = MECHANISMS["pairwise"](seed=0)
    gen.fit(fit_ds, profile, acc, target_eps=plan.synthesis_eps)

    res = AttributeInferenceAttack("income", seed=0).evaluate(
        gen.generate(fit_ds.num_rows), targets, reference)
    assert not res.leaks, f"DP release leaked {res.leakage_vs_conditional:+.3f}"


# ------------------------------------------------------------------ baselines

def test_both_baselines_are_computed_and_the_conditional_is_the_stronger_one():
    """The marginal baseline is the floor; the conditional captures everything an attacker
    could learn about the population without the release, so it is the one that matters."""
    fit_ds, targets, reference = _population()
    res = AttributeInferenceAttack("income", seed=0).evaluate(
        _release(fit_ds, 1.0), targets, reference)

    assert 0.0 < res.marginal_baseline < 1.0
    assert res.conditional_baseline >= res.marginal_baseline - 0.05, (
        "the conditional baseline should be at least as strong as always-guess-majority"
    )
    assert res.leakage_vs_conditional <= res.leakage_vs_marginal + 1e-9


def test_the_marginal_baseline_matches_the_majority_class_share():
    """Always predicting the most frequent value must score its prevalence."""
    fit_ds, targets, reference = _population()
    res = AttributeInferenceAttack("income", seed=0).evaluate(
        _release(fit_ds, 1.0), targets, reference)
    assert res.marginal_baseline == pytest.approx(
        max(targets["income"].value_counts(normalize=True)), abs=0.05
    )


def test_result_carries_the_context_needed_to_read_it():
    fit_ds, targets, reference = _population()
    res = AttributeInferenceAttack("income", seed=0).evaluate(
        _release(fit_ds, 1.0), targets, reference)
    assert res.num_targets == 400
    assert res.num_classes == 2
    assert 0.0 < res.majority_class_share < 1.0
    assert 0.0 <= res.attack_macro_f1 <= 1.0


# ------------------------------------------------------------------ mechanics

def test_a_missing_target_column_raises_rather_than_guessing():
    fit_ds, targets, reference = _population()
    with pytest.raises(ValueError, match="missing from the"):
        AttributeInferenceAttack("nonexistent", seed=0).evaluate(
            _release(fit_ds, 1.0), targets, reference)


def test_no_shared_auxiliary_columns_raises():
    fit_ds, targets, reference = _population()
    only_target = targets[["income"]]
    with pytest.raises(ValueError, match="No shared auxiliary columns"):
        AttributeInferenceAttack("income", seed=0).evaluate(
            only_target, only_target, only_target)


def test_categories_are_encoded_over_the_union_so_frames_stay_aligned():
    """Encoding each frame separately gives them different column spaces, and a model trained
    on one silently misaligns when applied to another."""
    syn = pd.DataFrame({"g": ["a"] * 60, "income": ["<=50K"] * 30 + [">50K"] * 30})
    tgt = pd.DataFrame({"g": ["b"] * 40, "income": ["<=50K"] * 20 + [">50K"] * 20})
    ref = pd.DataFrame({"g": ["c"] * 40, "income": ["<=50K"] * 20 + [">50K"] * 20})

    res = AttributeInferenceAttack("income", seed=0).evaluate(syn, tgt, ref)
    assert 0.0 <= res.attack_accuracy <= 1.0
