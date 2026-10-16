"""The W10 analysis returns the verdict docs/prereg/W10_h1_confirmatory.md defines, per comparison."""

import json

import numpy as np

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


def test_each_verdict_is_reached_by_the_data_that_should_reach_it(tmp_path):
    rng = np.random.default_rng(0)
    n = 15

    def arm(mean, sd):
        return rng.normal(mean, sd, n)

    plans = {
        # dataset: (aim at eps 1, pairwise at eps 1); eps 8 copies eps 1
        "adult": (arm(0.010, 0.001), arm(0.030, 0.001)),  # clearly AIM lower
        "acs": (arm(0.030, 0.001), arm(0.010, 0.001)),  # clearly pairwise lower
        "bank": (arm(0.020, 0.0005), arm(0.0201, 0.0005)),  # tight and within the margin
        "diabetes": (arm(0.020, 0.02), arm(0.024, 0.02)),  # too noisy to say
    }
    for ds, (aim, pw) in plans.items():
        cells = {}
        for eps in A.EPSILONS:
            cells[("aim", eps)] = aim
            cells[("pairwise", eps)] = pw
            cells[("independent", eps)] = arm(0.09, 0.01)
        _write(tmp_path, ds, cells)

    out = A.analyse(tmp_path, "confirmatory")
    verdicts = {(r["dataset"], r["eps"]): r["verdict"] for r in out["comparisons"]}
    for eps in A.EPSILONS:
        assert verdicts[("adult", eps)] == "AIM lower"
        assert verdicts[("acs", eps)] == "pairwise lower"
        assert verdicts[("bank", eps)] == "equivalent"
        assert verdicts[("diabetes", eps)] == "inconclusive"
    assert out["margin"] == 0.005 and out["tost_alpha"] == 0.05 / 8
    assert len(out["preregistration_sha256"]) == 64
