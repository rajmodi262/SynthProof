"""Tests for per-subgroup downstream utility.

The metric's whole design rests on one claim: raw per-subgroup TSTR measures how hard the task
is for that group, not what synthesis did to it. So the tests that matter are the ones checking
the TRTR baseline is actually subtracted, and that a disparity present in the REAL data does
not get reported as an effect of synthesis.

Positive and negative controls, per the project's standing rules:
  * positive -- a release that destroys one group's signal must show a gap for that group;
  * negative -- a release identical to the real data must show ~no gap for any group.
"""

import numpy as np
import pandas as pd
import pytest

from synthproof.evaluate.fairness import (
    MIN_RELIABLE_TEST_ROWS,
    SubgroupUtilityEvaluator,
)


def _frame(n_major=600, n_minor=250, seed=0, minor_signal=True):
    """Two subgroups occupying SEPARATE regions of feature space, each with its own rule.

    Getting this fixture right took three attempts and each failure is worth recording, because
    they are the ways a subgroup metric can look fine while measuring nothing:

    1. Both groups `y = x > 0`. The majority's rule generalised to the minority, so destroying
       the minority's labels in the release cost nothing and the positive control could not
       fire — there was no subgroup effect to detect.
    2. Opposite rules (`x > 0` vs `x < 0`) in the SAME region. The subgroup column is not a
       model feature, so one model cannot serve two contradictory rules over the same inputs;
       the minority scored ~0.09 on REAL data and had no headroom left for synthesis to take.
    3. This version. The minority lives near `x ≈ 6`, so a tree can learn both rules by
       splitting on `x`, and the minority's region is a distinct thing a release can preserve
       or destroy. That is what makes a group-specific effect detectable by a group-blind model.

    `minor_signal=False` makes the minority label pure noise in the REAL data too — used to
    check that a disparity belonging to the task is not attributed to synthesis.
    """
    rng = np.random.default_rng(seed)
    rows = []
    for group, n in (("major", n_major), ("minor", n_minor)):
        if group == "major":
            x = rng.normal(0.0, 1.0, size=n)
            y = (x > 0).astype(int)
        else:
            x = rng.normal(6.0, 1.0, size=n)
            y = rng.integers(0, 2, size=n) if not minor_signal else (x > 6.0).astype(int)
        rows.append(pd.DataFrame({"x": x, "z": rng.normal(size=n), "grp": group, "income": y}))
    return pd.concat(rows, ignore_index=True).sample(frac=1.0, random_state=seed)


def _release(real_kwargs=None, seed=99):
    """A stand-in for a synthesiser's output: a FRESH draw from the same process.

    Deliberately not `real.copy()`. The evaluator holds out part of the real table and scores
    both models on it, so handing it a copy lets the TSTR model train on the very rows it is
    then tested against -- in-sample prediction reported as utility. That is exactly audit
    finding F8, where TRTR was measured in-sample and read 0.971 until it was fixed. An early
    version of these tests did it and produced a minority TSTR of 0.984 on labels that were
    pure noise.
    """
    return _frame(seed=seed, **(real_kwargs or {}))


def _evaluate(real, synth, seed=0):
    return SubgroupUtilityEvaluator(target_col="income", subgroup_col="grp", seed=seed).evaluate(
        real, synth
    )


# --------------------------------------------------------------- controls


def test_negative_control_a_faithful_release_shows_no_gap():
    """Release == real data. Any group showing a large gap means the metric is broken."""
    real = _frame()
    res = _evaluate(real, _release())
    assert len(res.reliable) == 2
    for s in res.reliable:
        assert abs(s.utility_gap) < 0.10, f"{s.subgroup}: gap {s.utility_gap:.3f} on a copy"


def test_positive_control_destroying_one_groups_signal_is_detected():
    """Shuffle the minority's labels in the release only. Its gap must exceed the majority's."""
    real = _frame()
    synth = _release()
    minor = synth["grp"] == "minor"
    synth.loc[minor, "income"] = np.random.default_rng(1).permutation(
        synth.loc[minor, "income"].to_numpy()
    )
    res = _evaluate(real, synth)
    by = {s.subgroup: s for s in res.subgroups}
    assert by["minor"].utility_gap > by["major"].utility_gap, res.to_dict()
    assert res.worst_served.subgroup == "minor"


# --------------------------------------------------------------- the design claim


def test_a_disparity_in_the_real_data_is_not_attributed_to_synthesis():
    """The reason this metric subtracts a per-group TRTR baseline.

    Here the minority label is pure noise in BOTH real and synthetic data, so a model trained
    on real data does badly on that group too. Raw TSTR would flag the group as harmed by
    synthesis; the gap must not, and `baseline_spread` must show where the disparity lives.
    """
    # n_minor=300 so the group clears MIN_RELIABLE_TEST_ROWS on any split. At the default 120
    # it lands near 24 held-out rows and is correctly flagged unreliable — which is the
    # threshold working, not a bug, but it makes this particular assertion depend on the split.
    real = _frame(n_minor=300, minor_signal=False)
    res = _evaluate(real, _release({"n_minor": 300, "minor_signal": False}))
    by = {s.subgroup: s for s in res.reliable}

    assert by["minor"].trtr_macro_f1 < by["major"].trtr_macro_f1, "task should be harder here"
    assert abs(by["minor"].utility_gap) < 0.10, "synthesis did nothing; gap must be ~0"
    assert res.baseline_spread > 0.10, "the control must expose the real-data disparity"


# --------------------------------------------------------------- honesty of the report


def test_a_tiny_subgroup_is_reported_but_flagged_unreliable():
    """Dropping small groups would silently remove exactly what the question is about."""
    real = _frame(n_minor=8)
    res = _evaluate(real, _release({"n_minor": 8}))
    by = {s.subgroup: s for s in res.subgroups}
    assert "minor" in by, "small group must still appear"
    assert not by["minor"].is_reliable
    assert by["minor"].num_test_rows < MIN_RELIABLE_TEST_ROWS


def test_every_subgroup_carries_the_n_behind_its_numbers():
    res = _evaluate(_frame(), _release())
    for s in res.subgroups:
        d = s.to_dict()
        assert "num_test_rows" in d and "population_share" in d
        assert "is_reliable" in d


def test_spread_is_none_rather_than_zero_when_it_cannot_be_computed():
    """One reliable group is not a spread, and 0.0 would read as 'perfectly equal'."""
    real = _frame(n_minor=5)
    res = _evaluate(real, _release({"n_minor": 5}))
    assert len(res.reliable) < 2
    assert res.gap_spread is None
    assert res.baseline_spread is None


# --------------------------------------------------------------- no silent fallbacks


@pytest.mark.parametrize("target,subgroup", [("nope", "grp"), ("income", "nope")])
def test_a_missing_column_raises_rather_than_returning_a_placeholder(target, subgroup):
    real = _frame()
    with pytest.raises(ValueError, match="not in real data"):
        SubgroupUtilityEvaluator(target_col=target, subgroup_col=subgroup).evaluate(
            real, _release()
        )


def test_a_release_missing_feature_columns_raises():
    real = _frame()
    synth = _release().drop(columns=["z"])
    with pytest.raises(ValueError, match="missing feature columns"):
        _evaluate(real, synth)


def test_the_subgroup_attribute_is_not_used_as_a_model_feature():
    """It partitions the evaluation; it must not inform the classifier.

    Verified behaviourally: relabelling the groups cannot change any score.
    """
    real = _frame()
    renamed = real.copy()
    renamed["grp"] = renamed["grp"].map({"major": "A", "minor": "B"})

    a = {s.subgroup: s.tstr_macro_f1 for s in _evaluate(real, _release()).subgroups}
    b = {s.subgroup: s.tstr_macro_f1 for s in _evaluate(renamed, _release()).subgroups}
    assert a["major"] == pytest.approx(b["A"])
    assert a["minor"] == pytest.approx(b["B"])
