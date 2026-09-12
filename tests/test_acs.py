"""Tests for the ACSIncome loader.

The load itself needs a ~200 MB download from the Census Bureau, so tests that need real data
skip when it is absent. The coarsening logic — which is the part that can silently corrupt a
result — is tested without any download.
"""

import numpy as np
import pandas as pd
import pytest

from synthproof.data.acs import (
    ACS_COLUMNS,
    OCCP_GROUP_EDGES,
    POBP_REGION_EDGES,
    RACE_LABELS,
    SEX_LABELS,
    _coarsen,
    acs_income_schema,
    informative_numeric_pair,
    load_acs_income,
)

# ---------------------------------------------------------------------------- slow
# Loads and subsamples real ACS microdata: 65 seconds across four tests. Skipped by
# the fast lane (`pytest -m "not slow"`); CI still runs it.
pytestmark = pytest.mark.slow


def _fake_acs(n=500, seed=0):
    """Raw-coded ACS columns, spanning the real code ranges."""
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        {
            "AGEP": rng.integers(17, 95, n),
            "COW": rng.integers(1, 9, n),
            "SCHL": rng.integers(1, 25, n),
            "MAR": rng.integers(1, 6, n),
            "OCCP": rng.integers(10, 9830, n),  # 529 distinct codes in the real data
            "POBP": rng.integers(1, 555, n),  # 219 distinct
            "RELP": rng.integers(0, 18, n),
            "WKHP": rng.integers(1, 100, n),
            "SEX": rng.integers(1, 3, n),
            "RAC1P": rng.integers(1, 10, n),
        }
    )


def _has_acs():
    try:
        import folktables  # noqa: F401
    except ImportError:
        return False
    from pathlib import Path

    return Path("data/acs").exists()


requires_acs = pytest.mark.skipif(
    not _has_acs(), reason="ACS microdata not downloaded (needs `make h1-acs` once)"
)


# ------------------------------------------------------------------ coarsening


def test_coarsening_collapses_the_two_high_cardinality_columns():
    """THE reason this module exists.

    OCCP has 529 distinct codes and POBP has 219 in the real data. A 2-way marginal over
    them would be ~116,000 cells and AIM's junction tree would exceed any sane memory bound —
    the same failure that killed a full grid run on Adult, reached by a different route.
    """
    out = _coarsen(_fake_acs(n=3000))
    assert out["OCCP"].nunique() <= len(OCCP_GROUP_EDGES) + 1
    assert out["POBP"].nunique() <= len(POBP_REGION_EDGES) + 1
    # The binding constraint, over CATEGORICAL columns only: numerics are binned to 12
    # levels by the generator before any marginal is measured, so their raw cardinality
    # never reaches the junction tree.
    cats = ["COW", "MAR", "OCCP", "POBP", "RELP", "SEX", "RAC1P"]
    biggest = max(
        out[a].nunique() * out[b].nunique() for i, a in enumerate(cats) for b in cats[i + 1 :]
    )
    assert biggest < 5000, f"largest categorical 2-way clique is {biggest} cells"


def test_coarsening_uses_only_the_published_code_book_not_the_data():
    """A data-dependent binning would leak and would need to be charged.

    Two disjoint samples must map identical codes to identical groups. If the boundaries
    depended on observed frequencies they would not.
    """
    a = pd.DataFrame(
        {
            "OCCP": [10, 500, 9800],
            "POBP": [1, 100, 500],
            "AGEP": [20, 30, 40],
            "WKHP": [10, 20, 30],
            "SCHL": [1, 2, 3],
            "COW": [1, 2, 3],
            "MAR": [1, 2, 3],
            "RELP": [0, 1, 2],
            "SEX": [1, 2, 1],
            "RAC1P": [1, 2, 3],
        }
    )
    b = a.copy()
    b["AGEP"] = [90, 91, 92]  # a very different sample of everything else

    ca, cb = _coarsen(a), _coarsen(b)
    assert list(ca["OCCP"]) == list(cb["OCCP"])
    assert list(ca["POBP"]) == list(cb["POBP"])


def test_coarsening_is_monotone_in_the_underlying_code():
    """Group index must not decrease as the code increases, or the grouping is scrambled."""
    df = _fake_acs(n=200)
    df = df.sort_values("OCCP").reset_index(drop=True)
    groups = [int(g.removeprefix("soc")) for g in _coarsen(df)["OCCP"]]
    assert groups == sorted(groups)


def test_sex_and_race_become_readable_labels():
    """H2 tables print these; raw PUMS codes would make the results chapter unreadable."""
    out = _coarsen(_fake_acs(n=400))
    assert set(out["SEX"]).issubset(set(SEX_LABELS.values()))
    assert set(out["RAC1P"]).issubset(set(RACE_LABELS.values()))


def test_an_unknown_code_is_kept_rather_than_silently_becoming_null():
    """`.map` returns NaN for an unseen key, which would drop rows downstream."""
    df = _fake_acs(n=10)
    df.loc[0, "RAC1P"] = 99  # not in the code book
    out = _coarsen(df)
    assert out["RAC1P"].notna().all()
    assert "99" in set(out["RAC1P"])


# ------------------------------------------------------------------ schema


def test_schema_bounds_are_public_facts_not_measured_values():
    """The whole sensitivity argument rests on these being publishable domain knowledge."""
    schema = acs_income_schema()
    bounds = {c.name: (c.lower, c.upper) for c in schema.columns if c.lower is not None}
    assert bounds["AGEP"] == (17.0, 95.0)  # ACS surveys adults
    assert bounds["WKHP"] == (1.0, 99.0)  # the coding tops out at 99
    assert bounds["SCHL"] == (1.0, 24.0)


def test_schema_covers_every_column_the_loader_emits():
    names = {c.name for c in acs_income_schema().columns}
    assert names == set(ACS_COLUMNS)


def test_structure_metric_pair_matches_adults_for_comparability():
    """Measuring a different pair on each dataset would make the two incomparable."""
    assert informative_numeric_pair() == ["AGEP", "WKHP"]


# ------------------------------------------------------------------ real data


@requires_acs
def test_loads_with_the_requested_size_and_a_fingerprint():
    ds, fp = load_acs_income(n_rows=1500, download=False)
    assert ds.num_rows == 1500
    assert list(ds.df.columns) == ACS_COLUMNS
    assert ds.schema is not None
    # folktables has no pinned checksum, so the fingerprint is what ties a result to a slice.
    assert len(fp.content_sha256) == 64
    assert fp.rows_after_task_filter > fp.rows_used


@requires_acs
def test_the_income_task_matches_adults():
    """Both datasets pose >50K vs <=50K, so TSTR numbers are comparable."""
    ds, _ = load_acs_income(n_rows=2000, download=False)
    assert set(ds.df["income"]) <= {"<=50K", ">50K"}
    share = (ds.df["income"] == ">50K").mean()
    assert 0.2 < share < 0.6


@requires_acs
def test_subsampling_is_deterministic_under_a_seed():
    a, fa = load_acs_income(n_rows=800, seed=7, download=False)
    b, fb = load_acs_income(n_rows=800, seed=7, download=False)
    assert fa.content_sha256 == fb.content_sha256
    c, fc = load_acs_income(n_rows=800, seed=8, download=False)
    assert fc.content_sha256 != fa.content_sha256


@requires_acs
def test_every_column_stays_inside_its_declared_public_bounds():
    """A value outside the schema would be clipped, silently distorting the release."""
    ds, _ = load_acs_income(n_rows=2000, download=False)
    for spec in ds.schema.columns:
        if spec.lower is not None:
            assert ds.df[spec.name].between(spec.lower, spec.upper).all(), spec.name
