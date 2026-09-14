"""Probe: does publishing the seed turn a release into a deterministic membership test?

The signed Privacy Data Sheet records `seed`, and the Croissant record mirrors it as `dp:seed`.
Every noise draw in the pipeline (profiler, measurements, AIM selection) and, since 0da936e,
the sampling step, is derived from that seed. If the whole release is a deterministic function
of (table, seed), the standard DP adversary -- who knows every record except the target's, and
reads the published seed -- can rebuild the release for both candidate tables and see which one
reproduces the published output exactly.

For each mechanism and trial:
  D   = a table;  D' = D with one record removed (add/remove-one neighbour)
  R   = release from D at seed s                  (what is published)
  replay_D  = release from D  at the published s  -> does it equal R?
  replay_D' = release from D' at the published s  -> does it equal R?
  guess_D   = release from D  at a seed s+1       -> the adversary WITHOUT the seed

Both releases use the same number of output rows, so the row count cannot be what separates
them; this isolates the seed from D2 (the exact row count).
"""

import json
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from synthproof.accounting.accountant import Accountant  # noqa: E402
from synthproof.data.dataset import TabularDataset  # noqa: E402
from synthproof.data.profiler import DPDomainProfiler  # noqa: E402
from synthproof.frontier.experiment import MECHANISMS  # noqa: E402

EPS = 1.0
DELTA = 1e-5
N = 1000
OUT_ROWS = 900
TRIALS = 5


def release(ds: TabularDataset, mechanism: str, seed: int) -> pd.DataFrame:
    acc = Accountant(budget_eps=EPS * 1.02, budget_delta=DELTA)
    prof = DPDomainProfiler(accountant=acc, eps_budget=0.1 * EPS).profile(ds, seed=seed)
    gen = MECHANISMS[mechanism](seed=seed)
    gen.fit(ds, prof, acc, target_eps=0.9 * EPS)
    return gen.generate(num_samples=OUT_ROWS).reset_index(drop=True)


def same(a: pd.DataFrame, b: pd.DataFrame) -> bool:
    return a.shape == b.shape and a.equals(b)


def main(out_path: str) -> None:
    rows = []
    for mechanism in [m for m in ("independent", "pairwise", "aim") if m in MECHANISMS]:
        tally = {"replay_D_matches": 0, "replay_Dprime_matches": 0, "unknown_seed_matches": 0}
        t0 = time.time()
        for t in range(TRIALS):
            base = TabularDataset.create_synthetic_toy(num_rows=N, seed=100 + t)
            d = TabularDataset(base.df, name="probe", schema=base.schema)
            dprime = TabularDataset(
                base.df.drop(index=t).reset_index(drop=True), name="probe", schema=base.schema
            )
            seed = 1000 + t
            published = release(d, mechanism, seed)
            tally["replay_D_matches"] += same(release(d, mechanism, seed), published)
            tally["replay_Dprime_matches"] += same(release(dprime, mechanism, seed), published)
            tally["unknown_seed_matches"] += same(release(d, mechanism, seed + 1), published)
        row = {
            "mechanism": mechanism,
            "trials": TRIALS,
            "eps": EPS,
            "n": N,
            "output_rows": OUT_ROWS,
            **tally,
            "seconds": round(time.time() - t0, 1),
        }
        rows.append(row)
        print(json.dumps(row), flush=True)
    Path(out_path).write_text(json.dumps(rows, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "seed_replay_probe.json")
