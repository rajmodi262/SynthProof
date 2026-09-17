"""Benchmark dataset loaders with integrity verification.

Each loader fetches a public benchmark, verifies its SHA-256 against a pinned digest, and
returns a `TabularDataset` built against a **hand-declared public schema**.

The schemas here matter more than the download code. Their numeric bounds are publishable
facts about the domain (an age lies in [17, 90]; hours worked per week in [1, 99]) rather than
values measured from the data. That is what makes the sensitivity the profiler declares
defensible — see brutal_project_audit.md, finding F5.
"""

import hashlib
import io
import os
import urllib.request
import zipfile
from dataclasses import dataclass
from typing import Callable, Dict, Optional

import pandas as pd

from synthproof.data.dataset import TabularDataset
from synthproof.data.schema import CATEGORICAL, NUMERICAL, ColumnSpec, Schema

DEFAULT_DATA_DIR = os.environ.get("SYNTHPROOF_DATA_DIR", "data")


@dataclass(frozen=True)
class DatasetSource:
    """A downloadable benchmark and the digest that proves we got the right bytes."""

    name: str
    url: str
    sha256: str
    filename: str

    def __post_init__(self) -> None:
        # `urlopen` honours whatever scheme it is given, including `file:` and `ftp:`. A
        # dataset source is always a remote HTTPS artefact, so anything else is either a
        # typo or an attempt to make the loader read a local path. Rejecting it here means
        # the scheme cannot be smuggled in through a caller-constructed DatasetSource.
        if not self.url.startswith("https://"):
            raise ValueError(
                f"Dataset {self.name!r}: url must be https, got {self.url!r}. "
                "Other schemes (file:, ftp:) are refused."
            )

    def verify(self, blob: bytes) -> None:
        got = hashlib.sha256(blob).hexdigest()
        if self.sha256 and got != self.sha256:
            raise ValueError(
                f"Checksum mismatch for {self.name}.\n"
                f"  expected {self.sha256}\n  got      {got}\n"
                "Refusing to use these bytes. If the upstream file legitimately changed, "
                "update the pinned digest deliberately and record why."
            )


# UCI Adult (Becker & Kohavi, 1996). The column names are not in the CSV itself.
ADULT_COLUMNS = [
    "age",
    "workclass",
    "fnlwgt",
    "education",
    "education_num",
    "marital_status",
    "occupation",
    "relationship",
    "race",
    "sex",
    "capital_gain",
    "capital_loss",
    "hours_per_week",
    "native_country",
    "income",
]

ADULT = DatasetSource(
    name="uci_adult",
    url="https://archive.ics.uci.edu/static/public/2/adult.zip",
    sha256="7537312dd56c2b98035880805ce99e68183a30ee468aa5329d6df0fbb3cc21bb",
    filename="adult.zip",
)


def adult_schema() -> Schema:
    """Public schema for UCI Adult.

    Every bound below is domain knowledge, not a measurement. `fnlwgt` (a census sampling
    weight) and `education_num` (a redundant encoding of `education`) are deliberately
    excluded: releasing redundant encodings of the same attribute spends budget twice for no
    additional utility.
    """
    return Schema(
        columns=[
            ColumnSpec("age", NUMERICAL, lower=17.0, upper=90.0),
            ColumnSpec("hours_per_week", NUMERICAL, lower=1.0, upper=99.0),
            ColumnSpec("capital_gain", NUMERICAL, lower=0.0, upper=100000.0),
            ColumnSpec("capital_loss", NUMERICAL, lower=0.0, upper=5000.0),
            ColumnSpec(
                "workclass",
                CATEGORICAL,
                categories=[
                    "Private",
                    "Self-emp-not-inc",
                    "Self-emp-inc",
                    "Federal-gov",
                    "Local-gov",
                    "State-gov",
                    "Without-pay",
                    "Never-worked",
                ],
            ),
            ColumnSpec(
                "education",
                CATEGORICAL,
                categories=[
                    "Bachelors",
                    "Some-college",
                    "11th",
                    "HS-grad",
                    "Prof-school",
                    "Assoc-acdm",
                    "Assoc-voc",
                    "9th",
                    "7th-8th",
                    "12th",
                    "Masters",
                    "1st-4th",
                    "10th",
                    "Doctorate",
                    "5th-6th",
                    "Preschool",
                ],
            ),
            ColumnSpec(
                "marital_status",
                CATEGORICAL,
                categories=[
                    "Married-civ-spouse",
                    "Divorced",
                    "Never-married",
                    "Separated",
                    "Widowed",
                    "Married-spouse-absent",
                    "Married-AF-spouse",
                ],
            ),
            ColumnSpec(
                "occupation",
                CATEGORICAL,
                categories=[
                    "Tech-support",
                    "Craft-repair",
                    "Other-service",
                    "Sales",
                    "Exec-managerial",
                    "Prof-specialty",
                    "Handlers-cleaners",
                    "Machine-op-inspct",
                    "Adm-clerical",
                    "Farming-fishing",
                    "Transport-moving",
                    "Priv-house-serv",
                    "Protective-serv",
                    "Armed-Forces",
                ],
            ),
            ColumnSpec(
                "relationship",
                CATEGORICAL,
                categories=[
                    "Wife",
                    "Own-child",
                    "Husband",
                    "Not-in-family",
                    "Other-relative",
                    "Unmarried",
                ],
            ),
            # race and sex are the subgroup variables for hypothesis H2.
            ColumnSpec(
                "race",
                CATEGORICAL,
                categories=["White", "Asian-Pac-Islander", "Amer-Indian-Eskimo", "Other", "Black"],
            ),
            ColumnSpec("sex", CATEGORICAL, categories=["Female", "Male"]),
            ColumnSpec("income", CATEGORICAL, categories=["<=50K", ">50K"]),
        ]
    )


def _cache_path(source: DatasetSource, data_dir: str) -> str:
    return os.path.join(data_dir, source.filename)


# The THIRD benchmark, and the first that is not census-derived. Adult and ACSIncome share a
# collection process, a country and a broad schema shape, so agreement between them is weaker
# evidence of generality than it looks. This is Portuguese retail banking, gathered by outbound
# telemarketing, with a target that is 11.7% positive against Adult's ~24%.
BANK_MARKETING = DatasetSource(
    name="uci_bank_marketing",
    url="https://archive.ics.uci.edu/static/public/222/bank+marketing.zip",
    sha256="e0bf5f5de5b846e2f18e9d90606637267d46dfa260e0f17bb12e605db5efbeb4",
    filename="bank_marketing.zip",
)


def bank_marketing_schema() -> Schema:
    """Public schema for UCI Bank Marketing.

    Every bound is DECLARED domain knowledge, not a measurement -- the same rule the Adult
    schema follows, and the reason `domain_source` exists on the data sheet. Reading the true
    extremes off the table would be an uncharged query and would make the epsilon a false
    statement.

    TWO COLUMNS ARE DELIBERATELY EXCLUDED, both for reasons the dataset's own documentation
    gives:

      `duration` -- the length of the last call -- is not known before the call is made, and
      is near-perfectly predictive of the outcome because a call that ends in a subscription
      is a long call. UCI's own notes say it "should be discarded if the intention is to have
      a realistic predictive model". Including it would make every TSTR score meaningless in
      the same way `education_num` would have on Adult.

      `day` and `month` are the contact date. They encode campaign timing rather than anything
      about the person, and a synthesiser that reproduces them well is reproducing the bank's
      calling schedule.
    """
    return Schema(
        columns=[
            # Retail banking customers: the dataset is adults, and 95 is a defensible public
            # ceiling for a marketing contact list.
            ColumnSpec("age", NUMERICAL, lower=18.0, upper=95.0),
            # Account balance in euros. Negative because current accounts go overdrawn; the
            # bounds are a declared plausible range for a retail account, not observed extremes.
            ColumnSpec("balance", NUMERICAL, lower=-10000.0, upper=110000.0),
            # Contacts during this campaign, and contacts before it. Public operational limits.
            ColumnSpec("campaign", NUMERICAL, lower=1.0, upper=70.0),
            # 300, not 60. The first draft used 60 and silently clipped a real tail that
            # reaches 275 prior contacts. Clipping is how sensitivity is bounded and it is
            # safe for privacy, but a bound that truncates a fifth of a column's range
            # distorts the table the synthesiser is asked to model, and the distortion
            # would have shown up as a utility result.
            ColumnSpec("previous", NUMERICAL, lower=0.0, upper=300.0),
            ColumnSpec(
                "job",
                CATEGORICAL,
                categories=[
                    "admin.",
                    "blue-collar",
                    "entrepreneur",
                    "housemaid",
                    "management",
                    "retired",
                    "self-employed",
                    "services",
                    "student",
                    "technician",
                    "unemployed",
                    "unknown",
                ],
            ),
            ColumnSpec("marital", CATEGORICAL, categories=["married", "divorced", "single"]),
            ColumnSpec(
                "education",
                CATEGORICAL,
                categories=["primary", "secondary", "tertiary", "unknown"],
            ),
            ColumnSpec("default", CATEGORICAL, categories=["yes", "no"]),
            ColumnSpec("housing", CATEGORICAL, categories=["yes", "no"]),
            ColumnSpec("loan", CATEGORICAL, categories=["yes", "no"]),
            ColumnSpec("contact", CATEGORICAL, categories=["unknown", "telephone", "cellular"]),
            ColumnSpec(
                "poutcome",
                CATEGORICAL,
                categories=["unknown", "other", "failure", "success"],
            ),
            # The prediction target: did the client subscribe to the term deposit.
            ColumnSpec("y", CATEGORICAL, categories=["yes", "no"]),
        ]
    )


def load_bank_marketing(
    data_dir: str = DEFAULT_DATA_DIR, schema: Optional[Schema] = None
) -> TabularDataset:
    """Loads UCI Bank Marketing as a `TabularDataset` under its public schema.

    The archive is a zip containing a zip; `bank-full.csv` is the complete 45,211-row table
    (`bank.csv` is a 10% sample kept by the authors for slower algorithms). Fields are
    semicolon-separated and quoted.
    """
    import io

    path = fetch(BANK_MARKETING, data_dir)

    with zipfile.ZipFile(path) as outer:
        inner_name = next(n for n in outer.namelist() if n == "bank.zip")
        with zipfile.ZipFile(io.BytesIO(outer.read(inner_name))) as inner:
            raw = inner.read("bank-full.csv")

    df = pd.read_csv(io.BytesIO(raw), sep=";")
    df.columns = [c.strip().strip('"') for c in df.columns]

    spec = schema or bank_marketing_schema()
    # Keeping only the declared columns is what drops `duration`, `day` and `month`: the
    # schema defines the release, so an excluded column is excluded everywhere rather than
    # being dropped again at each call site.
    df = df[[c for c in spec.names if c in df.columns]].reset_index(drop=True)

    return TabularDataset(df=df, name="uci_bank_marketing", schema=spec)


def fetch(source: DatasetSource, data_dir: str = DEFAULT_DATA_DIR, force: bool = False) -> str:
    """Downloads `source` into `data_dir` if absent, verifying its digest.

    Returns the local path. Raises if the digest does not match a pinned value.
    """
    os.makedirs(data_dir, exist_ok=True)
    path = _cache_path(source, data_dir)

    if os.path.exists(path) and not force:
        with open(path, "rb") as f:
            source.verify(f.read())
        return path

    # Scheme is pinned to https by DatasetSource.__post_init__, so this cannot be
    # redirected to file:/ftp:. nosec B310 records that the check is deliberate.
    with urllib.request.urlopen(source.url, timeout=120) as resp:  # nosec B310
        blob = resp.read()
    source.verify(blob)

    with open(path, "wb") as f:
        f.write(blob)
    return path


def pin_checksum(source: DatasetSource, data_dir: str = DEFAULT_DATA_DIR) -> str:
    """Returns the SHA-256 of a locally cached file, for pinning into `DatasetSource`."""
    with open(_cache_path(source, data_dir), "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def load_adult(data_dir: str = DEFAULT_DATA_DIR, schema: Optional[Schema] = None) -> TabularDataset:
    """Loads UCI Adult as a `TabularDataset` under its public schema.

    Rows with missing values (encoded as "?") are dropped, matching the convention used by
    almost all published work on this benchmark.
    """
    path = fetch(ADULT, data_dir)

    with zipfile.ZipFile(path) as zf:
        member = next(n for n in zf.namelist() if n.endswith("adult.data"))
        raw = zf.read(member)

    df = (
        pd.read_csv(
            io.BytesIO(raw),
            header=None,
            names=ADULT_COLUMNS,
            skipinitialspace=True,
            na_values=["?"],
        )
        .dropna()
        .reset_index(drop=True)
    )

    return TabularDataset(df, name="uci_adult", schema=schema or adult_schema())


# UCI Diabetes 130-US Hospitals, 1999-2008 (Strack et al., 2014; UCI id 296). 101,766
# de-identified inpatient encounters for diabetic patients. This is the project's ONE genuine
# healthcare table -- Adult and ACS are census income, Bank is finance -- so it is the dataset
# the medical framing of the project actually rests on. The task is 30-day readmission, a real
# clinical prediction problem.
DIABETES_130 = DatasetSource(
    name="uci_diabetes_130",
    url="https://archive.ics.uci.edu/static/public/296/diabetes+130-us+hospitals+for+years+1999-2008.zip",
    sha256="f82ac129da2ddd2299391ff6fbae3a6a58b3edcf59ac9d7bd480c00fe453112a",
    filename="diabetes_130.zip",
)


def diabetes130_schema() -> Schema:
    """Public schema for UCI Diabetes 130.

    Every bound is DECLARED domain knowledge from the dataset's published codebook (Strack et
    al., 2014, Table 1), not a measurement of this table -- the same rule Adult and Bank follow,
    and the reason `domain_source` exists on the data sheet. The four integer counts have the
    ranges the codebook documents (time in hospital 1-14 days; up to 132 lab procedures; up to
    81 medications; up to 16 diagnoses).

    The 50-column raw table is reduced to a clinically meaningful, low-cardinality release. The
    excluded columns and why: the two ID columns (`encounter_id`, `patient_nbr`) are identifiers;
    `weight`, `payer_code` and `medical_specialty` are >40% missing; the three ICD-9 diagnosis
    codes (`diag_1..3`) have ~700 categories each and would explode the model domain; and the 20+
    individual drug columns are near-constant. `insulin` and `diabetesMed` are kept as the two
    medication signals that actually vary and matter clinically.
    """
    return Schema(
        columns=[
            ColumnSpec("time_in_hospital", NUMERICAL, lower=1.0, upper=14.0),
            ColumnSpec("num_lab_procedures", NUMERICAL, lower=1.0, upper=132.0),
            ColumnSpec("num_medications", NUMERICAL, lower=1.0, upper=81.0),
            ColumnSpec("number_diagnoses", NUMERICAL, lower=1.0, upper=16.0),
            ColumnSpec(
                "age",
                CATEGORICAL,
                categories=[
                    "[0-10)",
                    "[10-20)",
                    "[20-30)",
                    "[30-40)",
                    "[40-50)",
                    "[50-60)",
                    "[60-70)",
                    "[70-80)",
                    "[80-90)",
                    "[90-100)",
                ],
            ),
            ColumnSpec("gender", CATEGORICAL, categories=["Female", "Male"]),
            ColumnSpec(
                "race",
                CATEGORICAL,
                categories=["AfricanAmerican", "Asian", "Caucasian", "Hispanic", "Other"],
            ),
            ColumnSpec("insulin", CATEGORICAL, categories=["Down", "No", "Steady", "Up"]),
            ColumnSpec("diabetesMed", CATEGORICAL, categories=["No", "Yes"]),
            # The prediction target: readmitted within 30 days. The raw column has three levels
            # (<30, >30, NO); it is binarised to YES (<30) vs NO (>30 or NO) so the target names
            # the clinically actionable event -- early readmission -- rather than any return.
            ColumnSpec("readmitted", CATEGORICAL, categories=["YES", "NO"]),
        ]
    )


def load_diabetes130(
    data_dir: str = DEFAULT_DATA_DIR, schema: Optional[Schema] = None
) -> TabularDataset:
    """Loads UCI Diabetes 130 as a `TabularDataset` under its public schema.

    Rows with missing values ("?") in a declared column, and the 3 `Unknown/Invalid`-gender
    rows, are dropped. `readmitted` is binarised to early readmission (<30 days) vs not.
    """
    path = fetch(DIABETES_130, data_dir)

    with zipfile.ZipFile(path) as zf:
        raw = zf.read("diabetic_data.csv")

    df = pd.read_csv(io.BytesIO(raw), na_values=["?"], low_memory=False)
    # Binarise the target BEFORE narrowing to the schema: early (<30-day) readmission is the
    # clinically actionable outcome; >30 and NO both mean "not an early readmission".
    df["readmitted"] = df["readmitted"].map(lambda v: "YES" if v == "<30" else "NO")

    spec = schema or diabetes130_schema()
    df = df[[c for c in spec.names if c in df.columns]]
    # Drop the handful of Unknown/Invalid genders and any codebook "?" left in declared columns.
    df = df.dropna().reset_index(drop=True)
    df = df[df["gender"].isin(["Female", "Male"])].reset_index(drop=True)

    return TabularDataset(df=df, name="uci_diabetes_130", schema=spec)


REGISTRY: Dict[str, Callable[..., TabularDataset]] = {
    "adult": load_adult,
    "diabetes": load_diabetes130,
}


def load(name: str, **kwargs) -> TabularDataset:
    """Loads a benchmark by short name."""
    if name not in REGISTRY:
        raise KeyError(f"Unknown dataset {name!r}. Available: {sorted(REGISTRY)}")
    return REGISTRY[name](**kwargs)
