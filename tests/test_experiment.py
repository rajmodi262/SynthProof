"""Tests for the multi-seed experiment runner."""

import numpy as np
import pandas as pd
import pytest

from synthproof.data.dataset import TabularDataset
from synthproof.frontier.experiment import (
    bootstrap_ci,
    informative_numeric_columns,
    run_cell,
    run_grid,
)


def test_bootstrap_ci_brackets_the_mean():
    ci = bootstrap_ci([1.0, 1.1, 0.9, 1.05, 0.95])
    assert ci.lo <= ci.mean <= ci.hi
    assert ci.n == 5
    assert ci.sd > 0


def test_bootstrap_ci_handles_degenerate_input():
    assert bootstrap_ci([]).n == 0
    single = bootstrap_ci([2.0])
    assert single.mean == single.lo == single.hi == 2.0
    # Non-finite values are dropped rather than poisoning the interval.
    assert bootstrap_ci([1.0, float("nan"), 1.0]).n == 2


def test_degenerate_columns_are_excluded_from_structure_metric():
    """capital_gain-style columns (>85% one value) measure noise, not correlation."""
    df = pd.DataFrame({
        "spread": np.arange(100.0),
        "mostly_zero": [0.0] * 95 + [1.0] * 5,
        "constant": [7.0] * 100,
    })
    keep = informative_numeric_columns(df, ["spread", "mostly_zero", "constant"])
    assert keep == ["spread"]


def test_run_cell_reports_every_metric():
    ds = TabularDataset.create_synthetic_toy(400)
    out = run_cell(ds, "pairwise", target_eps=2.0, seed=0, num_canaries=10)
    for k in ("proved_eps", "audited_eps", "audit_p", "tstr_f1", "trtr_f1", "mia_auc"):
        assert k in out and np.isfinite(out[k])
    assert out["proved_eps"] <= 2.0 * 1.02


def test_run_cell_rejects_unknown_mechanism():
    ds = TabularDataset.create_synthetic_toy(100)
    with pytest.raises(KeyError, match="Unknown mechanism"):
        run_cell(ds, "nope", target_eps=1.0, seed=0)


def test_run_grid_aggregates_across_seeds():
    ds = TabularDataset.create_synthetic_toy(300)
    res = run_grid(ds, mechanisms=("independent",), eps_grid=(1.0,), seeds=(0, 1, 2))
    assert len(res) == 1
    cell = res[0]
    assert cell.seeds == 3
    assert cell.proved_eps.n == 3
    assert cell.proved_eps.lo <= cell.proved_eps.mean <= cell.proved_eps.hi
    assert "proved_eps" in cell.raw and len(cell.raw["proved_eps"]) == 3
    assert "raw" not in cell.to_dict()


def test_canaries_stay_inside_the_public_domain():
    """Regression: out-of-domain canaries stretched the profiled range and destroyed structure."""
    from synthproof.audit.canary import CanaryAuditor

    ds = TabularDataset.create_synthetic_toy(300)
    aug, canaries = CanaryAuditor(num_canaries=20, seed=0).plant_canaries(ds)

    assert aug.schema is not None, "planting must not drop the schema"
    lo, hi = ds.bounds("age")
    assert canaries.members["age"].between(lo, hi).all()
    assert canaries.holdout["age"].between(lo, hi).all()
    assert aug.df["age"].between(lo, hi).all()
