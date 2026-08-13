"""Tabular dataset abstraction.

A `TabularDataset` carries the data plus, ideally, a public `Schema`. When a schema is
supplied, numeric columns are clipped to their declared public bounds on construction, which is
what makes any downstream sensitivity claim defensible.

Without a schema the dataset falls back to inferring column kinds from the data itself
(`nunique() > 10`). That fallback is convenient for tests but is a non-private decision derived
from sensitive values, so a real release should always pass a schema.
"""

from typing import List, Optional

import numpy as np
import pandas as pd

from synthproof.data.schema import CATEGORICAL, NUMERICAL, ColumnSpec, Schema

# Threshold used only by the schema-free fallback path.
_FALLBACK_CATEGORICAL_MAX_UNIQUE = 10


class TabularDataset:
    """Wraps a dataframe with column-type classification and an optional public schema."""

    def __init__(self, df: pd.DataFrame, name: str = "dataset",
                 schema: Optional[Schema] = None):
        self.name = name
        self.schema = schema

        if schema is not None:
            missing = [c for c in schema.names if c not in df.columns]
            if missing:
                raise ValueError(f"Columns declared in schema but absent from data: {missing}")
            # Keep only declared columns, in declared order — the schema defines the release.
            df = df[schema.names]

        self.df = df.copy()

        if schema is not None:
            self._apply_schema(schema)
        else:
            self._classify_columns()

    # ------------------------------------------------------------------ construction

    def _apply_schema(self, schema: Schema) -> None:
        """Clips numerics to their public bounds and records column kinds."""
        self.numerical_cols = list(schema.numerical)
        self.categorical_cols = list(schema.categorical)

        for spec in schema.columns:
            if spec.kind == NUMERICAL:
                # Clipping to a PUBLIC range is what bounds sensitivity. Clipping against
                # data-derived bounds instead would leak the true extremes.
                self.df[spec.name] = pd.to_numeric(
                    self.df[spec.name], errors="coerce"
                ).fillna(spec.lower).clip(lower=spec.lower, upper=spec.upper)
            else:
                self.df[spec.name] = self.df[spec.name].astype(str)
                if spec.categories is not None:
                    allowed = set(map(str, spec.categories))
                    # Values outside the declared domain go to a sentinel rather than
                    # silently widening the domain the release commits to.
                    self.df[spec.name] = self.df[spec.name].where(
                        self.df[spec.name].isin(allowed), other="__OTHER__"
                    )

    def _classify_columns(self) -> None:
        """Fallback classification when no schema is supplied."""
        self.numerical_cols: List[str] = []
        self.categorical_cols: List[str] = []

        for col in self.df.columns:
            is_num = pd.api.types.is_numeric_dtype(self.df[col])
            if is_num and self.df[col].nunique() > _FALLBACK_CATEGORICAL_MAX_UNIQUE:
                self.numerical_cols.append(col)
            else:
                self.categorical_cols.append(col)

    @classmethod
    def from_csv(cls, path: str, schema: Optional[Schema] = None,
                 name: Optional[str] = None, **read_csv_kwargs) -> "TabularDataset":
        """Loads a CSV, applying a public schema if one is supplied.

        Args:
            path: Path to the CSV.
            schema: Public schema. If omitted, column kinds are inferred FROM THE DATA,
                which is not safe for a real release — see `Schema.infer_nonprivate`.
            name: Dataset name; defaults to the file stem.
            **read_csv_kwargs: Forwarded to `pandas.read_csv` (e.g. `na_values`, `sep`).
        """
        defaults = {"skipinitialspace": True}
        defaults.update(read_csv_kwargs)
        df = pd.read_csv(path, **defaults)
        df = df.dropna(axis=0, how="any").reset_index(drop=True)

        if name is None:
            base = str(path).replace("\\", "/").rsplit("/", 1)[-1]
            name = base.rsplit(".", 1)[0]

        return cls(df=df, name=name, schema=schema)

    @classmethod
    def create_synthetic_toy(cls, num_rows: int = 100, seed: int = 42) -> "TabularDataset":
        """Creates a toy dataset (age, income, category).

        NOTE: the three columns are drawn INDEPENDENTLY, so there is no joint structure for a
        synthesiser to preserve or destroy. Utility measured on this table is close to
        meaningless — it exists for unit tests, not for experiments.
        """
        np.random.seed(seed)
        rng = np.random.default_rng(seed)
        df = pd.DataFrame({
            "age": rng.integers(18, 70, size=num_rows),
            "income": rng.normal(50000, 15000, size=num_rows),
            "category": rng.choice(["A", "B", "C"], size=num_rows),
        })
        schema = Schema(columns=[
            ColumnSpec("age", NUMERICAL, lower=18.0, upper=70.0),
            ColumnSpec("income", NUMERICAL, lower=0.0, upper=150000.0),
            ColumnSpec("category", CATEGORICAL, categories=["A", "B", "C"]),
        ])
        return cls(df=df, name="toy_dataset", schema=schema)

    # ------------------------------------------------------------------ properties

    @property
    def num_rows(self) -> int:
        return len(self.df)

    @property
    def num_cols(self) -> int:
        return len(self.df.columns)

    @property
    def columns(self) -> List[str]:
        return list(self.df.columns)

    def bounds(self, col: str):
        """Public (lower, upper) for a numeric column, or None if no schema declares it."""
        if self.schema is None:
            return None
        spec = self.schema[col]
        return (spec.lower, spec.upper) if spec.kind == NUMERICAL else None
