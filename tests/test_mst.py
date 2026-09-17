"""Tests for the private-PGM-backed MST generator.

Skipped entirely when private-pgm is unavailable (it needs Python >= 3.11), so the suite stays
green on either environment. Mirrors tests/test_aim.py; the MST-specific guarantee is that the
measured 2-way marginals form a SPANNING TREE (no cycle, at most d-1 edges).
"""

import numpy as np
import pandas as pd
import pytest

from synthproof.accounting.accountant import Accountant
from synthproof.accounting.calibration import BudgetPlan
from synthproof.data.dataset import TabularDataset
from synthproof.data.profiler import DPDomainProfiler
from synthproof.data.schema import NUMERICAL, ColumnSpec, Schema
from synthproof.generators.aim import mbi_available
from synthproof.generators.mst import MSTGenerator, _UnionFind

requires_mbi = pytest.mark.skipif(not mbi_available(), reason="private-pgm not installed")


def _three_col(n=1500, seed=5):
    """Three columns so a spanning tree (2 edges) is distinguishable from the complete graph
    (3 edges): the MST constraint must refuse the third, cycle-closing edge."""
    rng = np.random.default_rng(seed)
    x = rng.uniform(0, 100, n)
    y = np.clip(x * 0.9 + rng.normal(0, 6, n), 0, 100)
    z = np.clip(y * 0.8 + rng.normal(0, 8, n), 0, 100)
    return TabularDataset(
        pd.DataFrame({"x": x, "y": y, "z": z}),
        schema=Schema(
            [
                ColumnSpec("x", NUMERICAL, lower=0.0, upper=100.0),
                ColumnSpec("y", NUMERICAL, lower=0.0, upper=100.0),
                ColumnSpec("z", NUMERICAL, lower=0.0, upper=100.0),
            ]
        ),
    )


def _fit(ds, eps, seed=0, **kw):
    plan = BudgetPlan.split(eps, 1e-5, 0.1)
    acc = Accountant(eps * 1.02, 1e-5)
    profile = DPDomainProfiler(acc, eps_budget=plan.profile_eps).profile(ds, seed=seed)
    gen = MSTGenerator(seed=seed, **kw)
    gen.fit(ds, profile, acc, target_eps=plan.synthesis_eps)
    return gen, acc


# --------------------------------------------------------------- unit: the cycle constraint


def test_union_find_detects_cycles():
    uf = _UnionFind(3)
    assert uf.union(0, 1) is True
    assert uf.union(1, 2) is True
    # 0-1-2 is now one set; joining 0 and 2 would close a cycle.
    assert uf.union(0, 2) is False


def test_selection_fraction_is_validated():
    for bad in (0.0, 1.0, -0.5):
        with pytest.raises(ValueError, match="selection_frac"):
            MSTGenerator(selection_frac=bad)


def test_model_size_bound_is_validated():
    with pytest.raises(ValueError, match="max_model_mb"):
        MSTGenerator(max_model_mb=0)


def test_generate_before_fit_raises():
    with pytest.raises(RuntimeError, match="fitted"):
        MSTGenerator().generate(10)


@pytest.mark.skipif(mbi_available(), reason="only meaningful without private-pgm")
def test_missing_mbi_raises_actionable_error():
    with pytest.raises(ImportError, match="private-pgm"):
        MSTGenerator().fit(None, None, None, 1.0)


# --------------------------------------------------------------- behaviour (needs mbi)


@requires_mbi
def test_mst_measures_a_spanning_tree_not_the_complete_graph():
    """The defining property: over 3 columns MST measures exactly the 2 tree edges and refuses
    the third, which would close a cycle."""
    ds = _three_col()
    gen, _ = _fit(ds, 6.0)
    two_way = [c for c in gen.measured_cliques_ if len(c) == 2]
    # A spanning tree over 3 connected nodes has exactly 2 edges, never 3.
    assert len(two_way) == 2, f"expected a 2-edge tree, got {two_way}"
    # No cycle: the 2 edges touch all 3 columns.
    touched = {col for edge in two_way for col in edge}
    assert touched == {"x", "y", "z"}


@requires_mbi
def test_mst_charges_selection_and_measurement_without_overspending():
    ds = _three_col(n=800)
    eps = 6.0
    gen, acc = _fit(ds, eps)
    run_ids = [s.run_id for s in acc.spends]
    assert any("mst_select" in r for r in run_ids), "selection was not charged"
    assert any("mst_1way" in r for r in run_ids)
    assert any("mst_2way" in r for r in run_ids)
    assert acc.total() <= eps * 1.02


@requires_mbi
def test_mst_preserves_correlation():
    ds = _three_col()
    gen, _ = _fit(ds, 6.0)
    synth = gen.generate(ds.num_rows)
    assert synth["x"].corr(synth["y"]) > 0.4


@requires_mbi
def test_mst_output_respects_schema_bounds():
    ds = _three_col(n=800)
    gen, _ = _fit(ds, 6.0)
    synth = gen.generate(500)
    assert list(synth.columns) == ds.columns
    assert len(synth) == 500
    for col in ("x", "y", "z"):
        assert synth[col].between(0, 100).all()


@requires_mbi
def test_a_tiny_model_budget_degrades_to_one_way_marginals():
    """As with AIM, a budget too small for any 2-way clique must degrade to 1-way and record
    what it refused, not crash."""
    ds = _three_col(n=600)
    gen, _ = _fit(ds, 6.0, max_model_mb=1e-6)
    synth = gen.generate(300)
    assert len(synth) == 300
    assert gen.skipped_cliques_, "refused cliques must be recorded"
    assert all(len(c) == 1 for c in gen.measured_cliques_)
