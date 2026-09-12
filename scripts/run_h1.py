"""Runs the H1 grid across all available mechanism families and writes the result.

H1: the ratio of empirical audited privacy loss to the formal bound, and the utility a
mechanism buys at fixed epsilon, differ across generator mechanism families.

Runs on either benchmark. The two datasets use the SAME subsample size, seed set, epsilon grid
and structure-metric column pair, so a difference between them is attributable to the data
rather than to the protocol.

Usage:
    python -m scripts.run_h1                 # UCI Adult (default)
    python -m scripts.run_h1 --dataset acs   # ACSIncome, CA 2018
    python -m scripts.run_h1 --dataset bank  # UCI Bank Marketing (non-census)
"""

import argparse
import json
import time

from synthproof.frontier.experiment import MECHANISMS, run_grid

# The preregistered protocol: 5 seeds, the full epsilon grid.
N_ROWS = 6000
EPS_GRID = (0.5, 1.0, 2.0, 4.0, 8.0)
SEEDS = (0, 1, 2, 3, 4)

DATASETS = {
    "adult": {
        "target_col": "income",
        "corr_cols": ("age", "hours_per_week"),
        "out": "results/h1_all_families.json",
        "checkpoints": "results/h1_cells",
        "label": "UCI Adult",
    },
    "acs": {
        "target_col": "income",
        # AGEP x WKHP are the direct analogues of Adult's age x hours_per_week. Using the
        # same pair on both keeps the structure numbers comparable, rather than measuring
        # whichever pair happens to correlate most strongly on each dataset.
        "corr_cols": ("AGEP", "WKHP"),
        "out": "results/acs/h1_all_families.json",
        "checkpoints": "results/acs/h1_cells",
        "label": "ACSIncome (CA 2018)",
    },
    # The third dataset exists to test whether the H1 ordering is a property of MECHANISMS
    # or a property of the census. Adult and ACSIncome share a country, a collection process
    # and a schema shape; agreement between them is close to one dataset measured twice.
    "bank": {
        "target_col": "y",
        # age x balance is this table's strongest numeric pair, and is the structural
        # analogue of the age x hours pair used on the census tables: a demographic axis
        # against an economic one. It is a much WEAKER correlation than the census pair,
        # which is itself part of the test -- a structure metric has less to detect here.
        "corr_cols": ("age", "balance"),
        "out": "results/bank/h1_all_families.json",
        "checkpoints": "results/bank/h1_cells",
        "label": "UCI Bank Marketing",
    },
}


def _load(name: str):
    if name == "adult":
        from synthproof.data.datasets import load_adult

        ds = load_adult()
        ds.df = ds.df.sample(n=N_ROWS, random_state=0).reset_index(drop=True)
        return ds, None
    if name == "acs":
        from synthproof.data.acs import load_acs_income

        return load_acs_income(n_rows=N_ROWS, seed=0, download=True)
    if name == "bank":
        from synthproof.data.datasets import load_bank_marketing

        ds = load_bank_marketing()
        # Same N_ROWS and same seed as the other two, so a difference between datasets is
        # attributable to the data and not to the sample size.
        ds.df = ds.df.sample(n=N_ROWS, random_state=0).reset_index(drop=True)
        return ds, None
    raise SystemExit(f"Unknown dataset {name!r}. Choose from {sorted(DATASETS)}.")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset", default="adult", choices=sorted(DATASETS))
    # A reduced run is a legitimate thing to want -- the full grid is ~4h per dataset -- but
    # it must be VISIBLE, so both overrides are written into the payload and the reduced
    # result cannot later be mistaken for the preregistered one.
    ap.add_argument(
        "--eps",
        type=float,
        nargs="+",
        default=None,
        help="epsilon grid override (default: the preregistered 0.5 1 2 4 8)",
    )
    ap.add_argument(
        "--seeds",
        type=int,
        nargs="+",
        default=None,
        help="seed set override (default: the preregistered 0 1 2 3 4)",
    )
    ap.add_argument("--out", default=None, help="output path override")
    args = ap.parse_args()

    eps_grid = tuple(args.eps) if args.eps else EPS_GRID
    seeds = tuple(args.seeds) if args.seeds else SEEDS
    reduced = (eps_grid != EPS_GRID) or (seeds != SEEDS)

    cfg = dict(DATASETS[args.dataset])
    if args.out:
        cfg["out"] = args.out
    ds, fingerprint = _load(args.dataset)
    a, b = cfg["corr_cols"]
    true_corr = ds.df[a].corr(ds.df[b])

    mechs = tuple(m for m in ("independent", "pairwise", "aim") if m in MECHANISMS)
    print(f"dataset: {cfg['label']}  n={ds.num_rows} x {ds.num_cols}")
    print(f"mechanisms: {mechs}")
    print(f"true corr{cfg['corr_cols']} = {true_corr:.4f}")
    if reduced:
        print(
            f"REDUCED RUN -- eps={list(eps_grid)} seeds={list(seeds)}. This is NOT the "
            "preregistered grid and is recorded as reduced in the output."
        )
    print("utility measured on a SECOND, canary-free fit (contamination fix)")
    if "aim" not in mechs:
        print("WARNING: private-pgm unavailable, so real AIM is NOT in this run.")

    from pathlib import Path

    Path(cfg["out"]).parent.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    res = run_grid(
        ds,
        mechanisms=mechs,
        eps_grid=eps_grid,
        seeds=seeds,
        target_col=cfg["target_col"],
        corr_cols=cfg["corr_cols"],
        checkpoint_dir=cfg["checkpoints"],
        progress=lambda m: print(m, flush=True),
    )
    elapsed = time.time() - t0

    print(f"\ncompleted in {elapsed:.0f}s\n")
    hdr = (
        f"{'mech':<13}{'eps':>5} {'proved':>8} "
        f"{'corr err (95% CI)':>26} {'TSTR F1 (95% CI)':>24} {'audited':>9}"
    )
    print(hdr)
    for r in res:
        print(
            f"{r.mechanism:<13}{r.target_eps:>5.1f} {r.proved_eps.mean:>8.3f} "
            f"{str(r.correlation_error):>26} {str(r.tstr_f1):>24} "
            f"{r.audited_eps.mean:>9.3f}"
        )
    print(f"\nTRTR baseline: {res[0].trtr_f1}")

    payload = {
        "dataset": args.dataset,
        "dataset_label": cfg["label"],
        "n_rows": ds.num_rows,
        "mechanisms": list(mechs),
        "eps_grid": list(eps_grid),
        "seeds": list(seeds),
        "reduced_run": reduced,
        "target_col": cfg["target_col"],
        "corr_cols": list(cfg["corr_cols"]),
        "true_correlation": float(true_corr),
        "utility_measured_on": "clean_fit",
        "elapsed_seconds": round(elapsed, 1),
        "cells": [r.to_dict() for r in res],
    }
    if fingerprint is not None:
        payload["fingerprint"] = fingerprint.to_dict()

    with open(cfg["out"], "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)
    print(f"wrote {cfg['out']}")


if __name__ == "__main__":
    main()
