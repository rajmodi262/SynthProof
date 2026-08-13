"""Per-column independent Gaussian generator with DP-noised moments.

NOTE ON THE NAME: despite `GaussianCopulaGenerator`, this does NOT implement a Gaussian
copula. It estimates no covariance matrix and applies no rank/Gaussianisation transform,
so it preserves no cross-column correlation. Kept as a second honest baseline until a real
copula lands. See brutal_project_audit.md, finding F6.
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


class GaussianCopulaGenerator(BaseGenerator):
    """Estimates per-column moments and category histograms under a calibrated DP budget."""

    def __init__(self, seed: int = 42):
        super().__init__(seed=seed)
        self.means: dict = {}
        self.stds: dict = {}
        self.categories: dict = {}

    def fit(self, dataset: TabularDataset, profile: DomainProfile,
            accountant: Accountant, target_eps: float) -> None:
        """Fits per-column parameters, spending `target_eps` in total."""
        rng = np.random.default_rng(self.seed)

        n_num = len(dataset.numerical_cols)
        n_cat = len(dataset.categorical_cols)
        # Two queries per numeric column (mean, std), one histogram per categorical.
        n_queries = max(1, 2 * n_num + n_cat)

        noise_scale = calibrate_noise_scale(
            target_eps=target_eps,
            target_delta=accountant.budget.delta,
            name="gaussian",
            sensitivity=1.0,
            steps=n_queries,
        )

        for col in dataset.columns:
            seed = int(rng.integers(0, 2**31 - 1))
            if col in dataset.numerical_cols:
                self._fit_numeric(dataset, profile, col, noise_scale, seed, accountant)
            else:
                self._fit_categorical(dataset, profile, col, noise_scale, seed, accountant)

        self.columns = dataset.columns
        self.numerical_cols = dataset.numerical_cols
        self.categorical_cols = dataset.categorical_cols
        self.is_fitted = True

    def _fit_numeric(self, dataset, profile, col, noise_scale, seed, accountant):
        accountant.charge(
            MechanismSpec(name="gaussian", sensitivity=1.0,
                          noise_scale=noise_scale, steps=2),
            run_id=f"copula_moments_{col}",
        )

        col_min = profile.columns[col].min_val
        col_max = profile.columns[col].max_val
        if col_min is None or col_max is None:
            raise ValueError(f"Column {col!r} has no DP range in the profile.")

        # Clip to the DP-profiled range before measuring. Without this the mean is taken
        # over an unbounded domain, so it has unbounded sensitivity and the declared
        # sensitivity=1.0 is unjustifiable. Calibrating sensitivity to the clip width
        # remains open (audit finding F5).
        clipped = dataset.df[col].clip(lower=col_min, upper=col_max)
        true_mean = float(clipped.mean())
        true_std = float(clipped.std()) if len(dataset.df) > 1 else 1.0

        noise = sample_discrete_gaussian(sigma=noise_scale, size=2, seed=seed)
        # NOTE: no abs() on the noise. A previous version used abs(...) on the std noise,
        # which is a biased one-sided perturbation, not the Gaussian mechanism, and voided
        # the guarantee. Clamping the *result* to a positive floor is post-processing and
        # is therefore safe.
        self.means[col] = true_mean + float(noise[0])
        self.stds[col] = max(1e-3, true_std + float(noise[1]))

    def _fit_categorical(self, dataset, profile, col, noise_scale, seed, accountant):
        accountant.charge(
            MechanismSpec(name="gaussian", sensitivity=1.0,
                          noise_scale=noise_scale, steps=1),
            run_id=f"copula_hist_{col}",
        )

        cats = profile.columns[col].categories
        if not cats:
            raise ValueError(f"Column {col!r} has no DP category domain in the profile.")

        counts = dataset.df[col].value_counts().to_dict()
        raw = np.array([counts.get(c, 0) for c in cats], dtype=float)

        # A previous version charged epsilon here and then used the raw counts with a +1
        # smoothing constant — it paid for a mechanism it never applied, releasing exact
        # category frequencies. The noise below is the mechanism actually being charged.
        noise = sample_discrete_gaussian(sigma=noise_scale, size=len(cats), seed=seed)
        dp_counts = np.maximum(0.0, raw + noise)

        total = dp_counts.sum()
        probs = (dp_counts / total) if total > 0 else np.full(len(cats), 1.0 / len(cats))
        self.categories[col] = (cats, probs)

    def generate(self, num_samples: int) -> pd.DataFrame:
        """Generates synthetic tabular samples."""
        if not self.is_fitted:
            raise RuntimeError("Generator must be fitted before calling generate().")
        rng = np.random.default_rng(self.seed)

        data = {}
        for col in self.columns:
            if col in self.numerical_cols:
                data[col] = rng.normal(loc=self.means[col], scale=self.stds[col],
                                       size=num_samples)
            else:
                cats, probs = self.categories[col]
                data[col] = rng.choice(cats, p=probs, size=num_samples)

        return pd.DataFrame(data)
