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
from sklearn.neighbors import NearestNeighbors

from synthproof.accounting.accountant import Accountant
from synthproof.accounting.noise import sample_discrete_laplace
from synthproof.accounting.types import MechanismSpec
from synthproof.data.schema import CATEGORICAL, NUMERICAL, Schema

MISSING_CATEGORY_LABEL = "__MISSING__"


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
    - Numericals: filled with the empirical median of the private column.
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
            med_val = float(out[col].median(skipna=True))
            if np.isnan(med_val):
                med_val = (
                    (col_spec.lower + col_spec.upper) / 2.0
                    if col_spec.lower is not None and col_spec.upper is not None
                    else 0.0
                )
            out[col] = out[col].fillna(med_val)

    return out


def dp_charged_impute(
    df: pd.DataFrame,
    schema: Schema,
    accountant: Accountant,
    eps_imp: float,
    seed: int = 42,
) -> pd.DataFrame:
    """Arm A3: Imputes using private statistics perturbed by DP noise and charged to Accountant.

    - Categoricals: DP mode via Report-Noisy-Max over candidate categories.
      Sensitivity = 1.0; noise scale = 1.0 / eps_col.
    - Numericals: DP mean bounded within schema bounds [lower, upper].
      Sensitivity of sum = (upper - lower); Sensitivity of count = 1.0.
      Budget split equally (eps_col / 2 for sum, eps_col / 2 for count).
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
            # Candidate categories: schema categories or observed unique non-null values
            declared = col_spec.categories or []
            observed = list(out[col].dropna().unique())
            candidates: List[str] = sorted(list(set(str(c) for c in declared + observed)))
            if not candidates:
                candidates = [MISSING_CATEGORY_LABEL]

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
            accountant.charge(
                MechanismSpec(
                    name="laplace",
                    sensitivity=width,
                    noise_scale=sum_scale,
                    steps=1,
                    metadata={"column": col, "query": "dp_sum"},
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

            valid_vals = np.clip(out[col].dropna().to_numpy(dtype=float), lo, hi)
            sum_seed = int(rng.integers(0, 2**31 - 1))
            count_seed = int(rng.integers(0, 2**31 - 1))

            noise_sum = float(sample_discrete_laplace(scale=sum_scale, size=1, seed=sum_seed)[0])
            noise_count = float(
                sample_discrete_laplace(scale=count_scale, size=1, seed=count_seed)[0]
            )

            dp_sum = float(np.sum(valid_vals)) + noise_sum
            dp_count = max(1.0, float(len(valid_vals)) + noise_count)

            dp_mean = float(np.clip(dp_sum / dp_count, lo, hi))
            out[col] = out[col].fillna(dp_mean)

    return out


def _prepare_distance_features(df: pd.DataFrame, schema: Schema) -> np.ndarray:
    """Builds a standardized [0, 1] feature matrix for k-NN distance computation."""
    coarse_df = df.copy()
    for col_spec in schema.columns:
        c = col_spec.name
        if c not in coarse_df.columns:
            continue
        if coarse_df[c].isna().sum() > 0:
            if col_spec.kind == CATEGORICAL:
                m = coarse_df[c].mode(dropna=True)
                cat_val = (
                    m.iloc[0]
                    if len(m) > 0
                    else (col_spec.categories[0] if col_spec.categories else "missing")
                )
                coarse_df[c] = coarse_df[c].fillna(cat_val)
            else:
                med = coarse_df[c].median(skipna=True)
                if np.isnan(med):
                    med = (
                        (col_spec.lower + col_spec.upper) / 2.0
                        if col_spec.lower is not None and col_spec.upper is not None
                        else 0.0
                    )
                coarse_df[c] = coarse_df[c].fillna(med)

    parts: List[np.ndarray] = []
    for col_spec in schema.columns:
        c = col_spec.name
        if c not in coarse_df.columns:
            continue
        if col_spec.kind == NUMERICAL:
            lo = float(col_spec.lower if col_spec.lower is not None else 0.0)
            hi = float(col_spec.upper if col_spec.upper is not None else 1.0)
            val = (coarse_df[c].astype(float) - lo) / max(1e-6, hi - lo)
            parts.append(val.to_numpy()[:, None])
        else:
            cats = col_spec.categories or sorted(list(coarse_df[c].astype(str).unique()))
            cat_map = {cat: i for i, cat in enumerate(cats)}
            codes = coarse_df[c].astype(str).map(cat_map).fillna(0).to_numpy(dtype=float)
            codes_norm = codes / max(1, len(cats) - 1)
            parts.append(codes_norm[:, None])

    return np.hstack(parts) if parts else np.zeros((len(df), 1))


def knn_impute(
    df: pd.DataFrame,
    schema: Schema,
    k: int = 5,
) -> pd.DataFrame:
    """Arm A4: Uncharged cross-record k-nearest-neighbors imputation.

    Finds the k nearest sensitive member rows based on observed features and imputes:
    - Categoricals: Mode (plurality vote) across the k neighbors.
    - Numericals: Mean across the k neighbors.
    Reads multi-attribute private relationships across records without privacy accounting.
    """
    out = df.copy()
    missing_cols = [
        c.name for c in schema.columns if c.name in out.columns and out[c.name].isna().sum() > 0
    ]
    if not missing_cols or len(out) <= 1:
        return out

    k_eff = min(k, len(out) - 1)
    x_mat = _prepare_distance_features(df, schema)
    nn = NearestNeighbors(n_neighbors=k_eff + 1, metric="euclidean").fit(x_mat)
    _, indices = nn.kneighbors(x_mat)

    for col in missing_cols:
        col_spec = schema[col]
        missing_rows = np.where(out[col].isna())[0]

        if col_spec.kind == CATEGORICAL:
            col_mode_series = out[col].mode(dropna=True)
            fallback = (
                col_mode_series.iloc[0]
                if len(col_mode_series) > 0
                else (col_spec.categories[0] if col_spec.categories else MISSING_CATEGORY_LABEL)
            )
            for r in missing_rows:
                neighbor_idx = indices[r, 1 : k_eff + 1]
                n_vals = out[col].iloc[neighbor_idx].dropna()
                if len(n_vals) > 0:
                    modes = n_vals.mode()
                    val = modes.iloc[0] if len(modes) > 0 else fallback
                else:
                    val = fallback
                out.loc[r, col] = val
        else:
            col_med = float(out[col].median(skipna=True))
            fallback_num = col_med if not np.isnan(col_med) else 0.0
            for r in missing_rows:
                neighbor_idx = indices[r, 1 : k_eff + 1]
                n_vals = out[col].iloc[neighbor_idx].dropna().to_numpy(dtype=float)
                if len(n_vals) > 0:
                    val_num = float(np.mean(n_vals))
                else:
                    val_num = fallback_num
                out.loc[r, col] = val_num

    return out


def dp_charged_knn_impute(
    df: pd.DataFrame,
    schema: Schema,
    accountant: Accountant,
    eps_imp: float,
    k: int = 5,
    seed: int = 42,
) -> pd.DataFrame:
    """Arm A4_CHARGED: DP-charged cross-record k-nearest-neighbors imputation.

    Uses identical k-NN neighbor pooling as Arm A4, but with calibrated Laplace noise
    and formal accounting:
    - Categoricals: Report-Noisy-Max over candidate categories from neighbor votes.
    - Numericals: Bounded Laplace perturbation on neighbor mean.
    - Budget formally debited from `Accountant`.
    """
    if eps_imp <= 0:
        raise ValueError(f"eps_imp must be positive, got {eps_imp}")

    out = df.copy()
    missing_cols = [
        c.name for c in schema.columns if c.name in out.columns and out[c.name].isna().sum() > 0
    ]
    if not missing_cols or len(out) <= 1:
        return out

    k_eff = min(k, len(out) - 1)
    x_mat = _prepare_distance_features(df, schema)
    nn = NearestNeighbors(n_neighbors=k_eff + 1, metric="euclidean").fit(x_mat)
    _, indices = nn.kneighbors(x_mat)

    rng = np.random.default_rng(seed)
    eps_per_col = eps_imp / len(missing_cols)

    for col in missing_cols:
        col_spec = schema[col]
        missing_rows = np.where(out[col].isna())[0]
        n_missing = len(missing_rows)
        eps_per_query = eps_per_col / max(1, n_missing)

        if col_spec.kind == CATEGORICAL:
            declared = col_spec.categories or []
            observed = list(out[col].dropna().unique())
            candidates = sorted(list(set(str(c) for c in declared + observed)))
            if not candidates:
                candidates = [MISSING_CATEGORY_LABEL]

            noise_scale = 1.0 / eps_per_query
            accountant.charge(
                MechanismSpec(
                    name="laplace",
                    sensitivity=1.0,
                    noise_scale=noise_scale,
                    steps=n_missing,
                    metadata={"column": col, "mechanism": "dp_knn_report_noisy_max", "k": k_eff},
                ),
                run_id=f"impute_dp_knn_mode_{col}",
            )

            for r in missing_rows:
                neighbor_idx = indices[r, 1 : k_eff + 1]
                n_vals = out[col].iloc[neighbor_idx].dropna()
                counts = n_vals.value_counts()
                vec = np.array([float(counts.get(c, 0)) for c in candidates], dtype=float)
                c_seed = int(rng.integers(0, 2**31 - 1))
                noise = sample_discrete_laplace(scale=noise_scale, size=len(vec), seed=c_seed)
                chosen = candidates[int(np.argmax(vec + noise))]
                out.loc[r, col] = chosen

        else:
            lo = float(col_spec.lower if col_spec.lower is not None else 0.0)
            hi = float(col_spec.upper if col_spec.upper is not None else 1.0)
            width = hi - lo
            noise_scale = width / eps_per_query

            accountant.charge(
                MechanismSpec(
                    name="laplace",
                    sensitivity=width,
                    noise_scale=noise_scale,
                    steps=n_missing,
                    metadata={"column": col, "mechanism": "dp_knn_mean", "k": k_eff},
                ),
                run_id=f"impute_dp_knn_mean_{col}",
            )

            for r in missing_rows:
                neighbor_idx = indices[r, 1 : k_eff + 1]
                n_vals = out[col].iloc[neighbor_idx].dropna().to_numpy(dtype=float)
                c_seed = int(rng.integers(0, 2**31 - 1))
                noise_mean = float(
                    sample_discrete_laplace(scale=noise_scale, size=1, seed=c_seed)[0]
                )
                if len(n_vals) > 0:
                    val_num = float(np.clip((np.sum(n_vals) + noise_mean) / len(n_vals), lo, hi))
                else:
                    val_num = (lo + hi) / 2.0
                out.loc[r, col] = val_num

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
