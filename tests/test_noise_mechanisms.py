"""The real-valued query release and the exponential mechanism, pinned to their formulas.

Mutation testing (results/mutation/) found these three functions reached by NO test in the
accounting selection: 74 mutants of `noisy_real_query`, `exponential_mechanism` and
`grid_sensitivity` would have shipped unnoticed. Each test here recomputes the output from the
documented formula, so a changed constant, operator or rounding fails it.
"""

import math

import numpy as np
import pytest

from synthproof.accounting.noise import (
    RESOLUTION,
    em_noise_scale,
    exponential_mechanism,
    grid_sensitivity,
    noisy_real_query,
    sample_discrete_gaussian,
    sample_discrete_laplace,
)

# ------------------------------------------------------------------ the grid


def test_the_grid_has_a_thousand_steps_and_sensitivity_one_more():
    # Rounding moves each neighbour by at most half a step, so the integer query can differ by
    # RESOLUTION + 1, never RESOLUTION.
    assert RESOLUTION == 1000
    assert grid_sensitivity() == 1001


# ------------------------------------------------------------------ noisy_real_query


@pytest.mark.parametrize("name, sampler", [("gaussian", "g"), ("laplace", "l")])
@pytest.mark.parametrize("value, sens, mult", [(3.14159, 2.0, 1.5), (-7.25, 0.5, 4.0)])
def test_the_release_is_the_rounded_value_plus_grid_noise(name, sampler, value, sens, mult):
    g = sens / RESOLUTION
    scale = mult * 1001
    z = int(
        sample_discrete_gaussian(sigma=scale, size=1, seed=11)[0]
        if sampler == "g"
        else sample_discrete_laplace(scale=scale, size=1, seed=11)[0]
    )
    expected = g * (round(value / g) + z)
    assert noisy_real_query(value, sens, mult, name, seed=11) == pytest.approx(expected, abs=1e-12)


def test_the_release_lies_on_the_grid_so_no_fractional_part_survives():
    g = 0.37 / RESOLUTION
    for seed in range(20):
        out = noisy_real_query(12.3456789, 0.37, 2.0, "gaussian", seed=seed)
        assert abs(out / g - round(out / g)) < 1e-6


def test_neighbouring_values_share_a_support():
    # The defect this function fixed: integer noise on a raw real kept frac(value) exactly, so
    # neighbours had disjoint supports. On the grid they differ only by whole steps.
    g = 1.0 / RESOLUTION
    a = {round(noisy_real_query(5.0001, 1.0, 1.0, "laplace", seed=s) / g) for s in range(200)}
    b = {round(noisy_real_query(5.0004, 1.0, 1.0, "laplace", seed=s) / g) for s in range(200)}
    assert a & b


@pytest.mark.parametrize("bad", [0.0, -1.0])
def test_a_non_positive_sensitivity_is_refused(bad):
    with pytest.raises(ValueError, match="sensitivity must be positive"):
        noisy_real_query(1.0, bad, 1.0, "gaussian", seed=0)


def test_an_unknown_mechanism_is_refused():
    with pytest.raises(ValueError, match="unknown mechanism"):
        noisy_real_query(1.0, 1.0, 1.0, "cauchy", seed=0)


# ------------------------------------------------------------------ exponential mechanism


def _expected_choice(scores, eps, sens, seed):
    q = np.asarray(scores, dtype=float)
    p = np.exp((eps / (2.0 * sens)) * (q - q.max()))
    return int(np.random.default_rng(seed).choice(q.size, p=p / p.sum()))


@pytest.mark.parametrize("seed", range(8))
def test_the_choice_is_the_documented_softmax_draw(seed):
    scores, eps, sens = [0.0, 1.5, 3.0, 2.2, -1.0], 1.3, 0.7
    assert exponential_mechanism(scores, eps, sens, seed=seed) == _expected_choice(
        scores, eps, sens, seed
    )


def test_the_selection_probabilities_follow_exp_eps_q_over_two_delta():
    scores, eps, sens, n = [0.0, 1.0], 2.0, 1.0, 20_000
    picks = sum(exponential_mechanism(scores, eps, sens, seed=s) for s in range(n))
    p1 = math.exp(eps * 1.0 / (2 * sens)) / (1 + math.exp(eps * 1.0 / (2 * sens)))
    assert picks / n == pytest.approx(p1, abs=4 * math.sqrt(p1 * (1 - p1) / n))


def test_huge_scores_do_not_overflow():
    # Shifting by the maximum is what keeps exp() finite; shifting by anything smaller overflows.
    assert exponential_mechanism([1000.0, 0.0], 10.0, 1.0, seed=0) == 0


@pytest.mark.parametrize(
    "scores, eps, sens, match",
    [
        ([], 1.0, 1.0, "at least one candidate"),
        ([1.0], 0.0, 1.0, "epsilon > 0"),
        ([1.0], -1.0, 1.0, "epsilon > 0"),
        ([1.0], 1.0, 0.0, "sensitivity > 0"),
        ([1.0], 1.0, -2.0, "sensitivity > 0"),
    ],
)
def test_invalid_inputs_are_refused(scores, eps, sens, match):
    with pytest.raises(ValueError, match=match):
        exponential_mechanism(scores, eps, sens, seed=0)


def test_the_em_charge_scale_is_two_delta_over_epsilon():
    assert em_noise_scale(0.5, 3.0) == pytest.approx(12.0)
