"""Run the FULL-dataset H1 grid with per-cell process isolation, then aggregate.

WHY THIS EXISTS. At full dataset size the AIM/MST fits (private-PGM + JAX) do not release memory
between cells, so a single long grid process OOMs after ~10 heavy cells (measured: full Adult died
at cell 60/100; Bank/Diabetes OOMed too). But a SINGLE heavy cell fits comfortably in a fresh
process (full Diabetes, 99k rows: 128s, no OOM). So we run every cell in its own subprocess -- a
fresh interpreter that frees all memory on exit -- and collect the one-cell result files into the
standard grid payload afterwards.

This is slower than one process (400 interpreter starts) but it is the honest way to get every row
on this hardware. It is resumable: a cell whose result file already exists is skipped.

Usage:
    python -m scripts.run_full_isolated --datasets adult bank acs diabetes
    python -m scripts.run_full_isolated --datasets diabetes        # one dataset
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from scripts.run_h1 import DATASETS, EPS_GRID, SEEDS
from synthproof.frontier.experiment import MECHANISMS

MECHS = tuple(m for m in ("independent", "pairwise", "aim", "mst") if m in MECHANISMS)


def _cell_path(cell_dir: Path, mech: str, eps: float, seed: int) -> Path:
    return cell_dir / f"{mech}__eps{eps:g}__seed{seed}.json"


def _run_cell(dataset: str, mech: str, eps: float, seed: int, cell_dir: Path) -> bool:
    """Run one cell in a fresh subprocess. Returns True on success (result file written)."""
    out = _cell_path(cell_dir, mech, eps, seed)
    if out.exists():
        return True  # resume: already done
    ckpt = cell_dir / f".ckpt_{mech}_{eps:g}_{seed}"  # throwaway; aggregation reads `out`, not this
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.run_h1",
            "--dataset",
            dataset,
            "--rows",
            "0",
            "--mechanisms",
            mech,
            "--eps",
            str(eps),
            "--seeds",
            str(seed),
            "--out",
            str(out),
            "--checkpoints",
            str(ckpt),
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0 or not out.exists():
        tail = "\n".join((proc.stdout + proc.stderr).strip().splitlines()[-3:])
        print(
            f"  [FAIL] {mech} eps={eps:g} seed={seed}: rc={proc.returncode}\n    {tail}", flush=True
        )
        return False
    return True


def _aggregate(dataset: str, cell_dir: Path, out_path: Path) -> int:
    """Collect every per-cell result file into one full-grid payload."""
    cells = []
    meta = None
    for mech in MECHS:
        for eps in EPS_GRID:
            for seed in SEEDS:
                p = _cell_path(cell_dir, mech, eps, seed)
                if not p.exists():
                    continue
                d = json.loads(p.read_text(encoding="utf-8"))
                if meta is None:
                    meta = d
                cells.extend(d.get("cells", []))
    if meta is None:
        print(f"  [{dataset}] no cells found; nothing to aggregate.")
        return 0
    payload = {
        "dataset": dataset,
        "dataset_label": meta.get("dataset_label"),
        "n_rows": meta.get("n_rows"),
        "mechanisms": list(MECHS),
        "eps_grid": list(EPS_GRID),
        "seeds": list(SEEDS),
        "reduced_run": False,
        "full_dataset": True,
        "target_col": meta.get("target_col"),
        "corr_cols": meta.get("corr_cols"),
        "true_correlation": meta.get("true_correlation"),
        "utility_measured_on": "clean_fit",
        "assembled_from": "per-cell isolated runs (scripts/run_full_isolated.py)",
        "cells": cells,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"  [{dataset}] aggregated {len(cells)} cells -> {out_path}")
    return len(cells)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--datasets", nargs="+", default=["adult", "bank", "acs", "diabetes"])
    args = ap.parse_args()

    for dataset in args.datasets:
        if dataset not in DATASETS:
            print(f"unknown dataset {dataset!r}; skipping")
            continue
        cell_dir = Path(f"results/full/percell/{dataset}")
        cell_dir.mkdir(parents=True, exist_ok=True)
        total = len(MECHS) * len(EPS_GRID) * len(SEEDS)
        print(f"\n===== FULL {dataset} (per-cell isolated, {total} cells) =====", flush=True)
        t0 = time.time()
        done = 0
        for mech in MECHS:
            for eps in EPS_GRID:
                for seed in SEEDS:
                    ok = _run_cell(dataset, mech, eps, seed, cell_dir)
                    done += 1 if ok else 0
                    if done % 10 == 0:
                        print(
                            f"  {dataset}: {done}/{total} cells ok ({time.time()-t0:.0f}s)",
                            flush=True,
                        )
        out_path = Path(f"results/full/{dataset}_h1_full.json")
        n = _aggregate(dataset, cell_dir, out_path)
        print(f"  {dataset}: {n}/{total} cells in {time.time()-t0:.0f}s", flush=True)
    print("\nALL FULL ISOLATED RUNS DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
