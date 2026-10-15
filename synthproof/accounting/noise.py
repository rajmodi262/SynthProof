"""Secure noise sampling routines (Discrete Gaussian & Discrete Laplace) for DP mechanisms.

Implements:
  - Discrete Laplace (DLap): Two-sided geometric (Ghosh, Roughgarden & Sundararajan, 2012).
  - Discrete Gaussian (DGauss): Rejection sampler from Canonne, Kamath & Steinke (2020),
    Section 5.2 Algorithm 1.

SCOPE OF THE FLOATING-POINT CLAIM. Both samplers emit integers, which avoids the Mironov
(2012) attack in its usual form — leakage through the output representation when a continuous
sample is rounded. The DEFAULT samplers are not exact-arithmetic: the acceptance test and the
underlying geometric draws use floating point. The distributions are correct (verified against
the exact PMFs by chi-square), but an adversary observing the sampler at bit level or through
timing is out of scope. `sample_discrete_gaussian` documents this in full.

EXACT MODE (added 2026-10-12). `exact_noise()` switches both samplers to Canonne, Kamath &
Steinke (2020) Algorithms 1-3 as specified: Bernoulli(exp(-gamma)) from rational arithmetic and
integer draws only, no floating point anywhere in a decision. The noise parameters are converted
to the EXACT rational value of the float they arrive as, so exact mode samples the discrete
Gaussian / Laplace for precisely the scale the accountant charged. Release surfaces (CLI `run`,
the API, the release builder) use it; the research grids keep the float sampler so committed
numbers stay reproducible. It is slower, by design: an exact decision costs rational arithmetic.
"""

import contextlib
import math
import random
from fractions import Fraction
from typing import Iterator, Optional

import numpy as np

# Module-level switch, read on every call so a context manager can scope it to one release.
_EXACT = False


@contextlib.contextmanager
def exact_noise(enabled: bool = True) -> Iterator[None]:
    """Within this block, both samplers use the exact-arithmetic CKS'20 algorithms."""
    global _EXACT
    previous = _EXACT
    _EXACT = enabled
    try:
        yield
    finally:
        _EXACT = previous


def exact_noise_enabled() -> bool:
    return _EXACT


# ---------------------------------------------------------------- exact samplers (CKS'20)


def _bernoulli(p: Fraction, rng: random.Random) -> int:
    """Bernoulli(p) for rational p in [0, 1], from one integer draw."""
    return int(rng.randrange(p.denominator) < p.numerator)


def _bernoulli_exp_small(gamma: Fraction, rng: random.Random) -> int:
    """Bernoulli(exp(-gamma)) for rational gamma in [0, 1] (CKS'20 Algorithm 1, first loop)."""
    k = 1
    while _bernoulli(gamma / k, rng):
        k += 1
    return k % 2


def _bernoulli_exp(gamma: Fraction, rng: random.Random) -> int:
    """Bernoulli(exp(-gamma)) for any rational gamma >= 0 (CKS'20 Algorithm 1)."""
    while gamma > 1:
        if not _bernoulli_exp_small(Fraction(1), rng):
            return 0
        gamma -= 1
    return _bernoulli_exp_small(gamma, rng)


def _discrete_laplace_exact(s: int, t: int, rng: random.Random) -> int:
    """One draw from the discrete Laplace with scale t/s (CKS'20 Algorithm 2)."""
    while True:
        u = rng.randrange(t)
        if not _bernoulli_exp(Fraction(u, t), rng):
            continue
        v = 0
        while _bernoulli_exp(Fraction(1), rng):
            v += 1
        y = (u + t * v) // s
        b = _bernoulli(Fraction(1, 2), rng)
        if b and y == 0:
            continue
        return (1 - 2 * b) * y


def _discrete_gaussian_exact(sigma_sq: Fraction, rng: random.Random) -> int:
    """One draw from the discrete Gaussian with variance parameter sigma_sq (CKS'20 Alg. 3)."""
    t = math.isqrt(sigma_sq.numerator // sigma_sq.denominator) + 1
    while True:
        y = _discrete_laplace_exact(1, t, rng)
        gamma = (abs(y) - sigma_sq / t) ** 2 / (2 * sigma_sq)
        if _bernoulli_exp(gamma, rng):
            return y


def sample_discrete_laplace_exact(
    scale: float, size: int = 1, seed: Optional[int] = None
) -> np.ndarray:
    """Exact DLap(scale): mass proportional to exp(-|x| / scale), from integer draws only."""
    if scale <= 0:
        raise ValueError(f"Scale must be positive, got {scale}")
    b = Fraction(scale)  # the exact value of the float, not a rounding of it
    rng = random.Random(seed)
    return np.array(
        [_discrete_laplace_exact(b.denominator, b.numerator, rng) for _ in range(size)],
        dtype=np.int64,
    )


def sample_discrete_gaussian_exact(
    sigma: float, size: int = 1, seed: Optional[int] = None
) -> np.ndarray:
    """Exact N_Z(0, sigma^2), from rational arithmetic and integer draws only."""
    if sigma <= 0:
        raise ValueError(f"Sigma must be positive, got {sigma}")
    sigma_sq = Fraction(sigma) ** 2
    rng = random.Random(seed)
    return np.array([_discrete_gaussian_exact(sigma_sq, rng) for _ in range(size)], dtype=np.int64)


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
    if _EXACT:
        return sample_discrete_laplace_exact(scale, size=size, seed=seed)

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
    if _EXACT:
        return sample_discrete_gaussian_exact(sigma, size=size, seed=seed)

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


def exponential_mechanism(
    scores, epsilon: float, sensitivity: float, seed: Optional[int] = None
) -> int:
    """Index chosen by the exponential mechanism: P(i) proportional to exp(eps * q_i / (2 * Delta)).

    Sampled exactly from the normalised distribution (log-sum-exp for stability) rather than by
    adding floating-point Gumbel noise. Privacy: eps-DP, and -- because the mechanism has bounded
    range -- (eps^2 / 8)-zCDP (Cesar & Rogers 2021, arXiv:2004.07223). The accountant charges it
    through that zCDP bound; see `MechanismSpec("exponential", ...)`.
    """
    q = np.asarray(scores, dtype=float)
    if q.size == 0:
        raise ValueError("exponential mechanism needs at least one candidate")
    if epsilon <= 0 or sensitivity <= 0:
        raise ValueError(f"need epsilon > 0 and sensitivity > 0, got {epsilon}, {sensitivity}")
    logits = (epsilon / (2.0 * sensitivity)) * (q - q.max())
    p = np.exp(logits)
    p /= p.sum()
    return int(np.random.default_rng(seed).choice(q.size, p=p))


def em_noise_scale(epsilon: float, sensitivity: float) -> float:
    """The `noise_scale` under which an exponential-mechanism step is charged.

    An eps-EM step is (eps^2/8)-zCDP. A Gaussian with noise multiplier m is 1/(2 m^2)-zCDP, so
    the two have identical RDP curves when m = 2 / eps; with the utility's sensitivity Delta the
    scale is m * Delta = 2 * Delta / eps. The accountant maps "exponential" to that Gaussian event.
    """
    return 2.0 * sensitivity / epsilon


# ── real-valued queries ──────────────────────────────────────────────────────────────────
#
# FOUND 2026-10-16 (W5 sensitivity sweep). Both samplers emit INTEGERS, and they are only a DP
# mechanism for an integer-valued query. Three charge sites added integer noise directly to a
# real number -- the moments generator's mean and std, the profiler's min/max for an undeclared
# range, and the imputation sums. Then `true + Z` keeps the true value's fractional part
# exactly, so neighbouring datasets give outputs with DISJOINT supports: the release reveals
# frac(true value) outright and is not DP at any epsilon, whatever the accountant recorded.
#
# The fix is the standard one: put the query on an integer grid first. With granularity
# g = Delta / RESOLUTION, Q = round(q / g) is an integer query, and since rounding moves a
# value by at most half a unit on each side, |Q(D) - Q(D')| <= RESOLUTION + 1. Noise is drawn in
# grid units at the same noise-to-sensitivity ratio as before, so the epsilon charged is
# unchanged, and the release g * (Q + Z) has a resolution of Delta / 1000.

RESOLUTION = 1000


def grid_sensitivity() -> int:
    """Integer sensitivity of a query rounded onto its grid (see the note above)."""
    return RESOLUTION + 1


def noisy_real_query(
    value: float, sensitivity: float, noise_multiplier: float, name: str, seed: Optional[int]
) -> float:
    """Releases a real-valued scalar query with a discrete mechanism, soundly.

    Args:
        value: The exact query answer.
        sensitivity: Its add/remove-one sensitivity Delta (> 0).
        noise_multiplier: noise_scale / sensitivity -- the ratio the accountant charges.
        name: "gaussian" or "laplace".
        seed: Sampler seed.

    Returns:
        g * (round(value / g) + Z), with g = sensitivity / RESOLUTION and Z drawn at scale
        noise_multiplier * (RESOLUTION + 1). Charge it as
        MechanismSpec(name, sensitivity=grid_sensitivity(),
                      noise_scale=noise_multiplier * grid_sensitivity()).
    """
    if sensitivity <= 0:
        raise ValueError(f"sensitivity must be positive, got {sensitivity}")
    g = sensitivity / RESOLUTION
    q = int(np.rint(value / g))
    scale = noise_multiplier * grid_sensitivity()
    if name == "gaussian":
        z = int(sample_discrete_gaussian(sigma=scale, size=1, seed=seed)[0])
    elif name == "laplace":
        z = int(sample_discrete_laplace(scale=scale, size=1, seed=seed)[0])
    else:
        raise ValueError(f"unknown mechanism {name!r}")
    return g * (q + z)
