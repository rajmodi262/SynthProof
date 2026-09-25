"""Quick sample: new pipeline vs the pre-fix grid, on a few cells per dataset.

    python -m scripts.ab_mechanism --datasets adult fire --mechs aim mst --eps 1 8 --seeds 0 --out x.json

For each (dataset, mechanism, eps, seed) it fits the CURRENT mechanism on the same 70% split the
grid uses, scores usefulness (TSTR / TRTR) on the 30% of rows the generator never saw, and prints
it beside the pre-fix grid's 5-seed mean at the same eps (results/archive_pre_audit27/). A
validation sample, not a replacement for a full grid.
"""

import argparse
import json
import time
from pathlib import Path

import numpy as np

from synthproof.accounting.accountant import Accountant
from synthproof.data.dataset import TabularDataset
from synthproof.data.profiler import DPDomainProfiler
from synthproof.evaluate.fidelity import pairwise_tvd
from synthproof.evaluate.utility import UtilityEvaluator
from synthproof.frontier.experiment import MECHANISMS

ARCH = Path("results/archive_pre_audit27")
SMALL = {"german", "wine", "bcw", "mushroom", "nursery"}


def _load(name):
    from scripts.run_h1 import DATASETS
    from scripts.run_h1 import _load as load_h1

    ds, _ = load_h1(name, rows=0)  # every row
    return ds, DATASETS[name]["target_col"]


def _old(name, mech, eps):
    """Pre-fix usefulness: seed-weighted mean TSTR / mean TRTR at this (mech, eps)."""
    p = ARCH / (f"{name}_h1_all_families.json" if name in SMALL else f"{name}_h1_full.json")
    if not p.exists():
        return None
    cells = json.loads(p.read_text(encoding="utf-8").replace("NaN", "null"))["cells"]
    t = r = n = 0.0
    for c in cells:
        if c["mechanism"] == mech and float(c["target_eps"]) == float(eps):
            k = c["tstr_f1"].get("n") or 1
            t += c["tstr_f1"]["mean"] * k
            r += c["trtr_f1"]["mean"] * k
            n += k
    return round(t / r, 4) if n else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", nargs="+", default=["adult"])
    ap.add_argument("--mechs", nargs="+", default=["aim"])
    ap.add_argument("--eps", nargs="+", type=float, default=[1.0])
    ap.add_argument("--seeds", nargs="+", type=int, default=[0])
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    rows = []
    for name in a.datasets:
        ds, tgt = _load(name)
        for seed in a.seeds:
            rng = np.random.default_rng(seed)
            idx = rng.permutation(len(ds.df))
            nh = int(len(idx) * 0.3)
            hold = ds.df.iloc[idx[:nh]].reset_index(drop=True)
            fit = TabularDataset(ds.df.iloc[idx[nh:]].reset_index(drop=True), name=ds.name, schema=ds.schema)
            for mech in a.mechs:
                for eps in a.eps:
                    acc = Accountant(eps * (1 + 1e-6), 1e-5)
                    prof = DPDomainProfiler(accountant=acc, eps_budget=0.1 * eps).profile(fit, seed=seed)
                    gen = MECHANISMS[mech](seed=seed)
                    if hasattr(gen, "target_col"):
                        gen.target_col = tgt
                    t = time.time()
                    gen.fit(fit, prof, acc, target_eps=eps - acc.total())
                    syn = gen.generate(len(fit.df))
                    dt = time.time() - t
                    u = UtilityEvaluator(target_col=tgt, seed=seed, multi_model=True).evaluate(fit.df, syn, test_df=hold)
                    row = dict(
                        dataset=name, mech=mech, eps=eps, seed=seed,
                        useful=round(u.tstr_macro_f1 / u.trtr_macro_f1, 4),
                        useful_before=_old(name, mech, eps),
                        useful_3model=round(u.usefulness_multi, 4),
                        pair_tvd=round(pairwise_tvd(fit.df, syn), 4),
                        proved=round(acc.total(), 4), secs=round(dt, 1),
                    )
                    rows.append(row)
                    print(json.dumps(row), flush=True)
    if a.out:
        Path(a.out).write_text(json.dumps(rows, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
