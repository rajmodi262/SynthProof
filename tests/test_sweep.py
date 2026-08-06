"""Smoke tests for the sweep runner — the code path that produces results/RESULTS.md.

This module previously had 0% coverage despite being the source of every published number.
"""

import pytest

from synthproof.data.dataset import TabularDataset
from synthproof.frontier.sweep import SweepRunner


@pytest.mark.parametrize("mechanism", ["AIM / MST", "Gaussian Copula"])
def test_run_cell_produces_measured_fields(mechanism):
    ds = TabularDataset.create_synthetic_toy(num_rows=80, seed=42)
    res = SweepRunner(seed=42).run_cell(ds, mechanism, target_eps=1.0)

    assert res.mechanism_name == mechanism
    assert res.proved_eps > 0.0
    assert res.audited_eps >= 0.0
    assert 0.0 <= res.audit_p_value <= 1.0
    assert 0.0 <= res.mia_auc <= 1.0
    assert 0.0 <= res.tstr_f1 <= 1.0


def test_mechanism_dispatch_actually_switches_generators():
    """Regression: `mechanism_name.lower() in ("aim", "mst")` never matched "AIM / MST".

    Every sweep therefore ran the copula generator, and the two halves of the results
    table were identical. The generators must now produce different privacy accounting.
    """
    ds = TabularDataset.create_synthetic_toy(num_rows=80, seed=42)
    runner = SweepRunner(seed=42)

    aim = runner.run_cell(ds, "AIM / MST", target_eps=1.0)
    copula = runner.run_cell(ds, "Gaussian Copula", target_eps=1.0)

    assert aim.proved_eps != copula.proved_eps, "both mechanisms took the same code path"


def test_mia_holdout_is_disjoint_from_generator_input():
    """The MIA needs true non-members; fitting and holdout rows must not overlap."""
    ds = TabularDataset.create_synthetic_toy(num_rows=100, seed=42)
    fit_ds, holdout_df = SweepRunner(seed=42)._split(ds)

    assert len(fit_ds.df) + len(holdout_df) == len(ds.df)
    fit_rows = {tuple(r) for r in fit_ds.df.to_numpy()}
    holdout_rows = {tuple(r) for r in holdout_df.to_numpy()}
    assert fit_rows.isdisjoint(holdout_rows)
