"""Nearest-neighbour distance membership inference baseline.

This is a WEAK baseline attack, not LiRA. It scores a record by its proximity to the
nearest synthetic record and tests whether training records score higher than held-out
records.

It is explicitly NOT the Likelihood Ratio Attack of Carlini et al. (2022), which
requires training many shadow models, fitting Gaussians to the per-example IN and OUT
score distributions, and running a calibrated likelihood-ratio test. An earlier version
of this module was named `LiRAAttack` and reported a fabricated AUC
(``auc = accuracy + 0.05``). Both the name and the metric have been corrected.

Implementing real LiRA and DOMIAS is tracked as Tier 2 work in brutal_project_audit.md.
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, roc_curve


@dataclass
class MIAResult:
    """Membership inference outcome. All fields are computed, none are assumed."""

    auc: float                  # threshold-free discrimination (0.5 == no signal)
    advantage: float            # max_t (TPR(t) - FPR(t)); the standard MIA advantage
    attack_accuracy: float      # balanced accuracy at the optimal threshold
    tpr_at_1pct_fpr: float      # low-FPR regime, the metric that actually matters
    num_train: int
    num_test: int


class DistanceMIABaseline:
    """Membership inference by nearest-neighbour distance to the synthetic table."""

    def __init__(self, seed: int = 42, max_records: Optional[int] = None):
        """
        Args:
            seed: RNG seed for reproducibility.
            max_records: Optional cap on records scored per split. ``None`` scores all
                of them. (The previous implementation silently used only the first 50
                rows, which made the result depend on row ordering.)
        """
        self.seed = seed
        self.max_records = max_records

    def _scores(self, df: pd.DataFrame, synthetic_df: pd.DataFrame,
                num_cols: list) -> np.ndarray:
        """Similarity to the nearest synthetic record; higher == more likely a member."""
        if not num_cols or len(synthetic_df) == 0 or len(df) == 0:
            return np.zeros(len(df))

        synth = synthetic_df[num_cols].to_numpy(dtype=float)
        scale = np.nanstd(synth, axis=0)
        scale[~np.isfinite(scale) | (scale == 0)] = 1.0

        target = df[num_cols].to_numpy(dtype=float)
        out = np.zeros(len(df))
        for i in range(len(df)):
            d = (synth - target[i]) / scale
            out[i] = 1.0 / (1.0 + float(np.min(np.sqrt(np.nansum(d ** 2, axis=1)))))
        return out

    def evaluate(self, synthetic_df: pd.DataFrame, train_df: pd.DataFrame,
                 test_df: pd.DataFrame) -> MIAResult:
        """Scores train (members) vs test (non-members) and reports real metrics."""
        if self.max_records is not None:
            train_df = train_df.head(self.max_records)
            test_df = test_df.head(self.max_records)

        num_cols = [
            c for c in train_df.columns
            if c in synthetic_df.columns and pd.api.types.is_numeric_dtype(synthetic_df[c])
        ]

        train_scores = self._scores(train_df, synthetic_df, num_cols)
        test_scores = self._scores(test_df, synthetic_df, num_cols)

        labels = np.concatenate([np.ones(len(train_scores)), np.zeros(len(test_scores))])
        scores = np.concatenate([train_scores, test_scores])

        if len(np.unique(labels)) < 2:
            raise ValueError("MIA needs both member and non-member records.")

        auc = float(roc_auc_score(labels, scores))
        fpr, tpr, _ = roc_curve(labels, scores)
        advantage = float(np.max(tpr - fpr))
        tpr_at_1pct = float(np.interp(0.01, fpr, tpr))

        return MIAResult(
            auc=auc,
            advantage=advantage,
            # Balanced accuracy at the optimal operating point. The previous version
            # thresholded at the median of the pooled scores, which mechanically forces
            # ~50% positive predictions and pinned accuracy at 0.48 in every experiment.
            attack_accuracy=float(0.5 * (1.0 + advantage)),
            tpr_at_1pct_fpr=tpr_at_1pct,
            num_train=len(train_scores),
            num_test=len(test_scores),
        )
