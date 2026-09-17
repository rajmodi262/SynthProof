"""The healthcare benchmark: UCI Diabetes 130-US Hospitals.

Adult and ACSIncome are US-census income; Bank is finance. This is the project's ONE genuine
healthcare table, so the medical framing of the whole project rests on it being correct. As with
Bank, the tests are mostly about the SCHEMA -- a bound read off the data makes the epsilon a false
statement, and a leaky or exploding column invalidates every downstream number.
"""

import io
import zipfile

import pandas as pd
import pytest

from synthproof.data.datasets import (
    DIABETES_130,
    diabetes130_schema,
    fetch,
    load_diabetes130,
)
from synthproof.data.schema import CATEGORICAL

pytestmark = pytest.mark.slow  # downloads ~3 MB and parses 100k rows


@pytest.fixture(scope="module")
def diabetes():
    return load_diabetes130()


@pytest.fixture(scope="module")
def raw_diabetes():
    """The table exactly as downloaded, before the schema clips anything."""
    with zipfile.ZipFile(fetch(DIABETES_130)) as zf:
        return pd.read_csv(
            io.BytesIO(zf.read("diabetic_data.csv")), na_values=["?"], low_memory=False
        )


def test_it_is_pinned_to_a_digest_like_every_other_benchmark():
    assert len(DIABETES_130.sha256) == 64
    assert DIABETES_130.url.startswith("https://")


def test_it_loads_a_healthcare_table(diabetes):
    assert diabetes.name == "uci_diabetes_130"
    # ~99.5k rows survive dropping missing/Unknown-gender; well above the 500-row preflight floor
    # and large enough to subsample n=6000 like the other three benchmarks.
    assert diabetes.num_rows > 90000


def test_the_target_is_early_readmission_and_binary(diabetes):
    """The raw column has three levels (<30, >30, NO); the release target is the clinically
    actionable event -- readmission WITHIN 30 days -- as a binary YES/NO."""
    assert set(diabetes.df["readmitted"].unique()) <= {"YES", "NO"}
    share = (diabetes.df["readmitted"] == "YES").mean()
    # Early readmission is the minority event; this is a realistically imbalanced clinical task.
    assert 0.08 < share < 0.15, f"target balance moved to {share:.3f}; the framing is stale"


def test_high_cardinality_and_leaky_columns_are_excluded(diabetes):
    """The ICD-9 diagnosis codes have ~700 categories each and would explode the model domain;
    the ID columns are identifiers. None may appear in the release."""
    for col in ("encounter_id", "patient_nbr", "diag_1", "diag_2", "diag_3", "weight"):
        assert col not in diabetes.columns


def test_the_schema_cannot_have_measured_anything():
    """Structural: `diabetes130_schema()` takes no data, so no bound was read off the table."""
    import inspect

    assert inspect.signature(diabetes130_schema).parameters == {}
    assert len(diabetes130_schema()) == 10


def test_declared_numeric_bounds_contain_the_RAW_data(raw_diabetes):
    """The defect-catcher: a declared bound that clips real rows distorts the table the
    synthesiser models. Checked against the table as downloaded, before any clipping."""
    schema = diabetes130_schema()
    for col in ("time_in_hospital", "num_lab_procedures", "num_medications", "number_diagnoses"):
        spec = schema[col]
        lo, hi = float(raw_diabetes[col].min()), float(raw_diabetes[col].max())
        assert spec.lower <= lo, f"{col}: declared lower {spec.lower} clips real minimum {lo}"
        assert spec.upper >= hi, f"{col}: declared upper {spec.upper} clips real maximum {hi}"


def test_gender_is_restricted_to_the_two_documented_values(diabetes):
    """The 3 Unknown/Invalid-gender rows are dropped; releasing a third level would spend budget
    on a category that is a data-entry artefact, not a fact about patients."""
    assert set(diabetes.df["gender"].unique()) == {"Female", "Male"}
    assert diabetes130_schema()["gender"].kind == CATEGORICAL
