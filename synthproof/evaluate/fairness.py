"""Per-subgroup downstream utility — the half of the subgroup story H2 does not measure.

WHY THIS EXISTS. H2 asks whether minority subgroups *leak* more. Its parent paper — Ganev,
Oprisanu & De Cristofaro, "Robin Hood and Matthew Effects", ICML 2022 — is about something
adjacent and better established: whether DP synthesis degrades downstream *accuracy* unevenly
across subgroups. The project measured the leakage half and none of the accuracy half, so the
subgroup story was missing the side the literature actually settled.

THE MISTAKE THIS MODULE IS BUILT TO AVOID, and it is the whole design. Reporting raw
per-subgroup TSTR would mostly measure **how hard the task is for that subgroup**, not what
synthesis did to it. A rare subgroup with an unusual label distribution scores badly on a model
trained on *real* data too. So every subgroup is scored against **its own TRTR baseline**, and
the reported quantity is the gap between them. That is the same reasoning
`attacks/attribute_inference.py` uses when it scores against a conditional rather than a
marginal baseline: subtract what was achievable anyway, report what the release changed.

TRTR per subgroup is therefore the built-in control. If TRTR varies as much across subgroups as
TSTR does, the variation belongs to the task and not to differential privacy, and this module
will show that rather than hide it.

WHAT IT DOES NOT DO. It reports no aggregate "fairness score". Collapsing a per-group table into
one number is how a metric stops being checkable, and the group sizes here differ by two orders
of magnitude — a mean over them is dominated by the majority group and says nothing about the
minority ones that motivated the question.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score
from sklearn.model_selection import train_test_split

# A group with fewer held-out rows than this cannot support a macro F1 anyone should read.
# It is reported anyway, flagged, because dropping it would silently remove exactly the rare
# groups the question is about.
MIN_RELIABLE_TEST_ROWS = 30


@dataclass
class SubgroupUtility:
    """Downstream utility for one subgroup, against its own real-data baseline."""

    subgroup: str
    population_share: float
    num_test_rows: int  # held-out REAL rows for this group -- the n behind every number below
    num_classes_present: int
    tstr_macro_f1: float  # model trained on the synthetic release
    trtr_macro_f1: float  # model trained on real data -- this group's own baseline
    utility_gap: float  # trtr - tstr. THE number: what synthesis cost this group

    @property
    def is_reliable(self) -> bool:
        """False when the group is too small, or degenerate, for the F1 to mean much."""
        return self.num_test_rows >= MIN_RELIABLE_TEST_ROWS and self.num_classes_present > 1

    def to_dict(self) -> dict:
        d = asdict(self)
        d["is_reliable"] = self.is_reliable
        return d


@dataclass
class SubgroupUtilityResult:
    """All subgroups from one release, plus the spread the question asks about."""

    attribute: str
    target_column: str
    subgroups: List[SubgroupUtility] = field(default_factory=list)

    @property
    def reliable(self) -> List[SubgroupUtility]:
        return [s for s in self.subgroups if s.is_reliable]

    @property
    def worst_served(self) -> Optional[SubgroupUtility]:
        """Largest utility gap -- the group synthesis cost the most."""
        return max(self.reliable, key=lambda s: s.utility_gap, default=None)

    @property
    def best_served(self) -> Optional[SubgroupUtility]:
        return min(self.reliable, key=lambda s: s.utility_gap, default=None)

    @property
    def gap_spread(self) -> Optional[float]:
        """worst gap - best gap, over reliable groups only.

        None when fewer than two groups are reliable, because a spread over one group is not
        a spread. Returning 0.0 there would read as "perfectly equal".
        """
        if len(self.reliable) < 2:
            return None
        return float(self.worst_served.utility_gap - self.best_served.utility_gap)

    @property
    def baseline_spread(self) -> Optional[float]:
        """The same spread measured on REAL data. The control.

        If this is comparable to `gap_spread`, the disparity belongs to the task rather than
        to synthesis, and no claim about DP should be made from it.
        """
        if len(self.reliable) < 2:
            return None
        f1s = [s.trtr_macro_f1 for s in self.reliable]
        return float(max(f1s) - min(f1s))

    def to_dict(self) -> dict:
        return {
            "attribute": self.attribute,
            "target_column": self.target_column,
            "subgroups": [s.to_dict() for s in self.subgroups],
            "gap_spread": self.gap_spread,
            "baseline_spread": self.baseline_spread,
            "num_reliable_subgroups": len(self.reliable),
            "num_subgroups": len(self.subgroups),
        }


class SubgroupUtilityEvaluator:
    """Scores TSTR and TRTR per subgroup on one shared held-out split of real data."""

    def __init__(
        self,
        target_col: str,
        subgroup_col: str,
        seed: int = 42,
        test_size: float = 0.2,
        n_estimators: int = 20,
    ):
        if not (0.0 < test_size < 1.0):
            raise ValueError(f"test_size must be in (0, 1), got {test_size}")
        self.target_col = target_col
        self.subgroup_col = subgroup_col
        self.seed = seed
        self.test_size = test_size
        self.n_estimators = n_estimators

    @staticmethod
    def _stratify(labels: pd.Series):
        """Stratify only when every class can appear on both sides of the split."""
        counts = labels.value_counts()
        return labels if len(counts) > 1 and counts.min() >= 2 else None

    def evaluate(
        self,
        real_df: pd.DataFrame,
        synthetic_df: pd.DataFrame,
        real_train_df: Optional[pd.DataFrame] = None,
    ) -> SubgroupUtilityResult:
        """Per-subgroup TSTR and TRTR macro F1, and the gap between them.

        `real_train_df` matters more than it looks. Without it the evaluator must carve a
        train split out of `real_df`, leaving only ~20% of the rows to score on — and a rare
        subgroup's share of 20% of a holdout is a handful of records. On UCI Adult that put
        `Amer-Indian-Eskimo` at **2 test rows**, an interval of [0.000, 0.667], and four of
        five race groups flagged unreliable. Passing the pipeline's own fit split as
        `real_train_df` lets TRTR train there and scores BOTH models on the ENTIRE holdout,
        which is ~5x the rows and costs nothing: the fit split is data the generator already
        saw, so no evaluation row is reused for training.

        No silent fallback: a missing target or subgroup column raises rather than returning a
        placeholder, for the reason recorded in `evaluate/utility.py` -- a hardcoded default
        makes a configuration error indistinguishable from a measurement.
        """
        for col, label in ((self.target_col, "target"), (self.subgroup_col, "subgroup")):
            if col not in real_df.columns:
                raise ValueError(
                    f"{label} column {col!r} not in real data (columns: {list(real_df.columns)})"
                )
        if self.target_col not in synthetic_df.columns:
            raise ValueError(f"target column {self.target_col!r} missing from the release")

        # Features are the numeric columns, excluding the target. The subgroup attribute is
        # categorical and is therefore NOT a feature -- it partitions the evaluation, it does
        # not inform the model.
        num_cols = [
            c
            for c in real_df.columns
            if pd.api.types.is_numeric_dtype(real_df[c]) and c != self.target_col
        ]
        if not num_cols:
            raise ValueError(
                f"no numeric feature columns (target={self.target_col!r}, "
                f"columns={list(real_df.columns)})"
            )
        missing = [c for c in num_cols if c not in synthetic_df.columns]
        if missing:
            raise ValueError(f"release is missing feature columns: {missing}")

        np.random.seed(self.seed)

        if real_train_df is not None:
            missing_tr = [c for c in num_cols + [self.target_col] if c not in real_train_df]
            if missing_tr:
                raise ValueError(f"real_train_df is missing columns: {missing_tr}")
            real_tr = real_train_df
            real_te = real_df
            idx_te = np.arange(len(real_df))
        else:
            # Carve a split out of `real_df`, carrying the subgroup labels with the rows.
            idx_tr, idx_te = train_test_split(
                np.arange(len(real_df)),
                test_size=self.test_size,
                random_state=self.seed,
                stratify=self._stratify(real_df[self.target_col]),
            )
            real_tr, real_te = real_df.iloc[idx_tr], real_df.iloc[idx_te]

        clf_trtr = RandomForestClassifier(n_estimators=self.n_estimators, random_state=self.seed)
        clf_trtr.fit(real_tr[num_cols], real_tr[self.target_col])

        clf_tstr = RandomForestClassifier(n_estimators=self.n_estimators, random_state=self.seed)
        clf_tstr.fit(synthetic_df[num_cols], synthetic_df[self.target_col])

        pred_trtr = clf_trtr.predict(real_te[num_cols])
        pred_tstr = clf_tstr.predict(real_te[num_cols])

        groups = real_df[self.subgroup_col].astype(str)
        te_groups = groups.iloc[idx_te].to_numpy()
        shares: Dict[str, float] = (groups.value_counts(normalize=True)).to_dict()

        out: List[SubgroupUtility] = []
        for name in sorted(shares):
            mask = te_groups == name
            n = int(mask.sum())
            if n == 0:
                # Present in the table, absent from the held-out split. Reported with n=0
                # rather than dropped, so the group does not vanish from the record.
                out.append(
                    SubgroupUtility(
                        subgroup=name,
                        population_share=float(shares[name]),
                        num_test_rows=0,
                        num_classes_present=0,
                        tstr_macro_f1=float("nan"),
                        trtr_macro_f1=float("nan"),
                        utility_gap=float("nan"),
                    )
                )
                continue

            y_true = real_te[self.target_col].to_numpy()[mask]
            tstr = float(f1_score(y_true, pred_tstr[mask], average="macro", zero_division=0))
            trtr = float(f1_score(y_true, pred_trtr[mask], average="macro", zero_division=0))
            out.append(
                SubgroupUtility(
                    subgroup=name,
                    population_share=float(shares[name]),
                    num_test_rows=n,
                    num_classes_present=int(len(np.unique(y_true))),
                    tstr_macro_f1=tstr,
                    trtr_macro_f1=trtr,
                    utility_gap=float(trtr - tstr),
                )
            )

        return SubgroupUtilityResult(
            attribute=self.subgroup_col, target_column=self.target_col, subgroups=out
        )
