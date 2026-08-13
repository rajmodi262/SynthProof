"""Pairwise-marginal DP generator over a tree-structured graphical model.

WHAT THIS IS. It discretises every column against the public schema, measures the 1-way
marginal of a root column and the 2-way marginals along a spanning tree, and samples from the
resulting tree-structured graphical model. Because each child is drawn conditionally on its
parent, the synthetic data **preserves pairwise dependence** — unlike the independent-marginal
baselines, which destroy all cross-column structure by construction.

WHAT THIS IS NOT. It is not AIM (McKenna et al., 2022) and not MST (McKenna et al., 2021):

  * The tree structure is **fixed and public**, not selected from the data. MST and AIM choose
    structure with the exponential mechanism, which costs budget and adds adaptivity this
    implementation does not have.
  * There is no iterative measure-and-refine loop and no private-PGM inference; sampling is a
    direct ancestral pass over the tree.

The reference implementation of AIM (`private-pgm`) requires Python >= 3.11, and this project
currently targets 3.10, so it could not be installed. Rather than name a class after an
algorithm it does not implement — the exact failure mode audit finding F6 recorded — this is a
separate, honestly-named mechanism. It is nonetheless a *genuinely different model family* from
the independent-marginal baselines, which is what hypothesis H1 requires.

Privacy accounting: d 1-way marginals plus (d-1) 2-way marginals are measured, all under one
calibrated Gaussian noise multiplier, so the fit composes to exactly its target epsilon.
Structure is public, so selecting it costs nothing.
"""

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from synthproof.accounting.accountant import Accountant
from synthproof.accounting.calibration import calibrate_noise_scale
from synthproof.accounting.noise import sample_discrete_gaussian
from synthproof.accounting.types import MechanismSpec
from synthproof.data.dataset import TabularDataset
from synthproof.data.profiler import DomainProfile
from synthproof.generators.base import BaseGenerator

DEFAULT_BINS = 12


class PairwiseMarginalGenerator(BaseGenerator):
    """Tree-structured DP generator preserving pairwise dependence."""

    def __init__(self, seed: int = 42, num_bins: int = DEFAULT_BINS,
                 tree: Optional[List[Tuple[str, str]]] = None):
        """
        Args:
            seed: RNG seed.
            num_bins: Bins per numeric column, over the public schema range.
            tree: Optional explicit (parent, child) edges. Must be PUBLIC knowledge — deriving
                it from the data would require the exponential mechanism and a budget charge.
                Defaults to a chain in column order.
        """
        super().__init__(seed=seed)
        self.num_bins = num_bins
        self.tree = tree
        self.levels_: Dict[str, list] = {}
        self.root_: Optional[str] = None
        self.edges_: List[Tuple[str, str]] = []
        self.root_probs_: Optional[np.ndarray] = None
        self.cond_: Dict[Tuple[str, str], np.ndarray] = {}
        self.bin_edges_: Dict[str, np.ndarray] = {}

    # ------------------------------------------------------------------ discretisation

    def _build_levels(self, dataset: TabularDataset, profile: DomainProfile) -> None:
        """Maps every column onto a finite, public set of levels."""
        for col in dataset.columns:
            if col in dataset.numerical_cols:
                lo, hi = profile.columns[col].min_val, profile.columns[col].max_val
                if lo is None or hi is None:
                    raise ValueError(f"Column {col!r} has no DP range in the profile.")
                edges = np.linspace(float(lo), float(hi), self.num_bins + 1)
                self.bin_edges_[col] = edges
                self.levels_[col] = list(range(self.num_bins))
            else:
                cats = profile.columns[col].categories
                if not cats:
                    raise ValueError(f"Column {col!r} has no DP category domain.")
                self.levels_[col] = list(cats)

    def _codes(self, dataset: TabularDataset, col: str) -> np.ndarray:
        """Integer level codes for a column; out-of-domain values map to -1."""
        if col in dataset.numerical_cols:
            edges = self.bin_edges_[col]
            idx = np.digitize(dataset.df[col].to_numpy(dtype=float), edges[1:-1], right=False)
            return np.clip(idx, 0, self.num_bins - 1)
        lookup = {v: i for i, v in enumerate(self.levels_[col])}
        return dataset.df[col].map(lambda v: lookup.get(v, -1)).to_numpy(dtype=int)

    # ------------------------------------------------------------------ fitting

    def fit(self, dataset: TabularDataset, profile: DomainProfile,
            accountant: Accountant, target_eps: float) -> None:
        rng = np.random.default_rng(self.seed)
        self.columns = dataset.columns
        self.numerical_cols = dataset.numerical_cols
        self.categorical_cols = dataset.categorical_cols

        self._build_levels(dataset, profile)

        cols = list(self.columns)
        if not cols:
            raise ValueError("Cannot fit on a dataset with no columns.")
        self.root_ = cols[0]
        # Public structure: a chain. No data is consulted, so no budget is charged for it.
        self.edges_ = self.tree if self.tree is not None else [
            (cols[i], cols[i + 1]) for i in range(len(cols) - 1)
        ]

        n_queries = 1 + len(self.edges_)
        noise_scale = calibrate_noise_scale(
            target_eps=target_eps,
            target_delta=accountant.budget.delta,
            name="gaussian",
            sensitivity=1.0,
            steps=n_queries,
        )

        codes = {c: self._codes(dataset, c) for c in cols}

        # Root 1-way marginal.
        accountant.charge(
            MechanismSpec(name="gaussian", sensitivity=1.0, noise_scale=noise_scale, steps=1),
            run_id=f"pairwise_root_{self.root_}",
        )
        k = len(self.levels_[self.root_])
        hist = np.bincount(codes[self.root_][codes[self.root_] >= 0], minlength=k).astype(float)
        noise = sample_discrete_gaussian(sigma=noise_scale, size=k,
                                         seed=int(rng.integers(0, 2**31 - 1)))
        self.root_probs_ = self._normalise(np.maximum(0.0, hist + noise))

        # 2-way marginals along the tree, stored as conditionals P(child | parent).
        for parent, child in self.edges_:
            accountant.charge(
                MechanismSpec(name="gaussian", sensitivity=1.0,
                              noise_scale=noise_scale, steps=1),
                run_id=f"pairwise_edge_{parent}__{child}",
            )
            kp, kc = len(self.levels_[parent]), len(self.levels_[child])
            joint = np.zeros((kp, kc), dtype=float)
            pc, cc = codes[parent], codes[child]
            valid = (pc >= 0) & (cc >= 0)
            np.add.at(joint, (pc[valid], cc[valid]), 1.0)

            noise = sample_discrete_gaussian(
                sigma=noise_scale, size=kp * kc, seed=int(rng.integers(0, 2**31 - 1))
            ).reshape(kp, kc)
            joint = np.maximum(0.0, joint + noise)

            # Row-normalise into a conditional. A parent level whose row is entirely noise-
            # clipped falls back to uniform rather than producing NaNs downstream.
            self.cond_[(parent, child)] = np.vstack([
                self._normalise(joint[i]) for i in range(kp)
            ])

        self.is_fitted = True

    @staticmethod
    def _normalise(counts: np.ndarray) -> np.ndarray:
        total = counts.sum()
        if total <= 0:
            return np.full(len(counts), 1.0 / len(counts))
        return counts / total

    # ------------------------------------------------------------------ sampling

    def generate(self, num_samples: int) -> pd.DataFrame:
        if not self.is_fitted:
            raise RuntimeError("Generator must be fitted before calling generate().")
        rng = np.random.default_rng(self.seed)

        drawn: Dict[str, np.ndarray] = {
            self.root_: rng.choice(len(self.root_probs_), p=self.root_probs_, size=num_samples)
        }
        # Ancestral pass. Edges are emitted parent-before-child by construction.
        for parent, child in self.edges_:
            table = self.cond_[(parent, child)]
            pvals = drawn[parent]
            out = np.empty(num_samples, dtype=int)
            # Group by parent level so each conditional is sampled in one vectorised call.
            for lvl in np.unique(pvals):
                mask = pvals == lvl
                out[mask] = rng.choice(table.shape[1], p=table[lvl], size=int(mask.sum()))
            drawn[child] = out

        data = {}
        for col in self.columns:
            idx = drawn[col]
            if col in self.numerical_cols:
                edges = self.bin_edges_[col]
                # Uniform within the sampled bin, so output is continuous rather than gridded.
                data[col] = rng.uniform(edges[idx], edges[idx + 1])
            else:
                levels = np.asarray(self.levels_[col], dtype=object)
                data[col] = levels[idx]

        return pd.DataFrame(data)
