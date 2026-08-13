"""Canary-based empirical privacy auditor.

Estimates an empirical *lower* bound on the privacy loss (``eps_audited``) of a
synthesis mechanism by planting canary records, measuring how well an adversary can
distinguish planted canaries from statistically identical held-out canaries, and
converting that advantage into an epsilon lower bound via Clopper-Pearson intervals.

Design notes (and honest limitations):

  * The baseline false-positive rate is **measured** from held-out canaries that were
    never planted. It is not a hardcoded constant. This is what makes the resulting
    epsilon a real quantity rather than an assertion.
  * Membership is decided by a continuous *similarity score* (nearest-neighbour in the
    synthetic table), not by exact value equality. Exact equality can never fire for
    continuous columns, which is why the previous version of this module returned
    eps_audited = 0.0 unconditionally.
  * This is a simplified, single-run audit in the spirit of Steinke, Nasr & Jagielski
    (2023). It is NOT their full construction: there is no randomised canary inclusion
    vector and no per-example independent randomness across many models. The bound it
    produces is therefore indicative, not a formally tight audit. Replacing this with
    the full construction is tracked as Tier 2 work in brutal_project_audit.md.
"""

from dataclasses import dataclass
from typing import Tuple

import numpy as np
import pandas as pd
from scipy import stats

from synthproof.data.dataset import TabularDataset

# Confidence level for the Clopper-Pearson interval used to derive the epsilon bound.
DEFAULT_CONFIDENCE = 0.95


@dataclass
class CanarySet:
    """Canaries generated for one audit run.

    Attributes:
        members: Canaries that WERE planted into the training data.
        holdout: Canaries drawn from the same distribution that were NOT planted.
            These measure the adversary's false-positive rate.
    """

    members: pd.DataFrame
    holdout: pd.DataFrame


@dataclass
class AuditResult:
    """Result of an empirical canary privacy audit."""

    audited_eps: float          # one-sided empirical lower bound on epsilon
    tpr: float                  # detection rate on planted canaries
    fpr: float                  # detection rate on held-out canaries
    tpr_lower: float            # Clopper-Pearson lower bound on TPR
    fpr_upper: float            # Clopper-Pearson upper bound on FPR
    num_members: int
    num_holdout: int
    p_value: float              # Fisher exact test, H0: TPR == FPR
    confidence: float


class CanaryAuditor:
    """Plants canary records and derives an empirical epsilon lower bound."""

    def __init__(self, num_canaries: int = 10, seed: int = 42,
                 confidence: float = DEFAULT_CONFIDENCE):
        if num_canaries < 1:
            raise ValueError(f"num_canaries must be >= 1, got {num_canaries}")
        if not (0.0 < confidence < 1.0):
            raise ValueError(f"confidence must be in (0, 1), got {confidence}")
        self.num_canaries = num_canaries
        self.seed = seed
        self.confidence = confidence

    # ------------------------------------------------------------------ planting

    def _make_canaries(self, dataset: TabularDataset, count: int,
                       rng: np.random.Generator) -> pd.DataFrame:
        """Builds `count` outlier canary rows from the dataset's observed ranges.

        Members and holdout canaries are drawn from the SAME distribution, which is what
        makes the held-out group a valid null for the false-positive rate.
        """
        rows = []
        for _ in range(count):
            row = {}
            for col in dataset.columns:
                if col in dataset.numerical_cols:
                    # Canaries must lie INSIDE the declared public domain. Placing them
                    # outside it was a real defect: the schema clips them away (so they can
                    # never be detected), and where clipping does not apply they drag the
                    # profiled range out to absurd bounds — a canary age of ~250 stretched
                    # UCI Adult's range to [17, 300] and compressed every real record into a
                    # handful of bins, destroying the structure the generator was measuring.
                    bounds = dataset.bounds(col) if dataset.schema is not None else None
                    if bounds is not None:
                        lo, hi = float(bounds[0]), float(bounds[1])
                    else:
                        lo, hi = float(dataset.df[col].min()), float(dataset.df[col].max())
                    span = max(1e-9, hi - lo)
                    # Extreme but in-domain: the top few percent of the range, randomised so
                    # members and holdout canaries remain exchangeable.
                    row[col] = hi - span * float(rng.uniform(0.0, 0.03))
                else:
                    observed = list(dataset.df[col].unique())
                    row[col] = observed[int(rng.integers(0, len(observed)))] if observed else "NA"
            rows.append(row)
        return pd.DataFrame(rows)

    def plant_canaries(self, dataset: TabularDataset) -> Tuple[TabularDataset, CanarySet]:
        """Plants `num_canaries` canaries and reserves an equal number as a held-out null.

        Returns:
            (augmented_dataset, canary_set) where only `canary_set.members` were added
            to the returned dataset.
        """
        rng = np.random.default_rng(self.seed)
        all_canaries = self._make_canaries(dataset, self.num_canaries * 2, rng)
        members = all_canaries.iloc[: self.num_canaries].reset_index(drop=True)
        holdout = all_canaries.iloc[self.num_canaries:].reset_index(drop=True)

        augmented_df = pd.concat([dataset.df, members], ignore_index=True)
        # Carry the schema through. Dropping it here silently disabled public bounds for the
        # whole downstream pipeline, pushing the profiler onto its noisy-min/max fallback.
        augmented = TabularDataset(df=augmented_df, name=f"{dataset.name}_canary",
                                   schema=dataset.schema)
        return augmented, CanarySet(members=members, holdout=holdout)

    # ------------------------------------------------------------------ scoring

    def _similarity_scores(self, canary_df: pd.DataFrame,
                           synthetic_df: pd.DataFrame) -> np.ndarray:
        """Scores each canary by its similarity to the nearest synthetic record.

        Higher score = the canary looks more like something the generator emitted, i.e.
        stronger evidence that it was in the training data.
        """
        if len(synthetic_df) == 0 or len(canary_df) == 0:
            return np.zeros(len(canary_df))

        shared = [c for c in canary_df.columns if c in synthetic_df.columns]
        num_cols = [c for c in shared if pd.api.types.is_numeric_dtype(synthetic_df[c])]
        cat_cols = [c for c in shared if c not in num_cols]

        scores = np.zeros(len(canary_df))

        if num_cols:
            synth_num = synthetic_df[num_cols].to_numpy(dtype=float)
            # Scale by the synthetic spread so columns contribute comparably.
            scale = np.nanstd(synth_num, axis=0)
            scale[~np.isfinite(scale) | (scale == 0)] = 1.0
            canary_num = canary_df[num_cols].to_numpy(dtype=float)
            for i in range(len(canary_df)):
                d = (synth_num - canary_num[i]) / scale
                min_dist = float(np.min(np.sqrt(np.nansum(d ** 2, axis=1))))
                scores[i] += 1.0 / (1.0 + min_dist)

        if cat_cols:
            for i in range(len(canary_df)):
                hits = sum(
                    1 for c in cat_cols
                    if canary_df.iloc[i][c] in set(synthetic_df[c].unique())
                )
                scores[i] += hits / len(cat_cols)

        return scores

    # ------------------------------------------------------------------ auditing

    @staticmethod
    def _clopper_pearson(successes: int, trials: int, confidence: float) -> Tuple[float, float]:
        """Exact (Clopper-Pearson) binomial confidence interval for a proportion."""
        if trials == 0:
            return 0.0, 1.0
        alpha = 1.0 - confidence
        lower = 0.0 if successes == 0 else float(
            stats.beta.ppf(alpha / 2.0, successes, trials - successes + 1)
        )
        upper = 1.0 if successes == trials else float(
            stats.beta.ppf(1.0 - alpha / 2.0, successes + 1, trials - successes)
        )
        return lower, upper

    def audit(self, synthetic_df: pd.DataFrame, canary_set: CanarySet) -> AuditResult:
        """Derives an empirical epsilon lower bound from member vs holdout separation.

        The adversary scores every canary and guesses the `num_members` highest-scoring
        ones as members. TPR and FPR follow from how many guesses were correct. The
        epsilon bound is log(TPR_lower / FPR_upper), using opposite ends of the
        Clopper-Pearson intervals so the result stays a conservative lower bound.
        """
        members, holdout = canary_set.members, canary_set.holdout
        n_mem, n_out = len(members), len(holdout)
        if n_mem == 0:
            raise ValueError("Cannot audit with zero member canaries.")

        member_scores = self._similarity_scores(members, synthetic_df)
        holdout_scores = self._similarity_scores(holdout, synthetic_df)

        # Adversary guesses the n_mem highest-scoring canaries as members.
        pooled = np.concatenate([member_scores, holdout_scores])
        is_member = np.concatenate([np.ones(n_mem, bool), np.zeros(n_out, bool)])
        guessed = np.zeros(len(pooled), bool)
        guessed[np.argsort(-pooled, kind="stable")[:n_mem]] = True

        tp = int(np.sum(guessed & is_member))
        fp = int(np.sum(guessed & ~is_member))
        fn = n_mem - tp
        tn = n_out - fp

        tpr = tp / n_mem
        fpr = fp / n_out if n_out > 0 else 0.0

        tpr_lower, _ = self._clopper_pearson(tp, n_mem, self.confidence)
        if n_out > 0:
            _, fpr_upper = self._clopper_pearson(fp, n_out, self.confidence)
        else:
            fpr_upper = 1.0

        # eps >= log(TPR_lo / FPR_hi). fpr_upper is strictly positive for any finite
        # sample under Clopper-Pearson, so this never divides by zero.
        if tpr_lower > 0.0 and fpr_upper > 0.0 and tpr_lower > fpr_upper:
            audited_eps = float(np.log(tpr_lower / fpr_upper))
        else:
            audited_eps = 0.0

        if n_out > 0:
            _, p_value = stats.fisher_exact([[tp, fn], [fp, tn]], alternative="greater")
        else:
            p_value = 1.0

        return AuditResult(
            audited_eps=max(0.0, audited_eps),
            tpr=tpr,
            fpr=fpr,
            tpr_lower=tpr_lower,
            fpr_upper=fpr_upper,
            num_members=n_mem,
            num_holdout=n_out,
            p_value=float(p_value),
            confidence=self.confidence,
        )
