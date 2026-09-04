"""Tests for the DP-SGD VAE — the project's first non-marginal-based mechanism.

The tests that earn their place here are the ones about the PRIVACY BOUNDARY, not the ones
about the model fitting. A generative model that fits badly is a utility result; a generative
model that emits a category the DP profiler suppressed, or that spends more budget than it
charged, is a broken guarantee.

Per the standing rules every measurement ships with a positive and a negative control, and
each negative control below was verified by making it fail first.
"""

import pytest

from synthproof.accounting.accountant import Accountant
from synthproof.accounting.types import BudgetExceededError
from synthproof.data.dataset import TabularDataset
from synthproof.data.profiler import DPDomainProfiler
from synthproof.generators.dpvae import DPVAEGenerator


@pytest.fixture(scope="module")
def fitted():
    """One trained model, reused — DP-SGD is the slow part of this file."""
    ds = TabularDataset.create_synthetic_toy(num_rows=1200, seed=0)
    acct = Accountant(budget_eps=6.0, budget_delta=1e-5)
    prof = DPDomainProfiler(acct, eps_budget=0.2).profile(ds)
    g = DPVAEGenerator(seed=0, steps=40, batch_size=256)
    g.fit(ds, prof, acct, target_eps=1.5)
    return ds, prof, acct, g


# --------------------------------------------------------------------------- the boundary


def test_training_charges_the_accountant(fitted):
    """POSITIVE CONTROL. DP-SGD must appear as a charge, not happen for free."""
    _, _, acct, _ = fitted
    dpsgd = [s for s in acct.spends if s.run_id == "dpvae_dpsgd"]
    assert len(dpsgd) == 1, "the training run must be charged exactly once"
    assert dpsgd[0].marginal_eps > 0


def test_the_charge_declares_steps_and_subsampling(fitted):
    """The whole soundness of DP-SGD accounting rests on these two fields reaching the
    accountant. Charging one Gaussian event instead of `steps` subsampled ones would
    under-report epsilon by orders of magnitude."""
    _, _, acct, g = fitted
    spec = [s for s in acct.spends if s.run_id == "dpvae_dpsgd"][0].mechanism
    assert spec.steps == 40
    assert spec.sampling_rate is not None and 0 < spec.sampling_rate < 1.0
    assert spec.name == "gaussian"
    assert spec.sensitivity == g.clip_norm


def test_it_never_overspends(fitted):
    """The release must cost at most the budget, like every other mechanism here."""
    _, _, acct, _ = fitted
    assert acct.total() <= acct.budget.epsilon


def test_budget_exhaustion_raises_rather_than_silently_proceeding():
    """NEGATIVE CONTROL. Asking for more than the budget must refuse, not train anyway."""
    ds = TabularDataset.create_synthetic_toy(num_rows=600, seed=1)
    acct = Accountant(budget_eps=0.3, budget_delta=1e-5)
    prof = DPDomainProfiler(acct, eps_budget=0.1).profile(ds)
    g = DPVAEGenerator(seed=1, steps=20, batch_size=128)
    with pytest.raises(BudgetExceededError):
        g.fit(ds, prof, acct, target_eps=5.0)


def test_more_budget_means_less_noise():
    """A larger epsilon must buy a smaller noise multiplier, or calibration is inverted."""
    ds = TabularDataset.create_synthetic_toy(num_rows=800, seed=2)
    scales = []
    for eps in (0.5, 4.0):
        acct = Accountant(budget_eps=10.0, budget_delta=1e-5)
        prof = DPDomainProfiler(acct, eps_budget=0.1).profile(ds)
        g = DPVAEGenerator(seed=2, steps=20, batch_size=128)
        g.fit(ds, prof, acct, target_eps=eps)
        scales.append(g.noise_scale_)
    assert scales[0] > scales[1], f"noise did not fall with budget: {scales}"


# --------------------------------------------------------------------------- the output


def test_generate_before_fit_refuses(fitted):
    """An unfitted model must raise, not return plausible-looking noise."""
    g = DPVAEGenerator(seed=0)
    with pytest.raises(RuntimeError):
        g.generate(10)


def test_output_matches_the_schema(fitted):
    ds, _, _, g = fitted
    syn = g.generate(300)
    assert list(syn.columns) == list(ds.columns)
    assert len(syn) == 300
    for col in ds.numerical_cols:
        assert syn[col].dtype.kind in "fi"


def test_no_category_outside_the_profiled_domain(fitted):
    """SAFETY-CRITICAL. The DP profiler suppresses rare categories on purpose. A generator
    that emitted a value outside the profiled domain would be releasing a category the
    profiler decided was too rare to release -- undoing the suppression it was charged for."""
    ds, prof, _, g = fitted
    syn = g.generate(500)
    for col in ds.categorical_cols:
        allowed = set(prof.columns[col].categories or [])
        assert allowed, f"no profiled domain for {col!r}"
        assert set(syn[col].unique()) <= allowed


def test_numerical_values_stay_inside_the_profiled_range(fitted):
    """Values are drawn within the public binning grid, so nothing can fall outside it."""
    ds, prof, _, g = fitted
    syn = g.generate(500)
    for col in ds.numerical_cols:
        lo, hi = prof.columns[col].min_val, prof.columns[col].max_val
        assert syn[col].min() >= lo - 1e-6
        assert syn[col].max() <= hi + 1e-6


def test_same_seed_reproduces(fitted):
    ds, prof, _, _ = fitted
    outs = []
    for _ in range(2):
        acct = Accountant(budget_eps=6.0, budget_delta=1e-5)
        g = DPVAEGenerator(seed=7, steps=20, batch_size=128)
        g.fit(ds, prof, acct, target_eps=1.0)
        outs.append(g.generate(50))
    assert outs[0].equals(outs[1])


# --------------------------------------------------------------------------- the control claim

# This mechanism exists to be a control for the clique-selection confound. That role is only
# valid if it genuinely has no marginal-selection step. These pin that property so a future
# "improvement" that adds workload awareness cannot silently invalidate the experiment.


def test_it_selects_no_marginals(fitted):
    """The claim that makes this a control: no clique selection, no workload, no marginals.

    AIM exposes its choices (`selected_cliques_`, `skipped_cliques_`); the marginal
    generators measure a fixed set. This model must expose no such attribute, because its
    parameters are updated by noisy gradients over whole records.
    """
    _, _, _, g = fitted
    for attr in ("selected_cliques_", "skipped_cliques_", "cliques_", "workload_", "marginals_"):
        assert not hasattr(g, attr), (
            f"DPVAEGenerator grew {attr!r}. If this mechanism now selects statistics it is no "
            "longer a valid control for the clique-selection confound, and the experiment in "
            "results/ must be re-run or withdrawn."
        )


def test_every_column_is_modelled_by_the_same_machinery(fitted):
    """No column gets a privileged budget share, which is what makes per-pair comparison fair."""
    ds, _, _, g = fitted
    assert len(g.blocks_) == len(ds.columns)
    assert sum(g.block_sizes_) == g.params_["out_b"].shape[0]


def test_sampling_gap_is_declared_not_hidden(fitted):
    """Poisson in the accounting, fixed-size batches in the loop. That gap is real and is
    reported rather than papered over -- the same rule that governs `audit_ceiling`."""
    _, _, acct, g = fitted
    assert "Poisson" in g.sampling_note_ and "fixed-size" in g.sampling_note_
    spec = [s for s in acct.spends if s.run_id == "dpvae_dpsgd"][0].mechanism
    assert "sampling_note" in spec.metadata
