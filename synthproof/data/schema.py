"""Public schema declarations for tabular datasets.

Differential privacy needs a *public* domain. If the clipping bounds or the category domain
are derived from the sensitive data itself, they leak — and any sensitivity claimed on top of
them is unjustified. This module makes that boundary explicit:

  * A `Schema` is **public metadata** supplied by the data holder. Column names, coarse types,
    and numeric bounds are assumed to be publishable facts about the domain (an age lies in
    [0, 120]; an income in [0, 1e7]). Nothing here is measured from the data.
  * `Schema.infer_nonprivate()` exists for convenience, and its name is deliberately loud: it
    reads the sensitive table and therefore **must not** be used for a real release. It is
    fine for tests and for exploring a dataset you already own.

Declared bounds are what make the profiler's sensitivity defensible: clipping a column to a
public [lower, upper] gives a mean sensitivity of (upper - lower) / n rather than the unbounded
sensitivity of an unclipped column. See brutal_project_audit.md, finding F5.
"""

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd

NUMERICAL = "numerical"
CATEGORICAL = "categorical"


@dataclass(frozen=True)
class ColumnSpec:
    """Public declaration for one column."""

    name: str
    kind: str                                    # NUMERICAL or CATEGORICAL
    lower: Optional[float] = None                # public clip bound (numerical)
    upper: Optional[float] = None                # public clip bound (numerical)
    categories: Optional[List[Any]] = None       # public domain (categorical), if known

    def __post_init__(self):
        if self.kind not in (NUMERICAL, CATEGORICAL):
            raise ValueError(
                f"Column {self.name!r}: kind must be {NUMERICAL!r} or {CATEGORICAL!r}, "
                f"got {self.kind!r}"
            )
        if self.kind == NUMERICAL:
            if self.lower is None or self.upper is None:
                raise ValueError(
                    f"Column {self.name!r}: numerical columns require public `lower` and "
                    "`upper` bounds. Deriving them from the data would leak, and the "
                    "sensitivity claimed on top of them would be unjustified."
                )
            if self.lower >= self.upper:
                raise ValueError(
                    f"Column {self.name!r}: lower ({self.lower}) must be < upper ({self.upper})"
                )

    @property
    def width(self) -> float:
        """Public range width — the basis for a defensible sensitivity."""
        if self.kind != NUMERICAL:
            raise ValueError(f"Column {self.name!r} is categorical and has no width.")
        return float(self.upper - self.lower)


@dataclass
class Schema:
    """A public description of a tabular domain."""

    columns: List[ColumnSpec] = field(default_factory=list)

    def __post_init__(self):
        seen = set()
        for c in self.columns:
            if c.name in seen:
                raise ValueError(f"Duplicate column in schema: {c.name!r}")
            seen.add(c.name)

    # ------------------------------------------------------------------ accessors

    def __len__(self) -> int:
        return len(self.columns)

    def __getitem__(self, name: str) -> ColumnSpec:
        for c in self.columns:
            if c.name == name:
                return c
        raise KeyError(f"No column {name!r} in schema")

    @property
    def names(self) -> List[str]:
        return [c.name for c in self.columns]

    @property
    def numerical(self) -> List[str]:
        return [c.name for c in self.columns if c.kind == NUMERICAL]

    @property
    def categorical(self) -> List[str]:
        return [c.name for c in self.columns if c.kind == CATEGORICAL]

    # ------------------------------------------------------------------ io

    def to_dict(self) -> Dict[str, Any]:
        out = []
        for c in self.columns:
            d: Dict[str, Any] = {"name": c.name, "kind": c.kind}
            if c.kind == NUMERICAL:
                d["lower"], d["upper"] = c.lower, c.upper
            elif c.categories is not None:
                d["categories"] = list(c.categories)
            out.append(d)
        return {"columns": out}

    def to_json(self, path: Optional[str] = None) -> str:
        text = json.dumps(self.to_dict(), indent=2)
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
        return text

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Schema":
        return cls(columns=[ColumnSpec(**c) for c in data["columns"]])

    @classmethod
    def from_json(cls, path: str) -> "Schema":
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    # ------------------------------------------------------------------ inference

    @classmethod
    def infer_nonprivate(cls, df: pd.DataFrame,
                         max_categories: int = 20) -> "Schema":
        """Infers a schema BY READING THE DATA. Not safe for a real release.

        Every bound this produces is a function of the sensitive table, so publishing a
        dataset profiled against such a schema leaks the true min and max of every numeric
        column. Use it for tests and exploration; supply a real `Schema` for a release.

        The loud name is the point — a reviewer scanning the pipeline should be able to see
        immediately whether any non-private path was taken.
        """
        specs: List[ColumnSpec] = []
        for col in df.columns:
            series = df[col]
            if pd.api.types.is_numeric_dtype(series) and series.nunique() > max_categories:
                lo, hi = float(series.min()), float(series.max())
                if lo >= hi:
                    hi = lo + 1.0
                specs.append(ColumnSpec(name=col, kind=NUMERICAL, lower=lo, upper=hi))
            else:
                specs.append(ColumnSpec(name=col, kind=CATEGORICAL,
                                        categories=sorted(map(str, series.unique()))))
        return cls(columns=specs)
