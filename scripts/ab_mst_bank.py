"""Ablation: which audit27 change moved MST on Bank (87% -> ~81%)?

    python -m scripts.ab_mst_bank

Toggles the MST-relevant changes one at a time on Bank, eps=8, seeds 0-2, unseen-row usefulness:
  base        = current code
  sel_0.25    = selection share 0.25 instead of the paper's 1/3
  no_log_bins = uniform bins everywhere (turns off the heavy-tail log bins)
  old_bounds  = Bank age bound back to the observed 18-95
"""

import json

import numpy as np

import synthproof.generators._marginal as M
from synthproof.accounting.accountant import Accountant
from synthproof.data.dataset import TabularDataset
from synthproof.data.datasets import load
from synthproof.data.profiler import DPDomainProfiler
from synthproof.data.schema import ColumnSpec, Schema
from synthproof.evaluate.utility import UtilityEvaluator
from synthproof.generators.mst import MSTGenerator


def run(ds, seed, eps=8.0, **kw):
    idx = np.random.default_rng(seed).permutation(len(ds.df))
    nh = int(len(idx) * 0.3)
    hold = ds.df.iloc[idx[:nh]].reset_index(drop=True)
    fit = TabularDataset(ds.df.iloc[idx[nh:]].reset_index(drop=True), name=ds.name, schema=ds.schema)
    acc = Accountant(eps * (1 + 1e-6), 1e-5)
    prof = DPDomainProfiler(accountant=acc, eps_budget=0.1).profile(fit, seed=seed)
    g = MSTGenerator(seed=seed, **kw)
    g.fit(fit, prof, acc, target_eps=eps)
    syn = g.generate(len(fit.df))
    u = UtilityEvaluator(target_col="y", seed=seed).evaluate(fit.df, syn, test_df=hold)
    edges = [c for c in g.measured_cliques_ if len(c) == 2]
    return u.tstr_macro_f1 / u.trtr_macro_f1, sum("y" in c for c in edges)


def main():
    ds = load("bank")
    print("numeric:", {c: ds.bounds(c) for c in ds.numerical_cols})
    variants = {"base": ({}, None), "sel_0.25": ({"selection_frac": 0.25}, None), "no_log_bins": ({}, "nolog")}
    old = Schema(columns=[ColumnSpec(s.name, s.kind, lower=18.0, upper=95.0) if s.name == "age" else s for s in ds.schema.columns])
    ds_old = TabularDataset(ds.df, name=ds.name, schema=old)
    for name, (kw, mode) in {**variants, "old_bounds": ({}, "old")}.items():
        saved = M.LOG_BIN_MIN_UPPER
        if mode == "nolog":
            M.LOG_BIN_MIN_UPPER = float("inf")
        try:
            res = [run(ds_old if mode == "old" else ds, s, **kw) for s in (0, 1, 2)]
        finally:
            M.LOG_BIN_MIN_UPPER = saved
        print(json.dumps({"variant": name, "useful": [round(r[0], 3) for r in res], "mean": round(float(np.mean([r[0] for r in res])), 3),
                          "target_edges": [r[1] for r in res]}), flush=True)


if __name__ == "__main__":
    main()
