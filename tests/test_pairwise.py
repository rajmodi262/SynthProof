"""Tests for the pairwise-marginal generator.

The point of this generator is that it forms a genuinely different model family from the
independent-marginal baselines, which is what hypothesis H1 requires. These tests assert that
difference rather than merely checking shapes.
"""

import numpy as np
import pandas as pd
import pytest

from synthproof.accounting.accountant import Accountant
from synthproof.accounting.calibration import BudgetPlan
from synthproof.data.dataset import TabularDataset
from synthproof.data.profiler import DPDomainProfiler
from synthproof.data.schema import NUMERICAL, ColumnSpec, Schema
from synthproof.generators.aim import AIMGenerator
from synthproof.generators.pairwise import PairwiseMarginalGenerator


def _correlated(n=3000, seed=5):
    rng = np.random.default_rng(seed)
    x = rng.uniform(0, 100, n)
    y = np.clip(x * 0.9 + rng.normal(0, 6, n), 0, 100)
    return TabularDataset(pd.DataFrame({"x": x, "y": y}), schema=Schema([
        ColumnSpec("x", NUMERICAL, lower=0.0, upper=100.0),
        ColumnSpec("y", NUMERICAL, lower=0.0, upper=100.0),
    ]))


def _synth(cls, ds, eps, seed=0):
    plan = BudgetPlan.split(eps, 1e-5, 0.1)
    acc = Accountant(eps * 1.02, 1e-5)
    profile = DPDomainProfiler(acc, eps_budget=plan.profile_eps).profile(ds, seed=seed)
    gen = cls(seed=seed)
    gen.fit(ds, profile, acc, target_eps=plan.synthesis_eps)
    return gen.generate(ds.num_rows), acc


def test_pairwise_preserves_correlation_the_baseline_destroys():
    """The defining difference between the two mechanism families."""
    ds = _correlated()
    real = ds.df["x"].corr(ds.df["y"])
    assert real > 0.9

    indep, _ = _synth(AIMGenerator, ds, 2.0)
    pair, _ = _synth(PairwiseMarginalGenerator, ds, 2.0)

    c_indep = abs(indep["x"].corr(indep["y"]))
    c_pair = pair["x"].corr(pair["y"])

    assert c_indep < 0.15, f"independent marginals leaked structure ({c_indep:.3f})"
    assert c_pair > 0.6, f"pairwise failed to preserve structure ({c_pair:.3f})"
    assert c_pair > c_indep * 3


def test_correlation_improves_with_budget():
    """More budget must mean less noise and better structure — monotone, not accidental."""
    ds = _correlated()
    lo = _synth(PairwiseMarginalGenerator, ds, 0.5)[0]
    hi = _synth(PairwiseMarginalGenerator, ds, 8.0)[0]
    assert hi["x"].corr(hi["y"]) > lo["x"].corr(lo["y"])


def test_pairwise_spends_its_target_budget_without_overspending():
    ds = _correlated(n=800)
    for eps in (1.0, 4.0):
        _, acc = _synth(PairwiseMarginalGenerator, ds, eps)
        assert acc.total() <= eps * 1.02
        assert acc.total() > eps * 0.7


def test_output_schema_matches_input():
    ds = _correlated(n=500)
    synth, _ = _synth(PairwiseMarginalGenerator, ds, 2.0)
    assert list(synth.columns) == ds.columns
    assert len(synth) == ds.num_rows
    assert synth["x"].between(0, 100).all()


def test_generate_before_fit_raises():
    with pytest.raises(RuntimeError, match="fitted"):
        PairwiseMarginalGenerator().generate(10)
