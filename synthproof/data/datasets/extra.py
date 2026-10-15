"""Further UCI benchmarks: Mushroom, Nursery, German Credit, Wine Quality, BCW."""

import io
import zipfile
from typing import Optional

import pandas as pd

from synthproof.data.dataset import TabularDataset
from synthproof.data.datasets._source import (
    DEFAULT_DATA_DIR,
    DatasetSource,
    fetch,
)
from synthproof.data.schema import CATEGORICAL, NUMERICAL, ColumnSpec, Schema

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
            ColumnSpec(
                "duration", NUMERICAL, lower=0.0, upper=80.0
            ),  # was the observed max 72 (C2)
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
