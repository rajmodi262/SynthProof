"""Tests for the fixed-workload control arm.

This mechanism's entire scientific value is that it is IDENTICAL to AIM except for selection.
Every test here defends one half of that sentence: the tests in the first block assert it
really does not select, and the tests in the second assert it really is otherwise the same.
If either half stops holding, the confound experiment it supports becomes uninterpretable.
"""

import pytest

from synthproof.accounting.accountant import Accountant
from synthproof.data.dataset import TabularDataset
from synthproof.data.profiler import DPDomainProfiler
from synthproof.generators.aim import AIMGenerator, mbi_available

pytestmark = pytest.mark.skipif(
    not mbi_available(), reason="private-PGM (mbi) not installed; needs Python >= 3.11"
)

if mbi_available():
    from synthproof.generators.fixed_workload import FixedWorkloadGenerator


def _fit(cls, eps=2.0, seed=0, **kw):
    ds = TabularDataset.create_synthetic_toy(num_rows=1200, seed=0)
    acct = Accountant(budget_eps=6.0, budget_delta=1e-5)
    prof = DPDomainProfiler(acct, eps_budget=0.2).profile(ds)
    g = cls(seed=seed, **kw)
    g.fit(ds, prof, acct, target_eps=eps)
    return ds, acct, g


# --------------------------------------------------------------------------- it does not select


def test_no_selection_is_ever_charged():
    """THE claim. AIM pays for report-noisy-max on every round; this must pay for none."""
    _, acct, _ = _fit(FixedWorkloadGenerator)
    selection = [s for s in acct.spends if "select" in (s.run_id or "")]
    assert selection == [], f"a control that selects is not a control: {selection}"


def test_aim_does_charge_for_selection():
    """POSITIVE CONTROL for the test above. If AIM stopped charging for selection the
    previous assertion would pass vacuously and prove nothing."""
    _, acct, _ = _fit(AIMGenerator)
    selection = [s for s in acct.spends if "select" in (s.run_id or "")]
    assert selection, "AIM no longer charges for selection; the control test is now vacuous"


def test_the_workload_does_not_depend_on_the_data():
    """Two different datasets, same public workload seed -> the same cliques.

    This is the property that makes the workload free. If it varied with the data it would be
    an uncharged query, and every epsilon this mechanism reports would be a false statement.
    """
    workloads = []
    for data_seed in (0, 99):
        ds = TabularDataset.create_synthetic_toy(num_rows=1200, seed=data_seed)
        acct = Accountant(budget_eps=6.0, budget_delta=1e-5)
        prof = DPDomainProfiler(acct, eps_budget=0.2).profile(ds)
        g = FixedWorkloadGenerator(seed=0, workload_seed=777)
        g.fit(ds, prof, acct, target_eps=2.0)
        workloads.append(sorted(g.workload_))
    assert workloads[0] == workloads[1], f"workload varied with the data: {workloads}"


def test_an_explicit_workload_is_honoured():
    ds = TabularDataset.create_synthetic_toy(num_rows=1200, seed=0)
    acct = Accountant(budget_eps=6.0, budget_delta=1e-5)
    prof = DPDomainProfiler(acct, eps_budget=0.2).profile(ds)
    g = FixedWorkloadGenerator(seed=0, workload=[("age", "income")])
    g.fit(ds, prof, acct, target_eps=2.0)
    assert g.workload_ == [("age", "income")]


def test_a_workload_outside_the_schema_is_refused():
    """NEGATIVE CONTROL. Silently dropping an unknown pair would make the arm measure
    something other than what the experiment recorded."""
    ds = TabularDataset.create_synthetic_toy(num_rows=600, seed=0)
    acct = Accountant(budget_eps=6.0, budget_delta=1e-5)
    prof = DPDomainProfiler(acct, eps_budget=0.2).profile(ds)
    g = FixedWorkloadGenerator(seed=0, workload=[("age", "not_a_column")])
    with pytest.raises(ValueError, match="not in the schema"):
        g.fit(ds, prof, acct, target_eps=2.0)


# --------------------------------------------------------------------------- otherwise identical


def test_it_uses_aims_engine():
    """Shares AIM's inference and sampler, which is what removes the 'different model class'
    objection that applies to the DP-VAE control."""
    assert issubclass(FixedWorkloadGenerator, AIMGenerator)
    assert FixedWorkloadGenerator.generate is AIMGenerator.generate


def test_it_measures_one_way_marginals_for_every_column():
    ds, acct, g = _fit(FixedWorkloadGenerator)
    one_way = [c for c in g.measured_cliques_ if len(c) == 1]
    assert len(one_way) == len(ds.columns)


def test_it_respects_the_model_size_bound():
    """A refused clique is recorded, never silently dropped -- same rule as AIM."""
    _, _, g = _fit(FixedWorkloadGenerator)
    assert isinstance(g.skipped_cliques_, list)
    for cl in g.skipped_cliques_:
        assert cl not in g.workload_


def test_it_never_overspends():
    _, acct, _ = _fit(FixedWorkloadGenerator)
    assert acct.total() <= acct.budget.epsilon


def test_output_matches_the_schema():
    ds, _, g = _fit(FixedWorkloadGenerator)
    syn = g.generate(400)
    assert list(syn.columns) == list(ds.columns)
    assert len(syn) == 400


def test_all_budget_goes_to_measurement():
    """AIM diverts part of the budget to selection; this arm spends none there. Every charge
    it makes must therefore be a measurement, one per marginal it actually measured."""
    ds, acct, g = _fit(FixedWorkloadGenerator)
    charges = [s.run_id for s in acct.spends if (s.run_id or "").startswith("fixedwl_")]
    assert len(charges) == len(ds.columns) + len(g.workload_)
    assert all("select" not in c for c in charges)
    assert g.meas_sigma_ > 0


def test_sampling_is_reproducible_from_the_seed():
    """Formerly `test_sampling_is_NOT_reproducible_and_that_is_recorded`, and it asked for this.

    That test pinned a known limitation: `mbi`'s `synthetic_data` drew from unseeded randomness,
    so `generate` twice on one fitted model returned different tables and no AIM-family result
    could be pinned in the manifest. Its docstring said that if the sampler could be seeded, the
    right response was to seed it and turn the assertion into equality -- not to delete it.

    It could be: the sampler draws from NumPy's GLOBAL generator, so `AIMGenerator.generate` now
    seeds that locally and restores the caller's state (2026-09-14, alongside the D1 fix).
    """
    _, _, g = _fit(FixedWorkloadGenerator, seed=3)
    assert g.generate(50).equals(g.generate(50))


def test_a_fresh_fit_and_sample_from_the_same_seed_is_bit_identical():
    """The claim that matters for the manifest: re-running a release reproduces it exactly."""
    _, _, a = _fit(FixedWorkloadGenerator, seed=3)
    _, _, b = _fit(FixedWorkloadGenerator, seed=3)
    assert a.generate(80).equals(b.generate(80))


def test_seeding_the_sampler_does_not_disturb_the_callers_global_rng():
    """Seeding NumPy's global generator must not leak into code that relies on it elsewhere."""
    import numpy as np

    _, _, g = _fit(FixedWorkloadGenerator, seed=3)
    np.random.seed(12345)
    expected = np.random.rand(3)
    np.random.seed(12345)
    g.generate(20)
    assert np.array_equal(np.random.rand(3), expected)


def test_the_fitted_workload_IS_reproducible():
    """What IS deterministic: which marginals get measured. The sampler is not, the
    measurement plan is, and the confound experiment depends only on the latter."""
    _, _, a = _fit(FixedWorkloadGenerator, seed=3)
    _, _, b = _fit(FixedWorkloadGenerator, seed=3)
    assert a.workload_ == b.workload_
