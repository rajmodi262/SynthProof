"""Base abstract interface for synthetic data generators."""

from abc import ABC, abstractmethod

import pandas as pd

from synthproof.accounting.accountant import Accountant
from synthproof.data.dataset import TabularDataset
from synthproof.data.profiler import DomainProfile


class BaseGenerator(ABC):
    """Abstract base class for all synthetic tabular data generators."""

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.is_fitted = False

    @abstractmethod
    def fit(
        self,
        dataset: TabularDataset,
        profile: DomainProfile,
        accountant: Accountant,
        target_eps: float,
    ) -> None:
        """Fits generator on sensitive dataset under accountant budget charges.

        NOTE, found by the type checker on 2026-09-12: the detection-floor controls call this
        as `fit(ds, None, None, 0.0)`, deliberately -- a control spends no budget and has no
        domain to respect. So the real contract is Optional, and this declaration is stricter
        than the code. Widening it here alone is not the fix: all seven subclasses declare the
        concrete types and a subclass may widen a parameter but never narrow it, so mypy
        reports fourteen incompatible overrides. Doing it properly means deciding, per
        generator, whether None means "control, proceed" or "programming error, raise" -- a
        decision about the budget-charging contract. Tracked in docs/ROAD_TO_TEN.md.
        """
        pass

    @abstractmethod
    def generate(self, num_samples: int) -> pd.DataFrame:
        """Generates synthetic tabular samples."""
        pass
