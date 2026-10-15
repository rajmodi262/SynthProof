"""Structure metrics: which numeric columns carry information, and how far a release's
pairwise associations are from the real table's."""

from typing import List, Sequence

import numpy as np
import pandas as pd

# A column that is overwhelmingly one value carries almost no correlation signal, and its
# sample correlation is dominated by the handful of non-modal rows. Including such columns
# makes the structure metric measure noise. UCI Adult's capital_gain (91.6% zeros) and
# capital_loss (95.5% zeros) are exactly this case.
MAX_MODAL_SHARE = 0.85


def informative_numeric_columns(
    df, cols: Sequence[str], max_modal_share: float = MAX_MODAL_SHARE
) -> List[str]:
    """Numeric columns with enough spread for a correlation to mean anything."""
    keep = []
    for c in cols:
        s = df[c]
        if s.std() > 0 and (s.value_counts(normalize=True).iloc[0] <= max_modal_share):
            keep.append(c)
    return keep


def _cramers_v(x, y) -> float:
    """Bias-corrected Cramér's V association between two categorical series, in [0, 1]."""
    from scipy.stats import chi2_contingency

    tab = pd.crosstab(x, y)
    if tab.shape[0] < 2 or tab.shape[1] < 2:
        return 0.0
    chi2 = chi2_contingency(tab, correction=False)[0]
    n = tab.to_numpy().sum()
    if n == 0:
        return 0.0
    phi2 = chi2 / n
    r, k = tab.shape
    phi2c = max(0.0, phi2 - (k - 1) * (r - 1) / (n - 1))
    rc = r - (r - 1) ** 2 / (n - 1)
    kc = k - (k - 1) ** 2 / (n - 1)
    denom = min(kc - 1, rc - 1)
    return float(np.sqrt(phi2c / denom)) if denom > 0 else 0.0


def _correlation_ratio(categories, values) -> float:
    """Correlation ratio (eta) between a categorical and a numeric series, in [0, 1]."""
    cats = pd.Series(categories).astype(str)
    vals = pd.to_numeric(pd.Series(values), errors="coerce")
    mask = vals.notna()
    cats, vals = cats[mask], vals[mask]
    if len(vals) < 2:
        return 0.0
    grand = vals.mean()
    # Both series were masked by the same rows, so grouping by `cats` aligns on the index.
    ss_between = float(sum((len(g) * (g.mean() - grand) ** 2 for _, g in vals.groupby(cats)), 0.0))
    ss_total = float(((vals - grand) ** 2).sum())
    return float(np.sqrt(ss_between / ss_total)) if ss_total > 0 else 0.0


def _association_matrix(df, cols: List[str]) -> np.ndarray:
    """Symmetric pairwise association matrix over mixed-type columns, each entry in [0, 1].

    num-num uses |Pearson|, num-cat/cat-num uses the correlation ratio (eta), and cat-cat
    uses bias-corrected Cramér's V. This generalises the Pearson correlation matrix so an
    all-categorical or mixed table gets a structure score at all.
    """
    is_num = {c: pd.api.types.is_numeric_dtype(df[c]) for c in cols}
    n = len(cols)
    m = np.eye(n)
    for i in range(n):
        for j in range(i + 1, n):
            ci, cj = cols[i], cols[j]
            if is_num[ci] and is_num[cj]:
                v = abs(float(df[[ci, cj]].corr().iloc[0, 1]))
            elif is_num[ci] and not is_num[cj]:
                v = _correlation_ratio(df[cj], df[ci])
            elif not is_num[ci] and is_num[cj]:
                v = _correlation_ratio(df[ci], df[cj])
            else:
                v = _cramers_v(df[ci], df[cj])
            m[i, j] = m[j, i] = 0.0 if v != v else v
    return m


def _mean_abs_corr_error(real, synth, cols: List[str]) -> float:
    """Mean absolute error over the pairwise association matrix — a structure metric.

    Independent-marginal mechanisms score badly here by construction; a model that captures
    pairwise dependence should score better. This is the quantity that separates the families.

    When every column is numeric this is exactly the mean absolute error of the Pearson
    correlation matrix (the original metric, unchanged, so committed numeric results are
    preserved). When any column is categorical it falls back to a mixed association matrix
    (|Pearson| / correlation-ratio / Cramér's V) so categorical and mixed tables score too.
    """
    if len(cols) < 2:
        return float("nan")
    all_numeric = all(pd.api.types.is_numeric_dtype(real[c]) for c in cols)
    iu = np.triu_indices(len(cols), k=1)
    if all_numeric:
        a = real[cols].corr().to_numpy()
        b = synth[cols].corr().to_numpy()
        diff = np.abs(a[iu] - b[iu])
        return float(np.nanmean(diff)) if diff.size else float("nan")
    a = _association_matrix(real, cols)
    b = _association_matrix(synth, cols)
    diff = np.abs(a[iu] - b[iu])
    return float(np.nanmean(diff)) if diff.size else float("nan")
