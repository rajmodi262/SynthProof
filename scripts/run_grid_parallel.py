"""Parallel full-grid runner for a bigger (more-RAM) machine.

Runs the SAME cells as `scripts.run_h1`, but fans (mechanism, eps, seed) cells across a process
pool instead of one at a time. Each cell is independent and seeded, so parallelism changes wall
clock only -- never the numbers. It writes the SAME checkpoint files the sequential pipeline
reads, then hands aggregation back to `run_h1 --checkpoints`, so there is one source of truth
for how a grid is aggregated and a partial run can never be mistaken for a complete one.

Why it needs a bigger machine: each AIM/MST cell holds ~8 GB (private-PGM + JAX). On a 16 GB
laptop only ONE fits, so `--workers` there is 1 and this is no faster than run_h1. On a machine
with more RAM, `--workers N` gives ~N x speed-up (memory, not CPU, is the limit).

Usage (on the bigger machine, from the repo root, in the Python 3.11 env with mbi/jax):
    python -m scripts.run_grid_parallel --dataset nursery --rows 0 --workers 6
    python -m scripts.run_grid_parallel --dataset mushroom --rows 0 --workers 6
Then it aggregates automatically; re-running resumes from whatever cells are already on disk.
"""

import argparse
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, Tuple

from synthproof.frontier.checkpoint import CellRecord, GridCheckpoint, config_hash
from synthproof.frontier.experiment import PIPELINE_VERSION

# Preregistered protocol -- identical to scripts.run_h1 so the cells (and their hashes) match.
EPS_GRID = (0.5, 1.0, 2.0, 4.0, 8.0)
SEEDS = (0, 1, 2, 3, 4)
MECHS = ("independent", "pairwise", "aim", "mst")
DELTA = 1e-5

Task = Tuple[str, int, str, float, int, float, str, Tuple[str, ...]]


def _work(task: Task) -> Dict[str, float]:
    """Worker: load the dataset, run ONE cell, return its serialisable metrics.

    Top-level (picklable) so it survives Windows spawn. Reloads the dataset per worker process
    -- cheap next to an AIM/MST fit -- which keeps each worker self-contained.
    """
    name, rows, mech, eps, seed, delta, target_col, corr_cols = task
    from scripts.run_h1 import _load
    from synthproof.frontier.experiment import run_cell

    ds, _ = _load(name, rows=rows)
    out = run_cell(
        ds,
        mech,
        float(eps),
        int(seed),
        delta=float(delta),
        target_col=target_col,
        corr_cols=list(corr_cols),
    )
    return {
        k: v for k, v in out.items() if not k.startswith("_") and isinstance(v, (int, float, str))
    }


def _default_workers() -> int:
    """One worker per ~9 GB of available RAM (an AIM/MST cell's footprint), at least 1."""
    try:
        import psutil

        return max(1, int(psutil.virtual_memory().available / 9e9))
    except Exception:
        return 1


def main() -> int:
    from scripts.run_h1 import DATASETS, _load

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset", required=True, choices=sorted(DATASETS))
    ap.add_argument("--rows", type=int, default=0, help="0 = full table (every row); default 0.")
    ap.add_argument(
        "--workers",
        type=int,
        default=None,
        help="parallel cells; default = available_RAM / 9 GB. Keep <= RAM/9 or you "
        "will OOM: each AIM/MST cell holds ~8 GB.",
    )
    ap.add_argument("--eps", type=float, nargs="+", default=None)
    ap.add_argument("--seeds", type=int, nargs="+", default=None)
    ap.add_argument("--mechanisms", nargs="+", default=None)
    ap.add_argument(
        "--no-aggregate",
        action="store_true",
        help="only fill checkpoints; skip the run_h1 aggregation step.",
    )
    args = ap.parse_args()

    cfg = DATASETS[args.dataset]
    eps_grid = tuple(args.eps) if args.eps else EPS_GRID
    seeds = tuple(args.seeds) if args.seeds else SEEDS
    mechs = tuple(args.mechanisms) if args.mechanisms else MECHS
    workers = args.workers or _default_workers()
    target_col = cfg["target_col"]
    corr_cols = tuple(cfg["corr_cols"])
    ckpt_dir = Path(cfg["checkpoints"])

    # Load once to fix the row count that goes into every cell's config hash. Must match what
    # run_h1 --rows <same> would build, or the cells will not be recognised as cached.
    ds, _ = _load(args.dataset, rows=args.rows)
    n_rows = ds.num_rows
    print(
        f"dataset={args.dataset} n={n_rows} workers={workers} "
        f"cells={len(mechs) * len(eps_grid) * len(seeds)}"
    )
    if workers > _default_workers():
        print(f"WARNING: {workers} workers may exceed RAM (~9 GB/cell); reduce if it OOMs.")

    # Build cells in EXACTLY run_grid's order and shape, so config_hash matches and run_h1 later
    # sees them as cached.
    cells = [
        {
            "mechanism": mech,
            "target_eps": float(eps),
            "seed": int(seed),
            "delta": float(DELTA),
            "dataset": ds.name,
            "rows": n_rows,
            "target_col": target_col,
            "corr_cols": list(corr_cols),
            "pipeline": PIPELINE_VERSION,
        }
        for mech in mechs
        for eps in eps_grid
        for seed in seeds
    ]

    ckpt = GridCheckpoint(ckpt_dir)
    pending: Dict[Any, int] = {}
    done = 0
    for i, c in enumerate(cells):
        h = config_hash(c)
        if ckpt.load(i, h) is not None:
            done += 1
            continue
        pending[i] = h
    print(f"{done} cached, {len(pending)} to run")

    if pending:
        tasks = {
            i: (
                args.dataset,
                args.rows,
                c["mechanism"],
                c["target_eps"],
                c["seed"],
                DELTA,
                target_col,
                corr_cols,
            )
            for i, c in enumerate(cells)
            if i in pending
        }
        with ProcessPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(_work, t): i for i, t in tasks.items()}
            for n, fut in enumerate(as_completed(futs), 1):
                i = futs[fut]
                metrics = fut.result()  # a failed cell raises here -- no partial aggregation
                ckpt.save(
                    CellRecord(index=i, config=cells[i], config_hash=pending[i], metrics=metrics)
                )
                c = cells[i]
                print(
                    f"  [{n}/{len(tasks)}] done {c['mechanism']} eps={c['target_eps']} "
                    f"seed={c['seed']}",
                    flush=True,
                )

    if args.no_aggregate:
        print("checkpoints filled; skipping aggregation (--no-aggregate).")
        return 0

    # Aggregate through the ONE canonical path: run_h1 with the same checkpoints finds every
    # cell cached and only aggregates + writes the payload.
    print("aggregating via run_h1 --checkpoints ...")
    cmd = [
        sys.executable,
        "-m",
        "scripts.run_h1",
        "--dataset",
        args.dataset,
        "--rows",
        str(args.rows),
        "--checkpoints",
        str(ckpt_dir),
    ]
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
