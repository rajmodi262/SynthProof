"""Validation of the canary auditor against known standards.

An auditor that reports a null on every real mechanism is only trustworthy if it can be shown
to detect leakage when leakage is present, and to stay quiet when it is not. This project's
first self-audit found an auditor that returned 0.00 in every cell for three structural
reasons — and nobody noticed, because 0.00 was also the expected answer.

These tests are the standing guard against that. They are cheap, they run on every commit,
and if the auditor ever goes blind again they fail loudly rather than producing a confident
null.
"""

import pytest

from synthproof.audit.canary import CanaryAuditor
from synthproof.audit.detection_floor import (
    FloorCell,
    FloorResult,
    format_floor_table,
    measure_detection_floor,
)
from synthproof.data.dataset import TabularDataset
from synthproof.generators.leaky import LeakyGenerator, NotPrivateError


def _factory(leak, seed):
    return LeakyGenerator(seed=seed, leak_fraction=leak)


# ------------------------------------------------------------------ the control itself

def test_leaky_generator_reproduces_training_rows_verbatim():
    """At leak_fraction=1.0 the output IS the training table — the worst possible release."""
    ds = TabularDataset.create_synthetic_toy(num_rows=200)
    gen = LeakyGenerator(seed=0, leak_fraction=1.0)
    gen.fit(ds, None, None, 0.0)
    synth = gen.generate(200)

    real_rows = {tuple(r) for r in ds.df.to_numpy()}
    synth_rows = {tuple(r) for r in synth.to_numpy()}
    # Every synthetic row is a real one.
    assert synth_rows <= real_rows
    assert len(synth_rows) > 100, "sampling with replacement should still cover most rows"


def test_shuffled_control_preserves_marginals_but_no_records():
    """The interesting lower control: perfect marginals, zero real records.

    A fidelity metric is satisfied by this table. A privacy metric must not be — and if one
    is, it is measuring similarity rather than disclosure.
    """
    ds = TabularDataset.create_synthetic_toy(num_rows=400)
    gen = LeakyGenerator(seed=0, leak_fraction=0.0)
    gen.fit(ds, None, None, 0.0)
    synth = gen.generate(400)

    # Marginals survive: the multiset of values in each column is drawn from the real one.
    assert set(synth["category"]) <= set(ds.df["category"])
    assert synth["age"].min() >= ds.df["age"].min()
    assert synth["age"].max() <= ds.df["age"].max()

    # Joint structure does not: almost no row is a verbatim copy.
    real_rows = {tuple(r) for r in ds.df.to_numpy()}
    exact = sum(1 for r in synth.to_numpy() if tuple(r) in real_rows)
    assert exact < len(synth) * 0.5


def test_leak_fraction_is_validated():
    for bad in (-0.1, 1.5):
        with pytest.raises(ValueError, match="leak_fraction"):
            LeakyGenerator(leak_fraction=bad)


def test_control_refuses_to_report_an_epsilon():
    """A non-private generator must not be able to masquerade as a private one."""
    with pytest.raises(NotPrivateError, match="no privacy guarantee"):
        _ = LeakyGenerator().epsilon


def test_controls_are_not_reachable_as_real_mechanisms():
    """A non-private generator must never be selectable by the CLI, API, or a sweep."""
    from synthproof.frontier.experiment import MECHANISMS

    assert not any("leak" in k for k in MECHANISMS)
    assert not any("shuffle" in k for k in MECHANISMS)


def test_generate_before_fit_raises():
    with pytest.raises(RuntimeError, match="fitted"):
        LeakyGenerator().generate(10)


# ------------------------------------------------------------------ the positive control

def test_auditor_detects_a_verbatim_release():
    """THE POSITIVE CONTROL. If this fails, every null result in the project is worthless.

    A release that reproduces its training data verbatim is the easiest case an auditor will
    ever face. An auditor that cannot see it has no standing to report a null on a real
    mechanism.
    """
    ds = TabularDataset.create_synthetic_toy(num_rows=800)
    auditor = CanaryAuditor(num_canaries=50, seed=0)
    aug, canaries = auditor.plant_canaries(ds)

    gen = LeakyGenerator(seed=0, leak_fraction=1.0)
    gen.fit(aug, None, None, 0.0)
    res = auditor.audit(gen.generate(aug.num_rows), canaries)

    assert res.audited_eps > 0.0, "auditor is blind to a verbatim release"
    assert res.p_value < 0.05
    assert res.tpr > res.fpr


def test_auditor_does_not_fire_on_a_release_with_no_real_records():
    """THE NEGATIVE CONTROL. A shuffled table leaks no individual, so the audit must stay quiet.

    Without this, a detection could be an artefact of the scoring rather than of leakage.
    """
    ds = TabularDataset.create_synthetic_toy(num_rows=800)
    auditor = CanaryAuditor(num_canaries=50, seed=0)
    aug, canaries = auditor.plant_canaries(ds)

    gen = LeakyGenerator(seed=0, leak_fraction=0.0)
    gen.fit(aug, None, None, 0.0)
    res = auditor.audit(gen.generate(aug.num_rows), canaries)

    assert res.audited_eps == 0.0, (
        f"false positive: audited eps {res.audited_eps:.3f} on a table containing no "
        "real records"
    )


def test_detection_is_monotone_in_leakage():
    """More leakage must be easier to detect. A non-monotone instrument is not measuring."""
    ds = TabularDataset.create_synthetic_toy(num_rows=600)
    scores = []
    for leak in (0.0, 0.5, 1.0):
        auditor = CanaryAuditor(num_canaries=40, seed=1)
        aug, canaries = auditor.plant_canaries(ds)
        gen = LeakyGenerator(seed=1, leak_fraction=leak)
        gen.fit(aug, None, None, 0.0)
        scores.append(auditor.audit(gen.generate(aug.num_rows), canaries).tpr)

    assert scores[0] <= scores[1] <= scores[2], f"TPR not monotone in leakage: {scores}"


# ------------------------------------------------------------------ the sweep

def test_floor_sweep_finds_the_floor_for_a_verbatim_release():
    result = measure_detection_floor(
        TabularDataset.create_synthetic_toy(num_rows=500),
        generator_factory=_factory,
        canary_counts=(10, 50),
        leak_fractions=(0.0, 1.0),
        seeds=(0, 1, 2),
    )

    assert result.floor_for(1.0) is not None, "no floor found for a verbatim release"
    assert result.floor_for(0.0) is None, "false positive on the shuffled control"
    assert len(result.cells) == 4


def test_floor_requires_a_majority_of_seeds():
    """One lucky seed is not a detection floor."""
    lucky = FloorCell(leak_fraction=0.1, num_canaries=10, seeds=3, detection_rate=1 / 3,
                      mean_audited_eps=0.1, max_audited_eps=0.3, mean_p_value=0.2,
                      mean_tpr=0.5, mean_fpr=0.4)
    solid = FloorCell(leak_fraction=0.1, num_canaries=50, seeds=3, detection_rate=1.0,
                      mean_audited_eps=0.5, max_audited_eps=0.6, mean_p_value=0.01,
                      mean_tpr=0.9, mean_fpr=0.2)

    assert lucky.detected is False
    assert solid.detected is True
    assert FloorResult(cells=[lucky, solid]).floor_for(0.1) == 50


def test_floor_table_renders_and_reports_undetected_levels():
    result = FloorResult(cells=[
        FloorCell(0.0, 10, 3, 0.0, 0.0, 0.0, 0.6, 0.5, 0.5),
        FloorCell(1.0, 10, 3, 1.0, 2.0, 2.4, 0.001, 1.0, 0.1),
    ])
    text = format_floor_table(result)
    assert "detection floor" in text
    assert "not detected" in text      # the 0.0 row
    assert "10" in text
