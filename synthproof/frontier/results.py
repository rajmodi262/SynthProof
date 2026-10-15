"""Aggregated cell results: the bootstrap interval and the per-cell summary run_grid returns."""

from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Sequence

import numpy as np

from synthproof.evaluate.structure import (  # noqa: F401  (re-exported for existing callers)
    MAX_MODAL_SHARE,
    _association_matrix,
    _correlation_ratio,
    _cramers_v,
    _mean_abs_corr_error,
    informative_numeric_columns,
)


@dataclass
class Interval:
    """A point estimate with a bootstrapped confidence interval."""

    mean: float
    lo: float
    hi: float
    sd: float
    n: int

    def __str__(self) -> str:
        return f"{self.mean:.3f} [{self.lo:.3f}, {self.hi:.3f}]"


def bootstrap_ci(
    values: Sequence[float], confidence: float = 0.95, resamples: int = 4000, seed: int = 0
) -> Interval:
    """Percentile bootstrap interval over `values`."""
    arr = np.asarray([v for v in values if np.isfinite(v)], dtype=float)
    if arr.size == 0:
        return Interval(float("nan"), float("nan"), float("nan"), float("nan"), 0)
    if arr.size == 1:
        v = float(arr[0])
        return Interval(v, v, v, 0.0, 1)

    rng = np.random.default_rng(seed)
    means = rng.choice(arr, size=(resamples, arr.size), replace=True).mean(axis=1)
    alpha = (1.0 - confidence) / 2.0
    return Interval(
        mean=float(arr.mean()),
        lo=float(np.quantile(means, alpha)),
        hi=float(np.quantile(means, 1.0 - alpha)),
        sd=float(arr.std(ddof=1)) if arr.size > 1 else 0.0,
        n=int(arr.size),
    )


@dataclass
class CellResult:
    """Aggregated result for one (dataset, mechanism, epsilon) cell."""

    dataset: str
    mechanism: str
    target_eps: float
    seeds: int
    proved_eps: Interval
    audited_eps: Interval
    audit_p: Interval
    tstr_f1: Interval
    trtr_f1: Interval
    mia_auc: Interval
    correlation_error: Interval
    # Table-wide structure (audit M1): every column pair, not the one pair in corr_cols.
    structure_error_all: Optional[Interval] = None
    pair_tvd: Optional[Interval] = None
    usefulness_multi: Optional[Interval] = None
    raw: Dict[str, List[float]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("raw", None)
        return d
