"""Independent-marginal DP generator.

NOTE ON THE NAME: this is NOT AIM (McKenna et al., 2022). There is no exponential-mechanism
marginal selection, no iteration, no 2D/kD marginals, and no PGM inference — it measures
independent 1-D marginals and samples each column independently, so the synthetic data
carries no cross-column structure. It is retained deliberately as an honest ablation
baseline. See brutal_project_audit.md, finding F6.
"""

import numpy as np
import pandas as pd

from synthproof.accounting.accountant import Accountant
from synthproof.accounting.calibration import calibrate_noise_scale
from synthproof.accounting.noise import sample_discrete_gaussian
from synthproof.accounting.types import MechanismSpec
from synthproof.data.dataset import TabularDataset
from synthproof.data.profiler import DomainProfile
from synthproof.generators.base import BaseGenerator

NUM_BINS = 10


class AIMGenerator(BaseGenerator):
    """Measures one noisy 1-D marginal per column under a calibrated DP budget."""

    def __init__(self, seed: int = 42):
        super().__init__(seed=seed)
        self.marginals: dict = {}
        self.columns: list = []

    def fit(self, dataset: TabularDataset, profile: DomainProfile,
            accountant: Accountant, target_eps: float) -> None:
        """Measures one DP marginal per column, spending `target_eps` in total."""
        rng = np.random.default_rng(self.seed)
        self.columns = dataset.columns
        self.numerical_cols = dataset.numerical_cols
        self.categorical_cols = dataset.categorical_cols
        self.profile = profile

        n_queries = max(1, len(self.columns))

        # Calibrate once for the whole fit so the measured marginals cost exactly
        # target_eps. The previous heuristic, noise_scale = sqrt(d) / target_eps, was not
        # an inversion of the composition theorem: a target of 8.0 composed to 70.49.
        noise_scale = calibrate_noise_scale(
            target_eps=target_eps,
            target_delta=accountant.budget.delta,
            name="gaussian",
            sensitivity=1.0,
            steps=n_queries,
        )

        for col in self.columns:
            accountant.charge(
                MechanismSpec(name="gaussian", sensitivity=1.0,
                              noise_scale=noise_scale, steps=1),
                run_id=f"aim_marginal_{col}",
            )
            seed = int(rng.integers(0, 2**31 - 1))
            if col in self.numerical_cols:
                self.marginals[col] = self._fit_numeric(
                    dataset, profile, col, noise_scale, seed)
            else:
                self.marginals[col] = self._fit_categorical(
                    dataset, profile, col, noise_scale, seed)

        self.is_fitted = True

    def _fit_numeric(self, dataset, profile, col, noise_scale, seed):
        col_min = profile.columns[col].min_val
        col_max = profile.columns[col].max_val
        if col_min is None or col_max is None:
            raise ValueError(f"Column {col!r} has no DP range in the profile.")

        hist, bin_edges = np.histogram(dataset.df[col], bins=NUM_BINS,
                                       range=(col_min, col_max))
        noise = sample_discrete_gaussian(sigma=noise_scale, size=len(hist), seed=seed)
        return bin_edges, self._normalise(np.maximum(0, hist + noise), NUM_BINS)

    def _fit_categorical(self, dataset, profile, col, noise_scale, seed):
        # Only categories the DP profiler released may be used. Falling back to
        # dataset.df[col].unique() here would reintroduce the exact domain leak the
        # profiler exists to prevent (audit finding F5).
        cats = profile.columns[col].categories
        if not cats:
            raise ValueError(f"Column {col!r} has no DP category domain in the profile.")

        counts = dataset.df[col].value_counts().to_dict()
        raw = np.array([counts.get(c, 0) for c in cats])
        noise = sample_discrete_gaussian(sigma=noise_scale, size=len(cats), seed=seed)
        return cats, self._normalise(np.maximum(0, raw + noise), len(cats))

    @staticmethod
    def _normalise(counts: np.ndarray, k: int) -> np.ndarray:
        """Turns noisy counts into a probability vector, falling back to uniform.

        Heavy noise can clip every bin to zero. Renormalising that by a 1e-10 epsilon (as
        a previous version did) yields an all-zero vector that np.random.choice rejects,
        so the failure surfaced as an opaque error deep inside generate().
        """
        total = counts.sum()
        if total <= 0:
            return np.full(k, 1.0 / k)
        return counts / total

    def generate(self, num_samples: int) -> pd.DataFrame:
        """Generates synthetic data by sampling from the measured DP marginals."""
        if not self.is_fitted:
            raise RuntimeError("Generator must be fitted before calling generate().")
        rng = np.random.default_rng(self.seed)

        data = {}
        for col in self.columns:
            if col in self.numerical_cols:
                bin_edges, probs = self.marginals[col]
                idx = rng.choice(len(probs), p=probs, size=num_samples)
                data[col] = rng.uniform(bin_edges[idx], bin_edges[idx + 1])
            else:
                cats, probs = self.marginals[col]
                data[col] = rng.choice(cats, p=probs, size=num_samples)

        return pd.DataFrame(data)
