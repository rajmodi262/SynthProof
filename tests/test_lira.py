"""LiRA must catch a verbatim leak, and must not invent one where the release is independent noise.

A membership attack is only trustworthy if it passes both directions: a generator that copies
its training rows must be detected, and a release that cannot depend on the target (shuffled
columns at leak_fraction 0, which keeps marginals but no record) must sit near chance.
"""

import numpy as np
import pandas as pd
import pytest

from synthproof.attacks.lira import LiRAAttack
from synthproof.data.dataset import TabularDataset
from synthproof.data.schema import CATEGORICAL, NUMERICAL, ColumnSpec, Schema
from synthproof.generators.leaky import LeakyGenerator


@pytest.fixture(scope="module")
def population():
    rng = np.random.default_rng(0)
    n = 900
    df = pd.DataFrame(
        {
            "age": rng.integers(18, 90, n).astype(float),
            "hours": rng.integers(1, 80, n).astype(float),
            "grp": rng.choice(list("abcd"), n),
        }
    )
    schema = Schema(
        [
            ColumnSpec("age", NUMERICAL, lower=0.0, upper=100.0),
            ColumnSpec("hours", NUMERICAL, lower=0.0, upper=100.0),
            ColumnSpec("grp", CATEGORICAL, categories=list("abcd")),
        ]
    )
    return TabularDataset(df, schema=schema)


def _run(population, leak):
    return LiRAAttack(
        lambda s: LeakyGenerator(seed=s, leak_fraction=leak),
        f"leaky_{leak}",
        None,
        num_targets=8,
        num_shadows=8,
        num_challenges=4,
        train_size=300,
        seed=1,
    ).run(population)


def test_lira_detects_a_verbatim_copy(population):
    res = _run(population, 1.0)
    assert res.auc >= 0.95
    assert res.tpr_at_1pct_fpr >= 0.5
    lo, hi = res.auc_ci(resamples=300)
    assert lo <= res.auc <= hi


def test_lira_stays_near_chance_when_no_record_survives(population):
    res = _run(population, 0.0)
    assert 0.25 <= res.auc <= 0.75, res.auc


def test_the_result_keeps_every_challenge_for_resampling(population):
    res = _run(population, 1.0)
    assert len(res.scores) == len(res.labels) == len(res.groups) == 8 * 4
    assert set(res.labels) == {0, 1}


@pytest.mark.parametrize(
    "kwargs",
    [{"num_shadows": 3}, {"num_shadows": 5}, {"num_challenges": 1}, {"target_selection": "x"}],
)
def test_bad_configurations_are_refused(kwargs):
    with pytest.raises(ValueError):
        LiRAAttack(lambda s: LeakyGenerator(seed=s), "x", None, **kwargs)
