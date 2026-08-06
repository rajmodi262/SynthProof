"""Unit tests for UtilityEvaluator, FrontierEngine, and PrivacyDataSheet export."""

import pytest
from synthproof.data.dataset import TabularDataset
from synthproof.evaluate.utility import UtilityEvaluator
from synthproof.frontier.certificate import FrontierEngine


def test_utility_evaluator():
    ds = TabularDataset.create_synthetic_toy(num_rows=100)
    evaluator = UtilityEvaluator(target_col="category", seed=42)
    res = evaluator.evaluate(real_df=ds.df, synthetic_df=ds.df)

    assert 0.0 <= res.tstr_macro_f1 <= 1.0
    assert 0.0 <= res.trtr_macro_f1 <= 1.0
    assert res.utility_gap >= 0.0


def test_trtr_is_held_out_not_in_sample():
    """Regression: TRTR used to be `clf.predict(X_train)`, a constant ~0.971.

    The toy dataset's label is independent of its features, so an honest held-out TRTR
    must land near chance. An in-sample score would be near 1.0.
    """
    ds = TabularDataset.create_synthetic_toy(num_rows=200)
    res = UtilityEvaluator(target_col="category", seed=42).evaluate(ds.df, ds.df)
    assert res.trtr_macro_f1 < 0.6, (
        f"TRTR={res.trtr_macro_f1:.3f} is implausibly high for random labels — "
        "it is probably being scored in-sample again"
    )


def test_utility_evaluator_raises_instead_of_returning_mock_values():
    """Regression: a schema mismatch used to silently return hardcoded 0.75/0.80."""
    ds = TabularDataset.create_synthetic_toy(num_rows=50)
    with pytest.raises(ValueError, match="not found"):
        UtilityEvaluator(target_col="does_not_exist", seed=42).evaluate(ds.df, ds.df)


def test_utility_result_has_no_fabricated_fairness_field():
    ds = TabularDataset.create_synthetic_toy(num_rows=100)
    res = UtilityEvaluator(target_col="category", seed=42).evaluate(ds.df, ds.df)
    assert not hasattr(res, "fairness_drift")


def test_frontier_engine_sweep_and_certificate():
    ds = TabularDataset.create_synthetic_toy(num_rows=50)
    engine = FrontierEngine(seed=42)
    datasheet = engine.run_sweep(ds, eps_grid=[0.5, 1.0])

    assert datasheet.dataset_name == ds.name
    assert len(datasheet.frontier_curve) == 2
    json_str = datasheet.to_json()
    assert "total_proved_eps" in json_str
    assert "AIM_Marginal_Generator" in json_str

    # Regression: the ledger hash used to be the all-zero genesis hash because the
    # engine created a Ledger and never appended to it.
    assert datasheet.ledger_hash != "0" * 64


def test_frontier_engine_honours_mechanism_selection():
    """Regression: `mechanism` was accepted and silently ignored (always AIM)."""
    ds = TabularDataset.create_synthetic_toy(num_rows=50)
    engine = FrontierEngine(seed=42)

    aim = engine.run_sweep(ds, eps_grid=[1.0], mechanism="AIM / MST")
    copula = engine.run_sweep(ds, eps_grid=[1.0], mechanism="Gaussian Copula")

    assert aim.mechanism_used == "AIM_Marginal_Generator"
    assert copula.mechanism_used == "Gaussian_Copula_Generator"
