"""Whole-table structure metrics: every column pair, not one.

The grids' "structure error" was the mean absolute error of the correlation matrix over
`corr_cols` -- for most datasets a single pair (Adult age/hours, Texas stay/charges), so the
headline "0.103 vs 0.008" was one coefficient (audit M1, research/27). Two table-wide measures
replace it as the reported structure numbers; the old one is kept for continuity.

  * `association_error`: mean |A_real - A_synth| over the mixed association matrix of ALL
    columns (|Pearson| for numeric pairs, correlation ratio for numeric-categorical, bias-
    corrected Cramer's V for categorical pairs). Lower is better; 0 = same pairwise strengths.
  * `pairwise_tvd`: mean total-variation distance between the real and synthetic 2-way
    marginal of every column pair (numeric columns cut at the REAL data's deciles). It compares
    whole joint distributions, not just their strength, and is the standard 2-way fidelity score
    of the synthetic-data literature (e.g. SDMetrics' ContingencySimilarity = 1 - TVD). In [0, 1],
    lower is better.

Both read the real table, so -- like every utility number -- they are evaluation statistics,
outside epsilon, and labelled as such in the release.
"""

from typing import List, Optional

import numpy as np
import pandas as pd


def association_error(real: pd.DataFrame, synth: pd.DataFrame, cols: Optional[List[str]] = None) -> float:
    from synthproof.frontier.experiment import _association_matrix

    cols = list(cols or [c for c in real.columns if c in synth.columns])
    if len(cols) < 2:
        return float("nan")
    iu = np.triu_indices(len(cols), k=1)
    a = _association_matrix(real, cols)
    b = _association_matrix(synth, cols)
    return float(np.nanmean(np.abs(a[iu] - b[iu])))


def _discretise(real: pd.DataFrame, synth: pd.DataFrame, cols: List[str], bins: int):
    r, s = pd.DataFrame(index=real.index), pd.DataFrame(index=synth.index)
    for c in cols:
        if pd.api.types.is_numeric_dtype(real[c]):
            edges = np.unique(np.quantile(real[c].to_numpy(dtype=float), np.linspace(0, 1, bins + 1)))
            inner = edges[1:-1]
            r[c] = np.digitize(real[c].to_numpy(dtype=float), inner)
            s[c] = np.digitize(pd.to_numeric(synth[c], errors="coerce").to_numpy(dtype=float), inner)
        else:
            r[c] = real[c].astype(str)
            s[c] = synth[c].astype(str)
    return r, s


def pairwise_tvd(
    real: pd.DataFrame, synth: pd.DataFrame, cols: Optional[List[str]] = None, bins: int = 10
) -> float:
    cols = list(cols or [c for c in real.columns if c in synth.columns])
    if len(cols) < 2:
        return float("nan")
    r, s = _discretise(real, synth, cols, bins)
    out = []
    for i, a in enumerate(cols):
        for b in cols[i + 1 :]:
            pr = r.groupby([a, b]).size() / len(r)
            ps = s.groupby([a, b]).size() / max(len(s), 1)
            idx = pr.index.union(ps.index)
            out.append(0.5 * float(np.abs(pr.reindex(idx, fill_value=0) - ps.reindex(idx, fill_value=0)).sum()))
    return float(np.mean(out))
