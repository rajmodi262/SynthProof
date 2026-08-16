"""H2 — does privacy leakage differ across demographic subgroups?

Preregistered: "Under uniform DP budget allocation, empirical audited privacy loss is
significantly higher for minority demographic subgroups than for majority groups."

Canaries are planted stratified by subgroup with EQUAL allocation, which deliberately
oversamples rare groups so each gets a comparable audit ceiling — proportional allocation
would give the rare groups H2 is about the weakest instrument, which is exactly backwards.

ONE CROSS-DATASET CAVEAT, and it must be read alongside any Adult-vs-ACS comparison. Equal
allocation splits a FIXED canary budget across however many levels the attribute has, so the
per-group ceiling depends on that count:

    Adult  race    5 levels -> 80 canaries/group -> ceiling 3.27
    ACS    RAC1P   9 levels -> 44 canaries/group -> ceiling 2.65

ACS's race instrument is therefore genuinely weaker than Adult's, before any mechanism is
run. Raising ACS's budget to equalise the ceilings would confound group count with total
canary count instead; the budget is held fixed and the ceiling difference is reported.

Usage:
    python -m scripts.run_h2                 # UCI Adult (default)
    python -m scripts.run_h2 --dataset acs   # ACSIncome, CA 2018
"""

import argparse
import json
import time
from pathlib import Path

import numpy as np

from synthproof.accounting.accountant import Accountant
from synthproof.accounting.calibration import BudgetPlan
from synthproof.audit.subgroup import SubgroupCanaryAuditor, summarise
from synthproof.data.profiler import DPDomainProfiler
from synthproof.frontier.experiment import MECHANISMS

# Held identical across datasets, so a difference between them is the data and not the
# protocol. The one thing that cannot be held identical is the per-group ceiling; see above.
N_ROWS = 6000
EPS_GRID = (1.0, 8.0)
SEEDS = (0, 1, 2)
MECHANISM = "pairwise"
TOTAL_CANARIES = 400

DATASETS = {
    "adult": {
        "attributes": ("sex", "race"),
        "out": "results/h2_subgroups.json",
        "label": "UCI Adult",
    },
    "acs": {
        # SEX and RAC1P are ACS's direct analogues of Adult's sex and race.
        "attributes": ("SEX", "RAC1P"),
        "out": "results/acs/h2_subgroups.json",
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

        # seed=0 matches run_h1, so H1 and H2 audit the SAME 6,000 rows.
        ds, _ = load_acs_income(n_rows=N_ROWS, seed=0, download=True)
        return ds
    raise SystemExit(f"Unknown dataset {name!r}. Choose from {sorted(DATASETS)}.")


def run_one(ds, attribute, eps, seed):
    """One release, audited per subgroup."""
    auditor = SubgroupCanaryAuditor(
        attribute=attribute, num_canaries=TOTAL_CANARIES, seed=seed, balanced=True, min_per_group=20
    )
    aug, canary_sets = auditor.plant_stratified(ds)

    plan = BudgetPlan.split(eps, delta=1e-5, profile_frac=0.1)
    acc = Accountant(budget_eps=eps * 1.02, budget_delta=1e-5)
    profile = DPDomainProfiler(accountant=acc, eps_budget=plan.profile_eps).profile(aug, seed=seed)

    gen = MECHANISMS[MECHANISM](seed=seed)
    gen.fit(aug, profile, acc, target_eps=plan.synthesis_eps)
    synth = gen.generate(num_samples=aug.num_rows)

    return auditor.audit_release(ds, synth, canary_sets), float(acc.total())


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset", default="adult", choices=sorted(DATASETS))
    args = ap.parse_args()

    cfg = DATASETS[args.dataset]
    attributes = cfg["attributes"]
    ds = _load(args.dataset)

    print(f"dataset: {cfg['label']} n={ds.num_rows}")
    print(f"mechanism: {MECHANISM}   canaries: {TOTAL_CANARIES} (balanced across subgroups)")
    for attr in attributes:
        shares = ds.df[attr].value_counts(normalize=True)
        print(f"  {attr}: " + ", ".join(f"{k}={v:.3f}" for k, v in shares.items()))
    print()

    t0 = time.time()
    payload = {
        "dataset": args.dataset,
        "dataset_label": cfg["label"],
        "n_rows": ds.num_rows,
        "mechanism": MECHANISM,
        "attributes": list(attributes),
        "total_canaries": TOTAL_CANARIES,
        "eps_grid": list(EPS_GRID),
        "seeds": list(SEEDS),
        "cells": [],
    }

    for attr in attributes:
        for eps in EPS_GRID:
            per_seed, proved = [], []
            for seed in SEEDS:
                print(f"  {attr:<6} eps={eps:<5} seed={seed}", flush=True)
                res, p = run_one(ds, attr, eps, seed)
                per_seed.append(res)
                proved.append(p)

            print(summarise([per_seed[0]]))

            # Aggregate across seeds per subgroup.
            names = [s.subgroup for s in per_seed[0].subgroups]
            agg = []
            for name in names:
                rows = [next(s for s in r.subgroups if s.subgroup == name) for r in per_seed]
                agg.append(
                    {
                        "subgroup": name,
                        "population_share": rows[0].population_share,
                        "num_canaries": rows[0].num_canaries,
                        "ceiling": rows[0].ceiling,
                        "mean_audited_eps": float(np.mean([r.audited_eps for r in rows])),
                        "max_audited_eps": float(np.max([r.audited_eps for r in rows])),
                        "mean_accuracy": float(np.mean([r.accuracy for r in rows])),
                        "mean_p_value": float(np.mean([r.p_value for r in rows])),
                    }
                )

            payload["cells"].append(
                {
                    "attribute": attr,
                    "target_eps": eps,
                    "proved_eps": float(np.mean(proved)),
                    "subgroups": agg,
                    "interpretation": per_seed[0].interpretation(),
                }
            )

    payload["elapsed_seconds"] = round(time.time() - t0, 1)
    Path(cfg["out"]).parent.mkdir(parents=True, exist_ok=True)
    with open(cfg["out"], "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"\ncompleted in {payload['elapsed_seconds']:.0f}s")
    print(f"wrote {cfg['out']}")

    # The honest headline: is H2 even measurable at this scale?
    measurable = [g for c in payload["cells"] for g in c["subgroups"] if g["mean_audited_eps"] > 0]
    print(
        f"\nsubgroup-cells with a positive bound: {len(measurable)} of "
        f"{sum(len(c['subgroups']) for c in payload['cells'])}"
    )
    if not measurable:
        print(
            "H2 is UNMEASURABLE at this canary budget. That is the result, and it follows "
            "from the audit ceiling rather than from the mechanisms."
        )


if __name__ == "__main__":
    main()
