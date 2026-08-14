"""Tests for the DOMIAS density-ratio membership attack.

An attack is only evidence if it succeeds where success is possible and stays at chance where
it is not. Both directions are asserted here — a membership attack that reports signal on a
release containing no real record is measuring an artefact of its own estimator, which is
exactly the bug these tests were written after finding.
"""

import numpy as np
import pandas as pd
import pytest

from synthproof.attacks.distance_mia import DistanceMIABaseline
from synthproof.attacks.domias import DOMIAS
from synthproof.data.dataset import TabularDataset
from synthproof.data.schema import NUMERICAL, ColumnSpec, Schema
from synthproof.generators.leaky import LeakyGenerator


def _split(n=1200, seed=0):
    rng = np.random.default_rng(seed)
    x = rng.uniform(0, 100, n)
    y = np.clip(x * 0.8 + rng.normal(0, 10, n), 0, 100)
    df = pd.DataFrame({"x": x, "y": y})
    schema = Schema([ColumnSpec("x", NUMERICAL, lower=0.0, upper=100.0),
                     ColumnSpec("y", NUMERICAL, lower=0.0, upper=100.0)])
    half = n // 2
    train, test = df.iloc[:half], df.iloc[half:]
    return TabularDataset(train.reset_index(drop=True), schema=schema), train, test


def _release(train_ds, leak, seed=0):
    gen = LeakyGenerator(seed=seed, leak_fraction=leak)
    gen.fit(train_ds, None, None, 0.0)
    return gen.generate(train_ds.num_rows)


# ------------------------------------------------------------------ controls

def test_positive_control_detects_a_verbatim_release():
    """A release that IS its training data must be attackable above chance."""
    ds, train, test = _split()
    res = DOMIAS(seed=0).evaluate(_release(ds, 1.0), train, test)
    assert res.auc > 0.53, f"DOMIAS found no signal in a verbatim release (AUC {res.auc:.3f})"


def test_negative_control_stays_at_chance_on_a_release_with_no_real_records():
    """Regression for a real defect in this implementation.

    The reference density is fitted on the non-member split, and those records were then
    scored against it — each was its own nearest neighbour at distance 0, so its reference
    density was enormous and its ratio score pushed down. That depressed every non-member and
    manufactured AUC 0.576 on a release containing no real record at all. Leave-one-out on
    the reference density fixed it.
    """
    ds, train, test = _split()
    res = DOMIAS(seed=0).evaluate(_release(ds, 0.0), train, test)
    assert 0.45 < res.auc < 0.55, (
        f"false positive: AUC {res.auc:.3f} on a shuffled release with no real records"
    )


def test_score_is_monotone_in_leakage():
    """More memorisation must be easier to detect."""
    ds, train, test = _split()
    aucs = [DOMIAS(seed=0).evaluate(_release(ds, lf), train, test).auc
            for lf in (0.0, 0.5, 1.0)]
    assert aucs[0] < aucs[-1], f"not monotone in leakage: {aucs}"


def test_a_private_release_is_not_attackable():
    """The whole point of the mechanism: a DP release should sit at chance."""
    from synthproof.accounting.accountant import Accountant
    from synthproof.accounting.calibration import BudgetPlan
    from synthproof.data.profiler import DPDomainProfiler
    from synthproof.frontier.experiment import MECHANISMS

    ds, train, test = _split()
    plan = BudgetPlan.split(1.0, 1e-5, 0.1)
    acc = Accountant(1.02, 1e-5)
    profile = DPDomainProfiler(acc, eps_budget=plan.profile_eps).profile(ds, seed=0)
    gen = MECHANISMS["pairwise"](seed=0)
    gen.fit(ds, profile, acc, target_eps=plan.synthesis_eps)

    res = DOMIAS(seed=0).evaluate(gen.generate(ds.num_rows), train, test)
    assert 0.42 < res.auc < 0.58, f"DP release attackable at AUC {res.auc:.3f}"


# ------------------------------------------------------------------ honest comparison

def test_domias_is_not_uniformly_stronger_than_the_nearest_neighbour_baseline():
    """Recorded because it is a finding, not a defect.

    On low-dimensional numeric data the nearest-neighbour baseline reaches AUC 1.000 on a
    verbatim release where DOMIAS reaches ~0.56. DOMIAS divides by a reference density to
    remove the typicality confound, and on a fully memorised release that denominator
    actively hurts: a leaked record that is ALSO typical has its score divided down.

    The two attacks fail differently, so both are reported rather than one being presented
    as strictly better. A results chapter claiming DOMIAS dominates would be wrong.
    """
    ds, train, test = _split()
    synth = _release(ds, 1.0)

    domias = DOMIAS(seed=0).evaluate(synth, train, test)
    baseline = DistanceMIABaseline(seed=0).evaluate(synth, train, test)

    assert baseline.auc > domias.auc, (
        "the baseline no longer dominates on a verbatim release; re-check this claim "
        f"(baseline {baseline.auc:.3f}, DOMIAS {domias.auc:.3f})"
    )


# ------------------------------------------------------------------ mechanics

def test_reports_low_fpr_rates_not_just_average_accuracy():
    """Carlini et al. (2022): average accuracy is the wrong metric for membership inference."""
    ds, train, test = _split()
    res = DOMIAS(seed=0).evaluate(_release(ds, 1.0), train, test)

    assert 0.0 <= res.tpr_at_1pct_fpr <= 1.0
    assert 0.0 <= res.tpr_at_01pct_fpr <= 1.0
    assert res.tpr_at_01pct_fpr <= res.tpr_at_1pct_fpr + 1e-9
    assert not hasattr(res, "attack_accuracy"), "accuracy at a median threshold is misleading"


def test_both_estimators_are_available_and_recorded():
    ds, train, test = _split()
    synth = _release(ds, 1.0)
    for est in ("knn", "kde"):
        res = DOMIAS(seed=0, estimator=est).evaluate(synth, train, test)
        assert res.estimator == est
        assert 0.0 <= res.auc <= 1.0


def test_invalid_estimator_is_rejected():
    with pytest.raises(ValueError, match="estimator must be"):
        DOMIAS(estimator="magic")


def test_needs_both_classes_and_a_numeric_column():
    ds, train, test = _split()
    synth = _release(ds, 1.0)

    with pytest.raises(ValueError, match="member and non-member"):
        DOMIAS(seed=0).evaluate(synth, train, test.head(0))

    cat = pd.DataFrame({"g": ["a", "b"] * 10})
    with pytest.raises(ValueError, match="numeric column"):
        DOMIAS(seed=0).evaluate(cat, cat, cat)


def test_an_explicit_reference_set_is_honoured():
    """A disjoint reference is the cleaner design; the default falls back to the non-members."""
    ds, train, test = _split(n=1600)
    synth = _release(ds, 1.0)
    ref = test.tail(200)

    res = DOMIAS(seed=0).evaluate(synth, train, test.head(200), reference_df=ref)
    assert res.num_reference == 200
    assert 0.0 <= res.auc <= 1.0
