"""Audit H3 (research/27): AIM chose a clique by its index in `affordable` but removed it from
`remaining` by the same index, so once any candidate had been skipped by the model-size bound
it measured a pair it had not selected."""

import numpy as np
import pandas as pd
import pytest

from synthproof.accounting.accountant import Accountant
from synthproof.data.dataset import TabularDataset
from synthproof.data.profiler import DPDomainProfiler
from synthproof.data.schema import CATEGORICAL, ColumnSpec, Schema
from synthproof.generators import aim as aim_mod

pytestmark = pytest.mark.skipif(not aim_mod.mbi_available(), reason="needs private-pgm")


def test_the_measured_pair_is_the_selected_pair(monkeypatch):
    rng = np.random.default_rng(0)
    n = 3000
    big = [f"v{i}" for i in range(60)]
    c = rng.choice(["x", "y"], n)
    df = pd.DataFrame({"a": rng.choice(big, n), "b": rng.choice(big, n), "c": c, "d": c})
    schema = Schema(
        columns=[
            ColumnSpec("a", CATEGORICAL, categories=big),
            ColumnSpec("b", CATEGORICAL, categories=big),
            ColumnSpec("c", CATEGORICAL, categories=["x", "y"]),
            ColumnSpec("d", CATEGORICAL, categories=["x", "y"]),
        ]
    )
    ds = TabularDataset(df, schema=schema)
    acc = Accountant(budget_eps=100.0, budget_delta=1e-5)
    prof = DPDomainProfiler(accountant=acc, eps_budget=1.0).profile(ds, seed=0)
    # No selection noise, so the pick is the true argmax: (c, d), perfectly dependent.
    monkeypatch.setattr(
        aim_mod, "exponential_mechanism", lambda scores, eps, sens, seed=None: int(np.argmax(scores))
    )
    # (a, b) -- the FIRST candidate -- is too big for the model bound and is skipped.
    gen = aim_mod.AIMGenerator(seed=0, rounds=1, max_model_mb=0.01)
    gen.fit(ds, prof, acc, target_eps=50.0)
    assert ("a", "b") in gen.skipped_cliques_
    two_way = [cl for cl in gen.measured_cliques_ if len(cl) == 2]
    assert two_way == [("c", "d")]
