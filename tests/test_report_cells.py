"""Regression: report generators must average per-seed cells, not keep the last seed."""

from scripts._cells import seed_mean_cells


def _cell(mech, eps, tstr, trtr=0.8, n=1):
    iv = lambda v: {"mean": v, "lo": v, "hi": v, "sd": 0.0, "n": n}  # noqa: E731
    return {
        "mechanism": mech,
        "target_eps": eps,
        "seeds": n,
        "tstr_f1": iv(tstr),
        "trtr_f1": iv(trtr),
        "correlation_error": iv(float("nan")),
    }


def test_per_seed_cells_are_averaged_not_overwritten():
    cells = [_cell("mst", 1.0, v) for v in (0.2, 0.4, 0.6)]  # last seed = 0.6, mean = 0.4
    out = seed_mean_cells(cells)
    assert len(out) == 1
    assert abs(out[0]["tstr_f1"]["mean"] - 0.4) < 1e-12
    assert out[0]["tstr_f1"]["n"] == 3 and out[0]["seeds"] == 3


def test_aggregated_cells_pass_through_and_nan_is_skipped():
    agg = [_cell("aim", 2.0, 0.5, n=5), _cell("mst", 2.0, 0.7, n=5)]
    assert seed_mean_cells(agg) == agg
    merged = seed_mean_cells([_cell("aim", 1.0, 0.3), _cell("aim", 1.0, 0.5)])[0]
    assert (
        merged["correlation_error"]["mean"] != merged["correlation_error"]["mean"]
    )  # stays NaN, not 0
