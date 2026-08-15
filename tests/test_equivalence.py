"""Tests for the H2 statistical reframe: multiplicity, equivalence, and detectability.

These decide whether a null is reported as "we found nothing" or as "the effect is bounded
below X and here is what we could have detected". The second is a scientific claim; the first
is not, and getting the machinery wrong turns one into the other.
"""

import numpy as np
import pytest

from synthproof.audit.equivalence import (
    H2Analysis,
    correct_multiplicity,
    describe_detectability,
    format_h2_table,
    minimum_detectable_epsilon,
)

# Aliased: pytest collects any module-level name starting with `test_` as a test case, and
# would otherwise try to run the library function itself.
from synthproof.audit.equivalence import test_equivalence as tost_equivalence

# ------------------------------------------------------------------ multiplicity

def test_bonferroni_is_never_less_conservative_than_bh():
    """FWER control must be at least as strict as FDR control, always."""
    p = [0.001, 0.01, 0.03, 0.2, 0.5, 0.9]
    r = correct_multiplicity([f"t{i}" for i in range(len(p))], p)
    assert all(b >= h - 1e-12 for b, h in zip(r.bonferroni_p, r.bh_p))
    assert sum(r.bonferroni_reject) <= sum(r.bh_reject)


def test_method_is_passed_explicitly_not_left_to_the_default():
    """`multipletests` defaults to Holm-Sidak. Relying on the default would silently apply a
    third procedure that neither 'BH' nor 'Bonferroni' describes."""
    import inspect

    from synthproof.audit import equivalence
    src = inspect.getsource(equivalence.correct_multiplicity)
    assert "method=\"fdr_bh\"" in src
    assert "method=\"bonferroni\"" in src


def test_expected_false_positives_is_reported():
    """With 20 tests at alpha=0.05, one false positive is expected. Saying so is what stops a
    single raw p<0.05 being read as a finding."""
    r = correct_multiplicity([f"t{i}" for i in range(20)], [0.5] * 20)
    assert r.num_tests == 20
    assert r.expected_false_positives == pytest.approx(1.0)
    assert "chance alone predicts 1.0" in r.summary()


def test_a_family_of_nulls_survives_correction_trivially():
    r = correct_multiplicity([f"t{i}" for i in range(14)], [0.2] * 14)
    assert sum(r.bh_reject) == 0
    assert sum(r.bonferroni_reject) == 0


def test_a_genuine_effect_survives_bh():
    p = [1e-6] + [0.6] * 13
    r = correct_multiplicity([f"t{i}" for i in range(14)], p)
    assert r.bh_reject[0] is True


def test_empty_family_does_not_crash():
    r = correct_multiplicity([], [])
    assert r.num_tests == 0


# ------------------------------------------------------------------ equivalence

def test_two_identical_samples_are_equivalent():
    """The basic sanity check: no difference must register as equivalent."""
    rng = np.random.default_rng(0)
    a = rng.normal(0, 1, 400)
    b = rng.normal(0, 1, 400)
    res = tost_equivalence("same", a, b, bound=0.5, justification="test")
    assert res.equivalent
    assert "positive claim" in res.interpretation()


def test_a_large_true_difference_is_not_equivalent():
    rng = np.random.default_rng(0)
    a = rng.normal(2.0, 1, 400)
    b = rng.normal(0.0, 1, 400)
    res = tost_equivalence("different", a, b, bound=0.5, justification="test")
    assert not res.equivalent
    assert "underpowered" in res.interpretation() or "NOT shown" in res.interpretation()


def test_a_small_sample_cannot_claim_equivalence():
    """Equivalence needs power too. A tiny sample must not license a positive claim."""
    rng = np.random.default_rng(0)
    res = tost_equivalence("tiny", rng.normal(0, 1, 4), rng.normal(0, 1, 4),
                           bound=0.05, justification="test")
    assert not res.equivalent


def test_the_bound_justification_travels_with_the_result():
    """A margin without its reasoning invites post-hoc tuning."""
    res = tost_equivalence("x", [0.0] * 30, [0.0] * 30, bound=0.1,
                           justification="from the measured detection floor")
    assert "measured detection floor" in res.bound_justification


def test_degenerate_input_returns_not_equivalent_rather_than_crashing():
    res = tost_equivalence("empty", [], [1.0, 2.0], bound=0.1, justification="j")
    assert not res.equivalent


# ------------------------------------------------------------------ detectability

def test_minimum_detectable_epsilon_needs_better_than_chance():
    """The MDE is the instrument's floor; reaching it must require beating chance."""
    eps, acc = minimum_detectable_epsilon(80)
    assert eps > 0.0
    assert acc > 0.5, "an MDE reachable at chance accuracy would be meaningless"


def test_more_guesses_lower_the_accuracy_needed_to_detect():
    """Statistical power: a bigger sample detects a smaller excursion from chance."""
    _, acc_small = minimum_detectable_epsilon(40)
    _, acc_large = minimum_detectable_epsilon(800)
    assert acc_large < acc_small


def test_detectability_places_the_observation_inside_the_instrument_range():
    """The number that makes the H2 null interpretable: how much of the range was used."""
    rep = describe_detectability(num_canaries=80, observed_epsilons=[0.036, 0.0],
                                 observed_accuracies=[0.562, 0.5])
    assert rep.ceiling > rep.observed_max_epsilon
    assert 0.0 < rep.fraction_of_range_used < 0.05, "observed should be a sliver of the range"
    text = rep.interpretation()
    assert "bounds the effect" in text
    assert "does not establish its absence" in text


def test_the_adversary_fell_short_of_the_detection_threshold():
    """The precise reason H2 is null, as a checkable assertion.

    At m=80 the instrument needs adversary accuracy ~0.60 to certify anything; the best
    observed subgroup accuracy was 0.562. The null is a power result, not an absence result.
    """
    _, needed = minimum_detectable_epsilon(80)
    observed_best = 0.562
    assert observed_best < needed, (
        "the observed adversary now clears the detection threshold — H2 must be re-read"
    )


# ------------------------------------------------------------------ reporting

def test_verdict_states_both_what_is_and_is_not_established():
    m = correct_multiplicity([f"t{i}" for i in range(14)], [0.3] * 14)
    d = describe_detectability(80, [0.036], [0.562])
    v = H2Analysis(multiplicity=m, equivalence=[], detectability=d).verdict()
    assert "NOT supported" in v
    assert "does not establish its absence" in v


def test_table_renders_every_comparison():
    m = correct_multiplicity(["a", "b"], [0.2, 0.4])
    text = format_h2_table(H2Analysis(multiplicity=m))
    assert "a" in text and "b" in text
    assert "BH p" in text
