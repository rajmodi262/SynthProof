"""Unit tests and property checks for Privacy Accountant and noise samplers."""

import pytest
import numpy as np
from synthproof.accounting.accountant import Accountant
from synthproof.accounting.types import BudgetExceededError, MechanismSpec
from synthproof.accounting.noise import sample_discrete_laplace, sample_discrete_gaussian


def test_accountant_initialization():
    acc = Accountant(budget_eps=2.0, budget_delta=1e-5)
    assert acc.budget.epsilon == 2.0
    assert acc.budget.delta == 1e-5
    assert acc.total() == 0.0
    assert acc.remaining() == 2.0


def test_gaussian_charge(fresh_accountant, standard_gaussian_spec):
    initial_remaining = fresh_accountant.remaining()
    spend = fresh_accountant.charge(standard_gaussian_spec)
    
    assert spend.computed_eps > 0
    assert fresh_accountant.total() == spend.computed_eps
    assert fresh_accountant.remaining() == initial_remaining - spend.computed_eps
    assert len(fresh_accountant.spends) == 1


def test_budget_exceeded_raises():
    acc = Accountant(budget_eps=0.5, budget_delta=1e-5)
    # High sensitivity, low noise scale produces large epsilon
    high_spend_spec = MechanismSpec(name="gaussian", sensitivity=10.0, noise_scale=0.1)
    
    with pytest.raises(BudgetExceededError) as exc_info:
        acc.charge(high_spend_spec)
    
    assert "exceeds remaining" in str(exc_info.value)


def test_dry_run_does_not_mutate_state(fresh_accountant, standard_gaussian_spec):
    initial_total = fresh_accountant.total()
    initial_spends_len = len(fresh_accountant.spends)
    
    dry_eps = fresh_accountant.dry_run(standard_gaussian_spec)
    
    assert dry_eps > initial_total
    assert fresh_accountant.total() == initial_total
    assert len(fresh_accountant.spends) == initial_spends_len


def test_snapshot_restore(fresh_accountant, standard_gaussian_spec):
    fresh_accountant.charge(standard_gaussian_spec)
    snap = fresh_accountant.snapshot()
    eps_before = fresh_accountant.total()
    
    # Charge again
    fresh_accountant.charge(standard_gaussian_spec)
    assert fresh_accountant.total() > eps_before
    
    # Restore
    fresh_accountant.restore(snap)
    assert fresh_accountant.total() == eps_before


def test_discrete_laplace_sampler():
    samples = sample_discrete_laplace(scale=2.0, size=100)
    assert len(samples) == 100
    assert isinstance(samples[0], (int, np.integer))


def test_discrete_gaussian_sampler():
    samples = sample_discrete_gaussian(sigma=1.5, size=100)
    assert len(samples) == 100
    assert isinstance(samples[0], (int, np.integer))


def test_discrete_gaussian_small_sigma_still_adds_noise():
    """Regression: a `sigma < 0.3` shortcut returned deterministic zeros.

    That silently removed all noise while the accountant kept charging epsilon, turning
    the privacy guarantee into a false statement. Small sigma must still *sample*.
    """
    samples = sample_discrete_gaussian(sigma=0.29, size=20000, seed=0)
    assert np.count_nonzero(samples) > 0, "small-sigma noise is deterministically zero"


def test_discrete_gaussian_matches_true_pmf():
    """Chi-square goodness-of-fit against the exact discrete Gaussian PMF."""
    from scipy import stats

    sigma, n = 2.0, 20000
    samples = sample_discrete_gaussian(sigma=sigma, size=n, seed=123)

    support = np.arange(-8, 9)
    weights = np.exp(-(support ** 2) / (2 * sigma ** 2))
    expected = n * weights / weights.sum()

    observed = np.array([np.sum(samples == k) for k in support], dtype=float)
    # Fold the tails so no expected bin is too small for the chi-square approximation.
    keep = expected >= 5
    _, p = stats.chisquare(observed[keep], expected[keep] * observed[keep].sum() / expected[keep].sum())
    assert p > 0.001, f"sampler does not match the discrete Gaussian PMF (p={p})"


def test_discrete_samplers_are_reproducible():
    a = sample_discrete_gaussian(sigma=2.0, size=50, seed=99)
    b = sample_discrete_gaussian(sigma=2.0, size=50, seed=99)
    assert np.array_equal(a, b)

    c = sample_discrete_laplace(scale=2.0, size=50, seed=99)
    d = sample_discrete_laplace(scale=2.0, size=50, seed=99)
    assert np.array_equal(c, d)
