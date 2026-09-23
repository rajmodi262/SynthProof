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
    # The one genuine HEALTHCARE table (Adult/ACS are census, Bank is finance). Task: 30-day
    # readmission. time_in_hospital x num_medications is the strongest clinical numeric pair
    # (sicker patients stay longer and take more drugs), the healthcare analogue of the census
    # age x hours pair.
    "diabetes": {
        "target_col": "readmitted",
        "corr_cols": ("time_in_hospital", "num_medications"),
        "out": "results/diabetes/h1_all_families.json",
        "checkpoints": "results/diabetes/h1_cells",
        "label": "UCI Diabetes 130 (healthcare)",
    },
    # Five extra UCI benchmarks added to test generalisation across data TYPES. Mushroom and
    # Nursery are ALL-CATEGORICAL (only runnable since the categorical-aware evaluator upgrade);
    # their corr_cols are categorical, scored by the mixed association matrix. Wine and BCW are
    # all-numeric; German is mixed. See research/23c_generalisation_benchmarks.md.
    "mushroom": {
        "target_col": "target",
        "corr_cols": ("odor", "gill_color", "cap_color"),
        "out": "results/mushroom/h1_all_families.json",
        "checkpoints": "results/mushroom/h1_cells",
        "label": "UCI Mushroom (all-categorical)",
    },
    "nursery": {
        "target_col": "target",
        "corr_cols": ("health", "parents", "has_nurs"),
        "out": "results/nursery/h1_all_families.json",
        "checkpoints": "results/nursery/h1_cells",
        "label": "UCI Nursery (all-categorical, 4-class)",
    },
    "german": {
        "target_col": "target",
        "corr_cols": ("duration", "credit_amount"),
        "out": "results/german/h1_all_families.json",
        "checkpoints": "results/german/h1_cells",
        "label": "Statlog German Credit (finance)",
    },
    "wine": {
        "target_col": "quality",
        "corr_cols": ("total_sulfur_dioxide", "free_sulfur_dioxide"),
        "out": "results/wine/h1_all_families.json",
        "checkpoints": "results/wine/h1_cells",
        "label": "UCI Wine Quality red (chemistry)",
    },
    "bcw": {
        "target_col": "diagnosis",
        "corr_cols": ("radius", "area"),
        "out": "results/bcw/h1_all_families.json",
        "checkpoints": "results/bcw/h1_cells",
        "label": "Breast Cancer Wisconsin (healthcare)",
    },
}

# Datasets that carry an H1 grid and deliberately NO H2 study, each with the reason. H2 measures
# whether membership leakage differs across protected subgroups, so it needs protected
# attributes to split on. Declaring the exception here, next to the dataset, is what stops a
# dataset being added to one runner and silently forgotten in the other:
# tests/test_experiment_scripts.py requires every H1 dataset to be in H2 OR in this map.
H1_ONLY = {
    "bank": (
        "Bank Marketing has no sex or race column -- it was chosen precisely because it is not "
        "census-derived -- so there are no protected subgroups for H2 to compare. Splitting on "
        "`marital` or `job` would be a different hypothesis, not a replication of H2."
    ),
    "diabetes": (
        "Diabetes 130 was added for the healthcare utility/privacy comparison (H1). It DOES carry "
        "gender and race, so an H2 subgroup-leakage study is possible and is declared future work "
        "-- simply not run yet, so it lives in H1 only for now, recorded here not silently omitted."
    ),
    "mushroom": (
        "Mushroom is a generalisation benchmark (all-categorical, no protected attribute); H2 "
        "subgroup-leakage has no group to split on, so H1 only."
    ),
    "nursery": (
        "Nursery is a generalisation benchmark (all-categorical admission ratings, no protected "
        "attribute); H1 only for the same reason as Mushroom."
    ),
    "german": (
        "German Credit is a finance generalisation benchmark; `personal_status` mixes sex with "
        "marital status and is not carried in the schema, so no clean H2 split -- H1 only."
    ),
    "wine": (
        "Wine Quality is an all-numeric chemistry benchmark with no personal subgroups -- H1 only."
    ),
    "bcw": (
        "Breast Cancer Wisconsin has no protected demographic attribute (only tumour "
        "measurements), so there is no H2 subgroup to compare -- H1 only."
    ),
}


def _subsample(ds, rows):
    """Subsample to `rows` at seed 0, or keep the FULL table when rows is 0/None or >= len."""
    if rows and 0 < rows < len(ds.df):
        ds.df = ds.df.sample(n=rows, random_state=0).reset_index(drop=True)
    return ds


def _load(name: str, rows: int = N_ROWS):
    if name == "adult":
        from synthproof.data.datasets import load_adult

        return _subsample(load_adult(), rows), None
    if name == "acs":
        from synthproof.data.acs import load_acs_income

        # ACS is loaded already-sampled; 0 asks for the full CA-2018 pool.
        return load_acs_income(n_rows=(rows or 10**9), seed=0, download=True)
    if name == "bank":
        from synthproof.data.datasets import load_bank_marketing

        return _subsample(load_bank_marketing(), rows), None
    if name == "diabetes":
        from synthproof.data.datasets import load_diabetes130

        return _subsample(load_diabetes130(), rows), None
    if name in ("mushroom", "nursery", "german", "wine", "bcw"):
        from synthproof.data.datasets import load as load_dataset

        return _subsample(load_dataset(name), rows), None
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
    ap.add_argument(
        "--mechanisms",
        nargs="+",
        default=None,
        help="mechanism subset override (default: independent pairwise aim mst, those available). "
        "Use to run one mechanism without re-running the others, e.g. --mechanisms mst.",
    )
    ap.add_argument(
        "--checkpoints",
        default=None,
        help="checkpoint dir override. Give a distinct dir when running a mechanism subset so its "
        "cells are not mixed with a committed full-grid run.",
    )
    ap.add_argument(
        "--rows",
        type=int,
        default=N_ROWS,
        help=f"rows to use (default {N_ROWS}). Pass 0 for the FULL table (every row). Full runs "
        "are recorded as full_dataset=True in the payload and must use a distinct --out.",
    )
    args = ap.parse_args()

    eps_grid = tuple(args.eps) if args.eps else EPS_GRID
    seeds = tuple(args.seeds) if args.seeds else SEEDS
    reduced = (eps_grid != EPS_GRID) or (seeds != SEEDS)
    full_dataset = args.rows == 0

    cfg = dict(DATASETS[args.dataset])
    if args.out:
        cfg["out"] = args.out
    if args.checkpoints:
        cfg["checkpoints"] = args.checkpoints
    ds, fingerprint = _load(args.dataset, rows=args.rows)
    # `true_corr` is an informational display of the FIRST structure pair. corr_cols may list
    # more than two columns (a richer association set for categorical datasets), so take the
    # first pair, and fall back to NaN when the pair is categorical -- Pearson .corr() is only
    # defined on numerics. The full corr_cols list still drives the mixed association matrix in
    # run_grid / _mean_abs_corr_error.
    cc = list(cfg["corr_cols"])
    a, b = cc[0], cc[1]
    try:
        true_corr = float(ds.df[a].corr(ds.df[b]))
    except (TypeError, ValueError):
        true_corr = float("nan")

    # MST is a registered select-measure mechanism (generators/mst.py); it belongs in the grid.
    default_mechs = ("independent", "pairwise", "aim", "mst")
    requested = tuple(args.mechanisms) if args.mechanisms else default_mechs
    unknown = [m for m in requested if m not in MECHANISMS and m in default_mechs]
    mechs = tuple(m for m in requested if m in MECHANISMS)
    if not mechs:
        raise SystemExit(f"None of {list(requested)} are available. Known: {sorted(MECHANISMS)}.")
    print(f"dataset: {cfg['label']}  n={ds.num_rows} x {ds.num_cols}")
    print(f"mechanisms: {mechs}")
    print(f"true corr{cfg['corr_cols']} = {true_corr:.4f}")
    if reduced:
        print(
            f"REDUCED RUN -- eps={list(eps_grid)} seeds={list(seeds)}. This is NOT the "
            "preregistered grid and is recorded as reduced in the output."
        )
    print("utility measured on a SECOND, canary-free fit (contamination fix)")
    if full_dataset:
        print(
            f"FULL-DATASET RUN -- every row (n={ds.num_rows}). Heavier and memory-bound for "
            "AIM/MST; the model-size bound skips blow-up cliques rather than crashing."
        )
    if unknown:
        print(
            f"WARNING: {unknown} requested but unavailable (private-pgm needs Python >= 3.11), "
            "so they are NOT in this run."
        )

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
        "full_dataset": full_dataset,
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
