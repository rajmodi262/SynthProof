"""What is, and is not, reproducible in an AIM-family release.

Measured 2026-10-16 while refactoring AIM: with the seed fixed, the FITTED MODEL is bit-identical
across processes and whatever ran before it -- but the table private-PGM SAMPLES from that model
is not: its float32 JAX sampler returned different tables in different processes and after JAX's
compilation caches changed. That is the precise meaning of "AIM-family results are reproducible
in distribution, not bit-identically" (scripts/reproduce.py).

These tests pin the half that IS deterministic, so a change that made the fit itself
nondeterministic -- the part every privacy charge and every model-level metric depends on --
fails here.
"""

import hashlib

import numpy as np
import pytest

from synthproof.accounting.accountant import Accountant
from synthproof.data.dataset import TabularDataset
from synthproof.data.profiler import DPDomainProfiler
from synthproof.frontier.experiment import MECHANISMS

pytestmark = pytest.mark.skipif("aim" not in MECHANISMS, reason="private-PGM not installed")

GENERATORS = [
    "synthproof.generators.aim.AIMGenerator",
    "synthproof.generators.fixed_workload.FixedWorkloadGenerator",
    "synthproof.generators.mst.MSTGenerator",
]


def _fitted_joint(cls_path, global_seed):
    """The fitted model's full joint distribution, as bytes, after disturbing global state."""
    import importlib

    mod, cls = cls_path.rsplit(".", 1)
    np.random.seed(global_seed)
    np.random.random(1000)
    ds = TabularDataset.create_synthetic_toy(num_rows=300, seed=1)
    acc = Accountant(10.0, 1e-5)
    prof = DPDomainProfiler(acc, eps_budget=0.3).profile(ds, seed=0)
    gen = getattr(importlib.import_module(mod), cls)(seed=5)
    gen.fit(ds, prof, acc, target_eps=2.0)
    joint = np.asarray(gen._model.project(tuple(gen.columns)).datavector(), dtype=float)
    return hashlib.sha256(joint.tobytes()).hexdigest(), gen.measured_cliques_, acc.total(1e-5)


@pytest.mark.parametrize("cls_path", GENERATORS, ids=lambda p: p.rsplit(".", 1)[1])
def test_the_fitted_model_is_identical_whatever_ran_before(cls_path):
    assert _fitted_joint(cls_path, 1) == _fitted_joint(cls_path, 987654)


def test_sampling_leaves_the_callers_global_generator_untouched():
    from synthproof.generators.aim import AIMGenerator

    ds = TabularDataset.create_synthetic_toy(num_rows=200, seed=1)
    acc = Accountant(10.0, 1e-5)
    prof = DPDomainProfiler(acc, eps_budget=0.3).profile(ds, seed=0)
    gen = AIMGenerator(seed=5)
    gen.fit(ds, prof, acc, target_eps=2.0)
    np.random.seed(42)
    expected = np.random.random(3)
    np.random.seed(42)
    gen.generate(100)
    assert np.array_equal(np.random.random(3), expected)
