"""Tests for the private-PGM-backed AIM generator.

Skipped entirely when private-pgm is unavailable (it needs Python >= 3.11), so the suite
stays green on either environment.
"""

import numpy as np
import pandas as pd
import pytest

from synthproof.accounting.accountant import Accountant
from synthproof.accounting.calibration import BudgetPlan
from synthproof.data.dataset import TabularDataset
from synthproof.data.profiler import DPDomainProfiler
from synthproof.data.schema import NUMERICAL, ColumnSpec, Schema
from synthproof.generators.aim import AIMGenerator, mbi_available

requires_mbi = pytest.mark.skipif(not mbi_available(), reason="private-pgm not installed")


def _correlated(n=1500, seed=5):
    rng = np.random.default_rng(seed)
    x = rng.uniform(0, 100, n)
    y = np.clip(x * 0.9 + rng.normal(0, 6, n), 0, 100)
    return TabularDataset(pd.DataFrame({"x": x, "y": y}), schema=Schema([
        ColumnSpec("x", NUMERICAL, lower=0.0, upper=100.0),
        ColumnSpec("y", NUMERICAL, lower=0.0, upper=100.0),
    ]))


def _fit(ds, eps, seed=0, **kw):
    plan = BudgetPlan.split(eps, 1e-5, 0.1)
    acc = Accountant(eps * 1.02, 1e-5)
    profile = DPDomainProfiler(acc, eps_budget=plan.profile_eps).profile(ds, seed=seed)
    gen = AIMGenerator(seed=seed, **kw)
    gen.fit(ds, profile, acc, target_eps=plan.synthesis_eps)
    return gen, acc


def test_selection_fraction_is_validated():
    for bad in (0.0, 1.0, -0.5):
        with pytest.raises(ValueError, match="selection_frac"):
            AIMGenerator(selection_frac=bad)


def test_generate_before_fit_raises():
    with pytest.raises(RuntimeError, match="fitted"):
        AIMGenerator().generate(10)


@pytest.mark.skipif(mbi_available(), reason="only meaningful without private-pgm")
def test_missing_mbi_raises_actionable_error():
    """Without private-pgm the failure must name the fix, not surface as an ImportError deep
    inside a third-party module."""
    with pytest.raises(ImportError, match="private-pgm"):
        AIMGenerator().fit(None, None, None, 1.0)


@requires_mbi
def test_aim_preserves_correlation():
    ds = _correlated()
    gen, _ = _fit(ds, 4.0)
    synth = gen.generate(ds.num_rows)
    assert synth["x"].corr(synth["y"]) > 0.5


@requires_mbi
def test_aim_charges_selection_and_measurement_without_overspending():
    """Selection is a mechanism and must be paid for, not taken free."""
    ds = _correlated(n=800)
    eps = 4.0
    gen, acc = _fit(ds, eps, rounds=1)

    run_ids = [s.run_id for s in acc.spends]
    assert any("aim_select" in r for r in run_ids), "selection was not charged"
    assert any("aim_1way" in r for r in run_ids)
    assert any("aim_2way" in r for r in run_ids)
    assert acc.total() <= eps * 1.02


@requires_mbi
def test_aim_records_which_cliques_it_measured():
    ds = _correlated(n=800)
    gen, _ = _fit(ds, 4.0, rounds=1)
    # Two 1-way marginals plus one adaptively selected 2-way.
    assert ("x",) in gen.measured_cliques_
    assert ("y",) in gen.measured_cliques_
    assert ("x", "y") in gen.measured_cliques_


@requires_mbi
def test_aim_output_respects_schema_bounds():
    ds = _correlated(n=800)
    gen, _ = _fit(ds, 4.0, rounds=1)
    synth = gen.generate(500)
    assert list(synth.columns) == ds.columns
    assert len(synth) == 500
    assert synth["x"].between(0, 100).all()
    assert synth["y"].between(0, 100).all()


def test_model_size_bound_is_validated():
    with pytest.raises(ValueError, match="max_model_mb"):
        AIMGenerator(max_model_mb=0)


@requires_mbi
def test_a_tiny_model_budget_refuses_cliques_rather_than_crashing():
    """Regression: unbounded inference exhausted memory mid-grid.

    Inference cost is exponential in the junction tree's treewidth, not in the row count, so
    a candidate clique that looked harmless can make the tree explode. This crashed with
    `MemoryError: bad allocation` inside variable elimination at cell 59 of a 75-cell grid,
    on UCI Adult at n=6000 — and NOT at n=3000, because the DP profiler's noisy threshold
    keeps more rare categories as n grows, so the DOMAIN grows with n even though the model
    does not.

    With a budget too small for any 2-way clique the generator must degrade to 1-way
    marginals and record what it refused, not raise.
    """
    ds = _correlated(n=600)
    gen, _ = _fit(ds, 4.0, rounds=2, max_model_mb=1e-6)

    synth = gen.generate(300)
    assert len(synth) == 300
    # Every 2-way candidate was refused, and each is recorded rather than dropped silently.
    assert gen.skipped_cliques_, "refused cliques must be recorded"
    assert all(len(c) == 1 for c in gen.measured_cliques_), (
        f"a 2-way clique was measured despite the budget: {gen.measured_cliques_}"
    )


@requires_mbi
def test_a_generous_budget_still_measures_two_way_marginals():
    """The bound must not silently disable the thing that makes AIM AIM."""
    ds = _correlated(n=600)
    gen, _ = _fit(ds, 4.0, rounds=1, max_model_mb=128.0)

    assert ("x", "y") in gen.measured_cliques_
    assert not gen.skipped_cliques_
