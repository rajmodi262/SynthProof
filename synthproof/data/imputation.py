"""Missing-data imputation mechanisms for tabular privacy audits.

Implements experimental arms:
  - A0: Complete-case drop (`df.dropna()`). (Stability-1 row filter; bias baseline, NOT a leak).
  - A1: Sentinel/Missing-as-category. Categorical -> "__MISSING__"; Numeric -> public schema
        midpoint. Zero private queries.
  - A2: Uncharged marginal imputation. Mode for categoricals; median for numerics computed
        directly on sensitive data without privacy accounting. (Low-sensitivity marginal baseline).
  - A3: Charged DP marginal imputation. Same marginal estimators (mode, mean) computed under DP
  - A4: Uncharged cross-record imputation ($k$-NN). Imputes missing values by pooling across
        the $k$ nearest sensitive member records without privacy accounting.
        (High-capacity model-based leak).
  - A4_CHARGED: DP-charged cross-record imputation ($k$-NN). Same $k$-NN neighbor pooling
        with calibrated Laplace noise on neighbor class votes and means, formally charged.
"""

from typing import List, Optional

import numpy as np
import pandas as pd

from synthproof.accounting.accountant import Accountant
from synthproof.accounting.noise import grid_sensitivity, noisy_real_query, sample_discrete_laplace
from synthproof.accounting.types import MechanismSpec
from synthproof.data._imputation_common import (  # noqa: F401  (re-exported for existing callers)
    MISSING_CATEGORY_LABEL,
    bounded_shifted_sum,
)
from synthproof.data.imputation_knn import (  # noqa: F401  (re-exported for existing callers)
    _prepare_distance_features,
    dp_charged_knn_impute,
    knn_impute,
)
from synthproof.data.schema import CATEGORICAL, NUMERICAL, Schema


def complete_case_drop(df: pd.DataFrame) -> pd.DataFrame:
    """Arm A0: Drops all rows containing any missing value.

    Row-wise stability-1 filter. A baseline for selection bias; not a DP leak.
    """
    return df.dropna().reset_index(drop=True)


def sentinel_impute(
    df: pd.DataFrame,
    schema: Schema,
    missing_cat: str = MISSING_CATEGORY_LABEL,
) -> pd.DataFrame:
    """Arm A1: Fills missingness with declared public sentinels without reading private statistics.

    - Categoricals: filled with `missing_cat` (e.g. '__MISSING__').
    - Numericals: filled with the public schema midpoint: (lower + upper) / 2.0.
    """
    out = df.copy()
    for col_spec in schema.columns:
        col = col_spec.name
        if col not in out.columns:
            continue
        if out[col].isna().sum() == 0:
            continue

        if col_spec.kind == CATEGORICAL:
            out[col] = out[col].fillna(missing_cat)
        elif col_spec.kind == NUMERICAL:
            if col_spec.lower is None or col_spec.upper is None:
                raise ValueError(f"Column {col!r} lacks declared public bounds in schema.")
            midpoint = (col_spec.lower + col_spec.upper) / 2.0
            out[col] = out[col].fillna(midpoint)

    return out


def uncharged_impute(df: pd.DataFrame, schema: Schema) -> pd.DataFrame:
    """Arm A2: Imputes using empirical private statistics without privacy budget accounting.

    - Categoricals: filled with the empirical mode of the private column.
    - Numericals: filled with the empirical mean of the private column (clipped to the public
      bounds). The MEAN, not the median, so A2 and A3 use the same estimator and differ only in
      whether it is noised and charged, as the preregistration requires.
    This reads private row values across records without charging any DP budget.
    """
    out = df.copy()
    for col_spec in schema.columns:
        col = col_spec.name
        if col not in out.columns:
            continue
        if out[col].isna().sum() == 0:
            continue

        if col_spec.kind == CATEGORICAL:
            modes = out[col].mode(dropna=True)
            mode_val = modes.iloc[0] if len(modes) > 0 else MISSING_CATEGORY_LABEL
            out[col] = out[col].fillna(mode_val)
        elif col_spec.kind == NUMERICAL:
            vals = out[col].dropna().to_numpy(dtype=float)
            if col_spec.lower is not None and col_spec.upper is not None:
                vals = np.clip(vals, col_spec.lower, col_spec.upper)
            if len(vals):
                mean_val = float(vals.mean())
            elif col_spec.lower is not None and col_spec.upper is not None:
                mean_val = (col_spec.lower + col_spec.upper) / 2.0
            else:
                mean_val = 0.0
            out[col] = out[col].fillna(mean_val)

    return out


def dp_charged_impute(
    df: pd.DataFrame,
    schema: Schema,
    accountant: Accountant,
    eps_imp: float,
    seed: int = 42,
) -> pd.DataFrame:
    """Arm A3: Imputes using private statistics perturbed by DP noise and charged to Accountant.

    - Categoricals: DP mode via Report-Noisy-Max over the DECLARED categories only.
      Sensitivity = 1.0; noise scale = 1.0 / eps_col. A candidate set read off the data would
      make the output space data-dependent (a value only one record holds could be released);
      a column with no declared domain falls back to the public sentinel, at no charge.
    - Numericals: DP mean bounded within schema bounds [lower, upper]. The noisy sum is over
      (value - lower), which lies in [0, upper - lower], so its add/remove-one sensitivity is
      exactly (upper - lower). Summing raw values instead has sensitivity max(|lower|, |upper|),
      which the earlier version under-charged (age in [15, 100]: 100, charged as 85).
      Sensitivity of count = 1.0. Budget split equally (eps_col / 2 for sum and for count).
    """
    if eps_imp <= 0:
        raise ValueError(f"eps_imp must be positive, got {eps_imp}")

    out = df.copy()
    # Find columns needing imputation
    missing_cols = [
        c.name for c in schema.columns if c.name in out.columns and out[c.name].isna().sum() > 0
    ]

    if not missing_cols:
        return out

    eps_per_col = eps_imp / len(missing_cols)
    rng = np.random.default_rng(seed)

    for col in missing_cols:
        col_spec = schema[col]
        col_seed = int(rng.integers(0, 2**31 - 1))

        if col_spec.kind == CATEGORICAL:
            # Candidates come from the PUBLIC schema only, never from the observed values.
            candidates: List[str] = [str(c) for c in (col_spec.categories or [])]
            if not candidates:
                # No declared domain: there is no private way to choose a category, so use the
                # public sentinel and charge nothing.
                out[col] = out[col].fillna(MISSING_CATEGORY_LABEL)
                continue

            # Empirical counts
            counts = out[col].value_counts()
            vec = np.array([float(counts.get(c, 0)) for c in candidates], dtype=float)

            # Report-noisy-max with Laplace noise
            noise_scale = 1.0 / eps_per_col
            noise = sample_discrete_laplace(scale=noise_scale, size=len(vec), seed=col_seed)
            noisy_counts = vec + noise
            dp_mode = candidates[int(np.argmax(noisy_counts))]

            # Charge accountant
            accountant.charge(
                MechanismSpec(
                    name="laplace",
                    sensitivity=1.0,
                    noise_scale=noise_scale,
                    steps=1,
                    metadata={"column": col, "mechanism": "dp_mode_report_noisy_max"},
                ),
                run_id=f"impute_dp_mode_{col}",
            )
            out[col] = out[col].fillna(dp_mode)

        elif col_spec.kind == NUMERICAL:
            lo = float(col_spec.lower if col_spec.lower is not None else 0.0)
            hi = float(col_spec.upper if col_spec.upper is not None else 1.0)
            width = hi - lo

            eps_half = eps_per_col / 2.0
            sum_scale = width / eps_half
            count_scale = 1.0 / eps_half

            # Charge accountant for sum and count
            # The shifted sum is real-valued, so it is released on the integer grid
            # (noisy_real_query; corrected 2026-10-16). Same ratio, same epsilon.
            accountant.charge(
                MechanismSpec(
                    name="laplace",
                    sensitivity=float(grid_sensitivity()),
                    noise_scale=(sum_scale / width) * grid_sensitivity(),
                    steps=1,
                    metadata={"column": col, "query": "dp_sum", "grid": "noisy_real_query"},
                ),
                run_id=f"impute_dp_sum_{col}",
            )
            accountant.charge(
                MechanismSpec(
                    name="laplace",
                    sensitivity=1.0,
                    noise_scale=count_scale,
                    steps=1,
                    metadata={"column": col, "query": "dp_count"},
                ),
                run_id=f"impute_dp_count_{col}",
            )

            valid_vals = out[col].dropna().to_numpy(dtype=float)
            sum_seed = int(rng.integers(0, 2**31 - 1))
            count_seed = int(rng.integers(0, 2**31 - 1))

            noise_count = float(
                sample_discrete_laplace(scale=count_scale, size=1, seed=count_seed)[0]
            )

            # Shifted by the public lower bound so each record contributes [0, width].
            dp_shifted_sum = noisy_real_query(
                bounded_shifted_sum(valid_vals, lo, hi),
                width,
                sum_scale / width,
                "laplace",
                sum_seed,
            )
            dp_count = max(1.0, float(len(valid_vals)) + noise_count)

            dp_mean = float(np.clip(lo + dp_shifted_sum / dp_count, lo, hi))
            out[col] = out[col].fillna(dp_mean)

    return out


def impute_arm(
    arm: str,
    df: pd.DataFrame,
    schema: Schema,
    accountant: Optional[Accountant] = None,
    eps_imp: float = 0.1,
    seed: int = 42,
) -> pd.DataFrame:
    """Unified entrypoint for the experimental imputation arms.

    Args:
        arm: One of 'A0', 'A1', 'A2', 'A3', 'A4', 'A4_CHARGED' (case-insensitive).
        df: Input DataFrame containing potential missing values.
        schema: Public Schema definition.
        accountant: Required for arms A3 and A4_CHARGED.
        eps_imp: Imputation epsilon budget (allocated to arms A3 and A4_CHARGED).
        seed: Random seed for reproducibility.

    Returns:
        pd.DataFrame with 0 NaNs across all schema columns.
    """
    arm_norm = arm.upper()
    if arm_norm == "A0":
        return complete_case_drop(df)
    elif arm_norm == "A1":
        return sentinel_impute(df, schema)
    elif arm_norm == "A2":
        return uncharged_impute(df, schema)
    elif arm_norm == "A3":
        if accountant is None:
            raise ValueError("Arm A3 requires an active Accountant instance.")
        return dp_charged_impute(df, schema, accountant, eps_imp, seed=seed)
    elif arm_norm == "A4":
        return knn_impute(df, schema)
    elif arm_norm == "A4_CHARGED":
        if accountant is None:
            raise ValueError("Arm A4_CHARGED requires an active Accountant instance.")
        return dp_charged_knn_impute(df, schema, accountant, eps_imp, seed=seed)
    else:
        raise ValueError(
            f"Unknown imputation arm {arm!r}. "
            "Expected one of ['A0', 'A1', 'A2', 'A3', 'A4', 'A4_CHARGED']."
        )
