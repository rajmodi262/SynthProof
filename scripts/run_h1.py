"""Runs the H1 grid across all available mechanism families and writes the result.

Usage (must be an environment with private-pgm for `aim` to be included):
    .venv311/Scripts/python.exe -m scripts.run_h1
"""

import json
import time

from synthproof.data.datasets import load_adult
from synthproof.frontier.experiment import MECHANISMS, run_grid

N_ROWS = 3000
EPS_GRID = (1.0, 4.0, 8.0)
SEEDS = (0, 1, 2)
TARGET_COL = "income"
CORR_COLS = ("age", "hours_per_week")


def main():
    ds = load_adult()
    ds.df = ds.df.sample(n=N_ROWS, random_state=0).reset_index(drop=True)
    true_corr = ds.df[CORR_COLS[0]].corr(ds.df[CORR_COLS[1]])

    mechs = tuple(m for m in ("independent", "pairwise", "aim") if m in MECHANISMS)
    print(f"dataset: UCI Adult n={ds.num_rows} x {ds.num_cols}")
    print(f"mechanisms: {mechs}")
    print(f"true corr{CORR_COLS} = {true_corr:.4f}")
    if "aim" not in mechs:
        print("WARNING: private-pgm unavailable, so real AIM is NOT in this run.")

    t0 = time.time()
    res = run_grid(ds, mechanisms=mechs, eps_grid=EPS_GRID, seeds=SEEDS,
                   target_col=TARGET_COL, corr_cols=CORR_COLS,
                   progress=lambda m: print(m, flush=True))
    elapsed = time.time() - t0

    print(f"\ncompleted in {elapsed:.0f}s\n")
    hdr = f"{'mech':<13}{'eps':>5} {'proved':>8} {'corr err (95% CI)':>26} {'TSTR F1 (95% CI)':>24}"
    print(hdr)
    for r in res:
        print(f"{r.mechanism:<13}{r.target_eps:>5.1f} {r.proved_eps.mean:>8.3f} "
              f"{str(r.correlation_error):>26} {str(r.tstr_f1):>24}")
    print(f"\nTRTR baseline: {res[0].trtr_f1}")

    payload = {
        "dataset": "uci_adult",
        "n_rows": ds.num_rows,
        "mechanisms": list(mechs),
        "eps_grid": list(EPS_GRID),
        "seeds": list(SEEDS),
        "target_col": TARGET_COL,
        "true_correlation": float(true_corr),
        "elapsed_seconds": round(elapsed, 1),
        "cells": [r.to_dict() for r in res],
    }
    with open("results/h1_all_families.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)
    print("wrote results/h1_all_families.json")


if __name__ == "__main__":
    main()
