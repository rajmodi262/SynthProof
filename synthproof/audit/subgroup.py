"""Per-subgroup privacy auditing — the instrument for hypothesis H2.

H2: under uniform budget allocation, records belonging to minority demographic subgroups leak
more than majority ones at fixed target epsilon. The intuition is that a DP mechanism spends
its budget on the distribution as a whole, so a rare subgroup is fitted from fewer effective
observations and its members sit further from the mass the model reproduces.

THE MEASUREMENT PROBLEM THIS FACES, stated up front because it dominates the result. A
per-subgroup audit gets a FRACTION of the canaries, and the audit ceiling
(``log(r / ln(1/alpha))``, see audit/steinke.py) falls with the guess count. Splitting m
canaries across k subgroups leaves each with ~m/k guesses and a correspondingly lower ceiling.
On UCI Adult, `race` has five levels of which the smallest is well under 1% of rows, so an
even split is not achievable and the rare subgroups — exactly the ones H2 is about — get the
weakest instrument.

Two consequences, both handled explicitly rather than hidden:

  * Canaries are planted **stratified by subgroup** at a caller-chosen allocation, so a rare
    subgroup can be given more canaries than its population share would suggest. This is
    deliberate oversampling of the group of interest, not a bug, and it is recorded.
  * Every per-subgroup result reports its own ceiling. Comparing an epsilon of 0 in a
    subgroup with 8 canaries against 0 in one with 300 is meaningless, and the ceiling is
    what makes that visible.

A null result here is a real possibility and would be reportable. It would say the instrument
cannot resolve subgroup differences at this scale, not that no difference exists.
"""

from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

from synthproof.audit.steinke import (
    SteinkeAuditor,
    epsilon_lower_bound,
    max_provable_epsilon,
)
from synthproof.data.dataset import TabularDataset

DEFAULT_ALPHA = 0.05


@dataclass
class SubgroupAudit:
    """Audit outcome for one subgroup."""

    subgroup: str
    population_share: float     # fraction of the real table in this subgroup
    num_canaries: int
    num_included: int
    guesses: int
    correct: int
    accuracy: float
    audited_eps: float
    ceiling: float              # most this subgroup's canary count could ever certify
    p_value: float
    saturated: bool

    @property
    def is_minority(self) -> bool:
        return self.population_share < 0.5


@dataclass
class SubgroupAuditResult:
    """All subgroups from one release, plus the comparison H2 asks for."""

    attribute: str
    subgroups: List[SubgroupAudit] = field(default_factory=list)
    alpha: float = DEFAULT_ALPHA
    total_canaries: int = 0

    def by_share(self) -> List[SubgroupAudit]:
        return sorted(self.subgroups, key=lambda s: s.population_share)

    @property
    def rarest(self) -> Optional[SubgroupAudit]:
        return self.by_share()[0] if self.subgroups else None

    @property
    def most_common(self) -> Optional[SubgroupAudit]:
        return self.by_share()[-1] if self.subgroups else None

    def leakage_gap(self) -> Optional[float]:
        """Audited epsilon of the rarest subgroup minus that of the most common.

        Positive supports H2. Returns None when either side is unmeasurable.
        """
        r, c = self.rarest, self.most_common
        if r is None or c is None or r is c:
            return None
        return r.audited_eps - c.audited_eps

    def interpretation(self) -> str:
        """Whether this result can speak to H2 at all, before what it says."""
        measurable = [s for s in self.subgroups if s.audited_eps > 0.0]
        if not measurable:
            ceilings = [s.ceiling for s in self.subgroups]
            return (
                f"UNMEASURABLE at this scale. No subgroup produced a positive bound; the "
                f"per-subgroup ceilings run {min(ceilings):.2f}-{max(ceilings):.2f}, so this "
                "says the instrument cannot resolve subgroup differences here, not that none "
                "exist."
            )
        gap = self.leakage_gap()
        if gap is None:
            return "Only one subgroup was measurable; no comparison is possible."
        direction = "MORE" if gap > 0 else "LESS"
        return (
            f"The rarest subgroup ({self.rarest.subgroup}, "
            f"{self.rarest.population_share:.1%} of rows) audited at "
            f"eps={self.rarest.audited_eps:.3f} against {self.most_common.audited_eps:.3f} "
            f"for the most common — {direction} leakage, gap {gap:+.3f}. Ceilings were "
            f"{self.rarest.ceiling:.2f} and {self.most_common.ceiling:.2f} respectively."
        )

    def to_dict(self) -> dict:
        return {
            "attribute": self.attribute,
            "alpha": self.alpha,
            "total_canaries": self.total_canaries,
            "leakage_gap": self.leakage_gap(),
            "interpretation": self.interpretation(),
            "subgroups": [asdict(s) for s in self.subgroups],
        }


class SubgroupCanaryAuditor:
    """Plants canaries stratified by a sensitive attribute and audits each group separately."""

    def __init__(self, attribute: str, num_canaries: int = 300, seed: int = 42,
                 alpha: float = DEFAULT_ALPHA, min_per_group: int = 20,
                 balanced: bool = True):
        """
        Args:
            attribute: Categorical column defining the subgroups (e.g. "race", "sex").
            num_canaries: Total canaries across all subgroups.
            min_per_group: Groups that cannot be given at least this many canaries are
                excluded and reported, rather than audited with a ceiling so low the result
                would be noise.
            balanced: Allocate canaries EQUALLY across subgroups rather than proportionally.
                Equal allocation deliberately oversamples rare groups so each gets a
                comparable ceiling — without it the rare groups H2 is about would get the
                weakest instrument, which is precisely backwards.
        """
        if num_canaries < 2:
            raise ValueError(f"num_canaries must be >= 2, got {num_canaries}")
        self.attribute = attribute
        self.num_canaries = num_canaries
        self.seed = seed
        self.alpha = alpha
        self.min_per_group = min_per_group
        self.balanced = balanced

    # ------------------------------------------------------------------ allocation

    def allocate(self, dataset: TabularDataset) -> Dict[str, int]:
        """Splits the canary budget across subgroups, dropping any that would be too small."""
        if self.attribute not in dataset.df.columns:
            raise KeyError(
                f"Attribute {self.attribute!r} not in the table. Available categorical "
                f"columns: {dataset.categorical_cols}"
            )
        shares = dataset.df[self.attribute].value_counts(normalize=True)
        levels = list(shares.index)

        if self.balanced:
            per = self.num_canaries // max(1, len(levels))
            alloc = {lv: per for lv in levels}
        else:
            alloc = {lv: int(round(self.num_canaries * shares[lv])) for lv in levels}

        return {lv: n for lv, n in alloc.items() if n >= self.min_per_group}

    # ------------------------------------------------------------------ audit

    def audit_release(
        self,
        dataset: TabularDataset,
        synthetic_df: pd.DataFrame,
        canary_sets: Dict[str, object],
    ) -> SubgroupAuditResult:
        """Audits each subgroup's canaries against the same released table."""
        shares = dataset.df[self.attribute].value_counts(normalize=True)
        result = SubgroupAuditResult(attribute=self.attribute, alpha=self.alpha)

        for level, cset in canary_sets.items():
            maker = SteinkeAuditor(num_canaries=len(cset.canaries), seed=self.seed,
                                   alpha=self.alpha)
            scores = maker._maker._similarity_scores(cset.canaries, synthetic_df)
            included = cset.included
            m = len(scores)

            order = np.argsort(-scores, kind="stable")
            k_high = m // 2
            guessed_in, guessed_out = order[:k_high], order[k_high:]
            correct = int(included[guessed_in].sum() + (~included[guessed_out]).sum())

            eps = epsilon_lower_bound(correct, m, alpha=self.alpha)
            ceiling = max_provable_epsilon(m, self.alpha)

            from scipy import stats
            result.subgroups.append(SubgroupAudit(
                subgroup=str(level),
                population_share=float(shares.get(level, 0.0)),
                num_canaries=m,
                num_included=int(included.sum()),
                guesses=m,
                correct=correct,
                accuracy=correct / max(1, m),
                audited_eps=eps,
                ceiling=ceiling,
                p_value=float(stats.binom.sf(correct - 1, m, 0.5)),
                saturated=eps > 0.0 and eps >= ceiling - 1e-6,
            ))

        result.total_canaries = sum(s.num_canaries for s in result.subgroups)
        return result

    def plant_stratified(self, dataset: TabularDataset):
        """Plants canaries per subgroup, each with its own randomised inclusion vector.

        Returns (augmented_dataset, {level: OneRunCanarySet}). A canary for a subgroup takes
        that subgroup's value for the sensitive attribute, so it is a member of that group by
        construction; every other field is drawn the same way as a standard canary.
        """
        alloc = self.allocate(dataset)
        if not alloc:
            raise ValueError(
                f"No subgroup of {self.attribute!r} could be given {self.min_per_group} "
                "canaries. Raise num_canaries or lower min_per_group."
            )

        rng = np.random.default_rng(self.seed)
        frames, sets = [dataset.df], {}

        for i, (level, count) in enumerate(sorted(alloc.items())):
            maker = SteinkeAuditor(num_canaries=count, seed=self.seed + i * 1000,
                                   alpha=self.alpha)
            canaries = maker._maker._make_canaries(dataset, count, rng)
            # Force group membership. Without this a "subgroup canary" would only belong to
            # its group by chance, and the per-group audit would be measuring nothing.
            canaries[self.attribute] = level

            included = rng.random(count) < 0.5
            if included.all():
                included[int(rng.integers(0, count))] = False
            if not included.any():
                included[int(rng.integers(0, count))] = True

            frames.append(canaries.loc[included].reset_index(drop=True))

            from synthproof.audit.steinke import OneRunCanarySet
            sets[level] = OneRunCanarySet(canaries=canaries, included=included)

        augmented = TabularDataset(
            df=pd.concat(frames, ignore_index=True),
            name=f"{dataset.name}_subgroup_canary",
            schema=dataset.schema,
        )
        return augmented, sets


def summarise(results: Sequence[SubgroupAuditResult]) -> str:
    """Renders one or more subgroup audits as a table for a terminal or a thesis figure."""
    lines = []
    for res in results:
        lines.append(f"\nattribute: {res.attribute}   (total canaries {res.total_canaries})")
        lines.append(f"{'subgroup':<22}{'share':>8}{'m':>6}{'acc':>7}{'eps':>8}{'ceiling':>9}{'p':>8}")
        for s in res.by_share():
            lines.append(
                f"{s.subgroup:<22}{s.population_share:>8.3f}{s.num_canaries:>6}"
                f"{s.accuracy:>7.3f}{s.audited_eps:>8.3f}{s.ceiling:>9.3f}{s.p_value:>8.3f}"
            )
        lines.append(f"  -> {res.interpretation()}")
    return "\n".join(lines)
