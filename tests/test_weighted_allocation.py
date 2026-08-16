"""Weighted budget allocation — the mechanism hypothesis H3 tests.

H3 asks whether spending more of a fixed budget on the columns an analyst declares as
important buys downstream utility. Answering it needs each query to carry its own noise scale
while the composed total still lands on the requested epsilon.

The property that matters most here is not that weighting helps — it does not, on this
mechanism — but that **the weighted arm spends no more than the uniform arm**. A weighted
allocation that quietly overspends would manufacture a utility gain out of extra privacy loss
and make H3 look supported for the worst possible reason.
"""

import numpy as np
import pandas as pd
import pytest

from synthproof.accounting.accountant import Accountant
from synthproof.accounting.calibration import calibrate_noise_scale, calibrate_weighted_scales
from synthproof.accounting.types import MechanismSpec
from synthproof.data.dataset import TabularDataset
from synthproof.data.profiler import DPDomainProfiler
from synthproof.data.schema import CATEGORICAL, NUMERICAL, ColumnSpec, Schema
from synthproof.generators.independent import IndependentMarginalGenerator


def _compose(scales, delta=1e-5):
    """Epsilon the accountant composes for a set of Gaussian queries at these scales."""
    acc = Accountant(budget_eps=float("inf"), budget_delta=delta)
    for s in scales:
        acc.charge(MechanismSpec(name="gaussian", sensitivity=1.0, noise_scale=s, steps=1))
    return acc.total()


# ------------------------------------------------------------------ calibration


def test_uniform_weights_reproduce_the_scalar_calibration():
    """The weighted path must not be a second, subtly different calibration. If it drifts from
    `calibrate_noise_scale`, every committed H1 number becomes incomparable to an H3 arm."""
    k, eps = 6, 1.0
    weighted = calibrate_weighted_scales([1.0] * k, target_eps=eps)
    scalar = calibrate_noise_scale(target_eps=eps, steps=k)
    assert len(set(round(s, 9) for s in weighted)) == 1, "uniform weights gave unequal scales"
    assert weighted[0] == pytest.approx(scalar, rel=1e-3)


@pytest.mark.parametrize("eps", [0.5, 1.0, 2.0, 8.0])
def test_the_weighted_split_never_overspends_the_budget(eps):
    """THE safety property. Verified against the accountant, not against our own algebra."""
    scales = calibrate_weighted_scales([4.0, 1.0, 1.0, 1.0, 1.0], target_eps=eps)
    assert _compose(scales) <= eps * (1 + 1e-6), "weighted allocation overspent"


@pytest.mark.parametrize("eps", [0.5, 2.0, 8.0])
def test_the_weighted_split_spends_essentially_the_whole_budget(eps):
    """Underspending would make the weighted arm quieter for a reason unrelated to weighting,
    which is a different confound in the other direction."""
    scales = calibrate_weighted_scales([4.0, 1.0, 1.0, 1.0, 1.0], target_eps=eps)
    assert _compose(scales) >= eps * 0.98


def test_a_heavier_weight_buys_less_noise():
    """The direction of the allocation. Inverted, H3 would be tested backwards."""
    scales = calibrate_weighted_scales([9.0, 1.0, 1.0], target_eps=1.0)
    assert scales[0] < scales[1], "the high-weight column did not receive less noise"
    assert scales[1] == pytest.approx(scales[2])


def test_the_uniform_and_weighted_arms_spend_the_same_total():
    """The comparison H3 makes is only meaningful if both arms cost the same."""
    eps = 2.0
    uni = [calibrate_noise_scale(target_eps=eps, steps=5)] * 5
    wtd = calibrate_weighted_scales([4.0, 1.0, 1.0, 1.0, 1.0], target_eps=eps)
    assert _compose(uni) == pytest.approx(_compose(wtd), abs=0.01)


def test_scaling_every_weight_by_a_constant_changes_nothing():
    """Only relative weight matters. If absolute size leaked in, an analyst writing 100s
    instead of 1s would silently get a different release."""
    a = calibrate_weighted_scales([2.0, 1.0, 1.0], target_eps=1.0)
    b = calibrate_weighted_scales([200.0, 100.0, 100.0], target_eps=1.0)
    for x, y in zip(a, b, strict=True):
        assert x == pytest.approx(y, rel=1e-6)


@pytest.mark.parametrize("bad", [[], [1.0, 0.0], [1.0, -2.0]])
def test_invalid_weights_are_rejected(bad):
    with pytest.raises(ValueError):
        calibrate_weighted_scales(bad, target_eps=1.0)


def test_a_non_positive_target_is_rejected():
    with pytest.raises(ValueError):
        calibrate_weighted_scales([1.0, 1.0], target_eps=0.0)


# ------------------------------------------------------------------ generator


def _toy(n=1500, seed=0):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(
        {
            "age": rng.integers(18, 90, n).astype(float),
            "region": rng.choice(list("abcdef"), n),
            "label": rng.choice(["yes", "no"], n),
        }
    )
    schema = Schema(
        [
            ColumnSpec("age", NUMERICAL, lower=0.0, upper=120.0),
            ColumnSpec("region", CATEGORICAL, categories=list("abcdef")),
            ColumnSpec("label", CATEGORICAL, categories=["yes", "no"]),
        ]
    )
    return TabularDataset(df, name="toy", schema=schema)


def _fit(weights, eps=2.0, seed=0):
    ds = _toy()
    acc = Accountant(budget_eps=1e6, budget_delta=1e-5)
    profile = DPDomainProfiler(accountant=acc, eps_budget=0.2).profile(ds, seed=seed)
    before = acc.total()
    gen = IndependentMarginalGenerator(seed=seed, column_weights=weights)
    gen.fit(ds, profile, acc, target_eps=eps)
    return gen, acc.total() - before


def test_the_generator_defaults_to_uniform_and_is_unchanged():
    """Every committed result used the uniform path. It must still behave identically."""
    gen, _ = _fit(None)
    assert gen.column_weights is None
    assert len(set(round(v, 9) for v in gen.noise_scales_.values())) == 1


def test_declared_weights_give_the_named_column_less_noise():
    gen, _ = _fit({"label": 4.0})
    assert gen.noise_scales_["label"] < gen.noise_scales_["age"]
    assert gen.noise_scales_["age"] == pytest.approx(gen.noise_scales_["region"])


def test_columns_absent_from_the_weight_map_default_to_one():
    """A caller naming only what they care about must not silently zero everything else."""
    gen, _ = _fit({"label": 4.0})
    assert gen.noise_scales_["age"] == pytest.approx(gen.noise_scales_["region"])
    assert all(np.isfinite(v) and v > 0 for v in gen.noise_scales_.values())


def test_both_arms_charge_the_same_epsilon():
    """REGRESSION-CRITICAL: if the weighted arm spent more, any H3 'improvement' would be
    bought with extra privacy loss rather than with better allocation."""
    _, spent_uniform = _fit(None, eps=2.0)
    _, spent_weighted = _fit({"label": 4.0}, eps=2.0)
    assert spent_weighted <= spent_uniform * 1.02
    assert spent_weighted >= spent_uniform * 0.98


def test_the_weighted_generator_still_produces_a_usable_table():
    gen, _ = _fit({"label": 4.0})
    out = gen.generate(num_samples=200)
    assert len(out) == 200
    assert set(out.columns) == {"age", "region", "label"}
    assert set(out["label"]) <= {"yes", "no"}


def test_an_extreme_weight_does_not_starve_the_others_into_failure():
    """A lopsided declaration is a bad idea, not a crash."""
    gen, _ = _fit({"label": 1000.0})
    out = gen.generate(num_samples=100)
    assert len(out) == 100
    assert all(v > 0 for v in gen.noise_scales_.values())
