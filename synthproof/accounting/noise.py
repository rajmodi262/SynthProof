"""Secure noise sampling routines (Discrete Gaussian & Discrete Laplace) for DP mechanisms.

Implements:
  - Discrete Laplace (DLap): Two-sided geometric (Ghosh, Roughgarden & Sundararajan, 2012).
  - Discrete Gaussian (DGauss): Rejection sampler from Canonne, Kamath & Steinke (2020),
    Section 5.2 Algorithm 1.

SCOPE OF THE FLOATING-POINT CLAIM. Both samplers emit integers, which avoids the Mironov
(2012) attack in its usual form — leakage through the output representation when a continuous
sample is rounded. Neither is an exact-arithmetic implementation: the acceptance test and the
underlying geometric draws use floating point. The distributions are correct (verified against
the exact PMFs by chi-square), but an adversary observing the sampler at bit level or through
timing is out of scope. `sample_discrete_gaussian` documents this in full.
"""

import math
from typing import Optional

import numpy as np


def sample_discrete_laplace(scale: float, size: int = 1, seed: Optional[int] = None) -> np.ndarray:
    """Samples from Discrete Laplace distribution DLap(scale) using two-sided geometric.

    The Discrete Laplace with parameter b = scale places mass proportional to
    exp(-|x| / b) on each integer x. It is realised as the difference of two
    independent Geometric(p) random variables, where p = 1 - exp(-1/b).

    This avoids the Mironov (2012) floating-point representation attack that
    affects continuous Laplace sampling via inverse-CDF.

    Args:
        scale: The scale parameter b > 0 of DLap(b).
        size: Number of independent samples to draw.
        seed: Optional RNG seed for reproducibility.

    Returns:
        Integer-valued numpy array of shape (size,).
    """
    if scale <= 0:
        raise ValueError(f"Scale must be positive, got {scale}")

    # Geometric parameter: p = 1 - exp(-1/b)
    p = 1.0 - math.exp(-1.0 / scale)
    # Clamp to avoid degenerate geometric
    p = max(1e-15, min(1.0 - 1e-15, p))

    # DLap(b) = Geometric(p) - Geometric(p), where Geometric(p) is supported on {0,1,2,...}
    rng = np.random.default_rng(seed)
    u1 = rng.geometric(p, size=size) - 1
    u2 = rng.geometric(p, size=size) - 1

    return (u1 - u2).astype(np.int64)


def _discrete_gaussian_single(sigma_sq: float, rng: np.random.Generator) -> int:
    """Draws a single sample from the Discrete Gaussian N_Z(0, sigma^2).

    Uses the CKS'20 Algorithm 1 rejection sampler:
      1. Sample Y ~ DLap(t) where t = floor(sigma) + 1.
      2. Sample C ~ Bernoulli(exp(-(|Y| - sigma^2/t)^2 / (2*sigma^2))).
      3. If C = 1, return Y; otherwise reject and resample.

    The acceptance probability is bounded below by a constant for sigma >= 1,
    so expected number of iterations is O(1).
    """
    t = math.floor(math.sqrt(sigma_sq)) + 1  # Laplace scale parameter

    # Geometric parameter for DLap(t)
    p_geom = 1.0 - math.exp(-1.0 / t)
    p_geom = max(1e-15, min(1.0 - 1e-15, p_geom))

    while True:
        # Step 1: Sample Y ~ DLap(t)
        g1 = rng.geometric(p_geom) - 1
        g2 = rng.geometric(p_geom) - 1
        y = int(g1 - g2)

        # Step 2: Compute rejection probability
        # Accept with probability exp(-(|y| - sigma^2/t)^2 / (2 * sigma^2))
        abs_y = abs(y)
        numerator = (abs_y - sigma_sq / t) ** 2
        log_accept = -numerator / (2.0 * sigma_sq)

        # Step 3: Accept/reject via Bernoulli
        if log_accept >= 0:
            # Probability >= 1, always accept
            return y
        if rng.random() < math.exp(log_accept):
            return y
        # Otherwise, reject and loop


def sample_discrete_gaussian(sigma: float, size: int = 1, seed: Optional[int] = None) -> np.ndarray:
    """Samples from Discrete Gaussian distribution N_Z(0, sigma^2).

    Implements the rejection sampler from Canonne, Kamath & Steinke (2020), Algorithm 1 —
    the sampler for the discrete Gaussian mechanism underpinning zCDP guarantees.

    WHAT THIS DOES AND DOES NOT DEFEND, stated precisely because the difference matters.

    It produces the discrete Gaussian over the integers directly, so it avoids the Mironov
    (2012) attack in its usual form: leakage through the *output* representation, where
    rounding or inverse-CDF sampling of a continuous Gaussian leaves gaps in the reachable
    float values that reveal the noise.

    It does NOT achieve exact-arithmetic sampling. The accept/reject step below uses
    `rng.random() < math.exp(log_accept)` — a floating-point Bernoulli — where CKS'20
    specify a Bernoulli(exp(-x)) built from integer arithmetic precisely so that no
    floating-point rounding enters the decision. `np.random.Generator.geometric` is likewise
    float-backed. A determined adversary with exact timing or bit-level observation of the
    sampler is therefore not in scope; see docs/thesis/ch03-threat-model.md.

    Concretely:
      - Produces the discrete Gaussian distribution over integers (verified against the
        exact PMF by chi-square in tests/test_accounting.py)
      - Avoids the output-representation form of the Mironov (2012) attack
      - Does NOT provide the exact-arithmetic guarantee of a full CKS'20 implementation

    Args:
        sigma: Standard deviation parameter sigma > 0.
        size: Number of independent samples to draw.
        seed: Optional RNG seed for reproducibility.

    Returns:
        Integer-valued numpy array of shape (size,).
    """
    if sigma <= 0:
        raise ValueError(f"Sigma must be positive, got {sigma}")

    sigma_sq = sigma * sigma

    # NOTE: there is deliberately no small-sigma shortcut here. A previous version
    # returned a deterministic zero vector for sigma < 0.3, which silently removed all
    # noise while the accountant still charged a finite epsilon — i.e. it turned the
    # privacy guarantee into a false statement. The CKS'20 rejection sampler below is
    # valid and terminates for every sigma > 0 (for small sigma it concentrates on 0,
    # which is the *correct* behaviour, arrived at by sampling rather than by fiat).
    rng = np.random.default_rng(seed)
    samples = np.array(
        [_discrete_gaussian_single(sigma_sq, rng) for _ in range(size)],
        dtype=np.int64,
    )
    return samples
