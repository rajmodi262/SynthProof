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

TWO HONEST DEVIATIONS FROM THE PAPER, the same two AIMGenerator declares and for the same
reasons, so the accounting stays inside what this project's accountant can express:

  * **Selection uses report-noisy-max with Laplace noise**, not the exponential mechanism. Both
    are epsilon-DP selection mechanisms with equivalent accounting (Dwork & Roth, 2014, §3.3);
    report-noisy-max is the one our accountant charges directly. Constraining the argmax to the
    cycle-free candidate subset does not change the selection score's sensitivity (2), so the
    per-round charge is identical to AIM's verified selection charge.
  * **Fixed budget split**, not MST's data-dependent one. The split is decided in advance
    (measurement vs selection), which is simpler to account for and strictly more conservative.

Requires Python >= 3.11 (a private-PGM constraint). `mbi` is imported lazily via the same helper
AIM uses; constructing this class without `mbi` raises with an actionable message.
"""

from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from synthproof.accounting.accountant import Accountant
from synthproof.accounting.calibration import calibrate_noise_scale
from synthproof.accounting.noise import sample_discrete_gaussian, sample_discrete_laplace
from synthproof.accounting.types import MechanismSpec
from synthproof.data.dataset import TabularDataset
from synthproof.data.profiler import DomainProfile
from synthproof.generators.aim import (  # reuse AIM's exact mbi loader + defaults
    DEFAULT_BINS,
    DEFAULT_MAX_MODEL_MB,
    DEFAULT_SELECTION_FRAC,
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
        selection_frac: float = DEFAULT_SELECTION_FRAC,
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
        self._model = None

    # ------------------------------------------------------------------ encoding
    # Identical to AIM's: a finite integer domain is an mbi requirement, and using the same
    # encoding keeps the two mechanisms comparable in the grid.

    def _build_levels(self, dataset: TabularDataset, profile: DomainProfile) -> None:
        for col in dataset.columns:
            if col in dataset.numerical_cols:
                lo, hi = profile.columns[col].min_val, profile.columns[col].max_val
                if lo is None or hi is None:
                    raise ValueError(f"Column {col!r} has no DP range in the profile.")
                self.bin_edges_[col] = np.linspace(float(lo), float(hi), self.num_bins + 1)
                self.levels_[col] = list(range(self.num_bins))
            else:
                cats = profile.columns[col].categories
                if not cats:
                    raise ValueError(f"Column {col!r} has no DP category domain.")
                self.levels_[col] = list(cats)

    def _encode(self, dataset: TabularDataset) -> pd.DataFrame:
        out = {}
        for col in dataset.columns:
            if col in dataset.numerical_cols:
                edges = self.bin_edges_[col]
                idx = np.digitize(dataset.df[col].to_numpy(dtype=float), edges[1:-1], right=False)
                out[col] = np.clip(idx, 0, self.num_bins - 1)
            else:
                lookup = {v: i for i, v in enumerate(self.levels_[col])}
                out[col] = (
                    dataset.df[col].map(lambda v, _lk=lookup: _lk.get(v, 0)).to_numpy(dtype=int)
                )
        return pd.DataFrame(out)

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

        coded = self._encode(dataset)
        shapes = tuple(len(self.levels_[c]) for c in self.columns)
        domain = Domain(tuple(self.columns), shapes)
        data = Dataset(coded, domain)

        col_index = {c: i for i, c in enumerate(self.columns)}
        candidates = [(a, b) for i, a in enumerate(self.columns) for b in self.columns[i + 1 :]]
        # A spanning tree over d nodes has exactly d-1 edges; that is the selection round count.
        rounds = min(max(len(self.columns) - 1, 0), len(candidates))
        self.skipped_cliques_ = []

        # ---- budget split. Measurement: d 1-way + `rounds` 2-way. Selection: `rounds`.
        # The same split and the same calibration calls as AIM, so the composed epsilon is
        # charged through the identical path.
        sel_eps = target_eps * self.selection_frac if rounds else 0.0
        meas_eps = target_eps - sel_eps
        n_meas = len(self.columns) + rounds

        meas_sigma = calibrate_noise_scale(
            target_eps=meas_eps,
            target_delta=accountant.budget.delta,
            name="gaussian",
            sensitivity=1.0,
            steps=n_meas,
        )
        sel_scale = (
            calibrate_noise_scale(
                target_eps=sel_eps,
                target_delta=accountant.budget.delta,
                name="laplace",
                sensitivity=2.0,
                steps=rounds,
            )
            if rounds
            else 0.0
        )

        measurements = []

        # ---- 1-way marginals
        for col in self.columns:
            accountant.charge(
                MechanismSpec("gaussian", sensitivity=1.0, noise_scale=meas_sigma, steps=1),
                run_id=f"mst_1way_{col}",
            )
            y = np.asarray(data.project((col,)).datavector(), dtype=float)
            noise = sample_discrete_gaussian(
                sigma=meas_sigma, size=y.size, seed=int(rng.integers(0, 2**31 - 1))
            )
            measurements.append(LinearMeasurement(y + noise, (col,), stddev=meas_sigma))
            self.measured_cliques_.append((col,))

        # ---- one model from the 1-way measurements. MST scores edges against THIS fixed model
        # (Kruskal on estimated weights), rather than re-fitting each round as AIM does. The
        # model total is private-pgm's estimate from the noisy measurements, never the exact n.
        base_model = None
        if rounds:
            base_model = estimation.MirrorDescent().estimate(
                domain, measurements, known_total=None, iters=150
            )

        # ---- Kruskal with private edge selection: d-1 rounds of report-noisy-max over the
        # cycle-free candidate subset.
        uf = _UnionFind(len(self.columns))
        remaining = list(candidates)
        for r in range(rounds):
            # Eligible = edges that do not close a cycle AND whose junction tree fits the bound.
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

            # Score each eligible edge by how badly the fixed 1-way model predicts it. Adding or
            # removing one record moves a 2-way marginal by 1 in one cell, so this L1 error has
            # sensitivity 2 -- the same score and sensitivity AIM's selection charges for.
            scores = []
            for cl in affordable:
                true_y = np.asarray(data.project(cl).datavector(), dtype=float)
                est_y = np.asarray(base_model.project(cl).datavector(), dtype=float)
                scores.append(float(np.abs(true_y - est_y).sum()))

            accountant.charge(
                MechanismSpec("laplace", sensitivity=2.0, noise_scale=sel_scale, steps=1),
                run_id=f"mst_select_round_{r}",
            )
            gumbelish = sample_discrete_laplace(
                scale=max(sel_scale, 1e-9), size=len(scores), seed=int(rng.integers(0, 2**31 - 1))
            )
            pick = int(np.argmax(np.asarray(scores) + gumbelish))
            clique = affordable[pick]
            remaining.remove(clique)
            uf.union(col_index[clique[0]], col_index[clique[1]])

            accountant.charge(
                MechanismSpec("gaussian", sensitivity=1.0, noise_scale=meas_sigma, steps=1),
                run_id=f"mst_2way_{clique[0]}__{clique[1]}",
            )
            y = np.asarray(data.project(clique).datavector(), dtype=float)
            noise = sample_discrete_gaussian(
                sigma=meas_sigma, size=y.size, seed=int(rng.integers(0, 2**31 - 1))
            )
            measurements.append(LinearMeasurement(y + noise, clique, stddev=meas_sigma))
            self.measured_cliques_.append(clique)

        self._model = estimation.MirrorDescent().estimate(
            domain, measurements, known_total=None, iters=400
        )
        self.is_fitted = True

    # ------------------------------------------------------------------ sampling
    # Identical to AIM's: private-pgm's sampler draws from NumPy's GLOBAL RNG, so it is seeded
    # locally and the caller's state restored. Sampling is post-processing of the private model,
    # so the local seed costs no privacy.

    def generate(self, num_samples: int) -> pd.DataFrame:
        if not self.is_fitted or self._model is None:
            raise RuntimeError("Generator must be fitted before calling generate().")
        rng = np.random.default_rng(self.seed)

        saved_state = np.random.get_state()
        if self.seed is not None:
            np.random.seed(int(self.seed) % (2**32))
        try:
            coded = pd.DataFrame(self._model.synthetic_data(rows=num_samples).to_dict())
        finally:
            np.random.set_state(saved_state)

        data = {}
        for col in self.columns:
            idx = np.clip(coded[col].to_numpy(dtype=int), 0, len(self.levels_[col]) - 1)
            if col in self.numerical_cols:
                edges = self.bin_edges_[col]
                data[col] = rng.uniform(edges[idx], edges[idx + 1])
            else:
                data[col] = np.asarray(self.levels_[col], dtype=object)[idx]
        return pd.DataFrame(data)
