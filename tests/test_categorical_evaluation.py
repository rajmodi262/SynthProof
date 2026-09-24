"""Tests for the categorical-aware evaluation upgrade.

Before this upgrade the utility evaluator trained on numeric feature columns only and raised
on an all-categorical table (Mushroom, Nursery), and the structure metric was Pearson-only
(NaN for categorical). These tests pin the new behaviour AND guard that the all-numeric path
is byte-for-byte the old Pearson computation, so committed numeric results cannot drift.
"""

import numpy as np
import pandas as pd

from synthproof.evaluate.utility import UtilityEvaluator
from synthproof.frontier.experiment import _mean_abs_corr_error


def _categorical_df(n=400, seed=0):
    """A table whose target is (mostly) a function of a categorical feature."""
    rng = np.random.default_rng(seed)
    a = rng.choice(["x", "y", "z"], size=n)
    b = rng.choice(["p", "q"], size=n)
    # target follows `a` with a little noise -> a real, learnable signal, no numeric column.
    y = np.where(rng.random(n) < 0.85, a, rng.choice(["x", "y", "z"], size=n))
    return pd.DataFrame({"a": a, "b": b, "target": y})


def test_all_categorical_table_evaluates_without_error():
    """The old evaluator raised 'No numeric feature columns'; now an all-categorical table
    trains and, on identical real/synth, TSTR recovers the learnable signal."""
    df = _categorical_df()
    res = UtilityEvaluator(target_col="target", seed=42).evaluate(df, df)
    assert 0.0 <= res.tstr_macro_f1 <= 1.0
    assert res.tstr_macro_f1 > 0.6, "TSTR should recover the target-from-`a` signal"
    assert not np.isnan(res.marginal_distance)


def test_categorical_marginal_distance_zero_on_identical():
    df = _categorical_df()
    res = UtilityEvaluator(target_col="target", seed=1).evaluate(df, df)
    assert res.marginal_distance == 0.0


def test_categorical_marginal_distance_positive_when_frequencies_shift():
    df = _categorical_df()
    synth = df.copy()
    synth["b"] = "p"  # collapse a category -> marginal must move
    res = UtilityEvaluator(target_col="target", seed=1).evaluate(df, synth)
    assert res.marginal_distance > 0.0


def test_association_error_zero_on_identical_categorical():
    df = _categorical_df()
    err = _mean_abs_corr_error(df, df, ["a", "b", "target"])
    assert err == 0.0 or err < 1e-9


def test_association_error_positive_when_structure_broken():
    df = _categorical_df(seed=2)
    broken = df.copy()
    broken["a"] = np.random.default_rng(9).permutation(broken["a"].to_numpy())
    err = _mean_abs_corr_error(df, broken, ["a", "b", "target"])
    assert err > 0.0


def test_all_numeric_path_is_unchanged_pearson():
    """Preservation guard: for all-numeric columns the metric must equal the ORIGINAL
    Pearson-matrix computation exactly, so previously committed results do not move."""
    rng = np.random.default_rng(3)
    real = pd.DataFrame({"x": rng.normal(size=300), "y": rng.normal(size=300)})
    real["z"] = real["x"] * 0.7 + rng.normal(size=300) * 0.5
    synth = pd.DataFrame({c: rng.permutation(real[c].to_numpy()) for c in real.columns})
    cols = ["x", "y", "z"]

    got = _mean_abs_corr_error(real, synth, cols)

    a = real[cols].corr().to_numpy()
    b = synth[cols].corr().to_numpy()
    iu = np.triu_indices(len(cols), k=1)
    expected = float(np.nanmean(np.abs(a[iu] - b[iu])))
    assert abs(got - expected) < 1e-12


def test_mixed_types_produce_a_finite_score():
    """A mixed numeric+categorical column set yields a finite association error (not NaN)."""
    df = _categorical_df(seed=4)
    df["num"] = np.random.default_rng(4).normal(size=len(df))
    err = _mean_abs_corr_error(df, df, ["a", "num", "target"])
    assert np.isfinite(err)


def test_utility_is_scored_on_the_given_unseen_rows():
    """Audit M2 (research/27): with `test_df`, both models are scored on rows the generator never
    saw. A test set whose labels are inverted must drive both scores down -- proof it is used."""
    import numpy as np
    import pandas as pd

    from synthproof.evaluate.utility import UtilityEvaluator

    rng = np.random.default_rng(0)
    x = rng.normal(size=600)
    real = pd.DataFrame({"x": x, "y": np.where(x > 0, "p", "n")})
    xt = rng.normal(size=300)
    flipped = pd.DataFrame({"x": xt, "y": np.where(xt > 0, "n", "p")})
    ev = UtilityEvaluator(target_col="y", seed=0)
    normal = ev.evaluate(real, real.copy())
    held = ev.evaluate(real, real.copy(), test_df=flipped)
    assert normal.trtr_macro_f1 > 0.9
    assert held.trtr_macro_f1 < 0.2 and held.tstr_macro_f1 < 0.2
