"""Unit tests for missingness injection and the four imputation arms."""

import numpy as np
import pandas as pd
import pytest

from synthproof.accounting.accountant import Accountant
from synthproof.data.imputation import (
    MISSING_CATEGORY_LABEL,
    bounded_shifted_sum,
    complete_case_drop,
    dp_charged_impute,
    dp_charged_knn_impute,
    impute_arm,
    knn_impute,
    sentinel_impute,
    uncharged_impute,
)
from synthproof.data.missingness import (
    inject_mar,
    inject_mcar,
    inject_missingness,
    inject_mnar,
    load_adult_raw,
)
from synthproof.data.schema import CATEGORICAL, NUMERICAL, ColumnSpec, Schema


@pytest.fixture
def toy_schema() -> Schema:
    return Schema(
        columns=[
            ColumnSpec("age", NUMERICAL, lower=10.0, upper=90.0),
            ColumnSpec("income", NUMERICAL, lower=0.0, upper=1000.0),
            ColumnSpec("job", CATEGORICAL, categories=["doctor", "engineer", "artist"]),
            ColumnSpec("city", CATEGORICAL, categories=["paris", "tokyo", "nyc"]),
        ]
    )


@pytest.fixture
def toy_data_with_missing() -> pd.DataFrame:
    # 10 rows, some missing entries
    data = {
        "age": [25.0, np.nan, 45.0, 30.0, np.nan, 60.0, 70.0, 35.0, 50.0, 40.0],
        "income": [100.0, 200.0, np.nan, 400.0, 500.0, np.nan, 700.0, 300.0, 450.0, 350.0],
        "job": [
            "doctor",
            "engineer",
            "engineer",
            np.nan,
            "artist",
            "doctor",
            "doctor",
            np.nan,
            "doctor",
            "engineer",
        ],
        "city": [
            "paris",
            "paris",
            np.nan,
            "tokyo",
            "nyc",
            "nyc",
            "paris",
            "tokyo",
            np.nan,
            "paris",
        ],
    }
    return pd.DataFrame(data)


def test_complete_case_drop(toy_data_with_missing):
    clean = complete_case_drop(toy_data_with_missing)
    assert clean.isna().sum().sum() == 0
    assert len(clean) < len(toy_data_with_missing)
    # Rows with any NaN dropped (rows 0, 6, 9 are complete)
    assert len(clean) == 3


def test_sentinel_impute(toy_data_with_missing, toy_schema):
    imputed = sentinel_impute(toy_data_with_missing, toy_schema)
    assert imputed.isna().sum().sum() == 0
    assert len(imputed) == len(toy_data_with_missing)

    # Numerical missing should be midpoint
    assert imputed.loc[1, "age"] == (10.0 + 90.0) / 2.0  # 50.0
    assert imputed.loc[2, "income"] == (0.0 + 1000.0) / 2.0  # 500.0

    # Categorical missing should be sentinel
    assert imputed.loc[3, "job"] == MISSING_CATEGORY_LABEL
    assert imputed.loc[2, "city"] == MISSING_CATEGORY_LABEL


def test_uncharged_impute(toy_data_with_missing, toy_schema):
    imputed = uncharged_impute(toy_data_with_missing, toy_schema)
    assert imputed.isna().sum().sum() == 0
    assert len(imputed) == len(toy_data_with_missing)

    # Mode of job: doctor (count=4), engineer (count=3), artist (count=1) -> doctor
    assert imputed.loc[3, "job"] == "doctor"
    # Mode of city: paris (count=4), tokyo (count=2), nyc (count=2) -> paris
    assert imputed.loc[2, "city"] == "paris"

    # Mean of age (the same estimator as A3): [25, 45, 30, 60, 70, 35, 50, 40] -> 44.375
    assert imputed.loc[1, "age"] == pytest.approx(44.375)


def test_dp_charged_impute(toy_data_with_missing, toy_schema):
    acc = Accountant(budget_eps=1.0, budget_delta=1e-5)
    prior_eps = acc.total()
    assert prior_eps == 0.0
    assert len(acc.spends) == 0

    imputed = dp_charged_impute(
        toy_data_with_missing,
        toy_schema,
        accountant=acc,
        eps_imp=0.2,
        seed=123,
    )
    assert imputed.isna().sum().sum() == 0
    assert len(imputed) == len(toy_data_with_missing)

    # Accountant MUST have recorded charges and total epsilon must increase
    assert acc.total() > 0.0
    assert len(acc.spends) > 0

    # Numerical imputed values must fall strictly within bounds
    assert toy_schema["age"].lower <= imputed["age"].min()
    assert imputed["age"].max() <= toy_schema["age"].upper


def test_a3_sum_sensitivity_is_the_width_it_is_charged_at():
    # Under add/remove-one the noisy sum moves by at most the charged sensitivity (upper - lower).
    # A raw sum of clipped values moves by up to max(|lower|, |upper|): 100 here, charged as 85.
    lo, hi = 15.0, 100.0
    base = np.array([20.0, 40.0, 60.0])
    worst = max(
        abs(bounded_shifted_sum(np.append(base, x), lo, hi) - bounded_shifted_sum(base, lo, hi))
        for x in (lo, hi, 50.0, 1e6, -1e6)
    )
    assert worst <= hi - lo


def test_a3_categorical_never_releases_an_undeclared_value(toy_schema):
    # "zzz" is the most common observed job but is not in the declared domain. A candidate set
    # read off the data would release it; the declared-only set cannot.
    df = pd.DataFrame(
        {
            "age": [30.0] * 8,
            "income": [100.0] * 8,
            "job": ["zzz"] * 5 + ["doctor", np.nan, np.nan],
            "city": ["paris"] * 8,
        }
    )
    for seed in range(5):
        acc = Accountant(budget_eps=1000.0, budget_delta=1e-5)
        out = dp_charged_impute(df, toy_schema, accountant=acc, eps_imp=500.0, seed=seed)
        assert set(out.loc[[6, 7], "job"]) <= set(toy_schema["job"].categories)


def test_a4_charged_votes_use_laplace_two_over_eps(toy_data_with_missing, toy_schema):
    acc = Accountant(budget_eps=10.0, budget_delta=1e-5)
    dp_charged_knn_impute(toy_data_with_missing, toy_schema, accountant=acc, eps_imp=0.4, k=3)
    votes = [s.mechanism for s in acc.spends if s.mechanism.metadata.get("column") == "job"]
    assert len(votes) == 1
    n_missing = int(toy_data_with_missing["job"].isna().sum())
    eps_per_query = 0.4 / 4 / n_missing  # 4 columns have missing cells
    assert votes[0].noise_scale == pytest.approx(2.0 / eps_per_query)


def test_knn_impute(toy_data_with_missing, toy_schema):
    imputed = knn_impute(toy_data_with_missing, toy_schema, k=3)
    assert imputed.isna().sum().sum() == 0
    assert len(imputed) == len(toy_data_with_missing)

    # Imputed categoricals must be valid categories
    assert imputed.loc[3, "job"] in toy_schema["job"].categories
    assert imputed.loc[2, "city"] in toy_schema["city"].categories

    # Imputed numerics must fall within bounds
    assert toy_schema["age"].lower <= imputed["age"].min()
    assert imputed["age"].max() <= toy_schema["age"].upper


def test_dp_charged_knn_impute(toy_data_with_missing, toy_schema):
    acc = Accountant(budget_eps=1.0, budget_delta=1e-5)
    assert acc.total() == 0.0

    imputed = dp_charged_knn_impute(
        toy_data_with_missing,
        toy_schema,
        accountant=acc,
        eps_imp=0.2,
        k=3,
        seed=123,
    )
    assert imputed.isna().sum().sum() == 0
    assert len(imputed) == len(toy_data_with_missing)

    # Accountant MUST record spends
    assert acc.total() > 0.0
    assert len(acc.spends) > 0

    # Bounds respected
    assert toy_schema["age"].lower <= imputed["age"].min()
    assert imputed["age"].max() <= toy_schema["age"].upper


def test_impute_arm_dispatch(toy_data_with_missing, toy_schema):
    acc = Accountant(budget_eps=1.0, budget_delta=1e-5)

    # Test all 6 arms via unified function
    a0 = impute_arm("A0", toy_data_with_missing, toy_schema)
    assert a0.isna().sum().sum() == 0

    a1 = impute_arm("A1", toy_data_with_missing, toy_schema)
    assert a1.isna().sum().sum() == 0

    a2 = impute_arm("A2", toy_data_with_missing, toy_schema)
    assert a2.isna().sum().sum() == 0
    # A2 leaves accountant untouched!
    assert acc.total() == 0.0

    a3 = impute_arm("A3", toy_data_with_missing, toy_schema, accountant=acc, eps_imp=0.1)
    assert a3.isna().sum().sum() == 0
    assert acc.total() > 0.0

    # A4: uncharged k-NN leaves accountant untouched
    acc2 = Accountant(budget_eps=1.0, budget_delta=1e-5)
    a4 = impute_arm("A4", toy_data_with_missing, toy_schema)
    assert a4.isna().sum().sum() == 0
    assert acc2.total() == 0.0

    # A4_CHARGED: charges accountant
    a4_c = impute_arm("A4_CHARGED", toy_data_with_missing, toy_schema, accountant=acc2, eps_imp=0.1)
    assert a4_c.isna().sum().sum() == 0
    assert acc2.total() > 0.0

    # Negative controls: A3 and A4_CHARGED without accountant should raise
    with pytest.raises(ValueError, match="requires an active Accountant"):
        impute_arm("A3", toy_data_with_missing, toy_schema, accountant=None)

    with pytest.raises(ValueError, match="requires an active Accountant"):
        impute_arm("A4_CHARGED", toy_data_with_missing, toy_schema, accountant=None)


def test_missingness_injectors():
    df = pd.DataFrame(
        {
            "age": np.linspace(20, 70, 100),
            "income": np.linspace(1000, 5000, 100),
            "cat": ["A", "B", "C", "D"] * 25,
        }
    )

    # MCAR
    mcar = inject_mcar(df, rate=0.2, seed=42)
    assert mcar.isna().sum().sum() > 0
    assert 0.10 < (mcar.isna().mean().mean()) < 0.30

    # MAR
    mar = inject_mar(df, rate=0.2, observed_col="age", seed=42)
    assert mar.isna().sum().sum() > 0

    # MNAR
    mnar = inject_mnar(df, rate=0.2, seed=42)
    assert mnar.isna().sum().sum() > 0

    # Dispatcher
    disp = inject_missingness(df, mechanism="mcar", rate=0.15, seed=42)
    assert disp.isna().sum().sum() > 0


def test_load_adult_raw():
    raw_ds = load_adult_raw()
    assert raw_ds.name == "uci_adult_raw"
    assert len(raw_ds.df) == 32561
    # Check that missingness exists in raw Adult
    assert raw_ds.df["workclass"].isna().sum() > 0
    assert raw_ds.df["occupation"].isna().sum() > 0
