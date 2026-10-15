"""Paired Clopper-Pearson auditor vs the one-run auditor, at equal total canary budgets.

`results/AUDITOR_COMPARISON.md` reported this comparison and cited `make audit-compare`, but that
target and any script behind it did not exist, so its measured numbers had no committed source.
This is that experiment, written down and re-run: the document's table is now generated from the
JSON this writes.

DESIGN (as the document states it). UCI Adult, a 3,000-row sample, alpha = 0.05, 3 seeds. Leakage
comes from `LeakyGenerator`, which copies a known fraction of its training rows verbatim. Both
auditors get the SAME total canary budget m: the paired auditor plants m/2 canaries and holds out
m/2 as its false-positive control; the one-run auditor includes each of its m canaries at random
and uses all of them. A leak fraction of 0 is the negative control (perfect marginals, no real
record): both must report 0.

    python -m scripts.run_auditor_comparison         # writes results/auditor_comparison.json
"""

import json
import sys
import time
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from synthproof.audit.canary import CanaryAuditor  # noqa: E402
from synthproof.audit.steinke import SteinkeAuditor, max_provable_epsilon  # noqa: E402
from synthproof.data.datasets import load_adult  # noqa: E402
from synthproof.generators.leaky import LeakyGenerator  # noqa: E402

N_ROWS = 3000
BUDGETS = (60, 120, 400)
LEAKS = (1.0, 0.25, 0.0)
SEEDS = (0, 1, 2)
ALPHA = 0.05
OUT = REPO_ROOT / "results" / "auditor_comparison.json"


def _release(aug_ds, leak: float, seed: int):
    gen = LeakyGenerator(seed=seed, leak_fraction=leak)
    # A control generator takes no budget; accountant and profile are irrelevant to it.
    gen.fit(aug_ds, None, None, 0.0)  # type: ignore[arg-type]
    return gen.generate(num_samples=aug_ds.num_rows)


def main() -> None:
    ds = load_adult()
    ds.df = ds.df.sample(n=N_ROWS, random_state=0).reset_index(drop=True)
    t0 = time.time()
    cells = []
    for m in BUDGETS:
        for leak in LEAKS:
            paired, one_run = [], []
            for seed in SEEDS:
                p_aud = CanaryAuditor(num_canaries=m // 2, seed=seed, confidence=1 - ALPHA)
                p_ds, p_can = p_aud.plant_canaries(ds)
                paired.append(p_aud.audit(_release(p_ds, leak, seed), p_can).audited_eps)

                o_aud = SteinkeAuditor(num_canaries=m, seed=seed, alpha=ALPHA)
                o_ds, o_can = o_aud.plant_canaries(ds)
                one_run.append(o_aud.audit(_release(o_ds, leak, seed), o_can).audited_eps)
            cell = {
                "canary_budget": m,
                "leak_fraction": leak,
                "paired_eps_mean": float(np.mean(paired)),
                "paired_eps_per_seed": [float(v) for v in paired],
                "one_run_eps_mean": float(np.mean(one_run)),
                "one_run_eps_per_seed": [float(v) for v in one_run],
                "one_run_ceiling": float(max_provable_epsilon(m, ALPHA)),
            }
            cells.append(cell)
            print(
                f"m={m:<4} leak={leak:<4} paired={cell['paired_eps_mean']:.3f} "
                f"one-run={cell['one_run_eps_mean']:.3f} ceiling={cell['one_run_ceiling']:.3f}",
                flush=True,
            )
    OUT.write_text(
        json.dumps(
            {
                "dataset": "uci_adult",
                "n_rows": N_ROWS,
                "alpha": ALPHA,
                "seeds": list(SEEDS),
                "design": "equal total canary budget; paired plants m/2 and holds out m/2",
                "cells": cells,
                "elapsed_seconds": round(time.time() - t0, 1),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
