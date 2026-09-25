"""Fair 'before' numbers: the PRE-FIX code scored with TODAY'S evaluator.

Run from a git worktree of commit c9336e8 placed next to this repo as ../sp_old:
    git worktree add ../sp_old c9336e8
    cp scripts/fair_before_old_code.py ../sp_old/ && cd ../sp_old
    ../SynthProof/.venv311/Scripts/python -u fair_before_old_code.py bank diabetes adult acs

The archived Adult/Bank/ACS/Diabetes grids were produced before the evaluator one-hot encoded
categorical features, so their usefulness ratios are not comparable with the audit27 sample.
This re-measures the old mechanisms on the same splits, same seed, with the current evaluator
(loaded from the main checkout by file path) scoring on the unseen 30% holdout.
Output committed as results/fair_before.log.
"""

import importlib.util
import json
import sys

import numpy as np

sys.path.insert(0, ".")
import synthproof  # noqa: E402

assert "sp_old" in synthproof.__file__, synthproof.__file__
from scripts.run_h1 import DATASETS, _load  # noqa: E402
from synthproof.accounting.accountant import Accountant  # noqa: E402
from synthproof.accounting.calibration import BudgetPlan  # noqa: E402
from synthproof.data.dataset import TabularDataset  # noqa: E402
from synthproof.data.profiler import DPDomainProfiler  # noqa: E402
from synthproof.frontier.experiment import MECHANISMS  # noqa: E402

spec = importlib.util.spec_from_file_location("new_utility", "../SynthProof/synthproof/evaluate/utility.py")
new_utility = importlib.util.module_from_spec(spec)
spec.loader.exec_module(new_utility)

for name in sys.argv[1:]:
    ds, _ = _load(name, rows=0)
    tgt = DATASETS[name]["target_col"]
    seed = 0
    idx = np.random.default_rng(seed).permutation(len(ds.df))
    nh = int(len(idx) * 0.3)
    hold = ds.df.iloc[idx[:nh]].reset_index(drop=True)
    fit = TabularDataset(ds.df.iloc[idx[nh:]].reset_index(drop=True), name=ds.name, schema=ds.schema)
    for mech in ("aim", "mst"):
        for eps in (1.0, 8.0):
            plan = BudgetPlan.split(eps, 1e-5, 0.1)
            acc = Accountant(eps * 1.02, 1e-5)
            prof = DPDomainProfiler(accountant=acc, eps_budget=plan.profile_eps).profile(fit, seed=seed)
            g = MECHANISMS[mech](seed=seed)
            g.fit(fit, prof, acc, target_eps=plan.synthesis_eps)
            syn = g.generate(len(fit.df))
            u = new_utility.UtilityEvaluator(target_col=tgt, seed=seed).evaluate(fit.df, syn, test_df=hold)
            print(json.dumps({"dataset": name, "mech": mech, "eps": eps, "seed": seed,
                              "useful_old_code": round(u.tstr_macro_f1 / u.trtr_macro_f1, 4),
                              "proved_old_code": round(acc.total(), 3)}), flush=True)
