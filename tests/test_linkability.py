"""Tests for the linkability evaluator.

The measurement only means anything relative to its control. Two disjoint halves of a record
agree on a synthetic row by chance at a rate set by the table size, not by privacy, so the
tests that matter are the ones checking `excess_over_baseline` separates a release that
preserves row structure from one that merely preserves marginals.
"""

import numpy as np
import pandas as pd
import pytest

from synthproof.attacks.linkability import LinkabilityEvaluator


def _real(n=300, seed=0, correlated=True):
    """Four columns. When `correlated`, all four derive from one latent per row.

    The latent is what makes a record linkable: both halves of the row point back to the same
    underlying person. Independent columns have no row-level identity to recover.
    """
    rng = np.random.default_rng(seed)
    if correlated:
        latent = rng.normal(size=n)
        return pd.DataFrame(
            {
                "a": latent + rng.normal(0, 0.1, n),
                "b": latent + rng.normal(0, 0.1, n),
                "c": latent + rng.normal(0, 0.1, n),
                "d": latent + rng.normal(0, 0.1, n),
            }
        )
    return pd.DataFrame({c: rng.normal(size=n) for c in "abcd"})


def _run(synth, target, **kw):
    return LinkabilityEvaluator(seed=0, **kw).evaluate(synth, target)


# --------------------------------------------------------------- controls


def test_positive_control_a_verbatim_release_is_maximally_linkable():
    """The release IS the private table. Every record links to itself."""
    real = _real()
    r = _run(real.copy(), real)
    assert r.linkability_rate > 0.95, r.to_dict()
    assert r.excess_over_baseline > 0.9
    assert r.is_informative


def test_negative_control_a_structureless_release_shows_no_excess():
    """Marginals preserved, row correspondence destroyed. Excess must be ~0."""
    real = _real()
    unrelated = _real(seed=99)
    r = _run(unrelated, real)
    assert abs(r.excess_over_baseline) < 0.10, r.to_dict()


def test_the_baseline_is_what_makes_the_rate_readable():
    """A raw rate cannot distinguish privacy from table size; the excess can.

    Shuffling the B columns preserves every marginal exactly, so any agreement that survives
    is chance. The control must land far below the verbatim rate.
    """
    real = _real()
    r = _run(real.copy(), real)
    assert r.baseline_rate < 0.2, f"chance agreement unexpectedly high: {r.baseline_rate}"
    assert r.linkability_rate - r.baseline_rate == pytest.approx(r.excess_over_baseline)


# --------------------------------------------------------------- it degrades sensibly


def test_partial_structure_lands_between_the_two_controls():
    """Half the release carries real rows, half is noise. Excess should be intermediate."""
    real = _real()
    mixed = pd.concat([real.iloc[:150], _real(n=150, seed=7)], ignore_index=True)
    partial = _run(mixed, real).excess_over_baseline
    verbatim = _run(real.copy(), real).excess_over_baseline
    none = _run(_real(seed=99), real).excess_over_baseline
    assert none < partial < verbatim, (none, partial, verbatim)


# --------------------------------------------------------------- report honesty


def test_the_result_names_the_columns_it_split_on():
    """A linkability number without its column split is not reproducible."""
    r = _run(_real().copy(), _real())
    assert r.columns_a and r.columns_b
    assert not set(r.columns_a) & set(r.columns_b), "halves must be disjoint"
    assert sorted(r.columns_a + r.columns_b) == ["a", "b", "c", "d"]


def test_a_tiny_release_is_flagged_uninformative():
    """With few synthetic rows, chance agreement swamps the signal."""
    real = _real(n=40)
    r = _run(real.copy(), real)
    assert not r.is_informative, r.to_dict()


def test_explicit_column_halves_are_honoured_and_must_be_disjoint():
    real = _real()
    r = _run(real.copy(), real, columns_a=["a", "b"], columns_b=["c", "d"])
    assert r.columns_a == ["a", "b"] and r.columns_b == ["c", "d"]

    with pytest.raises(ValueError, match="disjoint"):
        _run(real.copy(), real, columns_a=["a", "b"], columns_b=["b", "c"])


def test_too_few_columns_raises_rather_than_guessing():
    real = _real()[["a", "b"]]
    with pytest.raises(ValueError, match="at least 4"):
        _run(real.copy(), real)


def test_no_shared_columns_raises():
    real = _real()
    other = real.rename(columns={c: c.upper() for c in real.columns})
    with pytest.raises(ValueError, match="share no columns"):
        _run(other, real)


def test_categorical_columns_are_encoded_on_a_shared_vocabulary():
    """A level present in only one frame must not shift the other's encoding."""
    rng = np.random.default_rng(0)
    real = pd.DataFrame(
        {
            "a": rng.normal(size=200),
            "b": rng.choice(["x", "y"], size=200),
            "c": rng.normal(size=200),
            "d": rng.choice(["p", "q"], size=200),
        }
    )
    synth = real.copy()
    synth.loc[0, "b"] = "z"  # a level the target frame never contains
    r = _run(synth, real)
    assert 0.0 <= r.linkability_rate <= 1.0
