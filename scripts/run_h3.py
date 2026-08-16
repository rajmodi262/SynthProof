"""H3 — does utility-weighted budget allocation beat uniform allocation?

Preregistered: "Utility-weighted budget allocation across tabular columns yields significantly
higher downstream classifier macro F1 than uniform allocation at fixed total epsilon."

WHERE THE WEIGHTS COME FROM, because this is the whole design question. They are DECLARED, not
measured. The analyst states which columns they care about — here, the prediction target and
the columns a domain expert would name as its predictors — and that statement is public
metadata, exactly like the schema's numeric bounds.

Deriving weights from the data instead (mutual information with the target, variance, a
feature-importance run) would be a data-dependent parameter choice made with an uncharged
query, and every epsilon reported below would be a false statement. That version of H3 is not
testable at any budget and is not what is run here.

Both arms spend the SAME total epsilon; only the split across columns differs. The uniform arm
is the mechanism exactly as every committed H1 result used it, so the comparison is against a
real baseline rather than a strawman.

Usage:
    python -m scripts.run_h3                 # UCI Adult (default)
    python -m scripts.run_h3 --dataset acs   # ACSIncome, CA 2018
"""

import argparse
import json
import time
from dataclasses import asdict as _asdict
from pathlib import Path

import numpy as np

from synthproof.accounting.accountant import Accountant
from synthproof.accounting.calibration import BudgetPlan
from synthproof.data.profiler import DPDomainProfiler
from synthproof.evaluate.utility import UtilityEvaluator
from synthproof.frontier.experiment import bootstrap_ci
from synthproof.generators.independent import IndependentMarginalGenerator

N_ROWS = 6000
EPS_GRID = (0.5, 1.0, 2.0, 4.0, 8.0)
SEEDS = (0, 1, 2, 3, 4)

# The weight the analyst assigns to columns they have declared as mattering for the task.
# A single value keeps the comparison one-dimensional: this is "weighted vs uniform", not a
# search over weightings, which would be a different (and multiplicity-laden) study.
PRIORITY_WEIGHT = 4.0

DATASETS = {
    "adult": {
        "target_col": "income",
        # Declared by domain knowledge about what predicts income, NOT measured from the
        # table. A different analyst could reasonably name a different set; that is the point
        # of it being a declaration.
        "priority_cols": ("income", "education", "hours_per_week", "occupation"),
        "out": "results/h3_allocation.json",
        "label": "UCI Adult",
    },
    "acs": {
        "target_col": "income",
        "priority_cols": ("income", "SCHL", "WKHP", "OCCP"),
        "out": "results/acs/h3_allocation.json",
        "label": "ACSIncome (CA 2018)",
    },
}


def _load(name: str):
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


def run_arm(ds, eps, seed, target_col, weights):
    """One release. `weights=None` is the uniform arm.

    Returns (macro F1 on a held-out real split, epsilon the accountant actually composed).
    """
    plan = BudgetPlan.split(eps, delta=1e-5, profile_frac=0.1)
    acc = Accountant(budget_eps=eps * 1.02, budget_delta=1e-5)
    profile = DPDomainProfiler(accountant=acc, eps_budget=plan.profile_eps).profile(ds, seed=seed)

    gen = IndependentMarginalGenerator(seed=seed, column_weights=weights)
    gen.fit(ds, profile, acc, target_eps=plan.synthesis_eps)
    synth = gen.generate(num_samples=ds.num_rows)

    ev = UtilityEvaluator(target_col=target_col, seed=seed).evaluate(ds.df, synth)
    return float(ev.tstr_macro_f1), float(acc.total())


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset", default="adult", choices=sorted(DATASETS))
    args = ap.parse_args()

    cfg = DATASETS[args.dataset]
    ds = _load(args.dataset)
    target = cfg["target_col"]
    priority = [c for c in cfg["priority_cols"] if c in ds.columns]
    missing = [c for c in cfg["priority_cols"] if c not in ds.columns]

    weights = {c: PRIORITY_WEIGHT for c in priority}

    print(f"dataset: {cfg['label']}  n={ds.num_rows} x {ds.num_cols}")
    print(f"target: {target!r}")
    print(f"priority columns (DECLARED, weight {PRIORITY_WEIGHT}): {priority}")
    if missing:
        print(f"  WARNING: declared but absent from the table: {missing}")
    print("other columns keep weight 1.0. Both arms spend the same total epsilon.\n")

    t0 = time.time()
    cells = []
    for eps in EPS_GRID:
        arms = {}
        for arm, w in (("uniform", None), ("weighted", weights)):
            f1s, proved = [], []
            for seed in SEEDS:
                f1, p = run_arm(ds, eps, seed, target, w)
                f1s.append(f1)
                proved.append(p)
            arms[arm] = {
                "tstr_f1": _asdict(bootstrap_ci(f1s)),
                "proved_eps": float(np.mean(proved)),
                "per_seed_f1": f1s,
            }

        # Paired difference: same seeds, same data, only the allocation differs.
        diffs = [
            w - u
            for w, u in zip(
                arms["weighted"]["per_seed_f1"], arms["uniform"]["per_seed_f1"], strict=True
            )
        ]
        gap = bootstrap_ci(diffs)
        supports = gap.lo > 0.0

        cells.append(
            {
                "target_eps": eps,
                "uniform": arms["uniform"],
                "weighted": arms["weighted"],
                "paired_gap": _asdict(gap),
                "supports_h3": bool(supports),
            }
        )
        print(
            f"  eps={eps:<5} uniform F1={arms['uniform']['tstr_f1']['mean']:.4f}   "
            f"weighted F1={arms['weighted']['tstr_f1']['mean']:.4f}   "
            f"gap={gap.mean:+.4f} [{gap.lo:+.4f}, {gap.hi:+.4f}]   "
            f"{'SUPPORTS H3' if supports else 'no'}"
        )

    elapsed = time.time() - t0
    n_support = sum(c["supports_h3"] for c in cells)
    verdict = (
        f"H3 is SUPPORTED at {n_support} of {len(cells)} epsilon values: the paired "
        "weighted-minus-uniform gap in TSTR macro F1 has a bootstrap CI strictly above zero."
        if n_support
        else (
            f"H3 is NOT SUPPORTED. At none of the {len(cells)} epsilon values does the paired "
            "weighted-minus-uniform gap have a bootstrap CI excluding zero. Declaring which "
            "columns matter and spending more of a fixed budget on them did not measurably "
            "improve downstream macro F1 for this mechanism."
        )
    )
    print(f"\n{verdict}")

    payload = {
        "dataset": args.dataset,
        "dataset_label": cfg["label"],
        "hypothesis": (
            "Utility-weighted budget allocation across tabular columns yields significantly "
            "higher downstream classifier macro F1 than uniform allocation at fixed total eps."
        ),
        "n_rows": ds.num_rows,
        "mechanism": "independent",
        "target_col": target,
        "priority_cols": priority,
        "priority_weight": PRIORITY_WEIGHT,
        "weights_source": "declared-public",
        "eps_grid": list(EPS_GRID),
        "seeds": list(SEEDS),
        "elapsed_seconds": round(elapsed, 1),
        "cells": cells,
        "verdict": verdict,
    }
    Path(cfg["out"]).parent.mkdir(parents=True, exist_ok=True)
    with open(cfg["out"], "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"wrote {cfg['out']}")


if __name__ == "__main__":
    main()
