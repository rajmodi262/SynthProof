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
    # No schema: nothing is publicly declared, so every column's domain must be bought.
    ds = TabularDataset(TabularDataset.create_synthetic_toy(num_rows=5000).df)
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
    df = pd.DataFrame(
        {
            "age": rng.integers(18, 80, n),
            "income": rng.normal(5e4, 1e4, n),
            "g": rng.choice(["a", "b"], n),
        }
    )
    return TabularDataset(
        df,
        schema=Schema(
            [
                ColumnSpec("age", NUMERICAL, lower=0.0, upper=120.0),
                ColumnSpec("income", NUMERICAL, lower=0.0, upper=5e5),
                ColumnSpec("g", CATEGORICAL, categories=["a", "b"]),
            ]
        ),
    )


def test_public_ranges_cost_no_budget_and_are_used_verbatim():
    """Regression for audit finding F5, and for the bug that fix exposed.

    A publicly declared range reveals nothing, so re-estimating it under noise is pure
    waste. Worse, once sensitivity was sized correctly the noisy estimate became garbage:
    a column publicly bounded to [0, 100] was released with a range like (1633, 1634) —
    width 1 — collapsing every record into one bin and destroying all downstream structure.
    """
    ds = _bounded_dataset()
    profiler = DPDomainProfiler(accountant=Accountant(10.0, 1e-5), eps_budget=0.5)

    # Both numerics are publicly bounded and the categorical domain is declared: no queries.
    assert profiler._query_count(ds) == 0

    profile = profiler.profile(ds, seed=0)
    assert profile.columns["age"].is_public_range is True
    assert (profile.columns["age"].min_val, profile.columns["age"].max_val) == (0.0, 120.0)
    assert (profile.columns["income"].min_val, profile.columns["income"].max_val) == (0.0, 5e5)
    assert profile.columns["g"].is_public_range is False
    assert profile.columns["g"].is_public_domain is True
    assert profile.eps_spent == 0.0


def test_undeclared_numeric_range_still_falls_back_to_a_noisy_estimate():
    import pandas as pd

    ds = TabularDataset(pd.DataFrame({"v": range(300)}))  # no schema
    profiler = DPDomainProfiler(accountant=Accountant(10.0, 1e-5), eps_budget=0.5)
    assert profiler._query_count(ds) == 2

    profile = profiler.profile(ds, seed=0)
    assert profile.columns["v"].is_public_range is False
    assert profile.eps_spent > 0


def test_profiling_spends_exactly_its_budget_despite_mixed_sensitivities():
    """A shared noise multiplier keeps every query on the same RDP curve."""
    ds = TabularDataset(TabularDataset.create_synthetic_toy(5000).df)  # nothing declared
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


def test_dataset_source_refuses_non_https_urls():
    """Regression (bandit B310): `urlopen` honours file:/ and ftp:, so the scheme is pinned.

    Without this, a caller-constructed DatasetSource could make the loader read a local
    path instead of fetching a remote artefact.
    """
    from synthproof.data.datasets import DatasetSource

    for bad in ("file:///etc/passwd", "ftp://example.com/a.zip", "http://example.com/a.zip"):
        with pytest.raises(ValueError, match="must be https"):
            DatasetSource(name="x", url=bad, sha256="", filename="a.zip")

    # The real source is unaffected.
    from synthproof.data.datasets import ADULT

    assert ADULT.url.startswith("https://")


def test_declared_category_domain_is_used_whole_and_costs_nothing():
    """Regression for audit C1 (research/27): a declared domain used to be thresholded over the
    OBSERVED values only, so a public category with count 0 could never appear while one held
    by a single person survived ~1 time in 51 -- a delta near 2e-2 against a declared 1e-5.
    The declared domain is now released whole, which reads nothing from the data."""
    import pandas as pd

    from synthproof.data.schema import CATEGORICAL, ColumnSpec, Schema

    schema = Schema(columns=[ColumnSpec("g", CATEGORICAL, categories=["a", "b", "rare", "absent"])])
    with_one = TabularDataset(pd.DataFrame({"g": ["a"] * 300 + ["b"] * 300 + ["rare"]}), schema=schema)
    without = TabularDataset(pd.DataFrame({"g": ["a"] * 300 + ["b"] * 301}), schema=schema)
    for seed in range(20):
        outs = []
        for ds in (with_one, without):
            acc = Accountant(budget_eps=10.0, budget_delta=1e-5)
            prof = DPDomainProfiler(accountant=acc, eps_budget=1.0).profile(ds, seed=seed)
            outs.append(prof.columns["g"].categories)
            assert acc.spends == []
        # Identical output on neighbouring tables: the release does not depend on the data.
        assert outs[0] == outs[1] == ["a", "b", "rare", "absent"]
