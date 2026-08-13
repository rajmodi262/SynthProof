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


def _bounded_dataset(n=200):
    import numpy as np
    import pandas as pd

    from synthproof.data.schema import CATEGORICAL, NUMERICAL, ColumnSpec, Schema

    rng = np.random.default_rng(1)
    df = pd.DataFrame({
        "age": rng.integers(18, 80, n),
        "income": rng.normal(5e4, 1e4, n),
        "g": rng.choice(["a", "b"], n),
    })
    return TabularDataset(df, schema=Schema([
        ColumnSpec("age", NUMERICAL, lower=0.0, upper=120.0),
        ColumnSpec("income", NUMERICAL, lower=0.0, upper=5e5),
        ColumnSpec("g", CATEGORICAL, categories=["a", "b"]),
    ]))


def test_public_ranges_cost_no_budget_and_are_used_verbatim():
    """Regression for audit finding F5, and for the bug that fix exposed.

    A publicly declared range reveals nothing, so re-estimating it under noise is pure
    waste. Worse, once sensitivity was sized correctly the noisy estimate became garbage:
    a column publicly bounded to [0, 100] was released with a range like (1633, 1634) —
    width 1 — collapsing every record into one bin and destroying all downstream structure.
    """
    ds = _bounded_dataset()
    profiler = DPDomainProfiler(accountant=Accountant(10.0, 1e-5), eps_budget=0.5)

    # Only the categorical column needs a query; both numerics are publicly bounded.
    assert profiler._query_count(ds) == 1

    profile = profiler.profile(ds, seed=0)
    assert profile.columns["age"].is_public_range is True
    assert (profile.columns["age"].min_val, profile.columns["age"].max_val) == (0.0, 120.0)
    assert (profile.columns["income"].min_val, profile.columns["income"].max_val) == (0.0, 5e5)
    assert profile.columns["g"].is_public_range is False


def test_undeclared_numeric_range_still_falls_back_to_a_noisy_estimate():
    import pandas as pd

    ds = TabularDataset(pd.DataFrame({"v": range(300)}))   # no schema
    profiler = DPDomainProfiler(accountant=Accountant(10.0, 1e-5), eps_budget=0.5)
    assert profiler._query_count(ds) == 2

    profile = profiler.profile(ds, seed=0)
    assert profile.columns["v"].is_public_range is False
    assert profile.eps_spent > 0


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
