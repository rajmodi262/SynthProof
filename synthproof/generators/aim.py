"""AIM / MST Marginal-based Differentially Private generator."""

import numpy as np
import pandas as pd

from synthproof.accounting.accountant import Accountant
from synthproof.accounting.types import MechanismSpec
from synthproof.accounting.noise import sample_discrete_gaussian
from synthproof.data.dataset import TabularDataset
from synthproof.data.profiler import DomainProfile
from synthproof.generators.base import BaseGenerator


class AIMGenerator(BaseGenerator):
    """Adaptive DP Marginal Mechanism (AIM / MST baseline) generator."""

    def __init__(self, seed: int = 42):
        super().__init__(seed=seed)
        self.marginals: dict = {}
        self.columns: list = []

    def fit(self, dataset: TabularDataset, profile: DomainProfile, accountant: Accountant, target_eps: float) -> None:
        """Selects and measures 1D/2D marginal distributions under DP mechanism spend."""
        np.random.seed(self.seed)
        self.columns = dataset.columns
        self.numerical_cols = dataset.numerical_cols
        self.categorical_cols = dataset.categorical_cols
        self.profile = profile

        num_cols = max(1, len(self.columns))
        # Gaussian composition scaling: noise_scale = sqrt(num_cols) / target_eps
        noise_scale = float(np.sqrt(num_cols) / max(1e-4, target_eps))

        for col in self.columns:
            spec = MechanismSpec(
                name="gaussian",
                sensitivity=1.0,
                noise_scale=noise_scale,
                steps=1
            )
            accountant.charge(spec, run_id=f"aim_marginal_{col}")

            if col in self.numerical_cols:
                col_min = profile.columns[col].min_val or 0.0
                col_max = profile.columns[col].max_val or 100.0
                hist, bin_edges = np.histogram(dataset.df[col], bins=10, range=(col_min, col_max))
                # Add DP noise to histogram bins
                noise = sample_discrete_gaussian(sigma=noise_scale, size=len(hist))
                dp_hist = np.maximum(0, hist + noise)
                probs = dp_hist / (dp_hist.sum() + 1e-10)
                self.marginals[col] = (bin_edges, probs)
            else:
                cats = profile.columns[col].categories or list(dataset.df[col].unique())
                counts = dataset.df[col].value_counts().to_dict()
                raw_counts = np.array([counts.get(c, 0) for c in cats])
                noise = sample_discrete_gaussian(sigma=noise_scale, size=len(cats))
                dp_counts = np.maximum(0, raw_counts + noise)
                probs = dp_counts / (dp_counts.sum() + 1e-10)
                self.marginals[col] = (cats, probs)

        self.is_fitted = True

    def generate(self, num_samples: int) -> pd.DataFrame:
        """Generates synthetic data by sampling from measured DP marginals."""
        if not self.is_fitted:
            raise RuntimeError("Generator must be fitted before calling generate().")
        np.random.seed(self.seed)

        data = {}
        for col in self.columns:
            if col in self.numerical_cols:
                bin_edges, probs = self.marginals[col]
                # Sample bin indices
                bin_indices = np.random.choice(len(probs), p=probs, size=num_samples)
                samples = []
                for idx in bin_indices:
                    low = bin_edges[idx]
                    high = bin_edges[idx + 1]
                    samples.append(np.random.uniform(low, high))
                data[col] = samples
            else:
                cats, probs = self.marginals[col]
                samples = np.random.choice(cats, p=probs, size=num_samples)
                data[col] = samples

        return pd.DataFrame(data)
