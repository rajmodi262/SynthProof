"""Tests for public schema declarations and CSV ingestion."""

import json

import pandas as pd
import pytest

from synthproof.data.dataset import TabularDataset
from synthproof.data.schema import CATEGORICAL, NUMERICAL, ColumnSpec, Schema


def test_numerical_column_requires_public_bounds():
    """The whole point: a numeric domain must be declared, not measured."""
    with pytest.raises(ValueError, match="require public"):
        ColumnSpec("age", NUMERICAL)


def test_bounds_must_be_ordered():
    with pytest.raises(ValueError, match="lower"):
        ColumnSpec("age", NUMERICAL, lower=70.0, upper=18.0)


def test_unknown_kind_rejected():
    with pytest.raises(ValueError, match="kind must be"):
        ColumnSpec("age", "continuous", lower=0.0, upper=1.0)


def test_width_is_the_basis_for_sensitivity():
    assert ColumnSpec("age", NUMERICAL, lower=0.0, upper=120.0).width == 120.0
    with pytest.raises(ValueError, match="categorical"):
        _ = ColumnSpec("c", CATEGORICAL, categories=["a"]).width


def test_schema_rejects_duplicate_columns():
    with pytest.raises(ValueError, match="Duplicate"):
        Schema([ColumnSpec("a", CATEGORICAL), ColumnSpec("a", CATEGORICAL)])


def test_schema_roundtrips_through_json(tmp_path):
    schema = Schema([
        ColumnSpec("age", NUMERICAL, lower=0.0, upper=120.0),
        ColumnSpec("city", CATEGORICAL, categories=["pune", "delhi"]),
    ])
    p = tmp_path / "schema.json"
    schema.to_json(str(p))

    back = Schema.from_json(str(p))
    assert back.names == ["age", "city"]
    assert back["age"].upper == 120.0
    assert back["city"].categories == ["pune", "delhi"]
    assert json.loads(schema.to_json())["columns"][0]["kind"] == NUMERICAL


def test_clipping_uses_declared_bounds_not_observed_ones():
    """Values beyond the public range are clipped, so extremes never reach a mechanism."""
    df = pd.DataFrame({"age": [-5, 30, 500], "grp": ["a", "b", "a"]})
    schema = Schema([
        ColumnSpec("age", NUMERICAL, lower=0.0, upper=120.0),
        ColumnSpec("grp", CATEGORICAL, categories=["a", "b"]),
    ])
    ds = TabularDataset(df, schema=schema)

    assert ds.df["age"].min() == 0.0
    assert ds.df["age"].max() == 120.0
    assert ds.bounds("age") == (0.0, 120.0)
    assert ds.bounds("grp") is None


def test_undeclared_categories_go_to_a_sentinel():
    """An unexpected value must not silently widen the domain the release commits to."""
    df = pd.DataFrame({"grp": ["a", "b", "surprise"]})
    ds = TabularDataset(df, schema=Schema([
        ColumnSpec("grp", CATEGORICAL, categories=["a", "b"])
    ]))
    assert set(ds.df["grp"]) == {"a", "b", "__OTHER__"}


def test_schema_selects_and_orders_columns():
    df = pd.DataFrame({"z": [1, 2], "a": ["x", "y"], "ignored": [9, 9]})
    ds = TabularDataset(df, schema=Schema([
        ColumnSpec("a", CATEGORICAL), ColumnSpec("z", NUMERICAL, lower=0.0, upper=10.0)
    ]))
    assert ds.columns == ["a", "z"]


def test_missing_declared_column_is_an_error():
    with pytest.raises(ValueError, match="absent from data"):
        TabularDataset(pd.DataFrame({"a": [1]}),
                       schema=Schema([ColumnSpec("nope", CATEGORICAL)]))


def test_from_csv_roundtrip(tmp_path):
    csv = tmp_path / "people.csv"
    csv.write_text("age,income,city\n34,50000,pune\n61,120000,delhi\n", encoding="utf-8")

    schema = Schema([
        ColumnSpec("age", NUMERICAL, lower=0.0, upper=120.0),
        ColumnSpec("income", NUMERICAL, lower=0.0, upper=1e6),
        ColumnSpec("city", CATEGORICAL, categories=["pune", "delhi"]),
    ])
    ds = TabularDataset.from_csv(str(csv), schema=schema)

    assert ds.name == "people"
    assert ds.num_rows == 2
    assert ds.numerical_cols == ["age", "income"]
    assert ds.categorical_cols == ["city"]


def test_from_csv_drops_incomplete_rows(tmp_path):
    csv = tmp_path / "gappy.csv"
    csv.write_text("a,b\n1,x\n,y\n3,z\n", encoding="utf-8")
    assert TabularDataset.from_csv(str(csv)).num_rows == 2


def test_infer_nonprivate_produces_a_usable_schema():
    df = pd.DataFrame({"v": range(50), "g": ["a", "b"] * 25})
    schema = Schema.infer_nonprivate(df)
    assert schema["v"].kind == NUMERICAL
    assert schema["g"].kind == CATEGORICAL
    assert schema["v"].lower == 0.0 and schema["v"].upper == 49.0


def test_toy_dataset_now_carries_a_schema():
    ds = TabularDataset.create_synthetic_toy(50)
    assert ds.schema is not None
    assert ds.numerical_cols == ["age", "income"]
    assert ds.categorical_cols == ["category"]
    # Clipped to the declared public range, not to whatever the sample happened to produce.
    assert ds.df["age"].between(18, 70).all()


def test_dataset_without_schema_still_works():
    """The schema-free fallback stays available for tests and exploration."""
    df = pd.DataFrame({"n": range(30), "c": ["a"] * 30})
    ds = TabularDataset(df)
    assert ds.schema is None
    assert ds.numerical_cols == ["n"]
    assert ds.categorical_cols == ["c"]
