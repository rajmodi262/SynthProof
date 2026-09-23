"""Downstream ML Utility Evaluator (TSTR / TRTR, marginal fidelity).

TSTR and TRTR are both scored on the SAME held-out split of the real data, so the
utility gap reflects synthesis quality rather than a comparison between a held-out
score and an in-sample one.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder


@dataclass
class UtilityResult:
    """Downstream utility evaluation vector.

    Note: a `fairness_drift` field was removed. It was computed as
    ``abs(tstr_f1 - trtr_f1) * 0.1`` — i.e. utility_gap/10 — which is not a fairness
    metric. Real subgroup analysis lives in `audit/subgroup.py`, and H2 has been run on
    both UCI Adult and ACSIncome — see results/H2_RESULTS.md and results/acs/H2_RESULTS.md.
    The null replicates on both.
    """

    tstr_macro_f1: float
    trtr_macro_f1: float
    utility_gap: float
    # Mean per-column Wasserstein-1 distance, each standardised by the real column's SD.
    # 0 means the marginals match; it is scale-free, so it is comparable across columns
    # and across datasets.
    marginal_distance: float


class UtilityEvaluator:
    """Evaluates ML utility (TSTR vs TRTR) and statistical fidelity."""

    def __init__(self, target_col: str = "category", seed: int = 42, test_size: float = 0.2):
        if not (0.0 < test_size < 1.0):
            raise ValueError(f"test_size must be in (0, 1), got {test_size}")
        self.target_col = target_col
        self.seed = seed
        self.test_size = test_size

    @staticmethod
    def _stratify_labels(y: pd.Series) -> Optional[pd.Series]:
        """Stratifies the split only when every class has at least two members."""
        counts = y.value_counts()
        return y if len(counts) > 1 and int(counts.min()) >= 2 else None

    def _feature_columns(self, df: pd.DataFrame) -> Tuple[List[str], List[str]]:
        """Split feature columns into numeric and categorical (target excluded)."""
        num_cols, cat_cols = [], []
        for c in df.columns:
            if c == self.target_col:
                continue
            (num_cols if pd.api.types.is_numeric_dtype(df[c]) else cat_cols).append(c)
        return num_cols, cat_cols

    def evaluate(self, real_df: pd.DataFrame, synthetic_df: pd.DataFrame) -> UtilityResult:
        """Computes TSTR vs TRTR macro F1 on a shared held-out split, plus marginal distance.

        Features can be numeric, categorical, or a mix. Categorical features are one-hot
        encoded against a vocabulary built from BOTH real and synthetic values, so the
        TRTR model, the TSTR model, and the held-out test set all live in the same feature
        space. This is what lets an all-categorical table (e.g. Mushroom, Nursery) be
        evaluated at all -- the previous version used numeric columns only and raised on a
        table that had none.
        """
        np.random.seed(self.seed)

        num_cols, cat_cols = self._feature_columns(real_df)

        # No silent fallback. A previous version returned hardcoded values
        # (0.75 / 0.80 / 0.05 / 0.02) whenever the schema did not match, which made a
        # configuration error indistinguishable from a real measurement.
        if self.target_col not in real_df.columns:
            raise ValueError(
                f"Target column {self.target_col!r} not found in real data "
                f"(columns: {list(real_df.columns)})"
            )
        if not num_cols and not cat_cols:
            raise ValueError(
                f"No feature columns available for evaluation "
                f"(target={self.target_col!r}, columns={list(real_df.columns)})"
            )

        # A single encoder fit on real+synth categories, so a category that appears in only
        # one of them still gets a stable column. `handle_unknown="ignore"` keeps a stray
        # test-time category from raising -- it maps to an all-zero block, which is the honest
        # "no signal" outcome rather than a crash.
        encoder: Optional[OneHotEncoder] = None
        if cat_cols:
            encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
            vocab = pd.concat(
                [real_df[cat_cols].astype(str), synthetic_df[cat_cols].astype(str)],
                ignore_index=True,
            )
            encoder.fit(vocab)

        def encode(df: pd.DataFrame) -> np.ndarray:
            blocks = []
            if num_cols:
                blocks.append(df[num_cols].to_numpy(dtype=float))
            if cat_cols and encoder is not None:
                blocks.append(encoder.transform(df[cat_cols].astype(str)))
            return np.hstack(blocks) if len(blocks) > 1 else blocks[0]

        # Hold out real data ONCE; both models are scored on the same unseen split.
        # The previous version called clf_trtr.predict(X_real) on its own training data,
        # reporting in-sample accuracy (a constant 0.971) as the TRTR baseline. Splitting on
        # the row index keeps numeric and categorical features aligned per row.
        idx = np.arange(len(real_df))
        tr_idx, te_idx = train_test_split(
            idx,
            test_size=self.test_size,
            random_state=self.seed,
            stratify=self._stratify_labels(real_df[self.target_col]),
        )
        real_tr, real_te = real_df.iloc[tr_idx], real_df.iloc[te_idx]
        y_real_tr = real_df[self.target_col].iloc[tr_idx]
        y_real_te = real_df[self.target_col].iloc[te_idx]

        X_real_tr, X_real_te = encode(real_tr), encode(real_te)

        # TRTR: train on real, test on held-out real
        clf_trtr = RandomForestClassifier(n_estimators=20, random_state=self.seed)
        clf_trtr.fit(X_real_tr, y_real_tr)
        trtr_f1 = float(f1_score(y_real_te, clf_trtr.predict(X_real_te), average="macro"))

        # TSTR: train on synthetic, test on the SAME held-out real split
        X_synth = encode(synthetic_df)
        y_synth = synthetic_df[self.target_col]
        clf_tstr = RandomForestClassifier(n_estimators=20, random_state=self.seed)
        clf_tstr.fit(X_synth, y_synth)
        tstr_f1 = float(f1_score(y_real_te, clf_tstr.predict(X_real_te), average="macro"))

        # Marginal distance per feature column, averaged. Numeric columns use Wasserstein-1
        # standardised by the real column's spread (scale-free, comparable across columns).
        # Categorical columns use Total-Variation distance = 1/2 * sum |p_real - p_synth|,
        # which is in [0, 1] and 0 iff the category frequencies match.
        #
        # W1 REPLACED a standardised mean shift, which compared first moments only. That
        # proxy scores zero on a release whose mean is right and whose entire shape is wrong.
        distances = []
        for col in num_cols:
            real_col = real_df[col].to_numpy(dtype=float)
            synth_col = synthetic_df[col].to_numpy(dtype=float)
            scale = float(np.std(real_col)) if len(real_col) > 1 else 1.0
            distances.append(
                float(stats.wasserstein_distance(real_col, synth_col)) / (scale + 1e-9)
            )
        for col in cat_cols:
            pr = real_df[col].astype(str).value_counts(normalize=True)
            ps = synthetic_df[col].astype(str).value_counts(normalize=True)
            cats = pr.index.union(ps.index)
            tvd = 0.5 * float(
                np.abs(pr.reindex(cats, fill_value=0.0) - ps.reindex(cats, fill_value=0.0)).sum()
            )
            distances.append(tvd)
        marginal_dist = float(np.mean(distances)) if distances else float("nan")

        return UtilityResult(
            tstr_macro_f1=tstr_f1,
            trtr_macro_f1=trtr_f1,
            utility_gap=float(max(0.0, trtr_f1 - tstr_f1)),
            marginal_distance=marginal_dist,
        )
