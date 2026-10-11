"""Which column the utility evaluation predicts, on every surface that runs a release.

The default used to be the FIRST categorical column. On all five bundled demo tables that is
not the prediction task (gender, home_ownership, contract_type, years_at_company,
education_num), so the console's demo presets and every CLI release on those tables reported
utility for a column nobody wanted to predict. These tests pin the corrected default, the
explicit override, and the refusal of a column that cannot be a target.
"""

import json

import numpy as np
import pandas as pd
import pytest
from click.testing import CliRunner
from fastapi.testclient import TestClient

from synthproof.api.main import app
from synthproof.cli import main
from synthproof.data.dataset import TabularDataset
from synthproof.data.schema import CATEGORICAL, NUMERICAL, ColumnSpec, Schema
from synthproof.frontier.experiment import default_target


def _ds(cols):
    rng = np.random.default_rng(0)
    data, specs = {}, []
    for name, kind in cols:
        if kind == NUMERICAL:
            data[name] = rng.integers(0, 100, 50).astype(float)
            specs.append(ColumnSpec(name, NUMERICAL, lower=0.0, upper=100.0))
        else:
            data[name] = rng.choice(["a", "b"], 50)
            specs.append(ColumnSpec(name, CATEGORICAL, categories=["a", "b"]))
    return TabularDataset(pd.DataFrame(data), schema=Schema(specs))


def test_the_default_is_the_last_categorical_column_not_the_first():
    ds = _ds([("age", NUMERICAL), ("gender", CATEGORICAL), ("readmitted", CATEGORICAL)])
    assert default_target(ds) == "readmitted"


def test_income_wins_wherever_it_sits():
    ds = _ds([("income", CATEGORICAL), ("sex", CATEGORICAL), ("age", NUMERICAL)])
    assert default_target(ds) == "income"


def test_an_explicit_target_overrides_the_default():
    ds = _ds([("gender", CATEGORICAL), ("readmitted", CATEGORICAL)])
    assert default_target(ds, "gender") == "gender"


@pytest.mark.parametrize("bad", ["age", "nope"])
def test_a_numeric_or_unknown_target_is_refused(bad):
    ds = _ds([("age", NUMERICAL), ("readmitted", CATEGORICAL)])
    with pytest.raises(ValueError, match="not a categorical column"):
        default_target(ds, bad)


def test_a_table_with_no_categorical_column_has_no_target():
    assert default_target(_ds([("age", NUMERICAL)])) is None


@pytest.fixture
def credit_csv(tmp_path):
    rng = np.random.default_rng(0)
    n = 1500
    p = tmp_path / "credit.csv"
    pd.DataFrame(
        {
            "age": rng.integers(18, 90, n),
            "home_ownership": rng.choice(["RENT", "OWN"], n),
            "default_risk": rng.choice(["High", "Low"], n),
        }
    ).to_csv(p, index=False)
    return p


def test_the_cli_records_the_default_target_in_the_sheet(credit_csv, tmp_path):
    out = tmp_path / "sheet.json"
    r = CliRunner().invoke(
        main, ["run", "--input", str(credit_csv), "--eps", "1.0", "--out", str(out)]
    )
    assert r.exit_code == 0, r.output
    assert json.loads(out.read_text(encoding="utf-8"))["target_column"] == "default_risk"


def test_the_cli_honours_target(credit_csv, tmp_path):
    out = tmp_path / "sheet.json"
    r = CliRunner().invoke(
        main,
        ["run", "--input", str(credit_csv), "--eps", "1.0", "--out", str(out)]
        + ["--target", "home_ownership"],
    )
    assert r.exit_code == 0, r.output
    assert json.loads(out.read_text(encoding="utf-8"))["target_column"] == "home_ownership"


def test_the_cli_refuses_a_bad_target_before_spending_anything(credit_csv):
    r = CliRunner().invoke(
        main, ["run", "--input", str(credit_csv), "--eps", "1.0", "--target", "age"]
    )
    assert r.exit_code != 0
    assert "not a categorical column" in r.output
    assert "Traceback" not in r.output


def test_the_api_reports_a_bad_target_over_the_stream():
    res = TestClient(app).post(
        "/api/run",
        json={"dataset": "toy", "mechanism": "independent", "rows": 400, "target": "age"},
    )
    assert res.status_code == 200
    assert "not a categorical column" in res.text
    assert "event: done" not in res.text
