"""An ALGORITHM-AWARE membership score for marginals-based generators.

WHAT THIS IS, AND WHAT IT IS NOT. This implements the ζ score from **Golob, Pentyala,
Maratkhan & De Cock, "Privacy Vulnerabilities in Marginals-based Synthetic Data", IEEE SaTML
2025 (arXiv:2410.05506)** — the attack the authors call MAMA-MIA. Their score is

    ζ(t) = Σ_{F ∈ ℱ}  w_F · P̂_synth(F(t)) / P̂_aux(F(t))

where ℱ is the set of *focal points* — the marginals the generator actually measured — and
w_F is how often each was selected. It is a DOMIAS-style density ratio, but evaluated on the
statistics the algorithm itself chose rather than on a generic density estimator. In the
authors' words it "incorporates the normalization idea from DOMIAS, but is tailored to which
marginals-based algorithm was used".

**It is deliberately NOT called MAMA-MIA in this codebase, and the class name says so.** This
project has already shipped a misnamed attack once — an earlier `distance_mia` carried the
label "LiRA" that it had not earned, together with a fabricated AUC — and the rule that came
out of that (audit finding F7) is that a name is a claim. Two things here differ from the paper:

  ORACLE FOCAL POINTS, NOT SHADOW-MODELLED ONES. MAMA-MIA recovers ℱ by replicating the
  generator "up to the statistics selection step" on ~50 random subsets of auxiliary data,
  because a real attacker cannot see which marginals were selected. An AUDITOR can: our
  generators record them (`edges_`, `measured_cliques_`). We read the true set. That is a
  STRONGER adversary than the paper's, not a weaker one, and it is the right choice for an
  audit — a lower bound on epsilon is only useful if the attack behind it is as strong as we
  can make it. But it is a different threat model, and every number produced here is an upper
  bound on what MAMA-MIA proper would achieve against the same release.

  NO SHADOW WEIGHTS WHERE SELECTION IS PUBLIC. For `pairwise`, `fixed_workload`,
  `independent` and `moments` the workload is fixed and data-independent, so w_F is uniform
  by construction and there is nothing to estimate. Only AIM selects adaptively, and there we
  weight by the order of selection rather than by shadow frequency.

WHY IT SHOULD BEAT THE NEAREST-NEIGHBOUR AUDITOR. The existing `CanaryAuditor` scores a
record by its distance to the closest synthetic row, which is algorithm-agnostic: it asks
"does this record look like the output?" This asks "did the statistics this generator
measured move in the direction this record would have moved them?" — which is where the
membership signal actually lives in a marginals-based mechanism.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

# Laplace-style smoothing on empirical cell frequencies. Without it a focal point the target
# happens not to occupy in the synthetic sample gives a zero numerator and a ratio of 0 for
# the whole record, which is an artefact of finite sampling rather than evidence of anything.
_SMOOTHING = 0.5

# Numeric columns have to be discretised before a marginal has cells at all. Ten quantile bins
# is what `pairwise` uses for its own conditionals, so the attack sees the same resolution the
# generator modelled at.
_DEFAULT_BINS = 10


@dataclass
class FocalPoints:
    """The marginals a fitted generator actually measured, with their weights."""

    cliques: List[Tuple[str, ...]] = field(default_factory=list)
    weights: List[float] = field(default_factory=list)
    source: str = "unknown"

    def normalised(self) -> List[float]:
        total = float(sum(self.weights)) or 1.0
        return [w / total for w in self.weights]


def focal_points_of(generator, columns: Sequence[str]) -> FocalPoints:
    """Reads the measured marginals off a fitted generator.

    This is the oracle step described in the module docstring: the auditor sees the true
    selection instead of estimating it. Each branch names where its answer comes from, so a
    reader can tell a public workload from an adaptive one.
    """
    cols = list(columns)

    # AIM: adaptively selected by the exponential mechanism, and the ONLY case where the
    # selection is data-dependent. Earlier selections are weighted more heavily: AIM spends
    # budget in order, and the first cliques are the ones it judged most informative.
    measured = getattr(generator, "measured_cliques_", None)
    if measured:
        cliques = [tuple(c) for c in measured]
        n = len(cliques)
        weights = [float(n - i) for i in range(n)]
        return FocalPoints(cliques, weights, source="adaptive selection (read from generator)")

    # Pairwise tree: the edges ARE the 2-way marginals, and the tree is public and fixed.
    edges = getattr(generator, "edges_", None)
    if edges:
        cliques = [tuple(e) for e in edges]
        root = getattr(generator, "root_", None)
        if root:
            cliques.append((root,))
        return FocalPoints(cliques, [1.0] * len(cliques), source="public spanning tree")

    # Independent / moments: one-way marginals only, which is the whole model class.
    return FocalPoints([(c,) for c in cols], [1.0] * len(cols), source="one-way marginals")


def _binner(reference: pd.DataFrame, col: str, bins: int) -> Optional[np.ndarray]:
    """Quantile bin edges for a numeric column, or None if it is categorical."""
    if not pd.api.types.is_numeric_dtype(reference[col]):
        return None
    qs = np.linspace(0.0, 1.0, bins + 1)
    edges = np.unique(np.nanquantile(reference[col].to_numpy(dtype=float), qs))
    return edges if edges.size >= 2 else None


def _cell_keys(df: pd.DataFrame, clique: Tuple[str, ...], edges: Dict[str, Optional[np.ndarray]]):
    """Maps each row to the cell of `clique` it falls in, as a hashable tuple."""
    parts = []
    for col in clique:
        if col not in df.columns:
            parts.append(np.zeros(len(df), dtype=object))
            continue
        e = edges.get(col)
        if e is None:
            parts.append(df[col].astype(str).to_numpy(dtype=object))
        else:
            idx = np.digitize(df[col].to_numpy(dtype=float), e[1:-1], right=False)
            parts.append(idx.astype(object))
    # strict=True: every part is built from the same frame, so a length mismatch
    # would mean a column silently produced fewer keys than there are rows.
    return list(zip(*parts, strict=True)) if parts else [() for _ in range(len(df))]


@dataclass
class MarginalRatioResult:
    """Per-target scores, plus what produced them."""

    scores: np.ndarray
    cliques: List[Tuple[str, ...]]
    focal_source: str
    n_focal: int


class MarginalRatioScorer:
    """The ζ score of Golob et al. (arXiv:2410.05506), with oracle focal points.

    Not named after the paper's attack on purpose — see the module docstring. What it shares
    with MAMA-MIA is the score; what it does not share is the threat model.
    """

    def __init__(self, bins: int = _DEFAULT_BINS, smoothing: float = _SMOOTHING):
        self.bins = bins
        self.smoothing = smoothing

    def score(
        self,
        targets: pd.DataFrame,
        synthetic: pd.DataFrame,
        auxiliary: pd.DataFrame,
        focal: FocalPoints,
    ) -> MarginalRatioResult:
        """ζ(t) for every row of `targets`. Higher means "more likely a member".

        `auxiliary` plays the role of D_aux in the paper: a sample from the same population
        that the target may or may not be in. It is what turns a raw density into a RATIO, so
        that a record which is simply common does not score highly merely for being common.
        """
        if len(targets) == 0:
            return MarginalRatioResult(np.zeros(0), focal.cliques, focal.source, 0)

        # Bin edges come from the AUXILIARY data, never from the synthetic output: using the
        # release to define the cells would let the generator's own noise choose where the
        # boundaries fall.
        edges: Dict[str, Optional[np.ndarray]] = {}
        for clique in focal.cliques:
            for col in clique:
                if col not in edges and col in auxiliary.columns:
                    edges[col] = _binner(auxiliary, col, self.bins)

        weights = focal.normalised()
        zeta = np.zeros(len(targets), dtype=float)

        for clique, w in zip(focal.cliques, weights, strict=True):
            if not all(c in auxiliary.columns for c in clique):
                continue

            t_keys = _cell_keys(targets, clique, edges)
            s_counts = pd.Series(_cell_keys(synthetic, clique, edges)).value_counts()
            a_counts = pd.Series(_cell_keys(auxiliary, clique, edges)).value_counts()

            n_cells = max(len(s_counts), len(a_counts), 1)
            s_total = len(synthetic) + self.smoothing * n_cells
            a_total = len(auxiliary) + self.smoothing * n_cells

            for i, key in enumerate(t_keys):
                p_s = (float(s_counts.get(key, 0)) + self.smoothing) / s_total
                p_a = (float(a_counts.get(key, 0)) + self.smoothing) / a_total
                zeta[i] += w * (p_s / p_a)

        return MarginalRatioResult(
            scores=zeta,
            cliques=list(focal.cliques),
            focal_source=focal.source,
            n_focal=len(focal.cliques),
        )
