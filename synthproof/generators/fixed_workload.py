"""AIM's engine with a PRE-REGISTERED workload instead of adaptive selection.

WHY THIS IS THE CONTROL THE CONFOUND ARGUMENT NEEDS.

The project's strongest result argues that AIM's advantage on a structure metric measuring one
column pair is largely decided by whether AIM SELECTED that pair. Testing that requires holding
everything constant except selection, and until now the project had no way to do it:

  * `independent` and `moments` model no dependence at all, so they are a FLOOR, not a control.
    They cannot distinguish "selection causes the advantage" from "AIM is simply a better
    model".
  * `pairwise` uses a different model class (a chain) and a different inference procedure.
  * `dpvae` (`generators/dpvae.py`) selects nothing, which is right, but it is a different model
    class trained by DP-SGD. An examiner can fairly object that any difference is deep-vs-
    marginal rather than selecting-vs-not.

This class removes that objection. It is **AIM with the selection step deleted**: the same
private-PGM engine, the same MirrorDescent inference, the same discrete Gaussian measurement
noise, the same clique count, the same total epsilon. The only difference is WHERE the cliques
come from — a workload fixed in advance rather than chosen by looking at the data.

WHERE THE WORKLOAD COMES FROM, AND WHY IT COSTS NOTHING.
The cliques are drawn uniformly at random from all column pairs using `workload_seed`, which is
a PUBLIC parameter. No data is consulted, so there is no query to charge — exactly the argument
that makes the H3 column weights free (see ch06 §6.10). The consequence is that AIM's selection
budget (`selection_frac`, ~10% of the total) is not spent here, so **this mechanism puts MORE
epsilon into measurement than AIM does at the same target**. That asymmetry is real and is
reported rather than corrected away: it biases the comparison IN AIM's DISFAVOUR on the
selected pairs, which makes a positive selection effect harder to find, not easier.

WHY "ALL PAIRS" IS NOT THE WORKLOAD.
Measuring every pair would be the purest no-selection control, and it is not computable:
inference cost is exponential in the junction tree's treewidth, and a dense two-way graph on
this many columns exceeds the model-size bound AIM itself enforces. The same bound is applied
here, and refused cliques are recorded in `skipped_cliques_` rather than dropped silently.

WHAT WOULD FALSIFY THE CONFOUND READING.
If this mechanism shows the SAME selected-vs-unselected error gap that AIM shows -- when its
cliques were chosen without looking at the data and therefore cannot encode any property of the
pairs -- then the gap is a property of which pairs are easy, not of selection, and the project's
reading is wrong. `scripts/run_clique_confound.py` computes exactly that comparison.
"""

from typing import Dict, List, Optional, Tuple

import numpy as np

from synthproof.accounting.accountant import Accountant
from synthproof.accounting.calibration import calibrate_noise_scale
from synthproof.accounting.noise import sample_discrete_gaussian
from synthproof.accounting.types import MechanismSpec
from synthproof.data.dataset import TabularDataset
from synthproof.data.profiler import DomainProfile
from synthproof.generators.aim import DEFAULT_BINS, DEFAULT_ROUNDS, AIMGenerator, _require_mbi


class FixedWorkloadGenerator(AIMGenerator):
    """AIM's engine driven by a data-independent workload. Selects nothing."""

    def __init__(
        self,
        seed: int = 42,
        num_bins: int = DEFAULT_BINS,
        rounds: int = DEFAULT_ROUNDS,
        max_model_mb: float = 80.0,
        workload_seed: int = 12345,
        workload: Optional[List[Tuple[str, str]]] = None,
    ):
        """
        Args:
            rounds: How many 2-way cliques to measure. Matched to AIM's default so the two
                mechanisms measure the same number of marginals.
            workload_seed: PUBLIC seed for drawing the workload. Fixing it makes the arm
                reproducible and makes clear that no data was consulted to choose it.
            workload: An explicit list of pairs, overriding the random draw. Must be public.
        """
        super().__init__(seed=seed, num_bins=num_bins, rounds=rounds, max_model_mb=max_model_mb)
        self.workload_seed = workload_seed
        self.workload = workload
        # Recorded so an analysis can confirm the arm measured what it claimed to.
        self.workload_: List[Tuple[str, str]] = []

    def fit(
        self,
        dataset: TabularDataset,
        profile: DomainProfile,
        accountant: Accountant,
        target_eps: float,
    ) -> None:
        """Measures a fixed workload. No exponential mechanism, no selection charge."""
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
        n = len(coded)

        candidates = [(a, b) for i, a in enumerate(self.columns) for b in self.columns[i + 1 :]]
        self.skipped_cliques_ = []
        self.measured_cliques_ = []

        # ---- the workload, chosen WITHOUT touching the data -------------------------------
        if self.workload is not None:
            chosen = [tuple(p) for p in self.workload]
            unknown = [p for p in chosen if p not in candidates]
            if unknown:
                raise ValueError(f"Workload contains pairs not in the schema: {unknown}")
        else:
            wrng = np.random.default_rng(self.workload_seed)
            k = min(self.rounds, len(candidates))
            idx = wrng.choice(len(candidates), size=k, replace=False)
            chosen = [candidates[i] for i in sorted(idx)]

        # ---- budget. ALL of it goes to measurement: there is no selection to pay for. -----
        n_meas = len(self.columns) + len(chosen)
        meas_sigma = calibrate_noise_scale(
            target_eps=target_eps,
            target_delta=accountant.budget.delta,
            name="gaussian",
            sensitivity=1.0,
            steps=n_meas,
        )
        self.meas_sigma_ = float(meas_sigma)

        measurements = []

        # ---- 1-way marginals, same as AIM -------------------------------------------------
        for col in self.columns:
            accountant.charge(
                MechanismSpec("gaussian", sensitivity=1.0, noise_scale=meas_sigma, steps=1),
                run_id=f"fixedwl_1way_{col}",
            )
            y = np.asarray(data.project((col,)).datavector(), dtype=float)
            noise = sample_discrete_gaussian(
                sigma=meas_sigma, size=y.size, seed=int(rng.integers(0, 2**31 - 1))
            )
            measurements.append(LinearMeasurement(y + noise, (col,), stddev=meas_sigma))
            self.measured_cliques_.append((col,))

        # ---- the fixed 2-way workload -----------------------------------------------------
        # The model-size bound still applies: a clique whose junction tree would exceed the
        # budget is refused and recorded, exactly as AIM does. Refusing to measure a marginal
        # is a limitation of the run and belongs in the results.
        for clique in chosen:
            size_mb = hypothetical_model_size(domain, [*self.measured_cliques_, clique])
            if size_mb > self.max_model_mb:
                self.skipped_cliques_.append(clique)
                continue

            accountant.charge(
                MechanismSpec("gaussian", sensitivity=1.0, noise_scale=meas_sigma, steps=1),
                run_id=f"fixedwl_2way_{clique[0]}__{clique[1]}",
            )
            y = np.asarray(data.project(clique).datavector(), dtype=float)
            noise = sample_discrete_gaussian(
                sigma=meas_sigma, size=y.size, seed=int(rng.integers(0, 2**31 - 1))
            )
            measurements.append(LinearMeasurement(y + noise, clique, stddev=meas_sigma))
            self.measured_cliques_.append(clique)
            self.workload_.append(clique)

        self._model = estimation.MirrorDescent().estimate(
            domain, measurements, known_total=n, iters=400
        )
        self.is_fitted = True

    # `generate` is inherited from AIMGenerator unchanged: same model, same sampler.

    @property
    def selection_charges(self) -> Dict[str, int]:
        """Zero by construction. Asserted by test rather than trusted."""
        return {"selection_rounds": 0}
