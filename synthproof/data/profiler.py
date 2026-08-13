"""Differentially private domain profiler.

Discovers per-column ranges and category domains, charging the privacy budget for what
it learns. Noise is calibrated so the whole profiling pass costs the epsilon it was
given, rather than growing with the number of columns.

Known limitation (audit finding F5, partially open): min/max over an unbounded column
has unbounded sensitivity, so the `sensitivity` declared for the range queries is not yet
justified — that needs caller-declared public bounds. The categorical domain leak
described in F5 IS fixed here.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

from synthproof.accounting.accountant import Accountant
from synthproof.accounting.calibration import calibrate_noise_scale
from synthproof.accounting.noise import sample_discrete_laplace
from synthproof.accounting.types import MechanismSpec
from synthproof.data.dataset import TabularDataset


@dataclass
class ColumnProfile:
    """Discovered DP profile for a single column."""
    name: str
    dtype: str  # "numerical" or "categorical"
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    categories: Optional[List[Any]] = None
    suppressed_categories: int = 0   # rare categories withheld by the DP threshold


@dataclass
class DomainProfile:
    """Full DP domain profile for a tabular schema."""
    dataset_name: str
    num_rows: int
    columns: Dict[str, ColumnProfile] = field(default_factory=dict)
    eps_spent: float = 0.0


class DPDomainProfiler:
    """Discovers feature ranges and category domains under a calibrated DP budget.

    Column *names* and coarse types are treated as public schema metadata. Column
    *contents* — ranges, which categories occur, and how often — are sensitive and are
    released only through DP mechanisms.
    """

    def __init__(self, accountant: Accountant, eps_budget: float = 0.1,
                 sensitivity: float = 1.0, category_threshold_factor: float = 3.0):
        """
        Args:
            accountant: Accountant to charge.
            eps_budget: Total epsilon this profiling pass may spend. Noise is calibrated
                so the pass costs approximately this much regardless of column count.
                (Replaces the old `eps_per_col`, under which total cost grew with the
                schema and no caller could predict the release's epsilon.)
            sensitivity: Assumed per-query sensitivity.
            category_threshold_factor: Categories whose noisy count falls below this many
                noise standard deviations are suppressed. This is what stops the domain
                itself from leaking rare values.
        """
        if eps_budget <= 0:
            raise ValueError(f"eps_budget must be positive, got {eps_budget}")
        self.accountant = accountant
        self.eps_budget = eps_budget
        self.sensitivity = sensitivity
        self.category_threshold_factor = category_threshold_factor

    @staticmethod
    def _query_count(dataset: TabularDataset) -> int:
        """Two range queries per numeric column, one histogram per categorical column."""
        return 2 * len(dataset.numerical_cols) + len(dataset.categorical_cols)

    def _sensitivity_for(self, dataset: TabularDataset, col: str) -> float:
        """Sensitivity of this column's queries, derived from the public schema where possible.

        For a column clipped to a public range [lower, upper], adding or removing one record
        moves a min/max query by at most the range width, so `width` is a defensible
        sensitivity. Without a schema there is no public bound, the true sensitivity is
        unbounded, and `self.sensitivity` is an assumption rather than a derivation — which is
        why a real release should always supply a schema. See audit finding F5.

        Categorical histogram queries have sensitivity 1 under add/remove-one regardless.
        """
        if col not in dataset.numerical_cols:
            return 1.0
        bounds = dataset.bounds(col) if dataset.schema is not None else None
        if bounds is None:
            return self.sensitivity
        return max(1e-9, float(bounds[1] - bounds[0]))

    def profile(self, dataset: TabularDataset, seed: Optional[int] = None) -> DomainProfile:
        """Profiles the dataset schema, spending `eps_budget` in total."""
        n_queries = self._query_count(dataset)
        if n_queries == 0:
            return DomainProfile(dataset_name=dataset.name, num_rows=dataset.num_rows)

        # Calibrate a noise MULTIPLIER — the scale expressed in units of sensitivity — rather
        # than an absolute scale. Columns have different sensitivities (a range query on an
        # income column bounded to [0, 500000] is far more sensitive than a count), but a
        # shared multiplier gives every query the same RDP curve, so the whole pass still
        # composes to exactly eps_budget.
        noise_multiplier = calibrate_noise_scale(
            target_eps=self.eps_budget,
            target_delta=self.accountant.budget.delta,
            name="laplace",
            sensitivity=1.0,
            steps=n_queries,
        )

        rng = np.random.default_rng(seed)
        eps_before = self.accountant.total()
        col_profiles: Dict[str, ColumnProfile] = {}

        for col in dataset.columns:
            sens = self._sensitivity_for(dataset, col)
            noise_scale = noise_multiplier * sens
            if col in dataset.numerical_cols:
                col_profiles[col] = self._profile_numeric(
                    dataset, col, noise_scale, rng, sens)
            else:
                col_profiles[col] = self._profile_categorical(
                    dataset, col, noise_scale, rng, sens)

        return DomainProfile(
            dataset_name=dataset.name,
            num_rows=dataset.num_rows,
            columns=col_profiles,
            eps_spent=self.accountant.total() - eps_before,
        )

    def _profile_numeric(self, dataset: TabularDataset, col: str, noise_scale: float,
                         rng: np.random.Generator, sensitivity: float) -> ColumnProfile:
        """Releases noisy min/max for a numeric column (2 queries)."""
        self.accountant.charge(
            MechanismSpec(name="laplace", sensitivity=sensitivity,
                          noise_scale=noise_scale, steps=2),
            run_id=f"profile_range_{col}",
        )

        seed = int(rng.integers(0, 2**31 - 1))
        noise = sample_discrete_laplace(scale=noise_scale, size=2, seed=seed)

        dp_min = float(dataset.df[col].min()) + float(noise[0])
        dp_max = max(dp_min + 1.0, float(dataset.df[col].max()) + float(noise[1]))
        return ColumnProfile(name=col, dtype="numerical", min_val=dp_min, max_val=dp_max)

    def _profile_categorical(self, dataset: TabularDataset, col: str, noise_scale: float,
                             rng: np.random.Generator, sensitivity: float = 1.0) -> ColumnProfile:
        """Releases a DP category domain for a categorical column (1 histogram query).

        A previous version charged epsilon here and then published
        ``dataset.df[col].unique()`` verbatim — the exact, un-noised category domain,
        including any value occurring exactly once. Paying budget and then not applying
        the mechanism is strictly worse than not paying: privacy is spent AND the rare
        values that most identify individuals leak deterministically.

        Categories are now kept only when their noisy count clears a threshold, so a
        value present in a single record is unlikely to survive into the domain.
        """
        self.accountant.charge(
            MechanismSpec(name="laplace", sensitivity=sensitivity,
                          noise_scale=noise_scale, steps=1),
            run_id=f"profile_domain_{col}",
        )

        observed = list(dataset.df[col].unique())
        counts = dataset.df[col].value_counts().to_dict()

        seed = int(rng.integers(0, 2**31 - 1))
        noise = sample_discrete_laplace(scale=noise_scale, size=len(observed), seed=seed)

        # Discrete Laplace with scale b has standard deviation b * sqrt(2).
        threshold = self.category_threshold_factor * noise_scale * np.sqrt(2.0)

        kept = [
            cat for i, cat in enumerate(observed)
            if counts.get(cat, 0) + float(noise[i]) >= threshold
        ]
        suppressed = len(observed) - len(kept)

        # A completely empty domain is worse than a coarse one: downstream generators
        # would have nothing to sample. Fall back to the single most frequent category.
        if not kept and observed:
            kept = [max(observed, key=lambda c: counts.get(c, 0))]
            suppressed = len(observed) - 1

        return ColumnProfile(
            name=col,
            dtype="categorical",
            categories=kept,
            suppressed_categories=suppressed,
        )
