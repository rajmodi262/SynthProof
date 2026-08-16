"""Soundness tests for the DP domain profiler's category release.

The profiler is the FIRST and, before any noise is applied, the ONLY component that touches
raw sensitive values. A non-private path here makes every downstream epsilon a false
statement, so these tests target soundness rather than behaviour.
"""

import numpy as np
import pandas as pd
import pytest

from synthproof.accounting.accountant import Accountant
from synthproof.data.dataset import TabularDataset
from synthproof.data.profiler import DPDomainProfiler, InsufficientBudgetError
from synthproof.data.schema import CATEGORICAL, NUMERICAL, ColumnSpec, Schema

SENSITIVE = ["HIV", "Diabetes", "Cancer", "Flu"]
SHARES = [0.55, 0.25, 0.15, 0.05]
TRUE_MODE = "HIV"


def _clinic(n=6000, seed=0, with_schema=False):
    """A table with a strongly-moded sensitive categorical column."""
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(
        {
            "age": rng.integers(18, 90, n).astype(float),
            "diagnosis": rng.choice(SENSITIVE, n, p=SHARES),
        }
    )
    schema = None
    if with_schema:
        schema = Schema(
            [
                ColumnSpec("age", NUMERICAL, lower=0.0, upper=120.0),
                ColumnSpec("diagnosis", CATEGORICAL, categories=list(SENSITIVE)),
            ]
        )
    return TabularDataset(df, name="clinic", schema=schema)


def _profile(ds, eps_budget, seed):
    return DPDomainProfiler(
        accountant=Accountant(budget_eps=1e4, budget_delta=1e-5), eps_budget=eps_budget
    ).profile(ds, seed=seed)


# ------------------------------------------------------------------ the defect


def test_the_profiler_never_releases_the_un_noised_mode_of_a_sensitive_column():
    """REGRESSION (critical): the empty-domain fallback used to return
    `max(observed, key=counts.get)` — the exact mode of a sensitive column, released with no
    noise and no additional charge. That is an argmax over raw data; under DP it needs the
    exponential mechanism.

    It was measurably non-private: at eps_budget=0.001 the old code returned the true mode in
    196 of 200 seeds (98%), where a correct mechanism must approach data-independence as
    eps -> 0. This test drives the profiler into the empty-domain case with NO public schema
    and asserts it refuses rather than leaking.
    """
    ds = _clinic(with_schema=False)
    leaked = 0
    for seed in range(40):
        try:
            prof = _profile(ds, eps_budget=0.001, seed=seed)
        except InsufficientBudgetError:
            continue  # the sound outcome
        cats = prof.columns["diagnosis"].categories
        if cats == [TRUE_MODE]:
            leaked += 1
    assert leaked == 0, (
        f"the profiler returned exactly the true mode {TRUE_MODE!r} in {leaked}/40 seeds — "
        "the un-noised argmax fallback is back"
    )


def test_an_unsatisfiable_budget_raises_with_an_actionable_message():
    """Refusing is only useful if the user is told what to do about it."""
    ds = _clinic(with_schema=False)
    with pytest.raises(InsufficientBudgetError) as e:
        for seed in range(40):
            _profile(ds, eps_budget=0.0005, seed=seed)
    msg = str(e.value)
    assert "diagnosis" in msg
    assert "eps_budget" in msg
    assert "categories=" in msg, "the message must show the fix, not just the failure"


def test_the_public_schema_domain_is_used_instead_of_refusing_and_costs_nothing():
    """When the schema publishes the domain there IS a sound answer: use the public fact.

    Same argument as the public numeric bounds — a published domain reveals nothing, so it
    is free. The accountant must not move.
    """
    ds = _clinic(with_schema=True)
    acc = Accountant(budget_eps=1e4, budget_delta=1e-5)
    prof = DPDomainProfiler(accountant=acc, eps_budget=0.001).profile(ds, seed=0)
    spent_after_profile = acc.total()

    cats = prof.columns["diagnosis"].categories
    assert set(cats) == set(SENSITIVE), "the public domain should be released whole"

    # Charging happened for the histogram query itself, but the fallback added nothing.
    acc2 = Accountant(budget_eps=1e4, budget_delta=1e-5)
    DPDomainProfiler(accountant=acc2, eps_budget=0.001).profile(ds, seed=1)
    assert acc2.total() == pytest.approx(
        spent_after_profile
    ), "the fallback must not depend on the data, so its cost must be seed-independent"


def test_the_released_domain_is_data_independent_when_the_budget_is_negligible():
    """The defining property the old code violated.

    As eps -> 0 the output must stop depending on the data. With a public schema domain the
    release is identical across seeds AND across two datasets with opposite modes.
    """
    a = _clinic(with_schema=True, seed=0)
    b = _clinic(with_schema=True, seed=1)
    b.df["diagnosis"] = np.where(b.df["diagnosis"] == "HIV", "Flu", "HIV")  # invert the mode

    ra = [tuple(_profile(a, 1e-4, s).columns["diagnosis"].categories) for s in range(5)]
    rb = [tuple(_profile(b, 1e-4, s).columns["diagnosis"].categories) for s in range(5)]
    assert len(set(ra)) == 1, f"release varies with seed at negligible eps: {set(ra)}"
    assert set(ra) == set(rb), "release still depends on which value is the mode"


# ------------------------------------------------------------------ no regression elsewhere


def test_a_workable_budget_still_returns_a_thresholded_domain_not_the_public_one():
    """The fix must not short-circuit the real mechanism. At a usable budget the domain is
    still the DP-thresholded one, which may legitimately drop rare categories."""
    ds = _clinic(with_schema=True)
    prof = _profile(ds, eps_budget=0.05, seed=0)
    cats = prof.columns["diagnosis"].categories
    assert set(cats) <= set(SENSITIVE)
    assert len(cats) >= 2, "a usable budget should recover most of the domain"


def test_rare_categories_are_still_suppressed_at_a_usable_budget():
    """The original F5 defect (publishing `unique()` verbatim) must stay fixed: a value in a
    single record must not survive into the released domain."""
    ds = _clinic(with_schema=False)
    ds.df.loc[0, "diagnosis"] = "VeryRareCondition"
    survived = 0
    for seed in range(20):
        prof = _profile(ds, eps_budget=0.05, seed=seed)
        if "VeryRareCondition" in (prof.columns["diagnosis"].categories or []):
            survived += 1
    assert survived <= 1, f"a singleton category survived in {survived}/20 seeds"


# ------------------------------------------------------------------ threshold calibration


def test_an_inferred_schema_has_no_public_domain_to_fall_back_on():
    """REGRESSION (critical): `Schema.infer_nonprivate` fills `categories` from
    `series.unique()`, so on an inferred schema the "public" domain IS the data. The
    empty-domain fallback treated it as a publishable fact and released every observed value.

    Found while tightening the suppression threshold, which made the fallback fire MORE often
    and so made the damage larger: on a 2,000-row table with one identifier per row it went
    from ~13 identifiers reaching the release to 747.
    """
    ds = _clinic(with_schema=False)
    prof = DPDomainProfiler(
        accountant=Accountant(budget_eps=1e4, budget_delta=1e-5),
        eps_budget=0.001,
        schema_declared=False,
    )
    with pytest.raises(InsufficientBudgetError):
        for seed in range(40):
            prof.profile(ds, seed=seed)


def test_a_declared_schema_still_falls_back_to_its_public_domain():
    """The flag must not break the sound path: a genuinely declared domain is still free."""
    ds = _clinic(with_schema=True)
    prof = DPDomainProfiler(
        accountant=Accountant(budget_eps=1e4, budget_delta=1e-5),
        eps_budget=0.001,
        schema_declared=True,
    ).profile(ds, seed=0)
    assert set(prof.columns["diagnosis"].categories) == set(SENSITIVE)


def test_the_calibrated_threshold_carries_a_delta_term_and_the_legacy_one_does_not():
    """The defect in one assertion. The legacy threshold is a fixed multiple of the noise
    scale, so the probability a singleton survives cannot depend on the declared delta."""
    import numpy as np

    p = DPDomainProfiler(accountant=Accountant(budget_eps=10.0, budget_delta=1e-5), eps_budget=1.0)
    legacy = p._legacy_category_threshold(10.0)
    assert legacy == pytest.approx(3.0 * 10.0 * np.sqrt(2.0))

    tight = DPDomainProfiler(
        accountant=Accountant(budget_eps=10.0, budget_delta=1e-9), eps_budget=1.0
    )
    loose = DPDomainProfiler(
        accountant=Accountant(budget_eps=10.0, budget_delta=1e-3), eps_budget=1.0
    )
    # A smaller delta demands a higher bar; the legacy form cannot express that at all.
    assert tight._category_threshold(10.0, 5) > loose._category_threshold(10.0, 5)
    assert tight._category_threshold(10.0, 5) > legacy


def test_the_calibrated_threshold_splits_delta_across_categorical_columns():
    """Each column runs its own thresholded histogram, so the failure probabilities add."""
    p = DPDomainProfiler(accountant=Accountant(budget_eps=10.0, budget_delta=1e-5), eps_budget=1.0)
    assert p._category_threshold(10.0, 8) > p._category_threshold(10.0, 1)


def test_the_calibrated_threshold_is_off_by_default():
    """Committed results were produced with the legacy threshold. Switching the default would
    silently change every published number."""
    p = DPDomainProfiler(accountant=Accountant(budget_eps=10.0, budget_delta=1e-5), eps_budget=1.0)
    assert p.delta_calibrated_threshold is False


def test_a_zero_delta_is_rejected_by_the_calibrated_threshold():
    """The Accountant permits delta=0 (pure epsilon-DP), but a stability-based domain release
    has no sound threshold there: delta IS the probability a singleton survives, so with none
    to spend the mechanism cannot publish an unknown domain at all. It must say so rather than
    divide by zero.

    delta=1.0 is rejected earlier, by the Accountant itself, so it cannot reach this code.
    """
    p = DPDomainProfiler(accountant=Accountant(budget_eps=10.0, budget_delta=0.0), eps_budget=1.0)
    with pytest.raises(ValueError, match="0 < delta < 1"):
        p._category_threshold(10.0, 3)
