"""Differentially private domain profiler.

Discovers per-column ranges and category domains, charging the privacy budget for what
it learns. Noise is calibrated so the whole profiling pass costs the epsilon it was
given, rather than growing with the number of columns.

Audit finding F5 is closed here, in two parts:

  * The category domain is released through a noisy threshold rather than published verbatim.
  * Numeric ranges come from the schema's PUBLIC bounds and cost no budget, because a public
    fact reveals nothing. Only a column with no declared range falls back to a noisy min/max,
    and that path documents plainly that its sensitivity is an assumption.
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
    is_public_range: bool = False    # True when the range came from the schema, not the data


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
    def _public_bounds(dataset: TabularDataset, col: str):
        """Public [lower, upper] for a numeric column, or None if none is declared."""
        if dataset.schema is None or col not in dataset.numerical_cols:
            return None
        return dataset.bounds(col)

    def _query_count(self, dataset: TabularDataset) -> int:
        """Number of DP queries this pass will issue.

        A numeric column whose range is PUBLIC costs nothing: the bounds are already known, so
        there is nothing to learn and nothing to hide. Only columns without a declared range
        need a (2-query) noisy min/max, and only categorical columns need a histogram.
        """
        n = len(dataset.categorical_cols)
        for col in dataset.numerical_cols:
            if self._public_bounds(dataset, col) is None:
                n += 2
        return n

    def _sensitivity_for(self, dataset: TabularDataset, col: str) -> float:
        """Sensitivity of this column's queries.

        Categorical histograms have sensitivity 1 under add/remove-one. A noisy min/max on an
        unbounded column has *unbounded* sensitivity, so `self.sensitivity` there is an
        assumption, not a derivation — which is exactly why a release should declare bounds
        and take the zero-cost path instead. See audit finding F5.
        """
        return 1.0 if col not in dataset.numerical_cols else self.sensitivity

    def profile(self, dataset: TabularDataset, seed: Optional[int] = None) -> DomainProfile:
        """Profiles the dataset schema, spending at most `eps_budget` in total."""
        n_queries = self._query_count(dataset)
        if n_queries == 0:
            # Everything is publicly declared; profiling is free.
            rng = np.random.default_rng(seed)
            cols = {c: self._public_profile(dataset, c) for c in dataset.columns
                    if self._public_bounds(dataset, c) is not None}
            for c in dataset.categorical_cols:
                cols[c] = self._profile_categorical(dataset, c, 1.0, rng)
            return DomainProfile(dataset_name=dataset.name, num_rows=dataset.num_rows,
                                 columns={c: cols[c] for c in dataset.columns if c in cols})

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
                bounds = self._public_bounds(dataset, col)
                if bounds is not None:
                    # Declared publicly: use it, charge nothing. Spending budget to noisily
                    # re-estimate a range that is already public is pure waste — and with a
                    # correctly-sized sensitivity the estimate is garbage anyway. Before this
                    # branch existed, a column publicly bounded to [0, 100] was released with
                    # a noisy range like (1633, 1634): width 1, collapsing every record into a
                    # single bin and destroying all downstream structure.
                    col_profiles[col] = self._public_profile(dataset, col)
                else:
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

    def _public_profile(self, dataset: TabularDataset, col: str) -> ColumnProfile:
        """Uses the publicly declared range. Costs no budget, because it reveals nothing."""
        lo, hi = self._public_bounds(dataset, col)
        return ColumnProfile(name=col, dtype="numerical", min_val=float(lo),
                             max_val=float(hi), is_public_range=True)

    def _profile_numeric(self, dataset: TabularDataset, col: str, noise_scale: float,
                         rng: np.random.Generator, sensitivity: float) -> ColumnProfile:
        """Releases a noisy min/max for a column with no declared public range (2 queries).

        NOTE: min/max over an unbounded column has unbounded sensitivity, so the epsilon
        charged here rests on `self.sensitivity` being a correct assumption. Declare bounds in
        the schema instead — that path is both sound and free.
        """
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
                             rng: np.random.Generator,
                             sensitivity: float = 1.0) -> ColumnProfile:
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
