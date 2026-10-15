"""Per-column independent Gaussian generator with DP-noised moments.

Fits a mean and standard deviation per numeric column and a histogram per categorical one,
then samples every column independently. It estimates no covariance matrix and applies no
rank or Gaussianisation transform, so it preserves no cross-column correlation at all.

THE NAME. This was `GaussianCopulaGenerator` in `copula.py`, registered as `"copula"`, and it
is not a copula and never was — a copula is precisely the dependence structure this omits.
The docstring had said so since audit finding F6, which made the documentation honest and
left the identifier lying: a reader scanning the registry, the API's mechanism list or a
figure legend saw "copula" and had no reason to open the file. Standing rule 4 is to name
things what they are, so the class, module and registry key now say `moments`.

No committed result referenced the old key, so nothing published changes.
"""

import numpy as np
import pandas as pd

from synthproof.accounting.accountant import Accountant
from synthproof.accounting.calibration import calibrate_noise_scale
from synthproof.accounting.noise import grid_sensitivity, noisy_real_query, sample_discrete_gaussian
from synthproof.accounting.types import MechanismSpec
from synthproof.data.dataset import TabularDataset
from synthproof.data.profiler import DomainProfile
from synthproof.generators.base import BaseGenerator


class GaussianMomentGenerator(BaseGenerator):
    """Estimates per-column moments and category histograms under a calibrated DP budget."""

    def __init__(self, seed: int = 42):
        super().__init__(seed=seed)
        self.means: dict = {}
        self.stds: dict = {}
        self.categories: dict = {}

    def fit(
        self,
        dataset: TabularDataset,
        profile: DomainProfile,
        accountant: Accountant,
        target_eps: float,
    ) -> None:
        """Fits per-column parameters, spending `target_eps` in total."""
        rng = np.random.default_rng(self.seed)

        n_num = len(dataset.numerical_cols)
        n_cat = len(dataset.categorical_cols)
        # Three queries per numeric column (shifted sum, sum of squares, count), one histogram
        # per categorical.
        n_queries = max(1, 3 * n_num + n_cat)

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
        """Mean and std from three bounded queries, each with a sensitivity that is actually true.

        CORRECTED 2026-10-16. This used to add discrete noise directly to the clipped mean and
        std, charged at sensitivity 1.0 (the comment admitted the clip width was ignored, audit
        finding F5). Two defects: the mean of n values clipped to [a, b] moves by up to
        (b - a) / n when a record is removed, which exceeds 1 for a small table or a wide range;
        and integer noise on a real number keeps the value's fractional part, so the release was
        not DP at any epsilon (see `noisy_real_query`). Now, with x' = clip(x) - a in [0, w]:

            S1 = sum x'    sensitivity w      S2 = sum x'^2    sensitivity w^2
            N  = count     sensitivity 1

        each released by a discrete Gaussian at the calibrated noise multiplier, and
        mean = a + S1/N, var = S2/N - (S1/N)^2 -- post-processing.
        """
        col_min = profile.columns[col].min_val
        col_max = profile.columns[col].max_val
        if col_min is None or col_max is None:
            raise ValueError(f"Column {col!r} has no DP range in the profile.")
        width = float(col_max) - float(col_min)
        if width <= 0:
            # A single-valued public range: nothing about the data to measure.
            self.means[col], self.stds[col] = float(col_min), 1e-3
            return

        shifted = dataset.df[col].clip(lower=col_min, upper=col_max).to_numpy(float) - col_min
        rng = np.random.default_rng(seed)
        released = {}
        for query, value, sens in (
            ("sum", float(shifted.sum()), width),
            ("sumsq", float((shifted**2).sum()), width**2),
        ):
            accountant.charge(
                MechanismSpec(
                    name="gaussian",
                    sensitivity=float(grid_sensitivity()),
                    noise_scale=noise_scale * grid_sensitivity(),
                    steps=1,
                ),
                run_id=f"moments_{query}_{col}",
            )
            released[query] = noisy_real_query(
                value, sens, noise_scale, "gaussian", int(rng.integers(0, 2**31 - 1))
            )
        accountant.charge(
            MechanismSpec(name="gaussian", sensitivity=1.0, noise_scale=noise_scale, steps=1),
            run_id=f"moments_count_{col}",
        )
        count_noise = sample_discrete_gaussian(
            sigma=noise_scale, size=1, seed=int(rng.integers(0, 2**31 - 1))
        )
        n = max(1.0, float((np.array([len(shifted)], dtype=float) + count_noise)[0]))

        mean_shifted = float(np.clip(released["sum"] / n, 0.0, width))
        var = released["sumsq"] / n - mean_shifted**2
        self.means[col] = float(col_min) + mean_shifted
        # Clamping to a positive floor is post-processing, so it costs nothing.
        self.stds[col] = float(np.sqrt(max(var, 1e-6)))

    def _fit_categorical(self, dataset, profile, col, noise_scale, seed, accountant):
        accountant.charge(
            MechanismSpec(name="gaussian", sensitivity=1.0, noise_scale=noise_scale, steps=1),
            run_id=f"moments_hist_{col}",
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
                data[col] = rng.normal(loc=self.means[col], scale=self.stds[col], size=num_samples)
            else:
                cats, probs = self.categories[col]
                data[col] = rng.choice(cats, p=probs, size=num_samples)

        return pd.DataFrame(data)
