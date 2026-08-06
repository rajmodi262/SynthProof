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
    def fit(self, dataset: TabularDataset, profile: DomainProfile, accountant: Accountant, target_eps: float) -> None:
        """Fits generator on sensitive dataset under accountant budget charges."""
        pass

    @abstractmethod
    def generate(self, num_samples: int) -> pd.DataFrame:
        """Generates synthetic tabular samples."""
        pass
