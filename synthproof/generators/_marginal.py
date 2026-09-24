"""Shared machinery for the private-PGM marginal mechanisms (AIM, MST).

Three things both mechanisms need, kept in one place so they cannot drift apart:

  * **Encoding** a table onto a finite integer domain built ONLY from the DP profile (public
    bounds, public or DP-released category lists) -- never from the data.
  * **Binning** numeric columns. Uniform bins over a wide public range crushed heavy-tailed
    columns: UCI Adult's capital_gain spans 0-100,000 and twelve uniform bins put every value
    below 8,333 -- including the informative 7,688 -- in the same bin as the 92% zeros (audit H5,
    research/27). A column whose public range is non-negative and reaches 1,000 or more now gets
    geometric (log-scale) bins. The rule reads only the declared bounds, so it is free.
  * **One zCDP budget** for the whole release. Each step used to be calibrated to its own share
    and Renyi composition is sub-additive, so 18-25% of every budget went unspent (audit H1).
    Every step here -- Gaussian measurements and exponential-mechanism selections alike -- is a
    zCDP charge, the charges add exactly, and the total rho is found once, against the target.
"""

from typing import Dict, List

import numpy as np
import pandas as pd

from synthproof.accounting.calibration import calibrate_noise_scale
from synthproof.data.dataset import TabularDataset
from synthproof.data.profiler import DomainProfile

OTHER = "__other__"
# A non-negative public range reaching this far is treated as heavy-tailed (money, counts).
LOG_BIN_MIN_UPPER = 1000.0


def bin_edges(lo: float, hi: float, k: int) -> np.ndarray:
    """k bins over [lo, hi]: geometric for a wide non-negative range, uniform otherwise."""
    lo, hi = float(lo), float(hi)
    if lo >= 0.0 and hi >= LOG_BIN_MIN_UPPER:
        if lo == 0.0:
            # [0, 1) holds the exact zeros of a zero-inflated column; the rest is geometric.
            return np.concatenate([[0.0], np.geomspace(1.0, hi, k)])
        return np.geomspace(lo, hi, k + 1)
    return np.linspace(lo, hi, k + 1)


class MarginalEncoder:
    """Maps a table to and from the integer domain private-PGM needs."""

    def __init__(self, num_bins: int):
        self.num_bins = num_bins
        self.levels_: Dict[str, list] = {}
        self.bin_edges_: Dict[str, np.ndarray] = {}
        self.columns: List[str] = []
        self.numerical_cols: List[str] = []

    def build(self, dataset: TabularDataset, profile: DomainProfile) -> None:
        self.columns = list(dataset.columns)
        self.numerical_cols = list(dataset.numerical_cols)
        for col in dataset.columns:
            prof = profile.columns[col]
            if col in dataset.numerical_cols:
                if prof.min_val is None or prof.max_val is None:
                    raise ValueError(f"Column {col!r} has no DP range in the profile.")
                self.bin_edges_[col] = bin_edges(prof.min_val, prof.max_val, self.num_bins)
                self.levels_[col] = list(range(self.num_bins))
            else:
                cats = prof.categories
                if not cats:
                    raise ValueError(f"Column {col!r} has no DP category domain.")
                levels = list(cats)
                # A thresholded (DP-released) domain can omit real values. They get their own
                # OTHER level instead of being folded into the first real category, which
                # inflated that category's count (audit H4). Whether OTHER exists depends only
                # on the profile -- a DP output -- never on the data. A public domain is complete
                # by declaration, so it gets none.
                if not prof.is_public_domain:
                    levels.append(OTHER)
                self.levels_[col] = levels

    def shape(self) -> tuple:
        return tuple(len(self.levels_[c]) for c in self.columns)

    def encode(self, dataset: TabularDataset) -> pd.DataFrame:
        out = {}
        for col in self.columns:
            if col in self.numerical_cols:
                edges = self.bin_edges_[col]
                idx = np.digitize(dataset.df[col].to_numpy(dtype=float), edges[1:-1], right=False)
                out[col] = np.clip(idx, 0, self.num_bins - 1)
            else:
                levels = self.levels_[col]
                lookup = {v: i for i, v in enumerate(levels)}
                # Unknown values go to OTHER when the domain has one; a declared (complete)
                # domain has none, and a value outside it is a schema violation preflight owns.
                fallback = lookup.get(OTHER, 0)
                out[col] = (
                    dataset.df[col].map(lambda v, _lk=lookup, _f=fallback: _lk.get(v, _f))
                ).to_numpy(dtype=int)
        return pd.DataFrame(out)

    def decode(self, coded: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
        data = {}
        for col in self.columns:
            idx = np.clip(coded[col].to_numpy(dtype=int), 0, len(self.levels_[col]) - 1)
            if col in self.numerical_cols:
                edges = self.bin_edges_[col]
                data[col] = rng.uniform(edges[idx], edges[idx + 1])
            else:
                data[col] = np.asarray(self.levels_[col], dtype=object)[idx]
        return pd.DataFrame(data)


def rho_for(target_eps: float, delta: float) -> float:
    """Total zCDP budget rho whose (eps, delta) conversion -- by the project's own accountant --
    is target_eps. A Gaussian with multiplier m is 1/(2 m^2)-zCDP, and zCDP adds exactly under
    composition, so any mix of Gaussian and exponential-mechanism steps whose rhos sum to this
    composes to target_eps (conservative side of the bisection, never above)."""
    m = calibrate_noise_scale(
        target_eps=target_eps, target_delta=delta, name="gaussian", sensitivity=1.0, steps=1
    )
    return 1.0 / (2.0 * m * m)


def sigma_for_rho(rho: float) -> float:
    """Gaussian noise scale (sensitivity 1) that costs exactly `rho`."""
    return float(np.sqrt(1.0 / (2.0 * rho)))


def em_eps_for_rho(rho: float) -> float:
    """Pure epsilon of an exponential-mechanism step that costs exactly `rho` (rho = eps^2/8)."""
    return float(np.sqrt(8.0 * rho))


def enable_x64() -> None:
    """64-bit JAX for private-PGM. float32 stalls or diverges above ~100K rows (mbi's own
    warning), and the full grids fit 70K-214K rows (audit H6). Idempotent."""
    try:
        import jax

        jax.config.update("jax_enable_x64", True)
    except Exception:  # pragma: no cover - jax absent; mbi import will say so
        pass


def sample_model(model, rows: int) -> pd.DataFrame:
    """Draws `rows` records from a fitted private-PGM model.

    Under 64-bit JAX, private-PGM's sampler calls `np.asarray(counts, dtype=float64)` on a
    float64 JAX array, which returns a READ-ONLY view, and then scales it in place -- "output
    array is read-only". The model is cast to float32 for sampling only: the probabilities it
    samples from need no more precision than that, and estimation already ran in float64.
    """
    import jax
    import jax.numpy as jnp

    def _f32(x):
        return x.astype(jnp.float32) if getattr(x, "dtype", None) == jnp.float64 else x

    m32 = jax.tree_util.tree_map(_f32, model)
    # The sampler recomputes marginals internally, so 64-bit mode is also switched off for the
    # duration of the draw and restored afterwards.
    was_x64 = bool(jax.config.jax_enable_x64)
    jax.config.update("jax_enable_x64", False)
    try:
        return pd.DataFrame(m32.synthetic_data(rows=rows).to_dict())
    finally:
        jax.config.update("jax_enable_x64", was_x64)
