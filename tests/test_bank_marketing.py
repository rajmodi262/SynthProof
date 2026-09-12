"""The third benchmark, and the properties that make it worth adding.

Task 4.2 of docs/ROAD_TO_TEN.md. Adult and ACSIncome are both US-census-derived, single-table
and binary-target, so agreement between them is weaker evidence of generality than it looks —
it is closer to one dataset measured twice. UCI Bank Marketing is a different domain
(Portuguese retail banking), a different collection process (outbound telemarketing), and a
materially different target balance.

These tests are mostly about the SCHEMA rather than the loader, because the schema is where a
dataset can quietly invalidate every downstream number: a leaky column makes TSTR meaningless,
and a bound read off the data makes the epsilon a false statement.
"""

import pandas as pd
import pytest

from synthproof.data.datasets import (
    BANK_MARKETING,
    bank_marketing_schema,
    load_bank_marketing,
)
from synthproof.data.schema import CATEGORICAL

pytestmark = pytest.mark.slow  # downloads ~1 MB and parses 45k rows


@pytest.fixture(scope="module")
def bank():
    return load_bank_marketing()


@pytest.fixture(scope="module")
def raw_bank():
    """The table exactly as downloaded, before the schema clips anything."""
    import io
    import zipfile

    from synthproof.data.datasets import fetch

    with zipfile.ZipFile(fetch(BANK_MARKETING)) as outer:
        with zipfile.ZipFile(io.BytesIO(outer.read("bank.zip"))) as inner:
            return pd.read_csv(io.BytesIO(inner.read("bank-full.csv")), sep=";")


def test_it_is_pinned_to_a_digest_like_every_other_benchmark():
    """A dataset that can change under you is not a benchmark."""
    assert len(BANK_MARKETING.sha256) == 64
    assert BANK_MARKETING.url.startswith("https://")


def test_it_loads_the_full_table_not_the_sample(bank):
    """The archive ships a 10% sample alongside the full table; the full one is the benchmark."""
    assert bank.num_rows == 45211
    assert bank.name == "uci_bank_marketing"


def test_duration_is_excluded_because_it_leaks_the_target(bank):
    """The column that would have made every utility number meaningless.

    `duration` is the length of the last call, which is not known before the call is placed
    and is near-perfectly predictive of the outcome — a call ending in a subscription is a
    long call. UCI's own notes say it should be discarded for realistic modelling. Keeping it
    would inflate every TSTR score on this dataset in the same way `education_num` would on
    Adult, and the inflation would look like a result.
    """
    assert "duration" not in bank.columns


def test_the_contact_date_is_excluded_too(bank):
    """`day` and `month` encode the bank's calling schedule, not anything about a person."""
    assert "day" not in bank.columns
    assert "month" not in bank.columns


def test_the_target_is_far_more_imbalanced_than_adult(bank):
    """The reason this dataset is worth having, stated as a number.

    Adult's positive class is about 24%. Here it is 11.7%. A synthesiser that preserves a
    balanced target may not preserve a skewed one, and that is precisely the kind of
    generality two census datasets cannot test.
    """
    share = (bank.df["y"] == "yes").mean()
    assert 0.10 < share < 0.13, f"target balance moved to {share:.3f}; the framing is stale"


def test_the_schema_cannot_have_measured_anything():
    """Structural, not statistical: `bank_marketing_schema()` takes no data.

    The first version of this test compared the declared bounds against the loaded table's
    extremes and asserted they differed. That could never fail for the right reason --
    `TabularDataset` CLIPS to the declared bounds on construction, so the observed extremes
    equal the declared ones by construction. A test that cannot fail is worse than no test.

    What actually guarantees the bounds were not measured is that the function has no access
    to the data at all, which is checkable directly.
    """
    import inspect

    assert inspect.signature(bank_marketing_schema).parameters == {}
    schema = bank_marketing_schema()
    assert len(schema) == 13


def test_declared_bounds_contain_the_RAW_data(raw_bank):
    """Checked against the table as downloaded, before any clipping.

    This is the test that caught the real defect. Two of the first-draft bounds truncated
    real rows -- `previous` was declared 0..60 against a true tail reaching 275, and
    `balance` cut off at -8000 against a true minimum of -8019. Clipping is how sensitivity
    is bounded and it is safe for PRIVACY, but a bound that truncates a fifth of a column's
    range distorts the table the synthesiser is asked to model, and that distortion would
    have surfaced later as a utility finding.
    """
    schema = bank_marketing_schema()
    for col in ("age", "balance", "campaign", "previous"):
        spec = schema[col]
        lo, hi = float(raw_bank[col].min()), float(raw_bank[col].max())
        assert spec.lower <= lo, f"{col}: declared lower {spec.lower} clips real minimum {lo}"
        assert spec.upper >= hi, f"{col}: declared upper {spec.upper} clips real maximum {hi}"


def test_every_declared_category_level_is_present_and_vice_versa(bank):
    """A declared level that never occurs wastes budget; an undeclared one is silently dropped."""
    schema = bank_marketing_schema()
    for col in bank.categorical_cols:
        declared = set(schema[col].categories or [])
        observed = set(bank.df[col].astype(str).unique())
        assert observed <= declared | {
            "__OTHER__"
        }, f"{col} has levels not in the schema: {sorted(observed - declared)}"
        assert (
            declared <= observed
        ), f"{col} declares levels that never occur: {sorted(declared - observed)}"
        assert schema[col].kind == CATEGORICAL


def test_it_is_not_census_derived(bank):
    """A framing check, so the generality claim cannot quietly become 'three census tables'."""
    census_markers = {"fnlwgt", "relationship", "native_country", "occupation", "race", "sex"}
    assert not (census_markers & set(bank.columns)), (
        "this table shares columns with the census benchmarks; it is not the independent "
        "third domain the generality claim needs."
    )
