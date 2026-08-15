"""H2 — does privacy leakage differ across demographic subgroups?

Preregistered: "Under uniform DP budget allocation, empirical audited privacy loss is
significantly higher for minority demographic subgroups than for majority groups."

UCI Adult's schema already flags `race` and `sex` as the subgroup variables. Canaries are
planted stratified by subgroup with EQUAL allocation, which deliberately oversamples rare
groups so each gets a comparable audit ceiling — proportional allocation would give the rare
groups H2 is about the weakest instrument, which is exactly backwards.

Usage:
    .venv311/Scripts/python.exe -m scripts.run_h2
"""

import json
import time

import numpy as np

from synthproof.accounting.accountant import Accountant
from synthproof.accounting.calibration import BudgetPlan
from synthproof.audit.subgroup import SubgroupCanaryAuditor, summarise
from synthproof.data.datasets import load_adult
from synthproof.data.profiler import DPDomainProfiler
from synthproof.frontier.experiment import MECHANISMS

N_ROWS = 6000
ATTRIBUTES = ("sex", "race")
EPS_GRID = (1.0, 8.0)
SEEDS = (0, 1, 2)
MECHANISM = "pairwise"
TOTAL_CANARIES = 400


def run_one(ds, attribute, eps, seed):
    """One release, audited per subgroup."""
    auditor = SubgroupCanaryAuditor(attribute=attribute, num_canaries=TOTAL_CANARIES,
                                    seed=seed, balanced=True, min_per_group=20)
    aug, canary_sets = auditor.plant_stratified(ds)

    plan = BudgetPlan.split(eps, delta=1e-5, profile_frac=0.1)
    acc = Accountant(budget_eps=eps * 1.02, budget_delta=1e-5)
    profile = DPDomainProfiler(accountant=acc, eps_budget=plan.profile_eps).profile(
        aug, seed=seed)

    gen = MECHANISMS[MECHANISM](seed=seed)
    gen.fit(aug, profile, acc, target_eps=plan.synthesis_eps)
    synth = gen.generate(num_samples=aug.num_rows)

    return auditor.audit_release(ds, synth, canary_sets), float(acc.total())


def main():
    ds = load_adult()
    ds.df = ds.df.sample(n=N_ROWS, random_state=0).reset_index(drop=True)

    print(f"dataset: UCI Adult n={ds.num_rows}")
    print(f"mechanism: {MECHANISM}   canaries: {TOTAL_CANARIES} (balanced across subgroups)")
    for attr in ATTRIBUTES:
        shares = ds.df[attr].value_counts(normalize=True)
        print(f"  {attr}: " + ", ".join(f"{k}={v:.3f}" for k, v in shares.items()))
    print()

    t0 = time.time()
    payload = {"dataset": "uci_adult", "n_rows": ds.num_rows, "mechanism": MECHANISM,
               "total_canaries": TOTAL_CANARIES, "eps_grid": list(EPS_GRID),
               "seeds": list(SEEDS), "cells": []}

    for attr in ATTRIBUTES:
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
                rows = [next(s for s in r.subgroups if s.subgroup == name)
                        for r in per_seed]
                agg.append({
                    "subgroup": name,
                    "population_share": rows[0].population_share,
                    "num_canaries": rows[0].num_canaries,
                    "ceiling": rows[0].ceiling,
                    "mean_audited_eps": float(np.mean([r.audited_eps for r in rows])),
                    "max_audited_eps": float(np.max([r.audited_eps for r in rows])),
                    "mean_accuracy": float(np.mean([r.accuracy for r in rows])),
                    "mean_p_value": float(np.mean([r.p_value for r in rows])),
                })

            payload["cells"].append({
                "attribute": attr,
                "target_eps": eps,
                "proved_eps": float(np.mean(proved)),
                "subgroups": agg,
                "interpretation": per_seed[0].interpretation(),
            })

    payload["elapsed_seconds"] = round(time.time() - t0, 1)
    with open("results/h2_subgroups.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"\ncompleted in {payload['elapsed_seconds']:.0f}s")
    print("wrote results/h2_subgroups.json")

    # The honest headline: is H2 even measurable at this scale?
    measurable = [g for c in payload["cells"] for g in c["subgroups"]
                  if g["mean_audited_eps"] > 0]
    print(f"\nsubgroup-cells with a positive bound: {len(measurable)} of "
          f"{sum(len(c['subgroups']) for c in payload['cells'])}")
    if not measurable:
        print("H2 is UNMEASURABLE at this canary budget. That is the result, and it follows "
              "from the audit ceiling rather than from the mechanisms.")


if __name__ == "__main__":
    main()
