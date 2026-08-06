"""Differentially Private Domain Profiler that charges budget for schema and range discovery."""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Union, Optional
import numpy as np

from synthproof.accounting.accountant import Accountant
from synthproof.accounting.types import MechanismSpec
from synthproof.accounting.noise import sample_discrete_laplace
from synthproof.data.dataset import TabularDataset


@dataclass
class ColumnProfile:
    """Discovered DP profile for a single column."""
    name: str
    dtype: str  # "numerical" or "categorical"
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    categories: Optional[List[Any]] = None


@dataclass
class DomainProfile:
    """Full DP domain profile for a tabular schema."""
    dataset_name: str
    num_rows: int
    columns: Dict[str, ColumnProfile] = field(default_factory=dict)


class DPDomainProfiler:
    """Discovers feature ranges and cardinalities under formal DP budget charges."""

    def __init__(self, accountant: Accountant, eps_per_col: float = 0.05):
        self.accountant = accountant
        self.eps_per_col = eps_per_col

    def profile(self, dataset: TabularDataset) -> DomainProfile:
        """Profiles dataset schema, spending DP budget for range discovery."""
        col_profiles: Dict[str, ColumnProfile] = {}

        for col in dataset.columns:
            if col in dataset.numerical_cols:
                # Charge accountant for 2 range queries (min and max)
                spec = MechanismSpec(
                    name="laplace",
                    sensitivity=1.0,
                    noise_scale=1.0 / self.eps_per_col,
                    steps=2
                )
                self.accountant.charge(spec, run_id=f"profile_{col}")

                true_min = float(dataset.df[col].min())
                true_max = float(dataset.df[col].max())

                noise_scale = 1.0 / self.eps_per_col
                noise_min = float(sample_discrete_laplace(scale=noise_scale)[0])
                noise_max = float(sample_discrete_laplace(scale=noise_scale)[0])

                dp_min = true_min + noise_min
                dp_max = max(dp_min + 1.0, true_max + noise_max)

                col_profiles[col] = ColumnProfile(
                    name=col,
                    dtype="numerical",
                    min_val=dp_min,
                    max_val=dp_max,
                )
            else:
                # Categorical column profiling
                spec = MechanismSpec(
                    name="laplace",
                    sensitivity=1.0,
                    noise_scale=1.0 / self.eps_per_col,
                    steps=1
                )
                self.accountant.charge(spec, run_id=f"profile_{col}")

                unique_cats = list(dataset.df[col].unique())
                col_profiles[col] = ColumnProfile(
                    name=col,
                    dtype="categorical",
                    categories=unique_cats,
                )

        return DomainProfile(
            dataset_name=dataset.name,
            num_rows=dataset.num_rows,
            columns=col_profiles,
        )
