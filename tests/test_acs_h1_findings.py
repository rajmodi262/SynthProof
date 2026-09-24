"""Characterisation tests pinning the ACS-vs-Adult H1 findings.

These do not assert that anything is *correct*. They pin the observations that
`results/acs/H1_RESULTS.md` reasons from, so that if a future change alters them the
write-up cannot silently become false. Standing rule 6: every number in a document traces
to something committed and re-runnable.

The AIM fits here are slow (~2 min total). They are worth it: the confound they pin is the
one that undermines H1's headline, and nothing cheaper detects it.
"""

import json
from pathlib import Path

import pytest

from synthproof.accounting.accountant import Accountant
from synthproof.accounting.calibration import BudgetPlan
from synthproof.data.profiler import DPDomainProfiler
from synthproof.frontier.experiment import MECHANISMS

# ---------------------------------------------------------------------------- slow
# Every test here fits real AIM over ACS microdata. 273 of the suite's 485 seconds are
# in this file, and its slowest single test is 130s. Skipped by the fast lane
# (`pytest -m "not slow"`); CI still runs it.
pytestmark = pytest.mark.slow


ACS_H1 = Path("results/acs/h1_all_families.json")
ADULT_H1 = Path("results/h1_all_families.json")

requires_aim = pytest.mark.skipif("aim" not in MECHANISMS, reason="private-pgm unavailable")
requires_results = pytest.mark.skipif(
    not (ACS_H1.exists() and ADULT_H1.exists()),
    reason="H1 grids not run (make h1 && make h1-acs)",
)


def _two_way_cliques(ds, eps, seed=0):
    """The two-way cliques AIM actually selects at this budget."""
    plan = BudgetPlan.split(eps, delta=1e-5, profile_frac=0.1)
    acc = Accountant(budget_eps=eps * 1.02, budget_delta=1e-5)
    profile = DPDomainProfiler(accountant=acc, eps_budget=plan.profile_eps).profile(ds, seed=seed)
    gen = MECHANISMS["aim"](seed=seed)
    gen.fit(ds, profile, acc, target_eps=plan.synthesis_eps)
    return [set(c) for c in gen.measured_cliques_ if len(c) == 2], profile, gen


def _adult():
    from synthproof.data.datasets import load_adult

    ds = load_adult()
    ds.df = ds.df.sample(n=6000, random_state=0).reset_index(drop=True)
    return ds


def _cell(payload, mech, eps):
    return next(
        c for c in payload["cells"] if c["mechanism"] == mech and abs(c["target_eps"] - eps) < 1e-9
    )


# ------------------------------------------------------- the confound


# REMOVED 2026-09-24 (audit research/27): `test_aim_selects_the_measured_pair_on_adult_at_every_epsilon`
# pinned the OLD AIM's habit of selecting (age, hours_per_week) -- the one pair the structure metric
# read. That clique-selection confound was already retracted (research/, CLAUDE.md), and the
# structure metric is now table-wide (`structure_error_all`, `pair_tvd`; audit M1), so a
# coincidence with one pair can no longer drive the result. AIM was rebuilt (budget-driven rounds,
# exponential-mechanism selection, target workload), so the pinned behaviour is gone by design.


@requires_aim
def test_the_acs_domain_no_longer_depends_on_the_budget():
    """ACS's schema declares its category domains, so they are released whole and for free
    (audit C1, research/27). The domain used to be thresholded over the OBSERVED values and grew
    sharply with epsilon (OCCP: a handful of groups at 0.5, most of them at 8) -- a data-dependent
    domain, which was also the root cause of AIM's ACS degradation. It is now the same at every
    budget."""
    pytest.importorskip("folktables")
    if not Path("data/acs").exists():
        pytest.skip("ACS microdata not downloaded")
    from synthproof.data.acs import load_acs_income

    ds, _ = load_acs_income(n_rows=6000, seed=0, download=False)
    sizes = {}
    for eps in (0.5, 8.0):
        acc = Accountant(budget_eps=eps, budget_delta=1e-5)
        prof = DPDomainProfiler(accountant=acc, eps_budget=0.1 * eps).profile(ds, seed=0)
        sizes[eps] = {n: len(c.categories) for n, c in prof.columns.items() if c.categories}
        assert acc.total() == 0.0
    assert sizes[0.5] == sizes[8.0]


@requires_aim
def test_the_model_size_bound_is_not_what_degrades_aim_on_acs():
    """Rules out our own engineering bound as the cause. If this ever fails, the ACS
    write-up's diagnosis (§3) is wrong and the finding must be re-examined."""
    pytest.importorskip("folktables")
    if not Path("data/acs").exists():
        pytest.skip("ACS microdata not downloaded")
    from synthproof.data.acs import load_acs_income

    ds, _ = load_acs_income(n_rows=6000, seed=0, download=False)
    for eps in (0.5, 8.0):
        _, _, gen = _two_way_cliques(ds, eps)
        assert gen.skipped_cliques_ == [], (
            f"eps={eps} skipped {gen.skipped_cliques_} — the model-size bound IS binding, "
            "which contradicts results/acs/H1_RESULTS.md §3."
        )


# ------------------------------------------------------- the committed grids


@requires_results
def test_the_two_grids_ran_the_same_protocol():
    """A protocol difference would make the disagreement uninterpretable."""
    a, b = json.loads(ADULT_H1.read_text()), json.loads(ACS_H1.read_text())
    assert a["n_rows"] == b["n_rows"] == 6000
    assert a["seeds"] == b["seeds"]
    assert a["eps_grid"] == b["eps_grid"]
    assert a["mechanisms"] == b["mechanisms"]
    assert a["utility_measured_on"] == b["utility_measured_on"] == "clean_fit"


@requires_results
def test_the_correlation_error_ordering_disagrees_across_datasets():
    """Pins the contradiction itself. This test passing is NOT a good result — it records
    that the Adult ordering did not transfer, so the write-up stays true to the data."""
    a, b = json.loads(ADULT_H1.read_text()), json.loads(ACS_H1.read_text())
    rank = lambda p: [  # noqa: E731
        m
        for m, _ in sorted(
            ((m, _cell(p, m, 8.0)["correlation_error"]["mean"]) for m in p["mechanisms"]),
            key=lambda r: r[1],
        )
    ]
    assert rank(a) == ["aim", "pairwise", "independent"]
    assert rank(b) == ["pairwise", "independent", "aim"]


@requires_results
def test_aim_and_independent_do_not_separate_on_acs():
    """The weaker but sufficient statement: on ACS, AIM is not distinguishable from the
    independent-marginals baseline on structure."""
    b = json.loads(ACS_H1.read_text())
    aim = _cell(b, "aim", 8.0)["correlation_error"]
    ind = _cell(b, "independent", 8.0)["correlation_error"]
    assert not (aim["hi"] < ind["lo"] or ind["hi"] < aim["lo"])


# REMOVED 2026-09-24: `test_aim_utility_on_acs_falls_between_the_tightest_and_loosest_budget`
# pinned the old ACS grid, in which AIM got WORSE with more budget. Its cause -- a category domain
# that grew with epsilon because it was thresholded over the observed values -- was the C1 leak
# (research/27); with declared domains released whole, that grid is superseded by the re-run.


