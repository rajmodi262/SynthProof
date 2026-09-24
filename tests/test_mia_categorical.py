"""Audit C3 (research/27): the distance MIA used to return a constant score -- and so an AUC of
exactly 0.5 -- on any table without a numeric column, which the grids reported as "attacker at
chance" on every Mushroom, Nursery and SF-Fire cell. It now measures categorical distance, and
raises when there is genuinely nothing to compare."""

import numpy as np
import pandas as pd
import pytest

from synthproof.attacks.distance_mia import DistanceMIABaseline


def _cat_table(n, seed):
    rng = np.random.default_rng(seed)
    return pd.DataFrame({f"c{j}": rng.choice(list("abcdefgh"), n) for j in range(6)})


def test_a_copy_leak_is_detected_on_an_all_categorical_table():
    train, test = _cat_table(300, 0), _cat_table(300, 1)
    res = DistanceMIABaseline(seed=0).evaluate(train.copy(), train_df=train, test_df=test)
    assert res.auc > 0.9  # the release IS the training table


def test_an_unrelated_release_scores_near_chance_but_is_not_a_constant():
    train, test, synth = _cat_table(300, 0), _cat_table(300, 1), _cat_table(3000, 2)
    res = DistanceMIABaseline(seed=0).evaluate(synth, train_df=train, test_df=test)
    assert 0.4 < res.auc < 0.6
    assert res.auc != 0.5


def test_no_shared_column_raises_instead_of_reporting_chance():
    with pytest.raises(ValueError):
        DistanceMIABaseline(seed=0).evaluate(
            pd.DataFrame({"x": ["a"]}), train_df=pd.DataFrame({"y": ["b"]}), test_df=pd.DataFrame({"y": ["c"]})
        )
