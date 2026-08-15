"""Attribute inference, measured against the baseline that makes it meaningful.

THE MISTAKE THIS MODULE EXISTS TO AVOID. An attribute-inference attack predicts a sensitive
column from the others. It is tempting to report its accuracy as "leakage". It is not.
Jayaraman & Evans (CCS 2022, "Are Attribute Inference Attacks Just Imputation?") showed that a
naive attacker who ignores the release entirely and simply predicts the most common value
*outperformed three published state-of-the-art attacks*. An attack that beats chance is
measuring how **predictable** the attribute is, not how much the release **leaked**.

So the only defensible quantity is the difference:

    leakage = attack_success - imputation_baseline

where the baseline attacker sees the same auxiliary columns but NOT the synthetic release.
Both are computed here and both are reported. If the difference is zero, that is the result:
no individual-level leakage beyond what population statistics already gave away.

TWO BASELINES, because they answer different questions:

  * **Marginal.** Always predict the training set's most frequent value. The floor.
  * **Conditional.** Fit a model on a *reference* sample of real data the mechanism never saw,
    using the same auxiliary columns. This is the strong baseline — it captures everything an
    attacker could learn about the population without the release, so beating it is the only
    evidence of individual-level leakage.

Annamalai, Ganev & De Cristofaro (USENIX Security 2024) construct a game separating these for
synthetic data specifically; this module implements the comparison, not their full game.
"""

from dataclasses import dataclass
from typing import List, Optional, Sequence

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score


@dataclass
class AttributeInferenceResult:
    """Attack accuracy alongside the baselines that make it interpretable."""

    target_column: str
    attack_accuracy: float          # trained on the synthetic release
    marginal_baseline: float        # most-frequent-value, ignores the release
    conditional_baseline: float     # trained on real reference data, ignores the release
    leakage_vs_marginal: float
    leakage_vs_conditional: float   # THE number: evidence of individual-level leakage
    attack_macro_f1: float
    num_targets: int
    num_classes: int
    majority_class_share: float

    @property
    def leaks(self) -> bool:
        """Whether the release gave the attacker anything the population did not."""
        return self.leakage_vs_conditional > 0.0

    def interpretation(self) -> str:
        if self.leakage_vs_conditional <= 0.0:
            return (
                f"No individual-level leakage detected for {self.target_column!r}. The attack "
                f"reached {self.attack_accuracy:.3f}, against {self.conditional_baseline:.3f} "
                "for an attacker who never saw the release — so the release supplied nothing "
                "beyond population statistics. Reporting the raw attack accuracy alone would "
                "have described the attribute's predictability, not the mechanism's leakage."
            )
        return (
            f"Leakage of {self.leakage_vs_conditional:+.3f} accuracy for "
            f"{self.target_column!r}: the attack reached {self.attack_accuracy:.3f} where an "
            f"attacker without the release reached {self.conditional_baseline:.3f}. The "
            "release carried individual-level information beyond the population distribution."
        )


class AttributeInferenceAttack:
    """Predicts a sensitive column, and measures what the release actually contributed."""

    def __init__(self, target_column: str, seed: int = 42,
                 max_records: Optional[int] = None, n_estimators: int = 50):
        self.target_column = target_column
        self.seed = seed
        self.max_records = max_records
        self.n_estimators = n_estimators

    # ------------------------------------------------------------------ encoding

    @staticmethod
    def _shared_features(frames: Sequence[pd.DataFrame], target: str) -> List[str]:
        cols = set(frames[0].columns)
        for f in frames[1:]:
            cols &= set(f.columns)
        return [c for c in frames[0].columns if c in cols and c != target]

    def _encode(self, frames: Sequence[pd.DataFrame], features: List[str]):
        """One-hot on the UNION of every frame's categories.

        Encoding each frame separately would give them different column spaces, and a model
        trained on one could not be applied to another — the failure would surface as a shape
        error or, worse, as silently misaligned columns.
        """
        combined = pd.concat([f[features] for f in frames], keys=range(len(frames)))
        encoded = pd.get_dummies(combined, drop_first=False)
        return [encoded.xs(i, level=0) for i in range(len(frames))]

    def _fit_predict(self, X_train, y_train, X_test) -> np.ndarray:
        clf = RandomForestClassifier(n_estimators=self.n_estimators,
                                     random_state=self.seed, n_jobs=1)
        clf.fit(X_train, y_train)
        return clf.predict(X_test)

    # ------------------------------------------------------------------ attack

    def evaluate(self, synthetic_df: pd.DataFrame, target_df: pd.DataFrame,
                 reference_df: pd.DataFrame) -> AttributeInferenceResult:
        """Runs the attack and both baselines on the same targets.

        Args:
            synthetic_df: The release. The attacker trains on this.
            target_df: Records whose sensitive attribute is to be inferred (the victims).
            reference_df: Real records the mechanism never saw. Used ONLY for the conditional
                baseline — an attacker's population knowledge, obtained without the release.
        """
        t = self.target_column
        for name, df in (("synthetic", synthetic_df), ("target", target_df),
                         ("reference", reference_df)):
            if t not in df.columns:
                raise ValueError(f"Target column {t!r} missing from the {name} frame.")

        if self.max_records is not None:
            target_df = target_df.head(self.max_records)

        features = self._shared_features([synthetic_df, target_df, reference_df], t)
        if not features:
            raise ValueError("No shared auxiliary columns to infer from.")

        X_syn, X_tgt, X_ref = self._encode(
            [synthetic_df, target_df, reference_df], features)
        y_syn = synthetic_df[t].to_numpy()
        y_tgt = target_df[t].to_numpy()
        y_ref = reference_df[t].to_numpy()

        # 1. The attack: train on the release, predict the victims' sensitive attribute.
        pred_attack = self._fit_predict(X_syn, y_syn, X_tgt)
        attack_acc = float(accuracy_score(y_tgt, pred_attack))

        # 2. Marginal baseline: the release is ignored entirely.
        majority = pd.Series(y_ref).value_counts().idxmax()
        marginal_acc = float(accuracy_score(y_tgt, np.full(len(y_tgt), majority)))

        # 3. Conditional baseline: everything an attacker could learn about the POPULATION
        #    without ever seeing the release. Beating this is the only real evidence.
        pred_cond = self._fit_predict(X_ref, y_ref, X_tgt)
        cond_acc = float(accuracy_score(y_tgt, pred_cond))

        counts = pd.Series(y_ref).value_counts(normalize=True)
        return AttributeInferenceResult(
            target_column=t,
            attack_accuracy=attack_acc,
            marginal_baseline=marginal_acc,
            conditional_baseline=cond_acc,
            leakage_vs_marginal=attack_acc - marginal_acc,
            leakage_vs_conditional=attack_acc - cond_acc,
            attack_macro_f1=float(f1_score(y_tgt, pred_attack, average="macro",
                                           zero_division=0)),
            num_targets=len(y_tgt),
            num_classes=int(pd.Series(y_ref).nunique()),
            majority_class_share=float(counts.iloc[0]) if len(counts) else 0.0,
        )
