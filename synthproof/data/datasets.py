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
    "age", "workclass", "fnlwgt", "education", "education_num", "marital_status",
    "occupation", "relationship", "race", "sex", "capital_gain", "capital_loss",
    "hours_per_week", "native_country", "income",
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
    return Schema(columns=[
        ColumnSpec("age", NUMERICAL, lower=17.0, upper=90.0),
        ColumnSpec("hours_per_week", NUMERICAL, lower=1.0, upper=99.0),
        ColumnSpec("capital_gain", NUMERICAL, lower=0.0, upper=100000.0),
        ColumnSpec("capital_loss", NUMERICAL, lower=0.0, upper=5000.0),
        ColumnSpec("workclass", CATEGORICAL, categories=[
            "Private", "Self-emp-not-inc", "Self-emp-inc", "Federal-gov",
            "Local-gov", "State-gov", "Without-pay", "Never-worked"]),
        ColumnSpec("education", CATEGORICAL, categories=[
            "Bachelors", "Some-college", "11th", "HS-grad", "Prof-school",
            "Assoc-acdm", "Assoc-voc", "9th", "7th-8th", "12th", "Masters",
            "1st-4th", "10th", "Doctorate", "5th-6th", "Preschool"]),
        ColumnSpec("marital_status", CATEGORICAL, categories=[
            "Married-civ-spouse", "Divorced", "Never-married", "Separated",
            "Widowed", "Married-spouse-absent", "Married-AF-spouse"]),
        ColumnSpec("occupation", CATEGORICAL, categories=[
            "Tech-support", "Craft-repair", "Other-service", "Sales", "Exec-managerial",
            "Prof-specialty", "Handlers-cleaners", "Machine-op-inspct", "Adm-clerical",
            "Farming-fishing", "Transport-moving", "Priv-house-serv", "Protective-serv",
            "Armed-Forces"]),
        ColumnSpec("relationship", CATEGORICAL, categories=[
            "Wife", "Own-child", "Husband", "Not-in-family", "Other-relative", "Unmarried"]),
        # race and sex are the subgroup variables for hypothesis H2.
        ColumnSpec("race", CATEGORICAL, categories=[
            "White", "Asian-Pac-Islander", "Amer-Indian-Eskimo", "Other", "Black"]),
        ColumnSpec("sex", CATEGORICAL, categories=["Female", "Male"]),
        ColumnSpec("income", CATEGORICAL, categories=["<=50K", ">50K"]),
    ])


def _cache_path(source: DatasetSource, data_dir: str) -> str:
    return os.path.join(data_dir, source.filename)


def fetch(source: DatasetSource, data_dir: str = DEFAULT_DATA_DIR,
          force: bool = False) -> str:
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


def load_adult(data_dir: str = DEFAULT_DATA_DIR,
               schema: Optional[Schema] = None) -> TabularDataset:
    """Loads UCI Adult as a `TabularDataset` under its public schema.

    Rows with missing values (encoded as "?") are dropped, matching the convention used by
    almost all published work on this benchmark.
    """
    path = fetch(ADULT, data_dir)

    with zipfile.ZipFile(path) as zf:
        member = next(n for n in zf.namelist() if n.endswith("adult.data"))
        raw = zf.read(member)

    df = pd.read_csv(
        io.BytesIO(raw), header=None, names=ADULT_COLUMNS,
        skipinitialspace=True, na_values=["?"],
    ).dropna().reset_index(drop=True)

    return TabularDataset(df, name="uci_adult", schema=schema or adult_schema())


REGISTRY: Dict[str, Callable[..., TabularDataset]] = {
    "adult": load_adult,
}


def load(name: str, **kwargs) -> TabularDataset:
    """Loads a benchmark by short name."""
    if name not in REGISTRY:
        raise KeyError(f"Unknown dataset {name!r}. Available: {sorted(REGISTRY)}")
    return REGISTRY[name](**kwargs)
