"""Linkability — the third EDPB risk, and the only one this project did not measure.

WHERE THIS SITS. The EDPB's anonymisation criteria, and Anonymeter (Giomi et al., PoPETs 2023)
which operationalises them, treat three risks as distinct:

  1. **singling out** — can a record be isolated?          `attacks/exact_match_risk.py`
  2. **linkability**  — can two pieces of information be   **this module**
                        shown to concern the same person?
  3. **inference**    — can an attribute value be deduced?  `attacks/attribute_inference.py`

Two were already covered. Only linkability was missing, and the threat model implied all three.

WHY THIS IS NOT ANONYMETER, said plainly because standing rule 4 requires it. Anonymeter is a
published toolkit scored by its authors; this is our own approximation of the same concept.
Integrating the real thing was attempted on 2026-08-23 and is **not possible in this
environment**: `anonymeter` pins `numpy < 2`, while `jax`/`jaxlib` — and therefore `mbi`,
private-PGM and real AIM — require `numpy >= 2`. Installing it silently downgraded numpy and
broke AIM outright. Choosing between the reference toolkit and the project's flagship mechanism
is not a real choice, so this module exists instead and is named after what it is.

THE ATTACK. An adversary holds two disjoint sets of attributes about one person — say
`{age, education}` from one source and `{hours, occupation}` from another — and wants to know
whether they describe the same individual. If the release preserves record-level structure too
faithfully, each half independently points at the *same* synthetic row, and that agreement is
the link.

For every target record we find its nearest synthetic neighbour using set A alone, and again
using set B alone. **Linkability is the fraction where both halves agree on one synthetic
record.** A release that captured only marginals will send the two halves to unrelated rows.

THE CONTROL, and it is what makes the number readable. Agreement happens by chance, and how
often depends on the number of synthetic rows, not on privacy. So `baseline_rate` re-runs the
identical measurement against a release whose B-columns have been **independently shuffled** —
which destroys row-level correspondence while preserving every marginal exactly. The reported
`excess_over_baseline` is the difference. A raw agreement rate on its own is uninterpretable,
which is the same trap the subgroup-utility metric and the attribute-inference attack were both
built to avoid.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import List, Optional, Sequence

import numpy as np
import pandas as pd


@dataclass
class LinkabilityResult:
    """How often two disjoint halves of a record point at the same synthetic row."""

    num_targets: int
    num_synthetic: int
    columns_a: List[str]
    columns_b: List[str]
    linkability_rate: float  # fraction where both halves agree
    baseline_rate: float  # same measurement against a row-shuffled release -- the control
    excess_over_baseline: float  # THE number: agreement beyond what chance explains

    @property
    def is_informative(self) -> bool:
        """False when chance alone already explains most agreement.

        With few synthetic rows two halves collide often for reasons that have nothing to do
        with the release, and the excess is then measured against a large, noisy baseline.
        """
        return self.baseline_rate < 0.5 and self.num_synthetic >= 50

    def to_dict(self) -> dict:
        d = asdict(self)
        d["is_informative"] = self.is_informative
        return d


class LinkabilityEvaluator:
    """Splits the quasi-identifiers in two and asks whether the halves agree."""

    def __init__(
        self,
        seed: int = 42,
        max_records: Optional[int] = 400,
        columns_a: Optional[Sequence[str]] = None,
        columns_b: Optional[Sequence[str]] = None,
    ):
        self.seed = seed
        self.max_records = max_records
        self.columns_a = list(columns_a) if columns_a else None
        self.columns_b = list(columns_b) if columns_b else None

    @staticmethod
    def _encode(frames: Sequence[pd.DataFrame], cols: Sequence[str]) -> List[np.ndarray]:
        """Numeric matrices on a shared encoding, standardised so no column dominates.

        Categorical levels are mapped through the union of values across the frames, so a
        level present in only one of them does not shift the other's encoding.
        """
        out = [f[list(cols)].copy() for f in frames]
        for col in cols:
            if pd.api.types.is_numeric_dtype(out[0][col]):
                continue
            levels = pd.Index(sorted({str(v) for f in out for v in f[col].unique()}))
            for f in out:
                f[col] = levels.get_indexer(f[col].astype(str)).astype(float)  # type: ignore[arg-type]  # pandas-stubs: labels are Hashable, ours are always str

        mats = [f.to_numpy(dtype=float) for f in out]
        ref = mats[0]
        mu, sd = ref.mean(axis=0), ref.std(axis=0)
        sd = np.where(sd < 1e-9, 1.0, sd)
        return [(m - mu) / sd for m in mats]

    @staticmethod
    def _nearest(target: np.ndarray, pool: np.ndarray) -> np.ndarray:
        """Index of the closest pool row for each target row, by squared euclidean distance."""
        # (t, 1, d) - (1, p, d) would be clearer but allocates t*p*d floats; this is the same
        # ranking computed from norms, which is what `argmin` needs.
        d2 = (
            (target**2).sum(axis=1)[:, None]
            - 2.0 * target @ pool.T
            + (pool**2).sum(axis=1)[None, :]
        )
        return np.asarray(d2.argmin(axis=1))

    def _split_columns(self, df: pd.DataFrame) -> tuple[List[str], List[str]]:
        if self.columns_a and self.columns_b:
            overlap = set(self.columns_a) & set(self.columns_b)
            if overlap:
                raise ValueError(f"columns_a and columns_b must be disjoint; shared: {overlap}")
            return self.columns_a, self.columns_b

        # Deterministic split of the shared columns. Interleaved rather than halved so each
        # side gets a mix of column types rather than, say, every numeric column in A.
        cols = [c for c in df.columns]
        if len(cols) < 4:
            raise ValueError(
                f"linkability needs at least 4 shared columns to split in two, got {len(cols)}"
            )
        return cols[0::2], cols[1::2]

    def evaluate(self, synthetic_df: pd.DataFrame, target_df: pd.DataFrame) -> LinkabilityResult:
        """Measures agreement, then the same agreement against a row-shuffled release."""
        shared = [c for c in target_df.columns if c in synthetic_df.columns]
        if not shared:
            raise ValueError("release and target share no columns")
        cols_a, cols_b = self._split_columns(target_df[shared])

        rng = np.random.default_rng(self.seed)
        targets = target_df
        if self.max_records is not None and len(targets) > self.max_records:
            targets = targets.iloc[rng.choice(len(targets), size=self.max_records, replace=False)]

        def agreement(release: pd.DataFrame) -> float:
            ta, sa = self._encode([targets, release], cols_a)
            tb, sb = self._encode([targets, release], cols_b)
            return float((self._nearest(ta, sa) == self._nearest(tb, sb)).mean())

        rate = agreement(synthetic_df)

        # CONTROL: shuffle the B columns of the release independently. Every marginal is
        # preserved exactly and every row-level correspondence is destroyed, so whatever
        # agreement survives is what chance explains at this table size.
        shuffled = synthetic_df.copy()
        perm = rng.permutation(len(shuffled))
        for col in cols_b:
            shuffled[col] = shuffled[col].to_numpy()[perm]
        baseline = agreement(shuffled)

        return LinkabilityResult(
            num_targets=int(len(targets)),
            num_synthetic=int(len(synthetic_df)),
            columns_a=list(cols_a),
            columns_b=list(cols_b),
            linkability_rate=rate,
            baseline_rate=baseline,
            excess_over_baseline=float(rate - baseline),
        )
