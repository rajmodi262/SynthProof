"""Gaussian Copula synthetic data generator with DP noise calibration."""

import numpy as np
import pandas as pd

from synthproof.accounting.accountant import Accountant
from synthproof.accounting.noise import sample_discrete_gaussian
from synthproof.accounting.types import MechanismSpec
from synthproof.data.dataset import TabularDataset
from synthproof.data.profiler import DomainProfile
from synthproof.generators.base import BaseGenerator


class GaussianCopulaGenerator(BaseGenerator):
    """Per-column independent Gaussian sampler with DP-noised moments.

    NOTE: despite the name, this does NOT implement a Gaussian copula. It estimates no
    covariance and applies no rank transform, so it preserves no cross-column
    correlation. See brutal_project_audit.md, F6.
    """

    def __init__(self, seed: int = 42):
        super().__init__(seed=seed)
        self.means: dict = {}
        self.stds: dict = {}
        self.categories: dict = {}

    def fit(self, dataset: TabularDataset, profile: DomainProfile,
            accountant: Accountant, target_eps: float) -> None:
        """Fits Gaussian Copula parameters under DP budget charge."""
        np.random.seed(self.seed)
        eps_per_feature = target_eps / max(1, len(dataset.columns))

        for col in dataset.columns:
            if col in dataset.numerical_cols:
                # Charge accountant for mean and std estimation
                spec = MechanismSpec(
                    name="gaussian",
                    sensitivity=1.0,
                    noise_scale=2.0 / eps_per_feature,
                    steps=2
                )
                accountant.charge(spec, run_id=f"copula_fit_{col}")

                col_min = profile.columns[col].min_val or 0.0
                col_max = profile.columns[col].max_val or 100.0

                # Clip to the DP-profiled range before measuring. Without this the mean
                # is taken over an unbounded domain, so it has unbounded sensitivity and
                # the `sensitivity=1.0` declared above is unjustifiable. (These bounds
                # were previously computed and then discarded.) Calibrating sensitivity
                # to (col_max - col_min) remains Tier 1 work; see brutal_project_audit.md F5.
                clipped = dataset.df[col].clip(lower=col_min, upper=col_max)

                true_mean = float(clipped.mean())
                true_std = float(clipped.std()) if len(dataset.df) > 1 else 1.0

                # Add noise
                noise_scale = 2.0 / eps_per_feature
                noise_mean = float(sample_discrete_gaussian(sigma=noise_scale)[0])
                noise_std = float(abs(sample_discrete_gaussian(sigma=noise_scale)[0]))

                self.means[col] = true_mean + noise_mean
                self.stds[col] = max(1e-3, true_std + noise_std)
            else:
                # Categorical column mode estimation
                spec = MechanismSpec(
                    name="laplace",
                    sensitivity=1.0,
                    noise_scale=1.0 / eps_per_feature,
                    steps=1
                )
                accountant.charge(spec, run_id=f"copula_fit_{col}")
                cats = profile.columns[col].categories or list(dataset.df[col].unique())
                counts = dataset.df[col].value_counts().to_dict()
                probs = np.array([counts.get(c, 0) + 1.0 for c in cats])
                probs = probs / probs.sum()
                self.categories[col] = (cats, probs)

        self.columns = dataset.columns
        self.numerical_cols = dataset.numerical_cols
        self.categorical_cols = dataset.categorical_cols
        self.is_fitted = True

    def generate(self, num_samples: int) -> pd.DataFrame:
        """Generates synthetic tabular samples."""
        if not self.is_fitted:
            raise RuntimeError("Generator must be fitted before calling generate().")
        np.random.seed(self.seed)

        data = {}
        for col in self.columns:
            if col in self.numerical_cols:
                mean = self.means[col]
                std = self.stds[col]
                samples = np.random.normal(loc=mean, scale=std, size=num_samples)
                data[col] = samples
            else:
                cats, probs = self.categories[col]
                samples = np.random.choice(cats, p=probs, size=num_samples)
                data[col] = samples

        return pd.DataFrame(data)
