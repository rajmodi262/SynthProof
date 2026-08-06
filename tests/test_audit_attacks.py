"""Unit tests for CanaryAuditor, DistanceMIABaseline, and ExactMatchRiskEvaluator."""

import pandas as pd
import pytest

from synthproof.attacks.distance_mia import DistanceMIABaseline
from synthproof.attacks.exact_match_risk import ExactMatchRiskEvaluator
from synthproof.audit.canary import CanaryAuditor
from synthproof.data.dataset import TabularDataset


def test_canary_planting_splits_members_and_holdout():
    ds = TabularDataset.create_synthetic_toy(num_rows=50)
    auditor = CanaryAuditor(num_canaries=5, seed=42)
    aug_ds, canary_set = auditor.plant_canaries(ds)

    # Only the members are planted; the holdout must stay out of the training data.
    assert aug_ds.num_rows == 55
    assert len(canary_set.members) == 5
    assert len(canary_set.holdout) == 5


def test_canary_audit_detects_leakage_and_reports_zero_when_absent():
    ds = TabularDataset.create_synthetic_toy(num_rows=200)
    auditor = CanaryAuditor(num_canaries=30, seed=42)
    aug_ds, canary_set = auditor.plant_canaries(ds)

    # Worst case: the "synthetic" output is the training table verbatim.
    leaky = auditor.audit(synthetic_df=aug_ds.df, canary_set=canary_set)
    assert leaky.tpr == 1.0
    assert leaky.audited_eps > 0.0
    assert leaky.p_value < 0.05

    # Control: output that never saw the canaries must not yield a positive bound.
    clean = auditor.audit(synthetic_df=ds.df, canary_set=canary_set)
    assert clean.audited_eps < leaky.audited_eps
    assert clean.audited_eps == 0.0


def test_canary_audit_reports_measured_not_assumed_fpr():
    """Regression: the FPR must come from held-out canaries, not a hardcoded 0.05."""
    ds = TabularDataset.create_synthetic_toy(num_rows=100)
    auditor = CanaryAuditor(num_canaries=10, seed=7)
    aug_ds, canary_set = auditor.plant_canaries(ds)
    res = auditor.audit(synthetic_df=aug_ds.df, canary_set=canary_set)

    assert res.num_holdout == 10
    # fpr must be a realisable value of fp/num_holdout, i.e. a multiple of 1/10.
    assert res.fpr == pytest.approx(round(res.fpr * 10) / 10)
    assert 0.0 <= res.fpr_upper <= 1.0
    assert res.tpr_lower <= res.tpr


def test_distance_mia_reports_real_auc():
    """Regression: AUC must be computed, not derived as `accuracy + 0.05`."""
    ds = TabularDataset.create_synthetic_toy(num_rows=100)
    attack = DistanceMIABaseline(seed=42)
    res = attack.evaluate(
        synthetic_df=ds.df.head(50), train_df=ds.df.head(50), test_df=ds.df.tail(50)
    )

    assert 0.0 <= res.auc <= 1.0
    assert 0.0 <= res.advantage <= 1.0
    assert res.attack_accuracy == pytest.approx(0.5 * (1.0 + res.advantage))
    # Members were the synthesiser's own input, so the attack must beat chance here.
    assert res.auc > 0.5


def test_distance_mia_requires_both_classes():
    ds = TabularDataset.create_synthetic_toy(num_rows=20)
    with pytest.raises(ValueError):
        DistanceMIABaseline(seed=42).evaluate(
            synthetic_df=ds.df, train_df=ds.df, test_df=ds.df.head(0)
        )


def test_exact_match_risk_is_a_single_measured_field():
    """Regression: linkability/inference were affine fakes and must not return."""
    ds = TabularDataset.create_synthetic_toy(num_rows=100)
    res = ExactMatchRiskEvaluator(seed=42).evaluate(
        synthetic_df=ds.df, target_df=ds.df.head(50)
    )

    assert 0.0 <= res.singling_out_risk <= 1.0
    assert res.num_scored == 50
    assert not hasattr(res, "linkability_risk")
    assert not hasattr(res, "inference_risk")


def test_exact_match_risk_detects_verbatim_copies():
    df = pd.DataFrame({"a": ["x", "y", "z"], "b": ["1", "2", "3"]})
    res = ExactMatchRiskEvaluator(seed=1).evaluate(synthetic_df=df, target_df=df)
    assert res.singling_out_risk == 1.0
