"""The exact-arithmetic samplers (CKS'20 Algorithms 1-3) and where they are used.

The default samplers emit integers but decide accept/reject in floating point. Exact mode
decides with rational arithmetic and integer draws only. These tests check the distributions
against the exact PMFs, prove that no floating-point exp or float RNG is touched on the exact
path, and check that releases -- not the research grids -- run in exact mode.
"""

import math
import random
from fractions import Fraction

import numpy as np
import pytest
from scipy import stats

from synthproof.accounting import noise
from synthproof.accounting.noise import (
    exact_noise,
    exact_noise_enabled,
    sample_discrete_gaussian,
    sample_discrete_gaussian_exact,
    sample_discrete_laplace,
    sample_discrete_laplace_exact,
)


def _chi_square_p(samples, pmf, support):
    counts = np.array([(samples == k).sum() for k in support], dtype=float)
    probs = np.array([pmf(k) for k in support], dtype=float)
    probs /= probs.sum()
    expected = probs * len(samples)
    keep = expected >= 5
    return stats.chisquare(
        counts[keep], expected[keep] * counts[keep].sum() / expected[keep].sum()
    ).pvalue


def test_exact_discrete_gaussian_matches_its_pmf():
    sigma = 1.7
    x = sample_discrete_gaussian_exact(sigma, size=20000, seed=1)
    support = range(-10, 11)
    assert _chi_square_p(x, lambda k: math.exp(-(k * k) / (2 * sigma * sigma)), support) > 1e-3


def test_exact_discrete_laplace_matches_its_pmf():
    b = 2.5
    x = sample_discrete_laplace_exact(b, size=20000, seed=2)
    support = range(-20, 21)
    assert _chi_square_p(x, lambda k: math.exp(-abs(k) / b), support) > 1e-3


@pytest.mark.parametrize("gamma", [Fraction(3, 10), Fraction(27, 10)])
def test_bernoulli_exp_hits_exp_minus_gamma(gamma):
    rng = random.Random(0)
    n = 40000
    rate = sum(noise._bernoulli_exp(gamma, rng) for _ in range(n)) / n
    assert abs(rate - math.exp(-float(gamma))) < 4 * math.sqrt(0.25 / n)


def test_the_exact_path_touches_no_float_exp_and_no_numpy_rng(monkeypatch):
    # If any floating-point exp or numpy generator were used, these would raise.
    def boom(*_a, **_k):
        raise AssertionError("floating point used on the exact path")

    monkeypatch.setattr(noise.math, "exp", boom)
    monkeypatch.setattr(noise.np.random, "default_rng", boom)
    assert sample_discrete_gaussian_exact(3.3, size=200, seed=0).dtype == np.int64
    assert sample_discrete_laplace_exact(1.25, size=200, seed=0).dtype == np.int64


def test_the_switch_routes_the_default_samplers_and_restores_itself():
    assert not exact_noise_enabled()
    with exact_noise():
        assert exact_noise_enabled()
        g = sample_discrete_gaussian(2.0, size=5, seed=7)
        lap = sample_discrete_laplace(2.0, size=5, seed=7)
    assert not exact_noise_enabled()
    assert np.array_equal(g, sample_discrete_gaussian_exact(2.0, size=5, seed=7))
    assert np.array_equal(lap, sample_discrete_laplace_exact(2.0, size=5, seed=7))


def test_a_release_uses_exact_noise_and_a_research_cell_does_not(monkeypatch):
    from synthproof.data.dataset import TabularDataset
    from synthproof.frontier.certificate import FrontierEngine
    from synthproof.frontier.experiment import run_cell

    seen = []
    real = noise.sample_discrete_gaussian

    def spy(*a, **k):
        seen.append(exact_noise_enabled())
        return real(*a, **k)

    import synthproof.generators.independent as ind

    monkeypatch.setattr(ind, "sample_discrete_gaussian", spy)
    ds = TabularDataset.create_synthetic_toy(num_rows=600, seed=0)

    FrontierEngine(seed=3).run_sweep(
        ds, eps_grid=[1.0], mechanism="independent", num_canaries=4, release_rows=600
    )
    assert seen and all(seen), "the release drew noise outside exact mode"

    seen.clear()
    run_cell(ds, "independent", 1.0, seed=3, num_canaries=4, release_rows=600)
    assert seen and not any(seen), "a research cell switched to exact mode"
