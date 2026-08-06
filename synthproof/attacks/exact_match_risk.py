"""Exact-match singling-out risk.

Measures the fraction of target records that appear in the synthetic table as a unique
exact match — i.e. records the release "singles out".

This is NOT the Anonymeter library. An earlier version of this module was named
`AnonymeterEvaluator` and additionally reported ``linkability`` and ``inference`` risks
computed as affine functions of the singling-out score
(``linkability = singling_out * 0.8 + 0.05``). Those were fabricated and have been
removed rather than left in place with a disclaimer.

Real singling-out, linkability, and inference evaluations require the three separate
attack simulations implemented by the `anonymeter` package; wiring that in is tracked
as Tier 2 work in brutal_project_audit.md.
"""

from dataclasses import dataclass
from typing import Optional

import pandas as pd


@dataclass
class SinglingOutResult:
    """Exact-match singling-out risk. One measured field, no derived stand-ins."""

    singling_out_risk: float    # fraction of scored target records uniquely matched
    num_scored: int
    num_unique_matches: int


class ExactMatchRiskEvaluator:
    """Counts target records reproduced as a unique exact row in the synthetic table."""

    def __init__(self, seed: int = 42, max_records: Optional[int] = None):
        self.seed = seed
        self.max_records = max_records

    def evaluate(self, synthetic_df: pd.DataFrame,
                 target_df: pd.DataFrame) -> SinglingOutResult:
        """Evaluates exact-match singling-out risk.

        Note: for continuous columns an exact match is essentially impossible, so this
        metric floors at 0.0 on any table with float features. That is a real property
        of the metric, not a bug — but it means singling-out risk carries no signal for
        numeric data and should not be read as evidence of privacy.
        """
        scored = target_df if self.max_records is None else target_df.head(self.max_records)
        shared = [c for c in scored.columns if c in synthetic_df.columns]

        unique_matches = 0
        for _, row in scored.iterrows():
            exact = (synthetic_df[shared] == row[shared]).all(axis=1)
            if int(exact.sum()) == 1:
                unique_matches += 1

        n = max(1, len(scored))
        return SinglingOutResult(
            singling_out_risk=float(unique_matches / n),
            num_scored=len(scored),
            num_unique_matches=unique_matches,
        )
