"""M2.11 — does DP synthesis degrade downstream utility unevenly across subgroups?

THE HALF OF THE SUBGROUP STORY H2 DOES NOT MEASURE. H2 asks whether minority subgroups *leak*
more and returns a bounded null. Its parent paper — Ganev, Oprisanu & De Cristofaro, "Robin
Hood and Matthew Effects", ICML 2022 — is about the adjacent and better-established question:
whether DP synthesis costs some subgroups more *accuracy* than others. Measuring the leakage
half and none of the accuracy half left the subgroup story missing the side the literature
actually settled, and an examiner who knows that paper will ask.

WHAT IS REPORTED, AND WHY IT IS A GAP RATHER THAN A SCORE. Every subgroup is scored against
**its own TRTR baseline**, because raw per-subgroup TSTR mostly measures how hard the task is
for that group. `baseline_spread` — the same spread measured on real data — is the control: if
it is comparable to `gap_spread`, the disparity belongs to the task and not to synthesis, and
no claim about DP may be made from it.

PROTOCOL, held identical to H1 and H2 so the three are comparable: n = 6,000, the same seeds,
`pairwise`, and the same declared subgroup attributes. Utility is scored on the CANARY-FREE
release, for the reason recorded in the contamination finding — canaries move the joint
distribution and would penalise exactly the mechanisms that model it.

Run:

    python scripts/run_fairness.py            # both datasets
    python scripts/run_fairness.py adult      # one
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from synthproof.evaluate.fairness import SubgroupUtilityEvaluator  # noqa: E402
from synthproof.frontier.experiment import run_cell  # noqa: E402

N_ROWS = 6000
EPS_GRID = (1.0, 8.0)
SEEDS = (0, 1, 2)
MECHANISM = "pairwise"

DATASETS = {
    "adult": {
        "attributes": ("sex", "race"),
        "target": "income",
        "out": "results/fairness.json",
        "label": "UCI Adult",
    },
    "acs": {
        "attributes": ("SEX", "RAC1P"),
        "target": "income",  # the ACS loader renames PINCP to match Adult, so H1/H2/M2.11 align
        "out": "results/acs/fairness.json",
        "label": "ACSIncome (CA 2018)",
    },
}


def _load(name: str):
    """Identical loading to run_h1/run_h2 so all three speak about the same rows."""
    if name == "adult":
        from synthproof.data.datasets import load_adult

        ds = load_adult()
        ds.df = ds.df.sample(n=N_ROWS, random_state=0).reset_index(drop=True)
        return ds
    if name == "acs":
        from synthproof.data.acs import load_acs_income

        ds, _ = load_acs_income(n_rows=N_ROWS, seed=0, download=True)
        return ds
    raise SystemExit(f"Unknown dataset {name!r}. Choose from {sorted(DATASETS)}.")


def _mean_ci(values, n_boot=2000, seed=0):
    """Bootstrapped mean and 95% interval. Never a bare mean -- project-wide discipline."""
    arr = np.asarray([v for v in values if v is not None and np.isfinite(v)], dtype=float)
    if arr.size == 0:
        return {"mean": None, "lo": None, "hi": None, "n": 0}
    rng = np.random.default_rng(seed)
    boots = rng.choice(arr, size=(n_boot, arr.size), replace=True).mean(axis=1)
    return {
        "mean": float(arr.mean()),
        "lo": float(np.percentile(boots, 2.5)),
        "hi": float(np.percentile(boots, 97.5)),
        "n": int(arr.size),
    }


def run_cell_fairness(ds, attribute, target, eps, seed):
    """One release, scored per subgroup on the canary-free utility fit."""
    res = run_cell(
        ds,
        MECHANISM,
        float(eps),
        seed=seed,
        delta=1e-5,
        num_canaries=60,
        target_col=target,
        return_artifacts=True,
    )
    # `_synth` is the UTILITY release -- the canary-free one. Using `_audit_synth` here would
    # reintroduce the contamination the project already found and fixed.
    # TRTR trains on the fit split -- data the generator already saw, so no evaluation row is
    # reused -- and BOTH models are scored on the ENTIRE holdout. Carving a further test split
    # out of the holdout left rare race groups with 2-11 rows and four of five unreliable.
    return SubgroupUtilityEvaluator(target_col=target, subgroup_col=attribute, seed=seed).evaluate(
        res["_holdout_df"], res["_synth"], real_train_df=res["_fit_df"]
    )


def main() -> None:
    names = sys.argv[1:] or list(DATASETS)
    for name in names:
        cfg = DATASETS[name]
        ds = _load(name)
        started = time.time()
        print(f"\n=== {cfg['label']} — subgroup utility ===")

        cells = []
        for attribute in cfg["attributes"]:
            if attribute not in ds.df.columns:
                print(f"  SKIP {attribute}: not a column in this dataset")
                continue
            for eps in EPS_GRID:
                per_group: dict[str, dict[str, list]] = {}
                spreads, baselines = [], []
                for seed in SEEDS:
                    r = run_cell_fairness(ds, attribute, cfg["target"], eps, seed)
                    spreads.append(r.gap_spread)
                    baselines.append(r.baseline_spread)
                    for s in r.subgroups:
                        acc = per_group.setdefault(
                            s.subgroup,
                            {
                                "gap": [],
                                "tstr": [],
                                "trtr": [],
                                "n": [],
                                "share": s.population_share,
                                "reliable": [],
                            },
                        )
                        acc["gap"].append(s.utility_gap)
                        acc["tstr"].append(s.tstr_macro_f1)
                        acc["trtr"].append(s.trtr_macro_f1)
                        acc["n"].append(s.num_test_rows)
                        acc["reliable"].append(s.is_reliable)
                    print(f"  {attribute} eps={eps} seed={seed}: spread={r.gap_spread}")

                cells.append(
                    {
                        "attribute": attribute,
                        "target_eps": float(eps),
                        "seeds": list(SEEDS),
                        "gap_spread": _mean_ci(spreads),
                        "baseline_spread": _mean_ci(baselines),
                        "subgroups": [
                            {
                                "subgroup": g,
                                "population_share": v["share"],
                                "mean_test_rows": float(np.mean(v["n"])),
                                # A group unreliable on ANY seed is reported unreliable. The
                                # conservative direction: a wide interval must not be laundered
                                # into a narrow one by averaging across seeds.
                                "reliable": bool(all(v["reliable"])),
                                "utility_gap": _mean_ci(v["gap"]),
                                "tstr_macro_f1": _mean_ci(v["tstr"]),
                                "trtr_macro_f1": _mean_ci(v["trtr"]),
                            }
                            for g, v in sorted(per_group.items())
                        ],
                    }
                )

        payload = {
            "dataset": name,
            "dataset_label": cfg["label"],
            "n_rows": N_ROWS,
            "mechanism": MECHANISM,
            "target": cfg["target"],
            "attributes": list(cfg["attributes"]),
            "eps_grid": list(EPS_GRID),
            "seeds": list(SEEDS),
            "utility_measured_on": "canary_free_fit",
            "note": (
                "Every subgroup is scored against its own TRTR baseline; the reported number "
                "is the gap. `baseline_spread` is the same spread on real data and is the "
                "control -- if it is comparable to `gap_spread`, the disparity belongs to the "
                "task rather than to synthesis."
            ),
            "elapsed_seconds": round(time.time() - started, 1),
            "cells": cells,
        }
        out = ROOT / cfg["out"]
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(f"  wrote {cfg['out']}  ({len(cells)} cells, {payload['elapsed_seconds']}s)")


if __name__ == "__main__":
    main()
