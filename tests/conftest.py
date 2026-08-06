"""Pytest configuration and shared fixtures for SynthProof tests."""

import pytest
from synthproof.accounting.accountant import Accountant
from synthproof.accounting.types import MechanismSpec


@pytest.fixture
def fresh_accountant():
    """Provides a fresh Accountant instance with epsilon=5.0, delta=1e-5."""
    return Accountant(budget_eps=5.0, budget_delta=1e-5)


@pytest.fixture
def standard_gaussian_spec():
    """Provides a standard Gaussian mechanism specification."""
    return MechanismSpec(
        name="gaussian",
        sensitivity=1.0,
        noise_scale=2.0,
        steps=1
    )
