"""Unit tests for TabularDataset and DPDomainProfiler."""

import pytest

from synthproof.accounting.accountant import Accountant
from synthproof.data.dataset import TabularDataset
from synthproof.data.profiler import DPDomainProfiler


def test_tabular_dataset_classification():
    ds = TabularDataset.create_synthetic_toy(num_rows=50)
    assert ds.num_rows == 50
    assert ds.num_cols == 3
    assert "age" in ds.numerical_cols or "income" in ds.numerical_cols
    assert "category" in ds.categorical_cols


def test_dp_domain_profiler_charges_budget():
    ds = TabularDataset.create_synthetic_toy(num_rows=50)
    acc = Accountant(budget_eps=2.0, budget_delta=1e-5)
    
    initial_spends = len(acc.spends)
    profiler = DPDomainProfiler(accountant=acc, eps_budget=0.5)
    profile = profiler.profile(ds)
    
    assert len(profile.columns) == 3
    assert len(acc.spends) > initial_spends
    assert acc.total() > 0.0

    age_prof = profile.columns["age"]
    assert age_prof.min_val is not None
    assert age_prof.max_val is not None
    assert age_prof.min_val < age_prof.max_val


def test_sensitivity_is_derived_from_schema_width():
    """Regression for audit finding F5.

    A range query on a column clipped to [0, 500000] is vastly more sensitive than a count.
    Asserting sensitivity=1.0 for both, as an earlier version did, has no basis.
    """
    import numpy as np
    import pandas as pd

    from synthproof.data.schema import CATEGORICAL, NUMERICAL, ColumnSpec, Schema

    rng = np.random.default_rng(1)
    df = pd.DataFrame({
        "age": rng.integers(18, 80, 200),
        "income": rng.normal(5e4, 1e4, 200),
        "g": rng.choice(["a", "b"], 200),
    })
    ds = TabularDataset(df, schema=Schema([
        ColumnSpec("age", NUMERICAL, lower=0.0, upper=120.0),
        ColumnSpec("income", NUMERICAL, lower=0.0, upper=5e5),
        ColumnSpec("g", CATEGORICAL, categories=["a", "b"]),
    ]))

    profiler = DPDomainProfiler(accountant=Accountant(10.0, 1e-5), eps_budget=0.5)
    assert profiler._sensitivity_for(ds, "age") == 120.0
    assert profiler._sensitivity_for(ds, "income") == 5e5
    assert profiler._sensitivity_for(ds, "g") == 1.0


def test_profiling_spends_exactly_its_budget_despite_mixed_sensitivities():
    """A shared noise multiplier keeps every query on the same RDP curve."""
    ds = TabularDataset.create_synthetic_toy(200)
    for budget in (0.2, 1.0, 2.0):
        acc = Accountant(budget_eps=10.0, budget_delta=1e-5)
        profile = DPDomainProfiler(accountant=acc, eps_budget=budget).profile(ds, seed=0)
        assert profile.eps_spent == pytest.approx(budget, rel=0.02)


def test_rare_categories_are_suppressed_not_published():
    """Regression for audit finding F5: the domain used to be released verbatim."""
    import pandas as pd

    # One value appears once; it must not survive into the released domain.
    df = pd.DataFrame({"g": ["common"] * 400 + ["unique_person"]})
    ds = TabularDataset(df)
    acc = Accountant(budget_eps=10.0, budget_delta=1e-5)
    profile = DPDomainProfiler(accountant=acc, eps_budget=0.5).profile(ds, seed=3)

    assert "unique_person" not in (profile.columns["g"].categories or [])
    assert profile.columns["g"].suppressed_categories >= 1
