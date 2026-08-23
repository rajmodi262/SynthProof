"""Property-based and differential tests for the DP accounting layer.

The unit tests elsewhere check specific inputs. These check the *laws* the accounting must
obey for every input, and cross-check the composed epsilon against a second, independent
implementation.

Why this matters more here than in most code: a privacy accountant that is merely
self-consistent proves nothing. The first version of this project hand-rolled its RDP
composition and produced numbers that looked entirely reasonable while under-reporting epsilon
by roughly 2x at q = 0.01. Nothing in the code looked wrong, and no shape-checking test would
have caught it. An accountant validated against an independent implementation is *defensible*
rather than *asserted*.
"""

import numpy as np
import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from synthproof.accounting.accountant import Accountant
from synthproof.accounting.calibration import calibrate_noise_scale, epsilon_for_noise_scale
from synthproof.accounting.noise import sample_discrete_gaussian, sample_discrete_laplace
from synthproof.accounting.types import BudgetExceededError, MechanismSpec

# Composition is not cheap, so property tests get a modest example budget and a relaxed
# deadline rather than hypothesis's defaults.
SLOW = settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.too_slow])

scales = st.floats(min_value=0.5, max_value=50.0, allow_nan=False, allow_infinity=False)
steps = st.integers(min_value=1, max_value=30)
targets = st.floats(min_value=0.1, max_value=16.0, allow_nan=False, allow_infinity=False)
mechanisms = st.sampled_from(["gaussian", "laplace"])


# ------------------------------------------------------------------ composition laws


@given(scale=scales, k=steps, name=mechanisms)
@SLOW
def test_epsilon_is_monotone_decreasing_in_noise(scale, k, name):
    """More noise can never cost more privacy. The single most basic law here."""
    less_noisy = epsilon_for_noise_scale(scale, 1e-5, name, 1.0, k)
    more_noisy = epsilon_for_noise_scale(scale * 2.0, 1e-5, name, 1.0, k)
    assert more_noisy <= less_noisy + 1e-9


@given(scale=scales, k=steps, name=mechanisms)
@SLOW
def test_epsilon_is_monotone_increasing_in_composition(scale, k, name):
    """Composing more mechanisms can never reduce the total privacy loss."""
    fewer = epsilon_for_noise_scale(scale, 1e-5, name, 1.0, k)
    more = epsilon_for_noise_scale(scale, 1e-5, name, 1.0, k + 1)
    assert more >= fewer - 1e-9


@given(scale=scales, k=steps, name=mechanisms)
@SLOW
def test_composition_is_sublinear(scale, k, name):
    """k compositions must cost no more than k times one — that is the point of RDP.

    A linear result would mean the advanced composition is not being applied at all.
    """
    assume(k >= 2)
    one = epsilon_for_noise_scale(scale, 1e-5, name, 1.0, 1)
    many = epsilon_for_noise_scale(scale, 1e-5, name, 1.0, k)
    assert many <= k * one + 1e-9


@given(scale=scales, name=mechanisms)
@SLOW
def test_epsilon_grows_as_delta_shrinks(scale, name):
    """A stricter delta must cost more epsilon, never less."""
    loose = epsilon_for_noise_scale(scale, 1e-4, name, 1.0, 5)
    strict = epsilon_for_noise_scale(scale, 1e-7, name, 1.0, 5)
    assert strict >= loose - 1e-9


def test_zero_noise_is_infinite_epsilon():
    """Zero noise is not "a very small privacy loss" — it is none at all.

    Modelling it as a finite epsilon is how a system ends up charging budget for a mechanism
    that adds no noise, which is a false statement rather than a loose bound.
    """
    acc = Accountant(budget_eps=float("inf"))
    spec = MechanismSpec(name="gaussian", sensitivity=1.0, noise_scale=0.0)
    assert acc.dry_run(spec) == float("inf")


# ------------------------------------------------------------------ budget enforcement


@given(budget=st.floats(min_value=0.1, max_value=8.0), k=steps)
@SLOW
def test_charge_never_exceeds_the_budget(budget, k):
    """The invariant the whole budget interface exists to maintain."""
    acc = Accountant(budget_eps=budget, budget_delta=1e-5)
    spec = MechanismSpec(name="gaussian", sensitivity=1.0, noise_scale=1.0)

    for _ in range(k):
        try:
            acc.charge(spec)
        except BudgetExceededError:
            break
        assert acc.total() <= budget + 1e-9
    assert acc.total() <= budget + 1e-9
    assert acc.remaining() >= 0.0


@given(budget=st.floats(min_value=0.5, max_value=8.0))
@SLOW
def test_a_refused_charge_leaves_the_accountant_untouched(budget):
    """A rejected charge must not partially spend. Otherwise a caught exception silently
    erodes the budget."""
    acc = Accountant(budget_eps=budget, budget_delta=1e-5)
    # A deliberately cheap opening charge, so the accountant is in a non-empty state without
    # the setup itself exhausting the smallest budget hypothesis will generate.
    acc.charge(MechanismSpec("gaussian", 1.0, 60.0))
    before, spends_before = acc.total(), len(acc.spends)
    assert before < budget, "test setup must not exhaust the budget it is testing"

    with pytest.raises(BudgetExceededError):
        acc.charge(MechanismSpec("gaussian", sensitivity=100.0, noise_scale=0.01))

    assert acc.total() == before
    assert len(acc.spends) == spends_before


@given(k=st.integers(min_value=1, max_value=8))
@SLOW
def test_snapshot_restore_round_trips(k):
    """Speculative execution must be exactly reversible."""
    acc = Accountant(budget_eps=1e6, budget_delta=1e-5)
    spec = MechanismSpec("gaussian", 1.0, 2.0)
    acc.charge(spec)

    snap = acc.snapshot()
    before, n_before = acc.total(), len(acc.spends)
    for _ in range(k):
        acc.charge(spec)
    assert acc.total() > before

    acc.restore(snap)
    assert acc.total() == pytest.approx(before)
    assert len(acc.spends) == n_before


# ------------------------------------------------------------------ calibration


@given(target=targets, k=steps, name=mechanisms)
@SLOW
def test_calibration_never_overspends(target, k, name):
    """The headline claim, as a law rather than a fixed grid.

    CI checks 24 hand-picked configurations; this checks arbitrary ones. Calibration must
    return the conservative side of the bracket, so the achieved epsilon is never above what
    was asked for.
    """
    scale = calibrate_noise_scale(target, 1e-5, name, 1.0, k)
    achieved = epsilon_for_noise_scale(scale, 1e-5, name, 1.0, k)
    # No slack. The bisection returns the conservative end of a bracket that converges to
    # 1e-4 relative width, so the achieved epsilon is genuinely at or below target -- the
    # worst ratio over 56 hand-checked configurations is 0.99999839. The previous 0.1%
    # tolerance was wider than the bracket itself, so returning the OPTIMISTIC end of the
    # bracket still passed; a mutation probe caught exactly that.
    assert achieved <= target, f"overspend: asked {target}, got {achieved}"


@given(target=targets, k=steps, name=mechanisms)
@SLOW
def test_calibration_is_not_wastefully_loose(target, k, name):
    """Under-spending is safe but leaves utility on the table; it must stay bounded."""
    scale = calibrate_noise_scale(target, 1e-5, name, 1.0, k)
    achieved = epsilon_for_noise_scale(scale, 1e-5, name, 1.0, k)
    assert achieved >= target * 0.98, f"wasteful: asked {target}, got only {achieved}"


@given(a=targets, b=targets, k=steps)
@SLOW
def test_a_larger_budget_calibrates_to_less_noise(a, b, k):
    """More budget must buy less noise; the inverse must respect the ordering."""
    assume(abs(a - b) > 0.05)
    lo, hi = min(a, b), max(a, b)
    assert (
        calibrate_noise_scale(hi, 1e-5, "gaussian", 1.0, k)
        <= calibrate_noise_scale(lo, 1e-5, "gaussian", 1.0, k) + 1e-9
    )


# ------------------------------------------------------------------ noise samplers


@given(sigma=st.floats(min_value=0.5, max_value=20.0), seed=st.integers(0, 2**31 - 1))
@SLOW
def test_discrete_gaussian_is_centred_and_integral(sigma, seed):
    samples = sample_discrete_gaussian(sigma=sigma, size=2000, seed=seed)
    assert samples.dtype == np.int64
    # Standard error of the mean is sigma/sqrt(n); 5 SE is a very loose bound.
    assert abs(float(np.mean(samples))) < 5.0 * sigma / np.sqrt(2000)


@given(scale=st.floats(min_value=0.5, max_value=20.0), seed=st.integers(0, 2**31 - 1))
@SLOW
def test_discrete_laplace_is_centred_and_integral(scale, seed):
    samples = sample_discrete_laplace(scale=scale, size=2000, seed=seed)
    assert samples.dtype == np.int64
    sd = scale * np.sqrt(2.0)
    assert abs(float(np.mean(samples))) < 5.0 * sd / np.sqrt(2000)


@given(sigma=st.floats(min_value=0.5, max_value=10.0))
@SLOW
def test_noise_spread_grows_with_sigma(sigma):
    a = sample_discrete_gaussian(sigma=sigma, size=4000, seed=7)
    b = sample_discrete_gaussian(sigma=sigma * 3.0, size=4000, seed=7)
    assert float(np.std(b)) > float(np.std(a))


# ------------------------------------------------------------------ differential test

autodp = pytest.importorskip("autodp", reason="autodp is optional; used to cross-check")


@pytest.mark.parametrize("sigma", [1.0, 2.0, 5.0, 10.0])
@pytest.mark.parametrize("k", [1, 5, 20])
def test_epsilon_agrees_with_autodp(sigma, k):
    """Cross-check composition against a second, independent implementation.

    `dp_accounting` (Google) and `autodp` (Wang et al.) implement the same theory with
    different machinery. Agreement between them is meaningful evidence that our composed
    epsilon is correct; agreement of our code with itself is not.

    Measured agreement across this grid is within 0.05%.
    """
    from autodp.mechanism_zoo import GaussianMechanism
    from autodp.transformer_zoo import Composition

    ours = epsilon_for_noise_scale(sigma, 1e-5, "gaussian", 1.0, k)
    theirs = Composition()([GaussianMechanism(sigma=sigma, name="g")], [k]).get_approxDP(1e-5)

    assert ours == pytest.approx(
        theirs, rel=0.01
    ), f"sigma={sigma} k={k}: ours={ours:.6f} autodp={theirs:.6f}"


@pytest.mark.parametrize("sigma", [1.0, 2.0, 5.0])
@pytest.mark.parametrize("k", [1, 5, 20])
def test_we_never_under_report_epsilon_relative_to_autodp(sigma, k):
    """Disagreement is only safe in one direction.

    Reporting MORE privacy loss than an independent implementation is conservative — the
    release is at least as private as claimed. Reporting LESS would mean the guarantee we
    publish is not one we can support, which is the failure mode that made the hand-rolled
    accountant unusable.
    """
    from autodp.mechanism_zoo import GaussianMechanism
    from autodp.transformer_zoo import Composition

    ours = epsilon_for_noise_scale(sigma, 1e-5, "gaussian", 1.0, k)
    theirs = Composition()([GaussianMechanism(sigma=sigma, name="g")], [k]).get_approxDP(1e-5)

    assert (
        ours >= theirs * 0.999
    ), f"UNDER-REPORTING at sigma={sigma}, k={k}: ours={ours:.6f} < autodp={theirs:.6f}"


# ── the under-spend: where it is, and where it is not ────────────────────────────────────


@pytest.mark.parametrize("target", [0.5, 1.0, 8.0])
def test_single_stage_calibration_is_essentially_exact(target):
    """Pins the diagnosis: the bisection is NOT the source of the ~8% under-spend.

    Releases compose to ~0.92 of target (AIM ~0.79), and the obvious suspect is the
    calibration search. It is not: on one stage the search lands within 0.01%.
    """
    from synthproof.accounting.calibration import calibrate_noise_scale

    scale = calibrate_noise_scale(target, 1e-5, "gaussian", 1.0, 12)
    achieved = epsilon_for_noise_scale(scale, 1e-5, "gaussian", 1.0, 12)
    assert achieved / target == pytest.approx(1.0, abs=1e-3), achieved
    assert achieved <= target, "calibration must never overspend"


def test_a_linear_stage_split_is_what_loses_the_budget():
    """The actual cause, pinned so a future fix has a baseline to beat.

    RDP composition is SUBLINEAR, so calibrating stages against a LINEAR split of the total
    and composing them lands well short. This is conservative -- the release is more private
    than requested, never less -- but it is real utility left unspent, and it is why AIM,
    with the most charged operations, loses the most.
    """
    from synthproof.accounting.accountant import Accountant
    from synthproof.accounting.calibration import calibrate_noise_scale
    from synthproof.accounting.types import MechanismSpec

    target = 8.0
    profile, synthesis = 0.2 * target, 0.8 * target
    acc = Accountant(budget_eps=float("inf"), budget_delta=1e-5)
    for share in (profile, synthesis):
        scale = calibrate_noise_scale(share, 1e-5, "gaussian", 1.0, 12)
        acc.charge(MechanismSpec("gaussian", 1.0, scale, steps=12))

    ratio = acc.total() / target
    assert ratio < 0.90, f"expected a material shortfall, got {ratio:.4f}"
    assert ratio > 0.70, f"shortfall larger than diagnosed: {ratio:.4f}"
    # Conservative direction only. Overspending would be the F4-class failure.
    assert acc.total() < target
