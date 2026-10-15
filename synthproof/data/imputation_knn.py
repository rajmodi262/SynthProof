"""Cross-record k-nearest-neighbour imputation: the uncharged arm A4 and the budget-debited
heuristic A4_CHARGED."""

from typing import List

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors

from synthproof.accounting.accountant import Accountant
from synthproof.accounting.noise import grid_sensitivity, noisy_real_query, sample_discrete_laplace
from synthproof.accounting.types import MechanismSpec
from synthproof.data._imputation_common import MISSING_CATEGORY_LABEL, bounded_shifted_sum
from synthproof.data.schema import CATEGORICAL, NUMERICAL, Schema


def _prepare_distance_features(
    df: pd.DataFrame, schema: Schema, public_fill: bool = False
) -> np.ndarray:
    """Builds a standardized [0, 1] feature matrix for k-NN distance computation.

    Missing cells are filled before distances are taken. `public_fill=False` (arm A4) fills
    with the column's empirical mode/median, an uncharged read of the data. `public_fill=True`
    (arm A4_CHARGED) fills with the public schema midpoint / first declared category, so the
    charged arm reads no uncharged statistic.
    """
    coarse_df = df.copy()
    for col_spec in schema.columns:
        c = col_spec.name
        if c not in coarse_df.columns:
            continue
        if coarse_df[c].isna().sum() > 0:
            if public_fill:
                if col_spec.kind == CATEGORICAL:
                    fill = col_spec.categories[0] if col_spec.categories else "missing"
                else:
                    fill = (
                        (col_spec.lower + col_spec.upper) / 2.0
                        if col_spec.lower is not None and col_spec.upper is not None
                        else 0.0
                    )
                coarse_df[c] = coarse_df[c].fillna(fill)
            elif col_spec.kind == CATEGORICAL:
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
    """Arm A4_CHARGED: budget-debited cross-record k-nearest-neighbors imputation.

    Uses the same k-NN neighbor pooling as Arm A4, with Laplace noise debited to `Accountant`:
    - Categoricals: Report-Noisy-Max over the DECLARED categories from neighbor votes. Removing
      one record can drop its vote AND pull the (k+1)-th neighbour into the set, so a vote
      vector changes in two coordinates; Report-Noisy-Max then needs Laplace(2/eps), not 1/eps.
    - Numericals: Laplace perturbation of the neighbour sum (a swap moves it by at most width).
    - Distances use public fills (`public_fill=True`), never an uncharged mode/median.

    NOT A PROVEN DP MECHANISM, stated rather than implied. The per-query epsilon divides the
    column budget by the number of missing cells, which is itself a private count, so the noise
    scale is data-dependent. Read A4_CHARGED as a budget-debited heuristic comparator for A4,
    not as a formally private baseline.
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
    x_mat = _prepare_distance_features(df, schema, public_fill=True)
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
            candidates = [str(c) for c in (col_spec.categories or [])]
            if not candidates:
                out[col] = out[col].fillna(MISSING_CATEGORY_LABEL)
                continue

            # Two coordinates can move by one each (see the docstring): Laplace(2 / eps).
            noise_scale = 2.0 / eps_per_query
            accountant.charge(
                MechanismSpec(
                    name="laplace",
                    sensitivity=2.0,
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

            # Neighbour sums are real-valued: released on the integer grid, and shifted by the
            # public lower bound so each value contributes [0, width] -- the raw sum it used to
            # perturb has sensitivity max(|lo|, |hi|), not width (corrected 2026-10-16).
            accountant.charge(
                MechanismSpec(
                    name="laplace",
                    sensitivity=float(grid_sensitivity()),
                    noise_scale=(noise_scale / width) * grid_sensitivity(),
                    steps=n_missing,
                    metadata={"column": col, "mechanism": "dp_knn_mean", "k": k_eff},
                ),
                run_id=f"impute_dp_knn_mean_{col}",
            )

            for r in missing_rows:
                neighbor_idx = indices[r, 1 : k_eff + 1]
                n_vals = out[col].iloc[neighbor_idx].dropna().to_numpy(dtype=float)
                c_seed = int(rng.integers(0, 2**31 - 1))
                if len(n_vals) > 0:
                    noisy_sum = noisy_real_query(
                        bounded_shifted_sum(n_vals, lo, hi),
                        width,
                        noise_scale / width,
                        "laplace",
                        c_seed,
                    )
                    val_num = float(np.clip(lo + noisy_sum / len(n_vals), lo, hi))
                else:
                    val_num = (lo + hi) / 2.0
                out.loc[r, col] = val_num

    return out
