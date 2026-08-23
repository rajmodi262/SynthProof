"""Tests for the per-column Wasserstein-1 marginal distance.

`marginal_distance` was a standardised mean shift -- first moments only -- and the module
docstring had at one point called it the Wasserstein distance, which it was not. It was also
computed and never reported by anything, so nothing could have caught the difference.

The test that matters is the one the old proxy fails: a release with the RIGHT mean and the
WRONG shape. Measured on the fixture below, the old proxy scored 0.0141 where a faithful
release scored ~0.014 too -- indistinguishable. W1 gives 1.12 against 0.05.
"""

import numpy as np
import pandas as pd
import pytest

from synthproof.evaluate.utility import UtilityEvaluator


def _frame(n=800, seed=0):
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        {"x": rng.normal(0, 1, n), "y": rng.normal(0, 1, n), "t": rng.integers(0, 2, n)}
    )


def _w1(real, synth):
    return UtilityEvaluator(target_col="t", seed=0).evaluate(real, synth).marginal_distance


def test_a_faithful_release_scores_near_zero():
    """Independent draw from the same process. Not zero -- sampling noise is real."""
    assert _w1(_frame(), _frame(seed=99)) < 0.15


def test_the_case_the_old_first_moment_proxy_could_not_see():
    """Right mean, destroyed shape. This is why the proxy was replaced.

    A bimodal column centred on the real column's mean has almost the same first moment and
    an entirely different distribution. The old metric scored it as faithful.
    """
    real = _frame()
    rng = np.random.default_rng(1)
    n = len(real)
    bimodal = real.copy()
    bimodal["x"] = np.concatenate([rng.normal(-3, 0.3, n // 2), rng.normal(3, 0.3, n - n // 2)])

    # The old proxy, reconstructed, cannot separate these.
    old_proxy = abs(real["x"].mean() - bimodal["x"].mean()) / real["x"].std()
    assert old_proxy < 0.10, f"fixture is not a mean-preserving distortion: {old_proxy}"

    # W1 must.
    assert _w1(real, bimodal) > 5 * _w1(real, _frame(seed=99))


def test_it_grows_linearly_with_the_size_of_the_shift():
    """W1 between a distribution and its own translate is exactly the shift.

    The reported figure averages over the numeric columns, and only `x` moves here, so a
    shift of s across 2 columns lands at s/2. Measured: 0.0000, 0.2499, 0.9997 for shifts of
    0, 0.5 and 2.0 — which pins the averaging as well as the monotonicity, and is a stronger
    check than an arbitrary threshold.
    """
    real = _frame()
    n_numeric = 2  # x and y; the target `t` is excluded from features
    for shift in (0.0, 0.5, 2.0):
        moved = real.copy()
        moved["x"] = moved["x"] + shift
        assert _w1(real, moved) == pytest.approx(shift / n_numeric, abs=0.01)


def test_it_is_scale_free():
    """Standardised by the real column's SD, so a column's units cannot dominate the mean."""
    real, synth = _frame(), _frame(seed=99)
    scaled_real, scaled_synth = real.copy(), synth.copy()
    scaled_real["x"] *= 1000.0
    scaled_synth["x"] *= 1000.0
    assert _w1(real, synth) == pytest.approx(_w1(scaled_real, scaled_synth), rel=1e-6)


def test_the_pipeline_actually_reports_it():
    """A metric nothing reads cannot catch anything -- this one went unreported for months."""
    from synthproof.data.dataset import TabularDataset
    from synthproof.frontier.experiment import run_cell

    ds = TabularDataset.create_synthetic_toy(num_rows=400, seed=0)
    res = run_cell(ds, "pairwise", 1.0, seed=0, num_canaries=10)
    assert "marginal_w1" in res, sorted(res)
    assert np.isfinite(res["marginal_w1"])
