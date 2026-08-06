"""Tabular dataset abstractions and preprocessors."""

from typing import Dict, List, Optional
import pandas as pd
import numpy as np


class TabularDataset:
    """Wraps tabular datasets with column type classification and schema utilities."""

    def __init__(self, df: pd.DataFrame, name: str = "dataset"):
        self.df = df.copy()
        self.name = name
        self._classify_columns()

    def _classify_columns(self) -> None:
        self.numerical_cols: List[str] = []
        self.categorical_cols: List[str] = []

        for col in self.df.columns:
            if pd.api.types.is_numeric_dtype(self.df[col]) and self.df[col].nunique() > 10:
                self.numerical_cols.append(col)
            else:
                self.categorical_cols.append(col)

    @property
    def num_rows(self) -> int:
        return len(self.df)

    @property
    def num_cols(self) -> int:
        return len(self.df.columns)

    @property
    def columns(self) -> List[str]:
        return list(self.df.columns)

    @classmethod
    def create_synthetic_toy(cls, num_rows: int = 100, seed: int = 42) -> "TabularDataset":
        """Creates a toy tabular dataset (age, income, category) for testing."""
        np.random.seed(seed)
        ages = np.random.randint(18, 70, size=num_rows)
        incomes = np.random.normal(50000, 15000, size=num_rows)
        categories = np.random.choice(["A", "B", "C"], size=num_rows)
        df = pd.DataFrame({"age": ages, "income": incomes, "category": categories})
        return cls(df=df, name="toy_dataset")
