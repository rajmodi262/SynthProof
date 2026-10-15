"""Datasets used by the prior work this project compares against: Texas, SF Fire."""

from typing import Optional

import pandas as pd

from synthproof.data.dataset import TabularDataset
from synthproof.data.datasets._source import (
    DEFAULT_DATA_DIR,
    DatasetSource,
    fetch,
)
from synthproof.data.schema import CATEGORICAL, NUMERICAL, ColumnSpec, Schema

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
    return Schema(
        columns=[
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
        ]
    )


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
    for col_spec in spec.columns:
        if col_spec.kind == CATEGORICAL and col_spec.categories is not None:
            df = df[df[col_spec.name].isin(col_spec.categories)]
    return TabularDataset(
        df=df.reset_index(drop=True), name="texas_hospital_discharge", schema=spec
    )


SF_FIRE = DatasetSource(
    name="sf_fire_calls",
    url="https://raw.githubusercontent.com/ryan112358/hd-datasets/master/clean/fire.csv",
    sha256="2415d60acdfb96cbc3a1d0caee845245dc37b9b379884cb16dbf33e57bb9890b",
    filename="fire.csv",
)
# Category counts from the authors' published fire-domain.json (public, not read from the data).
_FIRE_COLS = {
    "ALS Unit": ("als_unit", 2),
    "Call Type Group": ("call_type_group", 5),
    "Priority": ("priority", 8),
    "Call Type": ("call_type", 31),
    "Zipcode of Incident": ("zipcode", 28),
    "Battalion": ("battalion", 11),
    "Call Final Disposition": ("final_disposition", 15),
    "City": ("city", 9),
    "Station Area": ("station_area", 46),
}


def sf_fire_schema() -> Schema:
    """All-categorical, integer-coded SF Fire table: the 9 of Annamalai et al.'s 10 trimmed
    attributes present in the clean file (Number of Alarms is not). Target: ALS Unit dispatched."""
    return Schema(
        columns=[
            ColumnSpec(new, CATEGORICAL, categories=[str(i) for i in range(k)])
            for new, k in _FIRE_COLS.values()
        ]
    )


def load_sf_fire(data_dir: str = DEFAULT_DATA_DIR, schema: Optional[Schema] = None):
    path = fetch(SF_FIRE, data_dir)
    df = pd.read_csv(path, dtype=str)
    df = df[list(_FIRE_COLS)].rename(columns={k: v[0] for k, v in _FIRE_COLS.items()})
    spec = schema or sf_fire_schema()
    return TabularDataset(df=df.reset_index(drop=True), name="sf_fire_calls", schema=spec)
