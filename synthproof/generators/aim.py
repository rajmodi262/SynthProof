"""AIM-style adaptive marginal mechanism backed by private-PGM.

Implements the structure of AIM (McKenna et al., 2022):

  1. Measure every 1-way marginal under the Gaussian mechanism.
  2. Repeat for R rounds: fit a graphical model to the measurements taken so far, score each
     candidate 2-way marginal by how badly the current model predicts it, privately select the
     worst, and measure it.
  3. Fit a final graphical model and sample from it.

Inference is the real thing — `mbi` / private-PGM (McKenna, Sheldon & Miklau, 2019) — so the
synthetic data is drawn from a distribution consistent with all measured marginals rather than
from independent columns.

TWO HONEST DEVIATIONS FROM THE PAPER, both stated plainly rather than glossed:

  * **Selection uses report-noisy-max with Laplace noise**, not the exponential mechanism.
    Both are epsilon-DP selection mechanisms (Dwork & Roth, 2014, §3.3) and the accounting is
    equivalent, but report-noisy-max is directly expressible in our accountant, whereas an
    exponential-mechanism event would need a bound we cannot currently cite.
  * **No adaptive budget split across rounds.** AIM grows its per-round budget when a
    measurement proves informative. Here the split is fixed in advance, which is simpler to
    account for and strictly more conservative.

Requires Python >= 3.11 (a private-PGM constraint). `mbi` is imported lazily so the rest of the
package still works without it; constructing this class without `mbi` installed raises with an
actionable message rather than failing at import time.
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
from synthproof.generators.base import BaseGenerator

DEFAULT_BINS = 12
DEFAULT_ROUNDS = 6
# Share of the synthesis budget spent choosing which marginals to measure. Selection is a
# mechanism and must be paid for; AIM spends a comparable minority of its budget here.
DEFAULT_SELECTION_FRAC = 0.25

_MBI_HINT = (
    "AIMGenerator requires private-pgm (package `mbi`), which needs Python >= 3.11.\n"
    "  uv venv --python 3.11 .venv311\n"
    "  uv pip install --python .venv311/Scripts/python.exe "
    "'git+https://github.com/ryan112358/private-pgm.git'\n"
    "See docs/PYTHON311_UPGRADE.md. Use IndependentMarginalGenerator or "
    "PairwiseMarginalGenerator if private-pgm is unavailable."
)


def _require_mbi():
    try:
        from mbi import Dataset, Domain, LinearMeasurement, estimation
    except ImportError as exc:  # pragma: no cover - exercised only without mbi
        raise ImportError(_MBI_HINT) from exc
    return Domain, Dataset, LinearMeasurement, estimation


def mbi_available() -> bool:
    """True when private-PGM can be imported, for tests and mechanism registration."""
    try:
        import mbi  # noqa: F401
        return True
    except ImportError:
        return False


class AIMGenerator(BaseGenerator):
    """Adaptive marginal selection with graphical-model inference."""

    def __init__(self, seed: int = 42, num_bins: int = DEFAULT_BINS,
                 rounds: int = DEFAULT_ROUNDS,
                 selection_frac: float = DEFAULT_SELECTION_FRAC):
        super().__init__(seed=seed)
        if not (0.0 < selection_frac < 1.0):
            raise ValueError(f"selection_frac must be in (0, 1), got {selection_frac}")
        self.num_bins = num_bins
        self.rounds = rounds
        self.selection_frac = selection_frac
        self.levels_: Dict[str, list] = {}
        self.bin_edges_: Dict[str, np.ndarray] = {}
        self.measured_cliques_: List[Tuple[str, ...]] = []
        self._model = None

    # ------------------------------------------------------------------ encoding

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
        """Integer-codes every column; mbi requires a finite integer domain."""
        out = {}
        for col in dataset.columns:
            if col in dataset.numerical_cols:
                edges = self.bin_edges_[col]
                idx = np.digitize(dataset.df[col].to_numpy(dtype=float),
                                  edges[1:-1], right=False)
                out[col] = np.clip(idx, 0, self.num_bins - 1)
            else:
                lookup = {v: i for i, v in enumerate(self.levels_[col])}
                # Values outside the DP-released domain fold into level 0 rather than
                # silently widening the domain the release commits to.
                # `lookup` bound as a default argument: a bare closure over the loop
                # variable is a latent bug if the mapping is ever deferred.
                out[col] = dataset.df[col].map(
                    lambda v, _lk=lookup: _lk.get(v, 0)).to_numpy(dtype=int)
        return pd.DataFrame(out)

    # ------------------------------------------------------------------ fitting

    def fit(self, dataset: TabularDataset, profile: DomainProfile,
            accountant: Accountant, target_eps: float) -> None:
        Domain, Dataset, LinearMeasurement, estimation = _require_mbi()
        rng = np.random.default_rng(self.seed)

        self.columns = dataset.columns
        self.numerical_cols = dataset.numerical_cols
        self.categorical_cols = dataset.categorical_cols
        self._build_levels(dataset, profile)

        coded = self._encode(dataset)
        shapes = tuple(len(self.levels_[c]) for c in self.columns)
        domain = Domain(tuple(self.columns), shapes)
        data = Dataset(coded, domain)
        n = len(coded)

        candidates = [(a, b) for i, a in enumerate(self.columns)
                      for b in self.columns[i + 1:]]
        rounds = min(self.rounds, len(candidates))

        # ---- budget split. Measurement: d 1-way + `rounds` 2-way. Selection: `rounds`.
        sel_eps = target_eps * self.selection_frac if rounds else 0.0
        meas_eps = target_eps - sel_eps
        n_meas = len(self.columns) + rounds

        meas_sigma = calibrate_noise_scale(
            target_eps=meas_eps, target_delta=accountant.budget.delta,
            name="gaussian", sensitivity=1.0, steps=n_meas)
        sel_scale = calibrate_noise_scale(
            target_eps=sel_eps, target_delta=accountant.budget.delta,
            name="laplace", sensitivity=2.0, steps=rounds) if rounds else 0.0

        measurements = []

        # ---- 1-way marginals
        for col in self.columns:
            accountant.charge(
                MechanismSpec("gaussian", sensitivity=1.0, noise_scale=meas_sigma, steps=1),
                run_id=f"aim_1way_{col}")
            y = np.asarray(data.project((col,)).datavector(), dtype=float)
            noise = sample_discrete_gaussian(sigma=meas_sigma, size=y.size,
                                             seed=int(rng.integers(0, 2**31 - 1)))
            measurements.append(LinearMeasurement(y + noise, (col,), stddev=meas_sigma))
            self.measured_cliques_.append((col,))

        # ---- adaptive rounds
        remaining = list(candidates)
        for r in range(rounds):
            model = estimation.MirrorDescent().estimate(
                domain, measurements, known_total=n, iters=150)

            # Score each candidate by how badly the current model predicts it. Adding or
            # removing one record moves a marginal by 1 in one cell, so this L1 error moves
            # by at most 2 — hence sensitivity 2 for the selection score.
            scores = []
            for cl in remaining:
                true_y = np.asarray(data.project(cl).datavector(), dtype=float)
                est_y = np.asarray(model.project(cl).datavector(), dtype=float)
                scores.append(float(np.abs(true_y - est_y).sum()))

            accountant.charge(
                MechanismSpec("laplace", sensitivity=2.0, noise_scale=sel_scale, steps=1),
                run_id=f"aim_select_round_{r}")
            # Report-noisy-max: perturb every score and take the argmax. Equivalent in
            # guarantee to the exponential mechanism, and expressible in our accountant.
            gumbelish = sample_discrete_laplace(
                scale=max(sel_scale, 1e-9), size=len(scores),
                seed=int(rng.integers(0, 2**31 - 1)))
            pick = int(np.argmax(np.asarray(scores) + gumbelish))
            clique = remaining.pop(pick)

            accountant.charge(
                MechanismSpec("gaussian", sensitivity=1.0, noise_scale=meas_sigma, steps=1),
                run_id=f"aim_2way_{clique[0]}__{clique[1]}")
            y = np.asarray(data.project(clique).datavector(), dtype=float)
            noise = sample_discrete_gaussian(sigma=meas_sigma, size=y.size,
                                             seed=int(rng.integers(0, 2**31 - 1)))
            measurements.append(LinearMeasurement(y + noise, clique, stddev=meas_sigma))
            self.measured_cliques_.append(clique)

        self._model = estimation.MirrorDescent().estimate(
            domain, measurements, known_total=n, iters=400)
        self.is_fitted = True

    # ------------------------------------------------------------------ sampling

    def generate(self, num_samples: int) -> pd.DataFrame:
        if not self.is_fitted:
            raise RuntimeError("Generator must be fitted before calling generate().")
        rng = np.random.default_rng(self.seed)

        # `.records` is an int, not a frame — `.to_dict()` is the supported accessor.
        coded = pd.DataFrame(self._model.synthetic_data(rows=num_samples).to_dict())

        data = {}
        for col in self.columns:
            idx = np.clip(coded[col].to_numpy(dtype=int), 0, len(self.levels_[col]) - 1)
            if col in self.numerical_cols:
                edges = self.bin_edges_[col]
                data[col] = rng.uniform(edges[idx], edges[idx + 1])
            else:
                data[col] = np.asarray(self.levels_[col], dtype=object)[idx]
        return pd.DataFrame(data)
