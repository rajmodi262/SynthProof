"""Quick A/B of a mechanism on one dataset: usefulness on unseen rows, proved epsilon, time.

    python -m scripts.ab_mechanism --datasets adult fire --mechs aim mst --eps 1 8 --seeds 0 1

Used to validate a mechanism change on a few cells BEFORE spending a full grid on it.
"""

import argparse
import json
import time

import numpy as np

from synthproof.accounting.accountant import Accountant
from synthproof.data.dataset import TabularDataset
from synthproof.data.profiler import DPDomainProfiler
from synthproof.evaluate.utility import UtilityEvaluator
from synthproof.frontier.experiment import MECHANISMS

def _load(name):
    from scripts.run_h1 import DATASETS  # the grid's own targets
    from synthproof.data.datasets import load

    return load(name), DATASETS[name]["target_col"]


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
                    u = UtilityEvaluator(target_col=tgt, seed=seed).evaluate(fit.df, syn, test_df=hold)
                    two = [c for c in getattr(gen, "measured_cliques_", []) if len(c) >= 2]
                    row = dict(dataset=name, mech=mech, eps=eps, seed=seed, useful=round(u.tstr_macro_f1 / u.trtr_macro_f1, 4),
                               tstr=round(u.tstr_macro_f1, 4), proved=round(acc.total(), 4), secs=round(dt, 1),
                               pairs=len(two), target_pairs=sum(tgt in c for c in two))
                    rows.append(row)
                    print(json.dumps(row), flush=True)
    if a.out:
        json.dump(rows, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
