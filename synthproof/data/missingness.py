"""Missingness models and benchmark loaders for privacy auditing.

Provides:
  - `load_adult_raw`: Loads UCI Adult retaining native missingness ('?' mapped to NaN).
  - `inject_mcar`: Missing Completely At Random.
  - `inject_mar`: Missing At Random (missingness depends on observed covariates).
  - `inject_mnar`: Missing Not At Random (missingness depends on unobserved/masked values).
  - `inject_missingness`: Unified dispatcher for injected missingness overlays.
"""

import io
import zipfile
from typing import List, Optional

import numpy as np
import pandas as pd

from synthproof.data.dataset import TabularDataset
from synthproof.data.datasets import (
    ADULT,
    ADULT_COLUMNS,
    DEFAULT_DATA_DIR,
    adult_schema,
    fetch,
)
from synthproof.data.schema import Schema


def load_adult_raw(
    data_dir: str = DEFAULT_DATA_DIR, schema: Optional[Schema] = None
) -> TabularDataset:
    """Loads UCI Adult as a `TabularDataset`, retaining native missing values.

    Unlike `load_adult()`, which drops rows containing missing values ("?"), this loader
    maps "?" to `NaN` and retains all 32,561 records. Columns are filtered to the
    declared schema.
    """
    path = fetch(ADULT, data_dir)

    with zipfile.ZipFile(path) as zf:
        member = next(n for n in zf.namelist() if n.endswith("adult.data"))
        raw = zf.read(member)

    spec = schema or adult_schema()
    df = pd.read_csv(
        io.BytesIO(raw),
        header=None,
        names=ADULT_COLUMNS,
        skipinitialspace=True,
        na_values=["?"],
    )
    # Filter to declared public schema columns
    df = df[[c for c in spec.names if c in df.columns]].reset_index(drop=True)

    return TabularDataset(df=df, name="uci_adult_raw", schema=spec, preserve_missing=True)


def inject_mcar(
    df: pd.DataFrame,
    rate: float = 0.1,
    columns: Optional[List[str]] = None,
    seed: int = 42,
) -> pd.DataFrame:
    """Injects Missing Completely At Random (MCAR) values into specified columns.

    Each cell in target columns is independently masked with probability `rate`.
    """
    if not (0.0 < rate < 1.0):
        raise ValueError(f"Rate must be in (0, 1), got {rate}")

    rng = np.random.default_rng(seed)
    out = df.copy()
    target_cols = columns if columns is not None else list(out.columns)

    for col in target_cols:
        mask = rng.random(len(out)) < rate
        out.loc[mask, col] = np.nan

    return out


def inject_mar(
    df: pd.DataFrame,
    rate: float = 0.1,
    target_cols: Optional[List[str]] = None,
    observed_col: str = "age",
    seed: int = 42,
) -> pd.DataFrame:
    """Injects Missing At Random (MAR) values into target columns.

    Missingness probability in `target_cols` depends on an observed column (e.g. `observed_col`).
    Records with `observed_col` above median have higher probability of missingness:
        P(missing | observed > median) = 1.5 * rate
        P(missing | observed <= median) = 0.5 * rate
    Total expected missingness equals `rate`.
    """
    if not (0.0 < rate < 0.6):
        raise ValueError(f"Rate must be in (0, 0.6) for valid MAR bounds, got {rate}")

    rng = np.random.default_rng(seed)
    out = df.copy()

    if observed_col not in out.columns:
        raise ValueError(f"Observed column {observed_col!r} not found in DataFrame.")

    # Sort/split by median of observed column
    obs_vals = pd.to_numeric(out[observed_col], errors="coerce").fillna(0)
    median_val = float(obs_vals.median())
    high_mask = obs_vals > median_val

    p_high = min(1.5 * rate, 0.95)
    p_low = max(0.5 * rate, 0.01)

    targets = (
        target_cols if target_cols is not None else [c for c in out.columns if c != observed_col]
    )

    for col in targets:
        probs = np.where(high_mask, p_high, p_low)
        mask = rng.random(len(out)) < probs
        out.loc[mask, col] = np.nan

    return out


def inject_mnar(
    df: pd.DataFrame,
    rate: float = 0.1,
    columns: Optional[List[str]] = None,
    seed: int = 42,
) -> pd.DataFrame:
    """Injects Missing Not At Random (MNAR) values into specified columns.

    Missingness probability depends on the values of the target column itself.
    For numerical columns: values in the upper quartile (or above median) have elevated missingness.
    For categorical columns: more frequent categories have elevated missingness.
    """
    if not (0.0 < rate < 0.6):
        raise ValueError(f"Rate must be in (0, 0.6) for valid MNAR bounds, got {rate}")

    rng = np.random.default_rng(seed)
    out = df.copy()
    target_cols = columns if columns is not None else list(out.columns)

    for col in target_cols:
        series = out[col]
        # Check if numerical
        is_num = pd.api.types.is_numeric_dtype(series)
        if is_num:
            vals = pd.to_numeric(series, errors="coerce").fillna(0)
            med = float(vals.median())
            probs = np.where(vals > med, min(1.6 * rate, 0.95), max(0.4 * rate, 0.01))
        else:
            vc = series.value_counts(normalize=True)
            probs = series.map(
                lambda c, _vc=vc: (
                    min(1.5 * rate, 0.95) if _vc.get(c, 0) > 0.1 else max(0.5 * rate, 0.01)
                )
            ).to_numpy()

        mask = rng.random(len(out)) < probs
        out.loc[mask, col] = np.nan

    return out


def inject_missingness(
    df: pd.DataFrame,
    mechanism: str = "mcar",
    rate: float = 0.1,
    seed: int = 42,
) -> pd.DataFrame:
    """Dispatches missingness injection according to specified mechanism ('mcar', 'mar', 'mnar')."""
    mech = mechanism.lower()
    if mech == "mcar":
        return inject_mcar(df, rate=rate, seed=seed)
    elif mech == "mar":
        return inject_mar(df, rate=rate, seed=seed)
    elif mech == "mnar":
        return inject_mnar(df, rate=rate, seed=seed)
    else:
        raise ValueError(
            f"Unknown missingness mechanism {mechanism!r}. Expected mcar, mar, or mnar."
        )
