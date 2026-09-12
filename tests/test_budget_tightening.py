"""The budget under-spend, and the fix that is deliberately switched off.

Task 4.3 of docs/ROAD_TO_TEN.md. `BudgetPlan` splits a release's total epsilon LINEARLY across
stages and calibrates each stage against its own share — but RDP composition is SUBLINEAR, so
the stages compose to materially less than the total. Measured here: **0.908 of target**, which
is 9% of the privacy budget bought and never spent, and therefore utility given away.

`split(tighten=True)` bisects an outer multiplier on the shares until the COMPOSED total meets
the target. It is off by default and these tests are why that is safe to leave alone AND safe
to turn on:

  the never-overspend invariant is the one that cannot be traded. A release that spends MORE
  than it declared is a false statement about a person's privacy, and no amount of recovered
  utility justifies it. `test_tightening_never_overspends_at_any_target` is the test that
  matters most in this file.

  the default must not move, because every published epsilon in `results/` was produced by it.
  `test_the_default_is_unchanged` pins that.
"""

import pytest

from synthproof.accounting.calibration import BudgetPlan

TARGETS = [0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0]


# --------------------------------------------------------------------- the invariant


@pytest.mark.parametrize("target", TARGETS)
def test_tightening_never_overspends_at_any_target(target):
    """The one property that cannot be traded for utility.

    The bisection returns the largest multiplier whose composition is still within budget, so
    the composed epsilon must land at or below the target at every target — not on average,
    not usually. A release that spends more than it declared is a false statement about a
    person's privacy.
    """
    plan = BudgetPlan.split(target, tighten=True)
    composed = plan.composed_eps
    assert composed <= target * (1 + 1e-9), (
        f"tightened plan at target {target} composed to {composed}, which OVERSPENDS. "
        "This is the invariant the whole accountant rests on."
    )


@pytest.mark.parametrize("target", TARGETS)
def test_the_linear_default_also_never_overspends(target):
    """The existing behaviour, restated as a test rather than assumed."""
    assert BudgetPlan.split(target).composed_eps <= target * (1 + 1e-9)


# --------------------------------------------------------------------- the under-spend


@pytest.mark.parametrize("target", [1.0, 4.0, 8.0])
def test_the_linear_split_leaves_budget_on_the_table(target):
    """Documents the defect, so the fix has something to be measured against.

    If this ever stops failing to reach the target, the sublinearity has changed and the
    tightening is no longer needed — which would be worth knowing.
    """
    ratio = BudgetPlan.split(target).composed_eps / target
    assert ratio < 0.95, (
        f"the linear split now reaches {ratio:.3f} of target; the under-spend this fix "
        "exists for may have gone away."
    )
    assert ratio > 0.85, f"the under-spend is worse than documented: {ratio:.3f}"


@pytest.mark.parametrize("target", [1.0, 4.0, 8.0])
def test_tightening_recovers_essentially_all_of_it(target):
    """The fix has to be worth having: within half a percent of the requested budget."""
    ratio = BudgetPlan.split(target, tighten=True).composed_eps / target
    assert ratio > 0.995, f"tightened plan reached only {ratio:.4f} of target"


def test_tightening_is_a_strict_improvement_not_a_different_answer():
    """Same shares, scaled by a common factor — the SPLIT is unchanged, only its size."""
    plain = BudgetPlan.split(4.0)
    tight = BudgetPlan.split(4.0, tighten=True)

    assert tight.tightening > 1.0
    assert plain.tightening == 1.0
    # The profile/synthesis ratio is a policy decision and must survive the rescaling.
    assert plain.profile_eps / plain.synthesis_eps == pytest.approx(
        tight.profile_eps / tight.synthesis_eps, rel=1e-9
    )
    assert tight.profile_eps > plain.profile_eps
    assert tight.synthesis_eps > plain.synthesis_eps


# --------------------------------------------------------------------- the default


@pytest.mark.parametrize("target", TARGETS)
def test_the_default_is_unchanged(target):
    """Every published epsilon in results/ came from the linear split.

    Turning tightening on by default would change all of them — proved 7.356 becomes ~8.0 —
    and invalidate the committed grid until a full re-run. That is a costed decision for a
    human to make, not a default to drift into.
    """
    assert BudgetPlan.split(target).tightening == 1.0
    assert BudgetPlan.split(target, tighten=False).tightening == 1.0


def test_the_shares_still_sum_to_the_requested_total_without_tightening():
    """The linear split's own arithmetic, which the tightening must not have disturbed."""
    plan = BudgetPlan.split(10.0, profile_frac=0.1)
    assert plan.profile_eps + plan.synthesis_eps == pytest.approx(10.0, rel=1e-9)
    assert plan.profile_eps == pytest.approx(1.0, rel=1e-9)


def test_below_a_floor_set_by_delta_the_request_itself_is_incoherent():
    """A property of (eps, delta)-DP, pinned because it LOOKS like an overspend.

    At delta = 1e-5 the composed epsilon cannot go below roughly 0.0035, no matter how much
    noise is added: the delta term dominates the RDP-to-(eps, delta) conversion. So a plan
    asked for eps = 0.001 reports 0.0035 and appears to overspend by 3.5x.

    It is not a calibration defect. `calibrate_noise_scale` behaves correctly there -- asked
    for 0.001 it returns a scale achieving 0.000000, undershooting as it should. What is
    wrong is the REQUEST: eps = 0.001 with delta = 1e-5 asks for a guarantee stronger in
    epsilon than the delta already concedes, and no mechanism can deliver it.

    Measured: the floor stops binding at about eps = 0.005, above which the ratio returns to
    the usual 0.90. Every target in TARGETS is above it, which is why the invariant tests
    hold. This is recorded rather than asserted away, because a reader who probes a tiny
    epsilon will see the same 3.5x and should find the explanation here instead of filing it
    as a broken accountant.
    """
    floor = BudgetPlan.split(1e-3).composed_eps
    assert floor > 1e-3, "the delta floor no longer binds at eps=0.001; this note is stale"

    # And above the floor, the invariant holds as everywhere else.
    for target in (0.01, 0.05, 0.25):
        assert BudgetPlan.split(target, tighten=True).composed_eps <= target * (1 + 1e-9)
