"""MST-style marginal mechanism backed by private-PGM.

Implements the structure of MST (McKenna, Miklau & Sheldon, the NIST 2018 differential-privacy
synthetic-data challenge winner; "Winning the NIST Contest", JPC 2021):

  1. Measure every 1-way marginal under the Gaussian mechanism.
  2. Choose a MAXIMUM SPANNING TREE over the columns: d-1 rounds of privately selecting the
     best-scoring 2-way marginal whose edge does NOT close a cycle (Kruskal's constraint),
     then measuring it.
  3. Fit ONE graphical model to all measurements and sample from it.

The one structural difference from AIM (`generators/aim.py`) is where this file earns its
place in the grid: AIM re-fits its model every round and selects adaptively against the current
fit, with no constraint on the graph. MST fixes the model class to a tree — it scores edges
against a model built once from the 1-way measurements, and constrains selection so the measured
edges form a spanning tree. Same mechanism family (select-measure-generate over private-PGM), a
different, lower-treewidth model class. Inference is the real thing (`mbi`).

BUDGET, as in the paper: one zCDP budget rho for the whole release (so none of it goes unspent
-- audit H1, research/27), split into thirds -- 1-way measurements, exponential-mechanism edge
selection, 2-way measurements. Selection is the exponential mechanism with utility sensitivity 1
under add/remove-one, charged through its (eps^2/8)-zCDP bound (Cesar & Rogers 2021); it used to
be report-noisy-max charged as a Laplace mechanism with the replace-one sensitivity 2 (audit L1).

Requires Python >= 3.11 (a private-PGM constraint). `mbi` is imported lazily via the same helper
AIM uses; constructing this class without `mbi` raises with an actionable message.
"""

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from synthproof.accounting.accountant import Accountant
from synthproof.accounting.noise import (
    em_noise_scale,
    exponential_mechanism,
    sample_discrete_gaussian,
)
from synthproof.accounting.types import MechanismSpec
from synthproof.data.dataset import TabularDataset
from synthproof.data.profiler import DomainProfile
from synthproof.generators._marginal import (
    MarginalEncoder,
    em_eps_for_rho,
    rho_for,
    sample_model,
    sigma_for_rho,
)
from synthproof.generators.aim import (  # reuse AIM's exact mbi loader + defaults
    DEFAULT_BINS,
    DEFAULT_MAX_MODEL_MB,
    _require_mbi,
)
from synthproof.generators.base import BaseGenerator


class _UnionFind:
    """Disjoint-set over column indices, so selection can enforce Kruskal's no-cycle rule."""

    def __init__(self, n: int):
        self._parent = list(range(n))

    def find(self, x: int) -> int:
        while self._parent[x] != x:
            self._parent[x] = self._parent[self._parent[x]]
            x = self._parent[x]
        return x

    def union(self, a: int, b: int) -> bool:
        """Joins the sets of a and b. Returns False if they were already joined (a cycle)."""
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        self._parent[ra] = rb
        return True


class MSTGenerator(BaseGenerator):
    """Maximum-spanning-tree marginal selection with graphical-model inference."""

    def __init__(
        self,
        seed: int = 42,
        num_bins: int = DEFAULT_BINS,
        selection_frac: float = 1.0 / 3.0,
        max_model_mb: float = DEFAULT_MAX_MODEL_MB,
    ):
        super().__init__(seed=seed)
        if not (0.0 < selection_frac < 1.0):
            raise ValueError(f"selection_frac must be in (0, 1), got {selection_frac}")
        if max_model_mb <= 0:
            raise ValueError(f"max_model_mb must be positive, got {max_model_mb}")
        self.num_bins = num_bins
        self.selection_frac = selection_frac
        self.max_model_mb = max_model_mb
        self.skipped_cliques_: List[Tuple[str, ...]] = []
        self.levels_: Dict[str, list] = {}
        self.bin_edges_: Dict[str, np.ndarray] = {}
        self.measured_cliques_: List[Tuple[str, ...]] = []
        self._encoder: Optional[MarginalEncoder] = None
        self._model = None

    # ------------------------------------------------------------------ encoding
    # Shared with AIM (generators/_marginal.py), so the two stay comparable in the grid.

    def _build_levels(self, dataset: TabularDataset, profile: DomainProfile) -> None:
        self._encoder = MarginalEncoder(self.num_bins)
        self._encoder.build(dataset, profile)
        self.levels_ = self._encoder.levels_
        self.bin_edges_ = self._encoder.bin_edges_

    def _encode(self, dataset: TabularDataset) -> pd.DataFrame:
        return self._encoder.encode(dataset)

    # ------------------------------------------------------------------ fitting

    def fit(
        self,
        dataset: TabularDataset,
        profile: DomainProfile,
        accountant: Accountant,
        target_eps: float,
    ) -> None:
        Domain, Dataset, LinearMeasurement, estimation, hypothetical_model_size = _require_mbi()
        rng = np.random.default_rng(self.seed)

        self.columns = dataset.columns
        self.numerical_cols = dataset.numerical_cols
        self.categorical_cols = dataset.categorical_cols
        self._build_levels(dataset, profile)
        # Fresh per fit: a second fit() used to append to the previous run's cliques.
        self.measured_cliques_ = []
        self.skipped_cliques_ = []

        coded = self._encode(dataset)
        domain = Domain(tuple(self.columns), self._encoder.shape())
        data = Dataset(coded, domain)
        d = len(self.columns)

        col_index = {c: i for i, c in enumerate(self.columns)}
        candidates = [(a, b) for i, a in enumerate(self.columns) for b in self.columns[i + 1 :]]
        # A spanning tree over d nodes has exactly d-1 edges; that is the selection round count.
        rounds = min(max(d - 1, 0), len(candidates))

        # ---- one zCDP budget, split in thirds as in the paper (selection share configurable).
        rho = rho_for(target_eps, accountant.budget.delta) * (1.0 - 1e-9)
        f = self.selection_frac if rounds else 0.0
        rho_1way = (1.0 - f) * rho / (2.0 if rounds else 1.0) / d
        rho_2way = (1.0 - f) * rho / 2.0 / rounds if rounds else 0.0
        rho_sel = f * rho / rounds if rounds else 0.0

        def measure(clique, rho_m, run_id):
            sigma = sigma_for_rho(rho_m)
            accountant.charge(
                MechanismSpec("gaussian", sensitivity=1.0, noise_scale=sigma, steps=1),
                run_id=run_id,
            )
            y = np.asarray(data.project(clique).datavector(), dtype=float)
            noise = sample_discrete_gaussian(
                sigma=sigma, size=y.size, seed=int(rng.integers(0, 2**31 - 1))
            )
            self.measured_cliques_.append(tuple(clique))
            return LinearMeasurement(y + noise, tuple(clique), stddev=sigma)

        measurements = [measure((col,), rho_1way, f"mst_1way_{col}") for col in self.columns]

        # ---- one model from the 1-way measurements. MST scores edges against THIS fixed model
        # (Kruskal on estimated weights), rather than re-fitting each round as AIM does. The
        # model total is private-pgm's estimate from the noisy measurements, never the exact n.
        base_model = None
        if rounds:
            base_model = estimation.MirrorDescent().estimate(
                domain, measurements, known_total=None, iters=150
            )

        # ---- Kruskal with private edge selection: d-1 exponential-mechanism rounds over the
        # cycle-free candidate subset.
        uf = _UnionFind(d)
        remaining = list(candidates)
        eps_sel = em_eps_for_rho(rho_sel) if rounds else 0.0
        for r in range(rounds):
            affordable = []
            for cl in remaining:
                a, b = col_index[cl[0]], col_index[cl[1]]
                if uf.find(a) == uf.find(b):
                    continue  # would close a cycle; not eligible this round
                size_mb = hypothetical_model_size(domain, [*self.measured_cliques_, cl])
                if size_mb <= self.max_model_mb:
                    affordable.append(cl)
                elif cl not in self.skipped_cliques_:
                    self.skipped_cliques_.append(cl)

            if not affordable:
                # The forest cannot be extended (disconnected by the size bound, or complete).
                break

            # Score: how badly the fixed 1-way model predicts the pair. Under add/remove-one a
            # record moves one cell of the true marginal by one, so the L1 score has
            # sensitivity 1.
            scores = []
            for cl in affordable:
                true_y = np.asarray(data.project(cl).datavector(), dtype=float)
                est_y = np.asarray(base_model.project(cl).datavector(), dtype=float)
                scores.append(float(np.abs(true_y - est_y).sum()))

            accountant.charge(
                MechanismSpec(
                    "exponential", sensitivity=1.0, noise_scale=em_noise_scale(eps_sel, 1.0)
                ),
                run_id=f"mst_select_round_{r}",
            )
            pick = exponential_mechanism(
                scores, eps_sel, 1.0, seed=int(rng.integers(0, 2**31 - 1))
            )
            clique = affordable[pick]
            remaining.remove(clique)
            uf.union(col_index[clique[0]], col_index[clique[1]])
            measurements.append(measure(clique, rho_2way, f"mst_2way_{clique[0]}__{clique[1]}"))

        self._model = estimation.MirrorDescent().estimate(
            domain, measurements, known_total=None, iters=1000
        )
        self.is_fitted = True

    # ------------------------------------------------------------------ sampling

    def generate(self, num_samples: int) -> pd.DataFrame:
        if not self.is_fitted or self._model is None:
            raise RuntimeError("Generator must be fitted before calling generate().")
        rng = np.random.default_rng(self.seed)
        # private-pgm samples from NumPy's GLOBAL generator; seeded locally, caller's state
        # restored. Sampling is post-processing: a public seed costs no privacy.
        saved_state = np.random.get_state()
        if self.seed is not None:
            np.random.seed(int(self.seed) % (2**32))
        try:
            coded = sample_model(self._model, num_samples)
        finally:
            np.random.set_state(saved_state)
        return self._encoder.decode(coded, rng)
