"""Unit tests for synthetic tabular generators (GaussianCopula, AIM)."""

import pandas as pd

from synthproof.accounting.accountant import Accountant
from synthproof.data.dataset import TabularDataset
from synthproof.data.profiler import DPDomainProfiler
from synthproof.generators.copula import GaussianCopulaGenerator
from synthproof.generators.independent import IndependentMarginalGenerator


def test_copula_generator_fit_and_generate():
    ds = TabularDataset.create_synthetic_toy(num_rows=100)
    acc = Accountant(budget_eps=10.0, budget_delta=1e-5)
    profiler = DPDomainProfiler(accountant=acc, eps_budget=0.5)
    profile = profiler.profile(ds)

    gen = GaussianCopulaGenerator(seed=42)
    initial_spends = len(acc.spends)
    gen.fit(ds, profile, acc, target_eps=1.0)

    assert gen.is_fitted is True
    assert len(acc.spends) > initial_spends

    synth_df = gen.generate(num_samples=50)
    assert isinstance(synth_df, pd.DataFrame)
    assert len(synth_df) == 50
    assert set(synth_df.columns) == set(ds.columns)


def test_aim_generator_fit_and_generate():
    ds = TabularDataset.create_synthetic_toy(num_rows=100)
    acc = Accountant(budget_eps=10.0, budget_delta=1e-5)
    profiler = DPDomainProfiler(accountant=acc, eps_budget=0.5)
    profile = profiler.profile(ds)

    gen = IndependentMarginalGenerator(seed=42)
    initial_spends = len(acc.spends)
    gen.fit(ds, profile, acc, target_eps=1.0)

    assert gen.is_fitted is True
    assert len(acc.spends) > initial_spends

    synth_df = gen.generate(num_samples=50)
    assert isinstance(synth_df, pd.DataFrame)
    assert len(synth_df) == 50
    assert set(synth_df.columns) == set(ds.columns)
