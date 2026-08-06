"""Unit tests for TabularDataset and DPDomainProfiler."""

import pytest
from synthproof.data.dataset import TabularDataset
from synthproof.data.profiler import DPDomainProfiler
from synthproof.accounting.accountant import Accountant


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
    profiler = DPDomainProfiler(accountant=acc, eps_per_col=0.05)
    profile = profiler.profile(ds)
    
    assert len(profile.columns) == 3
    assert len(acc.spends) > initial_spends
    assert acc.total() > 0.0

    age_prof = profile.columns["age"]
    assert age_prof.min_val is not None
    assert age_prof.max_val is not None
    assert age_prof.min_val < age_prof.max_val
