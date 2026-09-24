"""Audit C2 (research/27): a "public" numeric bound must not be read off the data.

A declared bound equal to the table's own non-zero extreme is a data-derived domain wearing a
public label -- the leak Ganev et al. (ICLR-W 2025) demonstrate (attack AUC 1.0), and one our
own RB6 cannot see because the sheet says "public". A zero floor is a physical limit, not an
observation. The allowlist holds bounds that are public for a stated reason; the loader clips
to them or a codebook fixes them, so equality with the data is by construction.
"""

import pytest

from synthproof.data.datasets import load

ALLOWED = {
    ("texas", "LENGTH_OF_STAY"): "loader clips stays to one year",
    ("texas", "TOTAL_CHARGES"): "loader clips charges at $1M",
    ("diabetes", "time_in_hospital"): "1-14 days is the cohort inclusion criterion (Strack 2014)",
    ("german", "installment_rate"): "codebook: installment rate is coded 1-4",
    ("bank", "campaign"): "codebook: contacts this campaign, including the last one, so >= 1",
}


@pytest.mark.parametrize("name", ["adult", "bank", "diabetes", "texas", "german", "wine", "bcw"])
def test_no_declared_bound_equals_a_nonzero_observed_extreme(name):
    ds = load(name)
    offenders = []
    for col in ds.numerical_cols:
        if (name, col) in ALLOWED:
            continue
        lo, hi = ds.bounds(col)
        mn, mx = float(ds.df[col].min()), float(ds.df[col].max())
        if lo == mn and lo != 0.0:
            offenders.append(f"{col}: lower {lo:g} == observed min")
        if hi == mx and hi != 0.0:
            offenders.append(f"{col}: upper {hi:g} == observed max")
    assert not offenders, f"{name}: data-derived bounds declared public: {offenders}"
