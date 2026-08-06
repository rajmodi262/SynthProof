"""Downstream ML Utility Evaluator (TSTR / TRTR, marginal fidelity).

TSTR and TRTR are both scored on the SAME held-out split of the real data, so the
utility gap reflects synthesis quality rather than a comparison between a held-out
score and an in-sample one.
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score
from sklearn.model_selection import train_test_split


@dataclass
class UtilityResult:
    """Downstream utility evaluation vector.

    Note: a `fairness_drift` field was removed. It was computed as
    ``abs(tstr_f1 - trtr_f1) * 0.1`` — i.e. utility_gap/10 — which is not a fairness
    metric. Real subgroup fairness analysis (and hypothesis H2, which depends on it)
    is tracked as Tier 3 work in brutal_project_audit.md.
    """
    tstr_macro_f1: float
    trtr_macro_f1: float
    utility_gap: float
    marginal_distance: float


class UtilityEvaluator:
    """Evaluates ML utility (TSTR vs TRTR) and statistical fidelity."""

    def __init__(self, target_col: str = "category", seed: int = 42,
                 test_size: float = 0.2):
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

    def evaluate(self, real_df: pd.DataFrame, synthetic_df: pd.DataFrame) -> UtilityResult:
        """Computes TSTR vs TRTR macro F1 on a shared held-out split, plus marginal distance."""
        np.random.seed(self.seed)

        # Numerical columns excluding target
        num_cols = [
            c for c in real_df.columns
            if pd.api.types.is_numeric_dtype(real_df[c]) and c != self.target_col
        ]

        # No silent fallback. A previous version returned hardcoded values
        # (0.75 / 0.80 / 0.05 / 0.02) whenever the schema did not match, which made a
        # configuration error indistinguishable from a real measurement.
        if self.target_col not in real_df.columns:
            raise ValueError(
                f"Target column {self.target_col!r} not found in real data "
                f"(columns: {list(real_df.columns)})"
            )
        if not num_cols:
            raise ValueError(
                f"No numeric feature columns available for evaluation "
                f"(target={self.target_col!r}, columns={list(real_df.columns)})"
            )

        # Hold out real data ONCE; both models are scored on the same unseen split.
        # The previous version called clf_trtr.predict(X_real) on its own training data,
        # reporting in-sample accuracy (a constant 0.971) as the TRTR baseline.
        X_real_tr, X_real_te, y_real_tr, y_real_te = train_test_split(
            real_df[num_cols], real_df[self.target_col],
            test_size=self.test_size, random_state=self.seed,
            stratify=self._stratify_labels(real_df[self.target_col]),
        )

        # TRTR: train on real, test on held-out real
        clf_trtr = RandomForestClassifier(n_estimators=20, random_state=self.seed)
        clf_trtr.fit(X_real_tr, y_real_tr)
        trtr_f1 = float(f1_score(y_real_te, clf_trtr.predict(X_real_te), average="macro"))

        # TSTR: train on synthetic, test on the SAME held-out real split
        X_synth = synthetic_df[num_cols]
        y_synth = synthetic_df[self.target_col]
        clf_tstr = RandomForestClassifier(n_estimators=20, random_state=self.seed)
        clf_tstr.fit(X_synth, y_synth)
        tstr_f1 = float(f1_score(y_real_te, clf_tstr.predict(X_real_te), average="macro"))

        # Standardised mean shift per column, averaged. NOTE: this is not the Wasserstein
        # distance the module docstring used to claim — it only compares first moments.
        # Replacing it with a true Wasserstein-1 distance is Tier 2 work.
        distances = []
        for col in num_cols:
            mean_diff = abs(real_df[col].mean() - synthetic_df[col].mean())
            std_real = real_df[col].std() if len(real_df) > 1 else 1.0
            distances.append(mean_diff / (std_real + 1e-5))
        marginal_dist = float(np.mean(distances))

        return UtilityResult(
            tstr_macro_f1=tstr_f1,
            trtr_macro_f1=trtr_f1,
            utility_gap=float(max(0.0, trtr_f1 - tstr_f1)),
            marginal_distance=marginal_dist,
        )
