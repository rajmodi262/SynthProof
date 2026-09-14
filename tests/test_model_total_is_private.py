"""A fitted model's total must come from noisy measurements, never from the exact row count.

research/11_selection_accounting.md. AIM and fixed_workload used to call private-pgm with
`known_total=n`, the exact number of records. Under the add/remove-one neighbouring relation this
project's accountant uses, n is private, and the consequences were measured rather than argued:

  E1 -- holding the released noisy measurements fixed, adding one record moved AIM's selection
        score by up to 1.71, against the sensitivity-1 assumption the Laplace selection is
        calibrated for;
  E2 -- the exact privacy of one selection round scales with that sensitivity, so the selection
        step was under-charged by at least 1.71x; and the final fit read n with no charge at all.

With `known_total=None`, private-pgm derives the total from the noisy measurements
(`minimum_variance_unbiased_total`) and the score sensitivity is exactly 1 (E1).

This test intercepts every model fit, so it fails on any path that hands the estimator the real
row count -- including one added later, in a mechanism that does not exist yet.
"""

import numpy as np
import pandas as pd
import pytest

from synthproof.generators.aim import mbi_available

pytestmark = pytest.mark.skipif(not mbi_available(), reason="private-pgm (mbi) not installed")


def _dataset():
    from synthproof.data.dataset import TabularDataset
    from synthproof.data.schema import CATEGORICAL, ColumnSpec, Schema

    rng = np.random.default_rng(0)
    cols = ["a", "b", "c", "d"]
    df = pd.DataFrame({c: rng.choice(["x", "y", "z"], 600) for c in cols})
    schema = Schema(
        columns=[ColumnSpec(name=c, kind=CATEGORICAL, categories=["x", "y", "z"]) for c in cols]
    )
    return TabularDataset(df, name="model_total_probe", schema=schema)


@pytest.mark.parametrize("mechanism", ["aim", "fixed_workload"])
def test_model_total_never_uses_the_exact_row_count(monkeypatch, mechanism):
    from mbi import estimation

    from synthproof.accounting.accountant import Accountant
    from synthproof.data.profiler import DPDomainProfiler
    from synthproof.frontier.experiment import MECHANISMS

    seen = []
    original = estimation.MirrorDescent.estimate

    def spy(self, *args, **kwargs):
        # estimate(domain, loss_fn, known_total=None, ...): positional index 2 after self
        if "known_total" in kwargs:
            seen.append(kwargs["known_total"])
        elif len(args) > 2:
            seen.append(args[2])
        else:
            seen.append(None)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(estimation.MirrorDescent, "estimate", spy)

    ds = _dataset()
    acc = Accountant(budget_eps=10.0, budget_delta=1e-5)
    profile = DPDomainProfiler(accountant=acc, eps_budget=0.5, schema_declared=True).profile(
        ds, seed=0
    )
    gen = MECHANISMS[mechanism](seed=0)
    gen.fit(ds, profile, acc, target_eps=4.0)

    assert seen, "the model was never fitted, so this test checked nothing"
    leaked = [k for k in seen if k is not None]
    assert not leaked, (
        f"{mechanism} passed known_total={leaked} to the estimator. The row count is private "
        "under add/remove neighbours; the total must come from the noisy measurements."
    )
