"""ACSIncome (US Census PUMS) via folktables — the second benchmark dataset.

WHY THIS DATASET. UCI Adult is a 1994 extract and the field's default benchmark largely by
inertia. Ding, Hardt, Miller & Schmidt ("Retiring Adult", NeurIPS 2021) built folktables as
its modern replacement: ACSIncome poses the same binary income task on current, far larger
American Community Survey microdata. Running both is what turns a single-dataset result into
a claim about mechanisms rather than about UCI Adult.

THE PROBLEM THIS FILE SOLVES, and it is not the one usually warned about. Advice on ACS for
DP synthesis warns against one-hot encoding, which inflates ACSIncome from 10 features to
~284. That is real but not the binding constraint here, because our mechanisms consume raw
categoricals. The binding constraint is **raw cardinality**:

    OCCP    529 distinct occupation codes
    POBP    219 distinct places of birth
    AGEP     75      WKHP     95      SCHL    24

A single 2-way marginal over OCCP x POBP would be 115,851 cells, and AIM's junction tree
would exceed any sane memory bound — the same failure that killed a full grid run on Adult,
arriving here by a different route.

THE FIX, and why it costs no privacy budget. ACS occupation codes are organised into
documented SOC major groups, and place-of-birth codes into documented ranges (1-56 US states,
60-99 US territories, 100+ foreign). Both groupings are published in the ACS PUMS data
dictionary. Collapsing to them is a **public** transformation: it uses only the code book, not
the data, so it reveals nothing and is charged nothing. That is the same argument the schema's
public numeric bounds rest on.

    OCCP  529 -> 25 SOC major groups
    POBP  219 ->  7 regions
    largest resulting 2-way clique: 600 cells

Anything data-dependent — merging rare occupations by observed frequency, say — would leak and
is deliberately not done.
"""

import hashlib
from dataclasses import dataclass
from typing import List, Optional

import numpy as np
import pandas as pd

from synthproof.data.dataset import TabularDataset
from synthproof.data.schema import CATEGORICAL, NUMERICAL, ColumnSpec, Schema

DEFAULT_STATE = "CA"
DEFAULT_YEAR = "2018"
DEFAULT_ROOT = "data/acs"

# SOC major-group boundaries as published in the ACS PUMS data dictionary. Public code-book
# structure, not a data-derived binning.
OCCP_GROUP_EDGES = [
    10,
    500,
    800,
    1000,
    1300,
    1600,
    2000,
    2100,
    2200,
    2600,
    3000,
    3600,
    3700,
    4000,
    4200,
    4300,
    4700,
    5000,
    6000,
    6200,
    6800,
    7000,
    7700,
    9000,
    9800,
    9840,
]

# POBP ranges: 1-56 US states, 57-99 US territories and abroad-to-citizens, then foreign
# birthplaces by continent block. Also from the published code book.
POBP_REGION_EDGES = [1, 57, 100, 200, 300, 400, 500]

# Ordered to match `acs_income_schema()`. TabularDataset reorders to the schema
# (`df[schema.names]`), so a constant in a different order would silently disagree with the
# frame it claims to describe.
ACS_COLUMNS = [
    "AGEP",
    "WKHP",
    "SCHL",
    "COW",
    "MAR",
    "OCCP",
    "POBP",
    "RELP",
    "SEX",
    "RAC1P",
    "income",
]

# Human-readable names, so a thesis table does not have to print raw PUMS codes.
RACE_LABELS = {
    1: "White",
    2: "Black",
    3: "AmerIndian",
    4: "AlaskaNative",
    5: "AmerIndianAlaska",
    6: "Asian",
    7: "PacificIslander",
    8: "Other",
    9: "TwoOrMore",
}
SEX_LABELS = {1: "Male", 2: "Female"}


@dataclass(frozen=True)
class ACSFingerprint:
    """Identifies exactly which slice of ACS produced a result."""

    state: str
    year: str
    rows_raw: int
    rows_after_task_filter: int
    rows_used: int
    content_sha256: str

    def to_dict(self) -> dict:
        return {
            "dataset": "acs_income",
            "state": self.state,
            "year": self.year,
            "rows_raw": self.rows_raw,
            "rows_after_task_filter": self.rows_after_task_filter,
            "rows_used": self.rows_used,
            "content_sha256": self.content_sha256,
        }


def acs_income_schema() -> Schema:
    """Public schema for the coarsened ACSIncome table.

    Every numeric bound is a publishable fact about the domain — ACS surveys adults, so age
    starts at 17; hours worked per week cannot exceed 99 in the coding — not a value read from
    the data. Categorical domains are the published code sets.
    """
    return Schema(
        [
            ColumnSpec("AGEP", NUMERICAL, lower=17.0, upper=95.0),
            ColumnSpec("WKHP", NUMERICAL, lower=1.0, upper=99.0),
            ColumnSpec("SCHL", NUMERICAL, lower=1.0, upper=24.0),
            ColumnSpec("COW", CATEGORICAL, categories=[str(i) for i in range(1, 9)]),
            ColumnSpec("MAR", CATEGORICAL, categories=[str(i) for i in range(1, 6)]),
            ColumnSpec(
                "OCCP",
                CATEGORICAL,
                categories=[f"soc{i}" for i in range(len(OCCP_GROUP_EDGES) + 1)],
            ),
            ColumnSpec(
                "POBP",
                CATEGORICAL,
                categories=[f"reg{i}" for i in range(len(POBP_REGION_EDGES) + 1)],
            ),
            ColumnSpec("RELP", CATEGORICAL, categories=[str(i) for i in range(0, 18)]),
            ColumnSpec("SEX", CATEGORICAL, categories=list(SEX_LABELS.values())),
            ColumnSpec("RAC1P", CATEGORICAL, categories=list(RACE_LABELS.values())),
            ColumnSpec("income", CATEGORICAL, categories=["<=50K", ">50K"]),
        ]
    )


def _coarsen(feats: pd.DataFrame) -> pd.DataFrame:
    """Applies the published code-book groupings. Uses no information from the data."""
    out = pd.DataFrame(index=feats.index)

    out["AGEP"] = feats["AGEP"].astype(float)
    out["WKHP"] = feats["WKHP"].astype(float)
    out["SCHL"] = feats["SCHL"].astype(float)

    for col in ("COW", "MAR", "RELP"):
        out[col] = feats[col].astype(int).astype(str)

    out["OCCP"] = [f"soc{i}" for i in np.digitize(feats["OCCP"], OCCP_GROUP_EDGES)]
    out["POBP"] = [f"reg{i}" for i in np.digitize(feats["POBP"], POBP_REGION_EDGES)]

    # Mapped to names so H2's subgroup tables are readable. Unknown codes would silently
    # become NaN under .map, so the fallback keeps them as their raw code instead.
    out["SEX"] = feats["SEX"].astype(int).map(SEX_LABELS).fillna(feats["SEX"].astype(str))
    out["RAC1P"] = feats["RAC1P"].astype(int).map(RACE_LABELS).fillna(feats["RAC1P"].astype(str))
    return out


def load_acs_income(
    state: str = DEFAULT_STATE,
    year: str = DEFAULT_YEAR,
    n_rows: Optional[int] = 6000,
    seed: int = 0,
    root_dir: str = DEFAULT_ROOT,
    download: bool = True,
) -> tuple:
    """Loads ACSIncome, coarsened and schema-bound.

    Args:
        n_rows: Subsample size. Defaults to 6,000 for parity with the UCI Adult runs — the
            two datasets must be the same size or a difference between them cannot be
            attributed to the data rather than to n.
        download: Fetch from the Census Bureau if not cached.

    Returns:
        (TabularDataset, ACSFingerprint). The fingerprint records exactly which slice was
        used, since folktables has no pinned checksum of its own.
    """
    try:
        from folktables import ACSDataSource, ACSIncome
    except ImportError as exc:  # pragma: no cover - exercised only without folktables
        raise ImportError(
            "ACSIncome needs folktables:  pip install folktables\n"
            "It downloads American Community Survey microdata from the Census Bureau."
        ) from exc

    source = ACSDataSource(survey_year=year, horizon="1-Year", survey="person", root_dir=root_dir)
    raw = source.get_data(states=[state], download=download)
    rows_raw = len(raw)

    feats, labels, _ = ACSIncome.df_to_pandas(raw)
    rows_after = len(feats)

    df = _coarsen(feats)
    # ACSIncome's own threshold is PINCP > 50000, matching UCI Adult's task so the two are
    # directly comparable.
    df["income"] = np.where(np.asarray(labels).ravel(), ">50K", "<=50K")

    if n_rows is not None and len(df) > n_rows:
        df = df.sample(n=n_rows, random_state=seed).reset_index(drop=True)
    else:
        df = df.reset_index(drop=True)

    df = df[ACS_COLUMNS]
    fingerprint = ACSFingerprint(
        state=state,
        year=year,
        rows_raw=rows_raw,
        rows_after_task_filter=rows_after,
        rows_used=len(df),
        content_sha256=hashlib.sha256(
            pd.util.hash_pandas_object(df, index=False).values.tobytes()  # type: ignore[union-attr]  # pandas-stubs: .values is ndarray for our numeric frames
        ).hexdigest(),
    )

    ds = TabularDataset(df, name=f"acs_income_{state}{year}", schema=acs_income_schema())
    return ds, fingerprint


def informative_numeric_pair() -> List[str]:
    """The column pair used as ACS's structure metric, chosen for parity with Adult.

    Adult's metric is age x hours_per_week; ACSIncome's direct analogues are AGEP x WKHP.
    Using the same pair keeps the two datasets' structure numbers comparable rather than
    measuring whichever pair happens to correlate most strongly on each.
    """
    return ["AGEP", "WKHP"]
