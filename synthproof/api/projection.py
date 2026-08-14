"""Projects real and synthetic tables into a shared 3D frame for the live console.

The console's hero visual is a point cloud of actual records, not decoration. For that to
mean anything, the real cloud, the synthetic cloud and the planted canaries must all be
projected through the SAME transform — otherwise "the canary dissolves into the crowd" is a
rendering artefact rather than a property of the mechanism.

The transform is fitted on the REAL table and then applied unchanged to everything else.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

# Points streamed per cloud. Enough to read as a distribution, small enough for a
# 60fps draw call and a payload that fits comfortably in one SSE frame.
MAX_POINTS = 700


@dataclass
class CloudProjection:
    """A fitted 3D projection plus the clouds pushed through it."""

    axes: List[str] = field(default_factory=list)
    real: List[List[float]] = field(default_factory=list)
    synthetic: List[List[float]] = field(default_factory=list)
    canaries: List[List[float]] = field(default_factory=list)
    explained_variance: List[float] = field(default_factory=list)
    method: str = "columns"


def _numeric_frame(df: pd.DataFrame, cols: Sequence[str]) -> np.ndarray:
    return df[list(cols)].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)


def _subsample(arr: np.ndarray, rng: np.random.Generator, cap: int = MAX_POINTS) -> np.ndarray:
    if len(arr) <= cap:
        return arr
    return arr[rng.choice(len(arr), size=cap, replace=False)]


def project(
    real_df: pd.DataFrame,
    synthetic_df: pd.DataFrame,
    numeric_cols: Sequence[str],
    canary_df: Optional[pd.DataFrame] = None,
    seed: int = 0,
) -> CloudProjection:
    """Fits a 3D frame on `real_df` and pushes every cloud through it.

    With three or more numeric columns the frame is the first three principal components of
    the standardised real data, which keeps the most structure visible. With fewer, the raw
    columns are used and the missing axes are zero-padded — an honest flat plane rather than
    an invented third dimension.
    """
    cols = [c for c in numeric_cols if c in real_df.columns and c in synthetic_df.columns]
    rng = np.random.default_rng(seed)

    if not cols:
        return CloudProjection(method="unavailable")

    real = _numeric_frame(real_df, cols)
    synth = _numeric_frame(synthetic_df, cols)
    canary = (_numeric_frame(canary_df, cols)
              if canary_df is not None and len(canary_df) else np.empty((0, len(cols))))

    # Standardise on the REAL table's moments. Using each cloud's own moments would
    # re-centre the synthetic data and hide exactly the distributional shift we want to show.
    mu = np.nanmean(real, axis=0)
    sd = np.nanstd(real, axis=0)
    sd[~np.isfinite(sd) | (sd == 0)] = 1.0

    def standardise(a: np.ndarray) -> np.ndarray:
        return np.nan_to_num((a - mu) / sd, nan=0.0, posinf=0.0, neginf=0.0)

    real_s, synth_s, canary_s = standardise(real), standardise(synth), standardise(canary)

    if len(cols) >= 3:
        # PCA via SVD on the real cloud; the same basis is reused for every other cloud.
        _, s, vt = np.linalg.svd(real_s - real_s.mean(axis=0), full_matrices=False)
        basis = vt[:3].T
        var = (s ** 2) / max(1.0, (len(real_s) - 1))
        explained = (var[:3] / var.sum()).tolist() if var.sum() > 0 else [0.0, 0.0, 0.0]
        method = "pca"
        to3 = lambda a: a @ basis  # noqa: E731
    else:
        basis_cols = len(cols)
        explained = [1.0 / basis_cols] * basis_cols
        method = "columns"

        def to3(a: np.ndarray) -> np.ndarray:
            out = np.zeros((len(a), 3))
            out[:, :basis_cols] = a[:, :basis_cols]
            return out

    real_3, synth_3, canary_3 = to3(real_s), to3(synth_s), to3(canary_s)

    # Scale so the real cloud fills a unit-ish box. Robust percentile rather than max, so a
    # single outlier cannot collapse the whole distribution toward the origin.
    span = np.percentile(np.abs(real_3), 98) if len(real_3) else 1.0
    span = float(span) if np.isfinite(span) and span > 0 else 1.0

    def pack(a: np.ndarray) -> List[List[float]]:
        if not len(a):
            return []
        clipped = np.clip(a / span, -2.5, 2.5)
        return [[round(float(v), 4) for v in row] for row in clipped]

    return CloudProjection(
        axes=list(cols[:3]) if method == "columns" else ["PC1", "PC2", "PC3"],
        real=pack(_subsample(real_3, rng)),
        synthetic=pack(_subsample(synth_3, rng)),
        canaries=pack(canary_3),
        explained_variance=[round(float(v), 4) for v in explained],
        method=method,
    )


def marginal_histograms(real_df: pd.DataFrame, synthetic_df: pd.DataFrame,
                        cols: Sequence[str], bins: int = 24) -> Dict[str, dict]:
    """Per-column real-vs-synthetic histograms on a shared binning.

    Shared edges matter: comparing two histograms binned independently is meaningless, and
    it is a common way for a fidelity chart to flatter a generator.
    """
    out: Dict[str, dict] = {}
    for col in cols:
        if col not in real_df.columns or col not in synthetic_df.columns:
            continue
        r = pd.to_numeric(real_df[col], errors="coerce").dropna().to_numpy(dtype=float)
        s = pd.to_numeric(synthetic_df[col], errors="coerce").dropna().to_numpy(dtype=float)
        if not len(r):
            continue
        lo, hi = float(np.min(r)), float(np.max(r))
        if hi <= lo:
            hi = lo + 1.0
        edges = np.linspace(lo, hi, bins + 1)
        r_h, _ = np.histogram(r, bins=edges)
        s_h, _ = np.histogram(s, bins=edges)
        out[col] = {
            "edges": [round(float(e), 4) for e in edges],
            "real": (r_h / max(1, r_h.sum())).round(5).tolist(),
            "synthetic": (s_h / max(1, s_h.sum())).round(5).tolist(),
        }
    return out
