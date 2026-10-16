"""The W10 analysis returns the verdict docs/prereg/W10_h1_confirmatory.md defines."""

import json

import numpy as np
import pytest

from scripts import analyse_h1_confirmatory as A


def _write(root, ds, cells):
    d = root / "h1_confirmatory" / f"{ds}_cells"
    d.mkdir(parents=True)
    i = 0
    for (mech, eps), values in cells.items():
        for seed, v in enumerate(values):
            cfg = {"mechanism": mech, "target_eps": eps, "seed": 100 + seed}
            payload = {"config": cfg, "metrics": {"correlation_error": float(v)}, "completed": True}
            (d / f"cell_{i:04d}.json").write_text(json.dumps(payload))
            i += 1


@pytest.mark.parametrize(
    "aim, pairwise, verdict",
    [
        ((0.010, 0.001), (0.030, 0.001), "AIM lower"),
        ((0.030, 0.001), (0.010, 0.001), "pairwise lower"),
        ((0.020, 0.0005), (0.0201, 0.0005), "equivalent"),  # tight and within the margin
        ((0.020, 0.02), (0.024, 0.02), "inconclusive"),  # too noisy to say
    ],
)
def test_each_verdict_is_reached_by_the_data_that_should_reach_it(tmp_path, aim, pairwise, verdict):
    rng = np.random.default_rng(0)
    for ds in A.DATASETS:
        cells = {}
        for eps in A.EPSILONS:
            cells[("aim", eps)] = rng.normal(*aim, 15)
            cells[("pairwise", eps)] = rng.normal(*pairwise, 15)
            cells[("independent", eps)] = rng.normal(0.09, 0.01, 15)
        _write(tmp_path, ds, cells)
    out = A.analyse(tmp_path, "confirmatory")
    assert [r["verdict"] for r in out["comparisons"]] == [verdict] * A.N_COMPARISONS
    assert out["margin"] == 0.005 and out["tost_alpha"] == 0.05 / A.N_COMPARISONS
    assert len(out["preregistration_sha256"]) == 64 and len(out["amendments_sha256"]) == 64


def test_the_amended_design_is_the_one_comparison_the_pilot_left_open():
    assert (A.DATASETS, A.EPSILONS, A.N_COMPARISONS) == (("adult",), (8.0,), 1)
