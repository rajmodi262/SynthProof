"""Tune AIM's round plan on a few cells: rounds_per_column x annealing, usefulness on unseen rows.

    python -m scripts.ab_aim_config --datasets fire adult --eps 1 --configs 1:1 2:1 2:0 4:1
    (config = rounds_per_column:adaptive_budget)
"""

import argparse
import json
import time

import numpy as np

from synthproof.accounting.accountant import Accountant
from synthproof.data.dataset import TabularDataset
from synthproof.data.profiler import DPDomainProfiler
from synthproof.evaluate.utility import UtilityEvaluator
from synthproof.generators.aim import AIMGenerator


def main():
    from scripts.run_h1 import DATASETS
    from synthproof.data.datasets import load

    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", nargs="+", default=["fire"])
    ap.add_argument("--eps", nargs="+", type=float, default=[1.0])
    ap.add_argument("--seeds", nargs="+", type=int, default=[0])
    ap.add_argument("--configs", nargs="+", default=["1:1"])
    a = ap.parse_args()
    for name in a.datasets:
        ds, tgt = load(name), DATASETS[name]["target_col"]
        for seed in a.seeds:
            idx = np.random.default_rng(seed).permutation(len(ds.df))
            nh = int(len(idx) * 0.3)
            hold = ds.df.iloc[idx[:nh]].reset_index(drop=True)
            fit = TabularDataset(ds.df.iloc[idx[nh:]].reset_index(drop=True), name=ds.name, schema=ds.schema)
            for eps in a.eps:
                for cfg in a.configs:
                    rpc, adapt = cfg.split(":")
                    acc = Accountant(eps * (1 + 1e-6), 1e-5)
                    prof = DPDomainProfiler(accountant=acc, eps_budget=0.1).profile(fit, seed=seed)
                    g = AIMGenerator(seed=seed, rounds_per_column=int(rpc), adaptive_budget=adapt == "1", target_col=tgt)
                    t = time.time()
                    g.fit(fit, prof, acc, target_eps=eps)
                    syn = g.generate(len(fit.df))
                    u = UtilityEvaluator(target_col=tgt, seed=seed).evaluate(fit.df, syn, test_df=hold)
                    cl = [c for c in g.measured_cliques_ if len(c) >= 2]
                    print(json.dumps(dict(dataset=name, eps=eps, seed=seed, cfg=cfg, useful=round(u.tstr_macro_f1 / u.trtr_macro_f1, 4),
                                          secs=round(time.time() - t, 1), cliques=len(cl), with_target=sum(tgt in c for c in cl))), flush=True)


if __name__ == "__main__":
    main()
