"""An empirical distinguishing test on neighbouring inputs, for every mechanism.

Each mechanism runs R times on a table D and R times on D' = D plus one record carrying a
category that appears nowhere in D. The event "the synthetic table contains that category" has
some probability under each; differential privacy bounds the ratio of those probabilities by
e^eps (plus delta). Clopper-Pearson intervals turn the observed frequencies into a LOWER bound on
the epsilon the mechanism actually satisfies, and that lower bound must not exceed what the
accountant charged.

What it can and cannot show. Passing means this one event did not expose a violation at this
sample size -- a test can only find a broken mechanism, never prove a correct one, and with
R runs it cannot certify much above log(R). It is sized to catch what has actually gone wrong in
this project's history: noise charged but not applied, a statistic released exactly, a record
copied through. The positive control (a generator that copies rows) proves it can fire.
"""

import math
import os

import numpy as np
import pandas as pd
import pytest
from scipy.stats import beta

from synthproof.accounting.accountant import Accountant
from synthproof.data.dataset import TabularDataset
from synthproof.data.profiler import DPDomainProfiler
from synthproof.data.schema import CATEGORICAL, NUMERICAL, ColumnSpec, Schema
from synthproof.frontier.experiment import MECHANISMS

EPS = 1.0
DELTA = 1e-5
ALPHA = 0.05
SCHEMA = Schema(
    [
        ColumnSpec("age", NUMERICAL, lower=0.0, upper=100.0),
        ColumnSpec("job", CATEGORICAL, categories=["a", "b", "c", "rare"]),
        ColumnSpec("sex", CATEGORICAL, categories=["F", "M"]),
    ]
)


def _tables(n=40):
    rng = np.random.default_rng(0)
    d = pd.DataFrame(
        {
            "age": rng.uniform(20, 70, n),
            "job": rng.choice(["a", "b", "c"], n),
            "sex": rng.choice(["F", "M"], n),
        }
    )
    d_prime = pd.concat(
        [d, pd.DataFrame({"age": [99.0], "job": ["rare"], "sex": ["M"]})], ignore_index=True
    )
    return d, d_prime


def _hits(gen_cls, df, runs, **gen_kw):
    """Per release, how many rows carry the rare category; and the epsilon charged."""
    ds = TabularDataset(df, schema=SCHEMA)
    # Every domain is declared, so profiling is free and identical on both sides.
    profile = DPDomainProfiler(Accountant(1.0, DELTA), eps_budget=0.5).profile(ds, seed=0)
    counts, charged = [], 0.0
    for seed in range(runs):
        acc = Accountant(EPS * 1.5, DELTA)
        gen = gen_cls(seed=seed, **gen_kw)
        gen.fit(ds, profile, acc, target_eps=EPS)
        out = gen.generate(len(df))
        counts.append(int((out["job"].astype(str) == "rare").sum()))
        charged = max(charged, acc.total(DELTA) if hasattr(acc, "total") else EPS)
    return counts, charged


# Events tested: "at least t rare rows", for a grid fixed before any run. A single event can
# saturate (pairwise and DP-VAE put the rare category in almost every release, so "appears at
# all" had no power); a higher threshold does not. Bonferroni over the grid keeps the overall
# confidence at 1 - ALPHA.
THRESHOLDS = (1, 2, 3, 5, 8, 13)


def empirical_epsilon_lower_bound(k1, n1, k0, n0, alpha=ALPHA, delta=DELTA):
    """Largest eps the data supports at confidence 1 - alpha, over the event and its complement,
    in both directions. 0 when nothing is significant."""

    def lo(k, n):
        return 0.0 if k == 0 else float(beta.ppf(alpha / 4, k, n - k + 1))

    def hi(k, n):
        return 1.0 if k == n else float(beta.ppf(1 - alpha / 4, k + 1, n - k))

    best = 0.0
    for a, na, b, nb in ((k1, n1, k0, n0), (k0, n0, k1, n1)):
        for ka, kb in ((a, b), (na - a, nb - b)):
            num, den = lo(ka, na) - delta, hi(kb, nb)
            if num > 0 and den > 0:
                best = max(best, math.log(num / den))
    return best


def _check(gen_cls, runs, **gen_kw):
    """Largest certified epsilon over the threshold grid; with the per-threshold hit counts."""
    d, d_prime = _tables()
    c0, charged = _hits(gen_cls, d, runs, **gen_kw)
    c1, _ = _hits(gen_cls, d_prime, runs, **gen_kw)
    found, k0s, k1s = 0.0, [], []
    for t in THRESHOLDS:
        k0, k1 = sum(c >= t for c in c0), sum(c >= t for c in c1)
        k0s.append(k0)
        k1s.append(k1)
        found = max(
            found, empirical_epsilon_lower_bound(k1, runs, k0, runs, alpha=ALPHA / len(THRESHOLDS))
        )
    return found, charged, k0s, k1s


def test_the_bound_is_zero_when_the_two_sides_agree():
    assert empirical_epsilon_lower_bound(50, 200, 52, 200) == 0.0


def test_the_bound_is_large_when_the_two_sides_are_disjoint():
    assert empirical_epsilon_lower_bound(200, 200, 0, 200) > 3.0


def test_the_positive_control_a_copying_generator_is_caught():
    """A generator that publishes its input must fail the same test the mechanisms pass."""
    from synthproof.generators.leaky import LeakyGenerator

    d, d_prime = _tables()
    runs = 120
    hits = []
    for df in (d, d_prime):
        k = 0
        for seed in range(runs):
            g = LeakyGenerator(seed=seed, leak_fraction=1.0)
            g.fit(TabularDataset(df, schema=SCHEMA), None, None, 0.0)  # type: ignore[arg-type]
            k += int((g.generate(len(df))["job"].astype(str) == "rare").any())
        hits.append(k)
    assert empirical_epsilon_lower_bound(hits[1], runs, hits[0], runs) > EPS


FAST = [
    ("synthproof.generators.independent", "IndependentMarginalGenerator"),
    ("synthproof.generators.pairwise", "PairwiseMarginalGenerator"),
    ("synthproof.generators.moments", "GaussianMomentGenerator"),
]
# AIM takes ~13 minutes for 160 fits and DP-VAE ~3, too slow for every push: they run in the
# weekly reproduction workflow (SYNTHPROOF_EMPIRICAL_DP_FULL=1). MST runs everywhere.
_FULL = os.environ.get("SYNTHPROOF_EMPIRICAL_DP_FULL") == "1"
SLOW = [
    (m, c)
    for m, c, key, always in (
        ("synthproof.generators.mst", "MSTGenerator", "mst", True),
        ("synthproof.generators.aim", "AIMGenerator", "aim", False),
        ("synthproof.generators.dpvae", "DPVAEGenerator", "dpvae", False),
    )
    if key in MECHANISMS and (always or _FULL)
]


def _cls(modname, clsname):
    import importlib

    return getattr(importlib.import_module(modname), clsname)


@pytest.mark.parametrize("modname,clsname", FAST, ids=lambda x: x.split(".")[-1])
def test_no_mechanism_is_measurably_less_private_than_charged(modname, clsname):
    found, charged, k0, k1 = _check(_cls(modname, clsname), runs=300)
    assert charged <= EPS + 1e-9
    assert found <= charged, (
        f"{clsname}: releases with >= t rare rows, t in {THRESHOLDS}: D {k0} vs D' {k1} "
        f"of 300, which certifies eps >= {found:.2f} against {charged:.2f} charged"
    )


@pytest.mark.slow
@pytest.mark.parametrize("modname,clsname", SLOW, ids=lambda x: x.split(".")[-1])
def test_no_slow_mechanism_is_measurably_less_private_than_charged(modname, clsname):
    kw = {"steps": 30} if clsname == "DPVAEGenerator" else {}
    found, charged, k0, k1 = _check(_cls(modname, clsname), runs=80, **kw)
    assert (
        found <= charged
    ), f"{clsname}: t in {THRESHOLDS}: D {k0} vs D' {k1} of 80 certifies eps >= {found:.2f}"
