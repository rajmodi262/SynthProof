"""AIM: adaptive, iterative marginal selection over private-PGM (McKenna et al., VLDB 2022).

Follows the published algorithm (Algorithm 1 of the paper), restricted to 2-way candidates:

  1. Convert the target (eps, delta) into ONE zCDP budget rho, found against the project's own
     accountant. Every step below is a zCDP charge and zCDP adds exactly, so the release spends
     its whole budget -- the previous version calibrated each stage separately and left 18-25%
     of it unspent (audit H1, research/27).
  2. Measure every 1-way marginal with the Gaussian mechanism.
  3. For d rounds: fit the graphical model (warm-started), score every candidate marginal not
     yet measured by how badly the model predicts it MINUS the error its own measurement noise
     would add (AIM's penalty -- without it large, noisy marginals win), pick one with the
     EXPONENTIAL MECHANISM, measure it. Candidates are every pair plus, when the release
     declares a target column, every 3-way marginal containing it (AIM's TARGET workload).
  4. Fit a final model and sample from it.

TWO STATED DEPARTURES FROM THE PAPER, both measured (research/27, scripts/ab_aim_config.py):
  * **~d rounds, not 16d, and no repeat measurements.** Each round costs ~8 s of JAX
    recompilation here, so 16d rounds would make the grid intractable on a laptop; with d
    rounds a repeat is a wasted round (on SF Fire the old code measured zipcode x station_area
    three times).
  * **Annealing is OFF by default.** AIM's budget-quadrupling rule assumes ~16d planned rounds;
    at ~d it ended SF Fire after 2 rounds. Unseen-row usefulness, seed 0: annealing on / off =
    79% / 98% (Fire, eps=1), 90% / 93% (Adult, eps=1). `adaptive_budget=True` keeps it.

What changed from the previous version, and why (audit H2):
  * It measured a FIXED 6 pairs whatever the budget. On SF Fire those 6 never touched the
    prediction target, so AIM scored 67% where MST scored 97%. Rounds are now budget-driven.
  * Selection was report-noisy-max charged as a Laplace mechanism -- not a theorem (audit L1).
    It is now the exponential mechanism, charged via its bounded-range (eps^2/8)-zCDP bound
    (Cesar & Rogers 2021), which is also cheaper for the same selection.
  * Selection sensitivity is 1: under add/remove-one -- the neighbouring relation every other
    charge here uses -- one record moves one cell of a pair's true marginal by one, and the
    model's estimate is post-processing of noisy measurements. The old value 2 is the
    replace-one sensitivity and was inconsistent with the Gaussian charges.

`rounds` given as an integer keeps the fixed-round variant (no annealing, budget split evenly
over exactly that many rounds), which the ablations and small tests use.

Requires Python >= 3.11 (a private-PGM constraint). `mbi` is imported lazily.
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
    enable_x64,
    rho_for,
    sample_model,
    sigma_for_rho,
)
from synthproof.generators.base import BaseGenerator

DEFAULT_BINS = 12
# Fixed-round count used only by the ablation arm (`fixed_workload.py`) and explicit callers.
DEFAULT_ROUNDS = 6
# AIM's own split: 10% of each round's budget selects, 90% measures (McKenna et al. 2022).
DEFAULT_SELECTION_FRAC = 0.1
# Budget-driven AIM starts with a per-round budget sized for `ROUNDS_PER_COLUMN * d` rounds;
# annealing then concentrates it into fewer, sharper measurements. The paper uses 16. Here each
# round costs ~8 s of JAX recompilation (the model's pair marginals are re-traced whenever the
# junction tree changes), so 1 keeps a fit near a minute; annealing usually ends it sooner.
ROUNDS_PER_COLUMN = 1
# Junction-tree budget in megabytes (AIM bounds model size for the same reason, section 4).
DEFAULT_MAX_MODEL_MB = 128.0
# Mirror-descent iterations: warm-started per round, longer for the final fit.
ROUND_ITERS = 100
FINAL_ITERS = 1000

_MBI_HINT = (
    "AIMGenerator requires private-pgm (package `mbi`), which needs Python >= 3.11.\n"
    "  uv venv --python 3.11 .venv311\n"
    "  uv pip install --python .venv311/Scripts/python.exe "
    "'git+https://github.com/ryan112358/private-pgm.git'\n"
    "See docs/PYTHON311_UPGRADE.md. Use IndependentMarginalGenerator or "
    "PairwiseMarginalGenerator if private-pgm is unavailable."
)


def _quiet_jax_cache() -> None:
    """Turns off JAX's persistent compilation cache before mbi is imported (mbi's own advice for
    a sweep of many small programs), and switches JAX to 64-bit (audit H6)."""
    try:
        import jax

        jax.config.update("jax_enable_compilation_cache", False)
    except Exception:  # pragma: no cover - jax absent or API moved; the warning is cosmetic
        pass
    enable_x64()


def _require_mbi():
    _quiet_jax_cache()
    try:
        from mbi import Dataset, Domain, LinearMeasurement, estimation
        from mbi.junction_tree import hypothetical_model_size
    except ImportError as exc:  # pragma: no cover - exercised only without mbi
        raise ImportError(_MBI_HINT) from exc
    return Domain, Dataset, LinearMeasurement, estimation, hypothetical_model_size


def mbi_available() -> bool:
    """True when private-PGM can be imported, for tests and mechanism registration."""
    _quiet_jax_cache()
    try:
        import mbi  # noqa: F401

        return True
    except ImportError:
        return False


class AIMGenerator(BaseGenerator):
    """Adaptive marginal selection with graphical-model inference."""

    def __init__(
        self,
        seed: int = 42,
        num_bins: int = DEFAULT_BINS,
        rounds: Optional[int] = None,
        selection_frac: float = DEFAULT_SELECTION_FRAC,
        max_model_mb: float = DEFAULT_MAX_MODEL_MB,
        adaptive_budget: bool = False,
        rounds_per_column: int = ROUNDS_PER_COLUMN,
        target_col: Optional[str] = None,
    ):
        super().__init__(seed=seed)
        if not (0.0 < selection_frac < 1.0):
            raise ValueError(f"selection_frac must be in (0, 1), got {selection_frac}")
        if max_model_mb <= 0:
            raise ValueError(f"max_model_mb must be positive, got {max_model_mb}")
        if rounds is not None and rounds < 0:
            raise ValueError(f"rounds must be >= 0 or None, got {rounds}")
        self.num_bins = num_bins
        self.rounds = rounds
        self.selection_frac = selection_frac
        self.max_model_mb = max_model_mb
        # AIM's annealing: opt-in (see the module docstring for the measurement that decided it).
        # Only meaningful for budget-driven rounds; a fixed round count never anneals.
        self.adaptive_budget = adaptive_budget
        self.rounds_per_column = rounds_per_column
        # AIM's TARGET workload (McKenna et al. 2022, section 6): when the release declares the
        # column a downstream model will predict, 3-way marginals containing it become candidates
        # too. Without them a 2-level target's pairs have too few cells to ever out-score big
        # feature pairs -- on SF Fire AIM never measured `als_unit` at all (audit H2). The target
        # is PUBLIC (it is printed in the data sheet), so using it costs no privacy.
        self.target_col = target_col
        # Cliques refused by the size bound. Recorded, not dropped silently.
        self.skipped_cliques_: List[Tuple[str, ...]] = []
        self.measured_cliques_: List[Tuple[str, ...]] = []
        self.levels_: Dict[str, list] = {}
        self.bin_edges_: Dict[str, np.ndarray] = {}
        self.unspent_rho_: float = 0.0
        self._encoder: Optional[MarginalEncoder] = None
        self._model = None

    # ------------------------------------------------------------------ encoding

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
        self.measured_cliques_ = []
        self.skipped_cliques_ = []

        coded = self._encode(dataset)
        domain = Domain(tuple(self.columns), self._encoder.shape())
        data = Dataset(coded, domain)
        d = len(self.columns)
        candidates = [(a, b) for i, a in enumerate(self.columns) for b in self.columns[i + 1 :]]
        if self.target_col is not None and self.target_col in self.columns:
            others = [c for c in self.columns if c != self.target_col]
            candidates += [
                (self.target_col, a, b) for i, a in enumerate(others) for b in others[i + 1 :]
            ]

        # ---- one budget. A hair below the calibrated rho so floating-point sums of many
        # charges can never tip the accountant over the target.
        rho = rho_for(target_eps, accountant.budget.delta) * (1.0 - 1e-9)
        f = self.selection_frac
        fixed = self.rounds is not None
        n_pairs = d * (d - 1) // 2
        planned = (
            min(self.rounds, n_pairs) if fixed else min(self.rounds_per_column * d, len(candidates))
        )
        if not candidates:
            planned = 0
        # Per-measurement cost so that d 1-ways + `planned` rounds spend exactly rho.
        rho_meas = rho / (d + planned / (1.0 - f)) if planned else rho / max(d, 1)
        rho_sel = rho_meas * f / (1.0 - f)
        used = 0.0

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
            return LinearMeasurement(y + noise, tuple(clique), stddev=sigma), sigma

        measurements = []
        for col in self.columns:
            m, _ = measure((col,), rho_meas, f"aim_1way_{col}")
            measurements.append(m)
            used += rho_meas

        model = None
        r = 0
        while planned and rho - used > 1e-12 * rho:
            if fixed and r >= planned:
                break
            remaining = rho - used
            if not fixed and remaining < 2.0 * (rho_meas + rho_sel):
                # The final round spends exactly what is left.
                rho_meas, rho_sel = (1.0 - f) * remaining, f * remaining
            if rho_meas + rho_sel > remaining * (1 + 1e-9):
                break

            model = estimation.MirrorDescent().estimate(
                # known_total=None: the total is estimated from the NOISY measurements, never
                # the exact row count (research/11_selection_accounting.md).
                domain, measurements, known_total=None, iters=ROUND_ITERS, warm_start=model
            )

            # A marginal already measured -- or contained in one that was -- is not a candidate
            # again. The paper allows repeats over its 16d rounds; with ~d rounds a repeat is a
            # wasted round, and on large tables the biggest pair's absolute error stays on top
            # after measurement (SF Fire re-measured zipcode x station_area three times).
            covered = [set(c) for c in self.measured_cliques_ if len(c) >= 2]
            def _affordable(pool):
                out = []
                for cl in pool:
                    if hypothetical_model_size(domain, [*self.measured_cliques_, cl]) <= self.max_model_mb:
                        out.append(cl)
                    elif cl not in self.skipped_cliques_:
                        self.skipped_cliques_.append(cl)
                return out

            affordable = _affordable([cl for cl in candidates if not any(set(cl) <= m for m in covered)])
            if not affordable:
                # Everything is covered: a repeat measurement beats leaving budget unspent.
                affordable = _affordable(candidates)
            if not affordable:
                break

            sigma = sigma_for_rho(rho_meas)
            scores = []
            for cl in affordable:
                true_y = np.asarray(data.project(cl).datavector(), dtype=float)
                est_y = np.asarray(model.project(cl).datavector(), dtype=float)
                penalty = np.sqrt(2.0 / np.pi) * sigma * true_y.size
                scores.append(float(np.abs(true_y - est_y).sum()) - penalty)

            eps_sel = em_eps_for_rho(rho_sel)
            accountant.charge(
                MechanismSpec("exponential", sensitivity=1.0, noise_scale=em_noise_scale(eps_sel, 1.0)),
                run_id=f"aim_select_round_{r}",
            )
            pick = exponential_mechanism(scores, eps_sel, 1.0, seed=int(rng.integers(0, 2**31 - 1)))
            # `pick` indexes `affordable` (audit H3).
            clique = affordable[pick]
            before = np.asarray(model.project(clique).datavector(), dtype=float)
            m, sigma = measure(clique, rho_meas, f"aim_{len(clique)}way_{'__'.join(clique)}")
            measurements.append(m)
            used += rho_meas + rho_sel
            r += 1

            if self.adaptive_budget and not fixed:
                model = estimation.MirrorDescent().estimate(
                    domain, measurements, known_total=None, iters=ROUND_ITERS, warm_start=model
                )
                after = np.asarray(model.project(clique).datavector(), dtype=float)
                if np.abs(after - before).sum() <= np.sqrt(2.0 / np.pi) * sigma * before.size:
                    rho_meas, rho_sel = 4.0 * rho_meas, 4.0 * rho_sel  # AIM: sigma halves

        self.unspent_rho_ = max(0.0, rho - used)
        self._model = estimation.MirrorDescent().estimate(
            domain, measurements, known_total=None, iters=FINAL_ITERS, warm_start=model
        )
        self.is_fitted = True

    # ------------------------------------------------------------------ sampling

    def generate(self, num_samples: int) -> pd.DataFrame:
        if not self.is_fitted or self._model is None:
            raise RuntimeError("Generator must be fitted before calling generate().")
        rng = np.random.default_rng(self.seed)
        # private-pgm samples from NumPy's GLOBAL generator; seed it locally and restore the
        # caller's state. Sampling is post-processing of the private model: a public seed costs
        # no privacy.
        saved_state = np.random.get_state()
        if self.seed is not None:
            np.random.seed(int(self.seed) % (2**32))
        try:
            coded = sample_model(self._model, num_samples)
        finally:
            np.random.set_state(saved_state)
        return self._encoder.decode(coded, rng)
