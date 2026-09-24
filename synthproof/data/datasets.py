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
            # Round, generous ranges. The previous 17-90 and 1-99 were exactly the observed
            # extremes -- a data-derived domain declared as "public" (audit C2, research/27).
            ColumnSpec("age", NUMERICAL, lower=15.0, upper=100.0),
            ColumnSpec("hours_per_week", NUMERICAL, lower=0.0, upper=100.0),
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
            ColumnSpec("age", NUMERICAL, lower=15.0, upper=100.0),  # was the observed 18-95 (C2)
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
            # 1-14 days is the cohort's published inclusion criterion (Strack et al. 2014), not
            # an observation. The other three were the observed extremes (132, 81, 16) -- a
            # data-derived domain declared as public (audit C2) -- and are now round ranges.
            ColumnSpec("time_in_hospital", NUMERICAL, lower=1.0, upper=14.0),
            ColumnSpec("num_lab_procedures", NUMERICAL, lower=0.0, upper=150.0),
            ColumnSpec("num_medications", NUMERICAL, lower=0.0, upper=100.0),
            ColumnSpec("number_diagnoses", NUMERICAL, lower=0.0, upper=20.0),
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


# --------------------------------------------------------------------------- extra benchmarks
# Five more public UCI benchmarks added to test generalisation of the mechanisms and of the
# categorical-aware evaluator across data TYPES: two all-categorical (Mushroom, Nursery), one
# all-numeric chemistry (Wine), one mixed finance (German credit) and one numeric healthcare
# (Breast Cancer Wisconsin). Every category set / bound below is from the dataset's published
# codebook or its domain, not measured from the data -- the same rule the other schemas follow.

MUSHROOM = DatasetSource(
    name="uci_mushroom",
    url="https://archive.ics.uci.edu/static/public/73/mushroom.zip",
    sha256="face32f32647e0d939f6233f36dd30dd5d619ae9f3f9b8e10bea4ac7e1f60b1a",
    filename="mushroom.zip",
)
_MUSHROOM_COLS = [
    "target",
    "cap_shape",
    "cap_surface",
    "cap_color",
    "bruises",
    "odor",
    "gill_attachment",
    "gill_spacing",
    "gill_size",
    "gill_color",
    "stalk_shape",
    "stalk_root",
    "stalk_surface_above",
    "stalk_surface_below",
    "stalk_color_above",
    "stalk_color_below",
    "veil_type",
    "veil_color",
    "ring_number",
    "ring_type",
    "spore_print_color",
    "population",
    "habitat",
]


def mushroom_schema() -> Schema:
    """Public schema for UCI Mushroom (category codes from agaricus-lepiota.names).

    `stalk_root` (2480 '?' values) and the constant `veil_type` are excluded; the remaining
    nine columns carry the edibility signal (odor and spore/gill colour dominate the codebook
    rules). All categorical: this is the primary all-categorical test for the evaluator.
    """
    return Schema(
        columns=[
            ColumnSpec("target", CATEGORICAL, categories=["e", "p"]),
            ColumnSpec("cap_shape", CATEGORICAL, categories=list("bcxfks")),
            ColumnSpec("cap_surface", CATEGORICAL, categories=list("fgys")),
            ColumnSpec("cap_color", CATEGORICAL, categories=list("nbcgrpuewy")),
            ColumnSpec("bruises", CATEGORICAL, categories=list("tf")),
            ColumnSpec("odor", CATEGORICAL, categories=list("alcyfmnps")),
            ColumnSpec("gill_spacing", CATEGORICAL, categories=list("cwd")),
            ColumnSpec("gill_size", CATEGORICAL, categories=list("bn")),
            ColumnSpec("gill_color", CATEGORICAL, categories=list("knbhgropuewy")),
        ]
    )


def load_mushroom(data_dir: str = DEFAULT_DATA_DIR, schema: Optional[Schema] = None):
    path = fetch(MUSHROOM, data_dir)
    with zipfile.ZipFile(path) as zf:
        raw = zf.read("agaricus-lepiota.data")
    df = pd.read_csv(io.BytesIO(raw), header=None, names=_MUSHROOM_COLS)
    spec = schema or mushroom_schema()
    df = df[[c for c in spec.names if c in df.columns]].reset_index(drop=True)
    return TabularDataset(df=df, name="uci_mushroom", schema=spec)


NURSERY = DatasetSource(
    name="uci_nursery",
    url="https://archive.ics.uci.edu/static/public/76/nursery.zip",
    sha256="914780f5e3050895216cb91f9e4a1408f3c0813b5854d5a6d6c601c2882091dd",
    filename="nursery.zip",
)


def nursery_schema() -> Schema:
    """Public schema for UCI Nursery (category codes from nursery.names). All categorical,
    four-class target after dropping the degenerate 2-row `recommend` class."""
    return Schema(
        columns=[
            ColumnSpec("parents", CATEGORICAL, categories=["usual", "pretentious", "great_pret"]),
            ColumnSpec(
                "has_nurs",
                CATEGORICAL,
                categories=["proper", "less_proper", "improper", "critical", "very_crit"],
            ),
            ColumnSpec(
                "form", CATEGORICAL, categories=["complete", "completed", "incomplete", "foster"]
            ),
            ColumnSpec("children", CATEGORICAL, categories=["1", "2", "3", "more"]),
            ColumnSpec("housing", CATEGORICAL, categories=["convenient", "less_conv", "critical"]),
            ColumnSpec("finance", CATEGORICAL, categories=["convenient", "inconv"]),
            ColumnSpec(
                "social", CATEGORICAL, categories=["nonprob", "slightly_prob", "problematic"]
            ),
            ColumnSpec("health", CATEGORICAL, categories=["recommended", "priority", "not_recom"]),
            ColumnSpec(
                "target",
                CATEGORICAL,
                categories=["not_recom", "very_recom", "priority", "spec_prior"],
            ),
        ]
    )


def load_nursery(data_dir: str = DEFAULT_DATA_DIR, schema: Optional[Schema] = None):
    path = fetch(NURSERY, data_dir)
    names = [
        "parents",
        "has_nurs",
        "form",
        "children",
        "housing",
        "finance",
        "social",
        "health",
        "target",
    ]
    with zipfile.ZipFile(path) as zf:
        raw = zf.read("nursery.data")
    df = pd.read_csv(io.BytesIO(raw), header=None, names=names)
    df = df[df["target"] != "recommend"].reset_index(drop=True)  # 2-row degenerate class
    spec = schema or nursery_schema()
    df = df[[c for c in spec.names if c in df.columns]].reset_index(drop=True)
    return TabularDataset(df=df, name="uci_nursery", schema=spec)


GERMAN_CREDIT = DatasetSource(
    name="statlog_german_credit",
    url="https://archive.ics.uci.edu/static/public/144/statlog+german+credit+data.zip",
    sha256="e12d9d5def6845c0622634a1cd2ab87fa470668c4298f1ec52a4e403376a435b",
    filename="german.zip",
)
_GERMAN_COLS = [
    "checking",
    "duration",
    "credit_history",
    "purpose",
    "credit_amount",
    "savings",
    "employment",
    "installment_rate",
    "personal_status",
    "other_debtors",
    "residence_since",
    "property",
    "age",
    "other_plans",
    "housing",
    "existing_credits",
    "job",
    "dependents",
    "telephone",
    "foreign_worker",
    "target",
]


def german_credit_schema() -> Schema:
    """Public schema for Statlog German Credit (codes A11.. from german.doc). Mixed
    numeric/categorical finance table; target 1=good, 2=bad -> mapped to good/bad."""
    return Schema(
        columns=[
            ColumnSpec("duration", NUMERICAL, lower=0.0, upper=80.0),  # was the observed max 72 (C2)
            ColumnSpec("credit_amount", NUMERICAL, lower=0.0, upper=20000.0),
            ColumnSpec("age", NUMERICAL, lower=18.0, upper=80.0),
            ColumnSpec("installment_rate", NUMERICAL, lower=1.0, upper=4.0),
            ColumnSpec("checking", CATEGORICAL, categories=["A11", "A12", "A13", "A14"]),
            ColumnSpec(
                "credit_history", CATEGORICAL, categories=["A30", "A31", "A32", "A33", "A34"]
            ),
            ColumnSpec("savings", CATEGORICAL, categories=["A61", "A62", "A63", "A64", "A65"]),
            ColumnSpec("employment", CATEGORICAL, categories=["A71", "A72", "A73", "A74", "A75"]),
            ColumnSpec("housing", CATEGORICAL, categories=["A151", "A152", "A153"]),
            ColumnSpec("target", CATEGORICAL, categories=["good", "bad"]),
        ]
    )


def load_german_credit(data_dir: str = DEFAULT_DATA_DIR, schema: Optional[Schema] = None):
    path = fetch(GERMAN_CREDIT, data_dir)
    with zipfile.ZipFile(path) as zf:
        raw = zf.read("german.data").decode("ascii")
    df = pd.read_csv(io.StringIO(raw), sep=r"\s+", header=None, names=_GERMAN_COLS)
    df["target"] = df["target"].map({1: "good", 2: "bad"})
    spec = schema or german_credit_schema()
    df = df[[c for c in spec.names if c in df.columns]].reset_index(drop=True)
    return TabularDataset(df=df, name="statlog_german_credit", schema=spec)


WINE_QUALITY = DatasetSource(
    name="uci_wine_quality",
    url="https://archive.ics.uci.edu/static/public/186/wine+quality.zip",
    sha256="3ed56667f4b828242bd732d7d1dd7f2861e54432239d7fa63877014cbb0304d4",
    filename="wine.zip",
)


def wine_quality_schema() -> Schema:
    """Public schema for UCI Wine Quality (red). All-numeric chemistry; quality>=6 -> good.
    Bounds are generous red-wine chemistry ranges (approximate domain, then clipped)."""
    b = {
        "fixed_acidity": (4.0, 16.0),
        "volatile_acidity": (0.0, 2.0),
        "citric_acid": (0.0, 2.0),
        "residual_sugar": (0.0, 16.0),
        "chlorides": (0.0, 1.0),
        # Were (1, 72) and (6, 289): the red wines' own min/max -- the exact data-derived domain
        # Ganev et al. (P4) attack, on their own dataset (audit C2). Now round ranges.
        "free_sulfur_dioxide": (0.0, 100.0),
        "total_sulfur_dioxide": (0.0, 300.0),
        "density": (0.985, 1.005),
        "pH": (2.7, 4.1),
        "sulphates": (0.0, 2.5),
        "alcohol": (8.0, 15.0),
    }
    cols = [ColumnSpec(k, NUMERICAL, lower=lo, upper=hi) for k, (lo, hi) in b.items()]
    cols.append(ColumnSpec("quality", CATEGORICAL, categories=["good", "bad"]))
    return Schema(columns=cols)


def load_wine_quality(data_dir: str = DEFAULT_DATA_DIR, schema: Optional[Schema] = None):
    path = fetch(WINE_QUALITY, data_dir)
    with zipfile.ZipFile(path) as zf:
        df = pd.read_csv(io.BytesIO(zf.read("winequality-red.csv")), sep=";")
    df.columns = [c.replace(" ", "_") for c in df.columns]
    df["quality"] = df["quality"].map(lambda q: "good" if q >= 6 else "bad")
    spec = schema or wine_quality_schema()
    df = df[[c for c in spec.names if c in df.columns]].reset_index(drop=True)
    return TabularDataset(df=df, name="uci_wine_red", schema=spec)


BREAST_CANCER = DatasetSource(
    name="uci_breast_cancer_wisc",
    url="https://archive.ics.uci.edu/static/public/17/breast+cancer+wisconsin+diagnostic.zip",
    sha256="bc154869ef13f753f9e2b5a17e248cfe1ba4b6721db7c4da9f4880e40b05d3af",
    filename="bcw.zip",
)
_BCW_FEATS = [
    "radius",
    "texture",
    "perimeter",
    "area",
    "smoothness",
    "compactness",
    "concavity",
    "concave_points",
    "symmetry",
    "fractal_dim",
]


def breast_cancer_schema() -> Schema:
    """Public schema for Breast Cancer Wisconsin (Diagnostic) -- the ten 'mean' features and
    the M/B diagnosis. Numeric healthcare table; bounds set generously wide, then clipped."""
    b = {
        "radius": (5, 30),
        "texture": (5, 45),
        "perimeter": (40, 200),
        "area": (100, 2600),
        "smoothness": (0.0, 0.2),
        "compactness": (0.0, 0.4),
        "concavity": (0.0, 0.5),
        "concave_points": (0.0, 0.25),
        "symmetry": (0.1, 0.4),
        "fractal_dim": (0.0, 0.12),
    }
    cols = [ColumnSpec(k, NUMERICAL, lower=float(lo), upper=float(hi)) for k, (lo, hi) in b.items()]
    cols.append(ColumnSpec("diagnosis", CATEGORICAL, categories=["malignant", "benign"]))
    return Schema(columns=cols)


def load_breast_cancer(data_dir: str = DEFAULT_DATA_DIR, schema: Optional[Schema] = None):
    path = fetch(BREAST_CANCER, data_dir)
    with zipfile.ZipFile(path) as zf:
        df = pd.read_csv(io.BytesIO(zf.read("wdbc.data")), header=None)
    df = df.rename(columns={1: "diagnosis", **{i + 2: _BCW_FEATS[i] for i in range(10)}})
    df["diagnosis"] = df["diagnosis"].map({"M": "malignant", "B": "benign"})
    spec = schema or breast_cancer_schema()
    df = df[[c for c in spec.names if c in df.columns]].reset_index(drop=True)
    return TabularDataset(df=df, name="uci_breast_cancer_wisc", schema=spec)


# --------------------------------------------------------------------------- same-dataset rivals
# Two benchmarks taken straight from the base papers so the comparison is SAME-DATASET:
# Texas Hospital Discharge (Stadler et al., USENIX Sec '22 -- their healthcare table) and
# San Francisco Fire calls (Annamalai et al., USENIX Sec '24; McKenna et al. AIM, VLDB '22).
# Both are pinned to the exact bytes those authors publish.

TEXAS = DatasetSource(
    name="texas_hospital_discharge",
    url="https://raw.githubusercontent.com/spring-epfl/synthetic_data_release/master/data/texas.csv",
    sha256="9f61d15ebcd52cc7e9c27c030068a2c55e46474aec64a67a1fc409a7c2668c87",
    filename="texas.csv",
)


def texas_schema() -> Schema:
    """Public schema for the Texas Hospital Discharge sample used by Stadler et al. (GroundHog).

    Category codes follow the Texas DSHS PUDF codebook; PAT_AGE is its 22 coded age bands.
    Numeric bounds are public clips: a stay of at most a year, charges capped at $1M. Target:
    high in-hospital mortality risk (APR-DRG risk 3-4 = major/extreme) vs low (1-2).
    """
    return Schema(columns=[
        ColumnSpec("TYPE_OF_ADMISSION", CATEGORICAL, categories=["1", "2", "3", "4", "5", "9"]),
        ColumnSpec("SEX_CODE", CATEGORICAL, categories=["F", "M"]),
        ColumnSpec("RACE", CATEGORICAL, categories=["1", "2", "3", "4", "5"]),
        ColumnSpec("ETHNICITY", CATEGORICAL, categories=["1", "2"]),
        ColumnSpec("PAT_AGE", CATEGORICAL, categories=[f"{i:02d}" for i in range(22)]),
        ColumnSpec("ADMIT_WEEKDAY", CATEGORICAL, categories=[str(i) for i in range(1, 8)]),
        ColumnSpec("ILLNESS_SEVERITY", CATEGORICAL, categories=["1", "2", "3", "4"]),
        ColumnSpec("LENGTH_OF_STAY", NUMERICAL, lower=1.0, upper=365.0),
        ColumnSpec("TOTAL_CHARGES", NUMERICAL, lower=0.0, upper=1000000.0),
        ColumnSpec("mortality_risk", CATEGORICAL, categories=["low", "high"]),
    ])


def load_texas(data_dir: str = DEFAULT_DATA_DIR, schema: Optional[Schema] = None):
    path = fetch(TEXAS, data_dir)
    df = pd.read_csv(path, dtype=str, low_memory=False)
    df = df[df["RISK_MORTALITY"].isin(["1", "2", "3", "4"])]
    df["mortality_risk"] = df["RISK_MORTALITY"].map(lambda v: "high" if v in ("3", "4") else "low")
    for c in ("LENGTH_OF_STAY", "TOTAL_CHARGES"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    spec = schema or texas_schema()
    df = df[[c for c in spec.names if c in df.columns]].dropna()
    # Drop the codebook's INVALID / unknown codes rather than inventing a category for them.
    for c in spec.columns:
        if c.kind == CATEGORICAL:
            df = df[df[c.name].isin(c.categories)]
    return TabularDataset(df=df.reset_index(drop=True), name="texas_hospital_discharge", schema=spec)


SF_FIRE = DatasetSource(
    name="sf_fire_calls",
    url="https://raw.githubusercontent.com/ryan112358/hd-datasets/master/clean/fire.csv",
    sha256="2415d60acdfb96cbc3a1d0caee845245dc37b9b379884cb16dbf33e57bb9890b",
    filename="fire.csv",
)
# Category counts from the authors' published fire-domain.json (public, not read from the data).
_FIRE_COLS = {"ALS Unit": ("als_unit", 2), "Call Type Group": ("call_type_group", 5),
              "Priority": ("priority", 8), "Call Type": ("call_type", 31),
              "Zipcode of Incident": ("zipcode", 28), "Battalion": ("battalion", 11),
              "Call Final Disposition": ("final_disposition", 15), "City": ("city", 9),
              "Station Area": ("station_area", 46)}


def sf_fire_schema() -> Schema:
    """All-categorical, integer-coded SF Fire table: the 9 of Annamalai et al.'s 10 trimmed
    attributes present in the clean file (Number of Alarms is not). Target: ALS Unit dispatched."""
    return Schema(columns=[ColumnSpec(new, CATEGORICAL, categories=[str(i) for i in range(k)])
                           for new, k in _FIRE_COLS.values()])


def load_sf_fire(data_dir: str = DEFAULT_DATA_DIR, schema: Optional[Schema] = None):
    path = fetch(SF_FIRE, data_dir)
    df = pd.read_csv(path, dtype=str)
    df = df[list(_FIRE_COLS)].rename(columns={k: v[0] for k, v in _FIRE_COLS.items()})
    spec = schema or sf_fire_schema()
    return TabularDataset(df=df.reset_index(drop=True), name="sf_fire_calls", schema=spec)


REGISTRY: Dict[str, Callable[..., TabularDataset]] = {
    "adult": load_adult,
    "diabetes": load_diabetes130,
    "bank": load_bank_marketing,
    "mushroom": load_mushroom,
    "nursery": load_nursery,
    "german": load_german_credit,
    "wine": load_wine_quality,
    "bcw": load_breast_cancer,
    "texas": load_texas,
    "fire": load_sf_fire,
}


def load(name: str, **kwargs) -> TabularDataset:
    """Loads a benchmark by short name."""
    if name not in REGISTRY:
        raise KeyError(f"Unknown dataset {name!r}. Available: {sorted(REGISTRY)}")
    return REGISTRY[name](**kwargs)
