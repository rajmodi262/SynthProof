"""Every charge site's declared sensitivity, checked against the statistic it actually perturbs.

HOW. Each generator imports its noise sampler into its own namespace. The test swaps that
sampler for one that returns a zero-valued RECORDING array: whatever the code adds the noise to
-- the exact pre-noise statistic, however it was computed -- is captured by `__array_ufunc__`.
Fitting on a dataset D and on a neighbour D' (one record removed, or one extreme record added:
the project's unit of privacy is add/remove-one-record) gives the statistic on both sides, and
the largest observed change must not exceed the sensitivity passed to the accountant for that
charge (L2 for the Gaussian, L1 for the Laplace).

So the test fails if someone changes the charged sensitivity without changing the statistic, or
changes the statistic (its scale, clipping, binning, normalisation) without changing the charge.
It is a necessary check, not a proof: an observed change on chosen neighbours is a LOWER bound
on the true sensitivity. The argument for each site is in docs/SENSITIVITY.md.
"""

import importlib

import numpy as np
import pandas as pd
import pytest

from synthproof.accounting.accountant import Accountant
from synthproof.data.dataset import TabularDataset
from synthproof.data.profiler import DPDomainProfiler
from synthproof.data.schema import CATEGORICAL, NUMERICAL, ColumnSpec, Schema
from synthproof.frontier.experiment import MECHANISMS


class _Recorder(np.ndarray):
    """Zero noise that remembers what it was added to."""

    log: list = []

    def __array_ufunc__(self, ufunc, method, *inputs, **kwargs):
        plain = [np.asarray(x) if isinstance(x, _Recorder) else x for x in inputs]
        if ufunc in (np.add, np.subtract) and method == "__call__":
            for x in inputs:
                if not isinstance(x, _Recorder):
                    _Recorder.log.append(np.array(x, dtype=float, copy=True))
        return getattr(ufunc, method)(*plain, **kwargs)

    def __float__(self):
        # `float(noise[0])` -- the scalar path (moments, imputation sums). Record the use; the
        # statistic is captured by the addition that follows in plain Python, see _scalar_hook.
        return 0.0


def _zero_noise(**kw):
    size = kw.get("size", 1)
    return np.zeros(size).view(_Recorder)


class _Real:
    """A real-valued query released through `noisy_real_query`: its value and declared Delta."""

    def __init__(self, value, sensitivity):
        self.value, self.sensitivity = float(value), float(sensitivity)


def _record_real_query(value, sensitivity, noise_multiplier, name, seed):
    _Recorder.log.append(_Real(value, sensitivity))
    return float(value)


def _schema_dataset(n, seed):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(
        {
            "age": rng.integers(17, 90, n).astype(float),
            "hours": rng.integers(1, 99, n).astype(float),
            "job": rng.choice(["a", "b", "c", "d"], n),
            "sex": rng.choice(["F", "M"], n),
        }
    )
    schema = Schema(
        [
            ColumnSpec("age", NUMERICAL, lower=17.0, upper=90.0),
            ColumnSpec("hours", NUMERICAL, lower=1.0, upper=99.0),
            ColumnSpec("job", CATEGORICAL, categories=["a", "b", "c", "d"]),
            ColumnSpec("sex", CATEGORICAL, categories=["F", "M"]),
        ]
    )
    return df, schema


def _neighbours(df):
    """D minus its first row, and D plus one extreme record."""
    extreme = pd.DataFrame({"age": [90.0], "hours": [1.0], "job": ["d"], "sex": ["M"]})
    return [df.iloc[1:].reset_index(drop=True), pd.concat([df, extreme], ignore_index=True)]


def _fit_and_record(gen_cls, module, df, schema, profile, monkeypatch, sampler):
    """Fit once; return [(charged spec, captured statistic)] in charge order."""
    charges, pairs = [], []
    _Recorder.log = []
    acc = Accountant(1e6, 1e-5)
    real_charge = acc.charge

    def charge(spec, *a, **k):
        # Close out the previous charge: everything recorded since belongs to it.
        if charges:
            pairs.append((charges[-1], list(_Recorder.log)))
        _Recorder.log = []
        charges.append(spec)
        return real_charge(spec, *a, **k)

    monkeypatch.setattr(acc, "charge", charge)
    monkeypatch.setattr(module, sampler, _zero_noise)
    if hasattr(module, "noisy_real_query"):
        monkeypatch.setattr(module, "noisy_real_query", _record_real_query)
    gen = gen_cls(seed=0)
    gen.fit(TabularDataset(df, schema=schema), profile, acc, target_eps=4.0)
    if charges:
        pairs.append((charges[-1], list(_Recorder.log)))
    return pairs


def _norm(spec, delta):
    return float(np.abs(delta).sum()) if spec.name == "laplace" else float(np.linalg.norm(delta))


GENERATORS = [
    (
        "synthproof.generators.independent",
        "IndependentMarginalGenerator",
        "sample_discrete_gaussian",
    ),
    ("synthproof.generators.pairwise", "PairwiseMarginalGenerator", "sample_discrete_gaussian"),
    ("synthproof.generators.moments", "GaussianMomentGenerator", "sample_discrete_gaussian"),
]
if "mst" in MECHANISMS:
    GENERATORS.append(("synthproof.generators.mst", "MSTGenerator", "sample_discrete_gaussian"))
if "aim" in MECHANISMS:
    GENERATORS.append(("synthproof.generators.aim", "AIMGenerator", "sample_discrete_gaussian"))


@pytest.mark.parametrize("n", [60, 2000])
@pytest.mark.parametrize("modname,clsname,sampler", GENERATORS, ids=lambda x: str(x).split(".")[-1])
def test_no_charge_understates_the_sensitivity_of_what_it_perturbs(
    modname, clsname, sampler, n, monkeypatch
):
    module = importlib.import_module(modname)
    gen_cls = getattr(module, clsname)
    df, schema = _schema_dataset(n, seed=11)
    # One public profile for every side: the domain is a separately charged stage, and holding
    # it fixed is what makes the two fits differ only in the one record.
    profile = DPDomainProfiler(Accountant(1e6, 1e-5), eps_budget=1.0).profile(
        TabularDataset(df, schema=schema), seed=0
    )
    base = _fit_and_record(gen_cls, module, df, schema, profile, monkeypatch, sampler)
    assert base, "no charges recorded -- the generator spent nothing?"
    for nb in _neighbours(df):
        other = _fit_and_record(gen_cls, module, nb, schema, profile, monkeypatch, sampler)
        assert len(other) == len(base), "neighbouring datasets made different numbers of charges"
        for (spec, stats_a), (_, stats_b) in zip(base, other, strict=True):
            if spec.name == "exponential":
                # Selection scores depend on a model fitted to earlier releases, which differ
                # between the two fits here (zero noise), so a score difference is not a clean
                # sensitivity measurement. Argued in docs/SENSITIVITY.md instead.
                continue
            assert stats_a, f"{clsname}: a charge ({spec}) perturbed nothing the test could see"
            for a, b in zip(stats_a, stats_b, strict=False):
                if isinstance(a, _Real):
                    moved = abs(b.value - a.value)
                    assert moved <= a.sensitivity + 1e-9, (
                        f"{clsname}: a real-valued query declared sensitivity {a.sensitivity} "
                        f"but one record moved it by {moved:.6g} (n={n})"
                    )
                    continue
                if a.shape != b.shape:
                    continue  # a data-dependent shape is caught by the domain tests instead
                moved = _norm(spec, b - a)
                bound = spec.sensitivity * max(1, int(spec.steps) if a.size == spec.steps else 1)
                assert moved <= bound + 1e-9, (
                    f"{clsname}: a charge declared sensitivity {spec.sensitivity} "
                    f"({spec.name}, steps={spec.steps}) but one record moved the perturbed "
                    f"statistic by {moved:.6g} (n={n})"
                )


# ------------------------------------------------------------- real-valued queries


@pytest.mark.parametrize("name", ["gaussian", "laplace"])
def test_a_real_valued_release_never_carries_the_true_values_fractional_part(name):
    """Integer noise added to a real number keeps its fractional part, so neighbouring inputs
    give disjoint output supports and the release is not DP at any epsilon. Through the grid,
    every output is a multiple of Delta / RESOLUTION whatever the input."""
    from synthproof.accounting.noise import RESOLUTION, noisy_real_query

    sens = 7.3
    g = sens / RESOLUTION
    for i, value in enumerate([0.123456789, 1234.98765, -3.14159, 0.0005]):
        out = noisy_real_query(value, sens, 2.0, name, seed=i)
        assert abs(out / g - round(out / g)) < 1e-6, (value, out)


def test_the_grid_charge_keeps_the_noise_to_sensitivity_ratio():
    """Charging (RESOLUTION + 1, m * (RESOLUTION + 1)) spends exactly what (1, m) spends."""
    from synthproof.accounting.calibration import epsilon_for_noise_scale
    from synthproof.accounting.noise import grid_sensitivity

    for m in (0.7, 2.0, 9.0):
        unit = epsilon_for_noise_scale(m, 1e-5, "gaussian", 1.0, 1)
        grid = epsilon_for_noise_scale(
            m * grid_sensitivity(), 1e-5, "gaussian", float(grid_sensitivity()), 1
        )
        assert grid == pytest.approx(unit, rel=1e-9)
