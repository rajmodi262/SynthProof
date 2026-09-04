"""Does measuring a pair help BECAUSE it was selected, or because the pair is dependent?

WHY THIS EXPERIMENT EXISTS. `run_clique_confound.py` established that AIM's error is lower on
pairs it selected. That is not sufficient to support the project's reading, because AIM selects
almost exactly the most-dependent pair and nothing else:

    |true corr| 0.1034  selection rate 0.88   age x hours_per_week
    |true corr| 0.0797  selection rate 0.00   hours_per_week x capital_gain
    ...
    corr(|true corr|, selection rate) = +0.700 on Adult, +0.809 on ACS

So "selected" and "strongly dependent" are confounded, and the within-pair analysis that would
break the confound has only ONE pair in both states on each dataset, with no confidence
interval. Chen, Gong & Wang (arXiv:2511.13893) give the rival explanation directly: on Adult
the unselected pairs are nearly independent, so the independent-marginals baseline is a CORRECT
model on them rather than a weak one.

THE DESIGN. `FixedWorkloadGenerator` takes a PUBLIC, explicit workload, so measurement can be
decoupled from dependence. For each target pair p we fit an arm whose workload is exactly [p],
then evaluate correlation error on EVERY pair. Every arm therefore has an identical budget
structure -- d one-way marginals plus exactly one two-way -- and differs only in WHICH pair was
measured. A `none` arm measuring no two-way marginal is the floor.

    error[measured=p][evaluated=q]      diagonal  = the pair was measured
                                        off-diag  = it was not

    measurement_effect(p) = mean error on p when p was measured
                          - mean error on p when some other pair was measured

Dependence is held fixed inside each `measurement_effect(p)` because the evaluated pair is the
same in both terms. That is exactly the control the confound argument was missing.

THE FALSIFICATION CRITERION, FIXED BEFORE THE RUN.

  * If `measurement_effect` is large for the high-dependence pair and ~0 for low-dependence
    pairs, then measuring only helps where dependence exists. AIM's advantage is then about
    WHICH PAIRS ARE DEPENDENT, not about selection, the rival explanation stands, and the
    project's confound reading must be withdrawn.
  * If `measurement_effect` is comparably large across pairs regardless of dependence, then
    "the mechanism does better on what it measured" is a general property of measurement, not
    a discovery about selection -- true, trivial, and also not a finding.
  * The claim survives only in the narrow form that a benchmark scoring ONE fixed pair reports
    the selector's choice rather than the estimator's fidelity, which is a statement about
    EVALUATION DESIGN and is what `research/10_deep_survey_2026-08-25.md` Axis C says is the
    one thing still unrun.

Either way the answer is reported. Usage:

    python -m scripts.run_selection_ablation                 # UCI Adult
    python -m scripts.run_selection_ablation --dataset acs   # ACSIncome
"""

import argparse
import json
import time
from itertools import combinations
from pathlib import Path

import numpy as np

from synthproof.accounting.accountant import Accountant
from synthproof.accounting.calibration import BudgetPlan
from synthproof.data.profiler import DPDomainProfiler
from synthproof.frontier.experiment import MECHANISMS

N_ROWS = 6000
EPS_GRID = (0.5, 1.0, 2.0, 4.0, 8.0)
SEEDS = (0, 1, 2, 3, 4)

DATASETS = {
    "adult": {"out": "results/selection_ablation.json", "label": "UCI Adult"},
    "acs": {"out": "results/acs/selection_ablation.json", "label": "ACSIncome (CA 2018)"},
}


def _load(name):
    if name == "adult":
        from synthproof.data.datasets import load_adult

        ds = load_adult()
        ds.df = ds.df.sample(n=N_ROWS, random_state=0).reset_index(drop=True)
        return ds
    if name == "acs":
        from synthproof.data.acs import load_acs_income

        ds, _ = load_acs_income(n_rows=N_ROWS, seed=0, download=True)
        return ds
    raise SystemExit(f"Unknown dataset {name!r}")


def corr_err(synth, a, b, truth):
    try:
        got = float(synth[a].corr(synth[b]))
    except Exception:
        return float("nan")
    if not np.isfinite(got):
        return abs(truth)
    return abs(truth - got)


def run_arm(ds, workload, eps, seed, pairs, truth):
    """One fit with an explicit public workload. Returns per-pair errors."""
    plan = BudgetPlan.split(eps, delta=1e-5, profile_frac=0.1)
    acc = Accountant(budget_eps=eps * 1.02, budget_delta=1e-5)
    profile = DPDomainProfiler(accountant=acc, eps_budget=plan.profile_eps).profile(ds, seed=seed)
    gen = MECHANISMS["fixed_workload"](seed=seed, workload=workload)
    gen.fit(ds, profile, acc, target_eps=plan.synthesis_eps)
    synth = gen.generate(num_samples=ds.num_rows)
    return {f"{a}|{b}": corr_err(synth, a, b, truth[(a, b)]) for a, b in pairs}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset", default="adult", choices=sorted(DATASETS))
    args = ap.parse_args()
    cfg = DATASETS[args.dataset]

    ds = _load(args.dataset)
    pairs = list(combinations(ds.numerical_cols, 2))
    truth = {(a, b): float(ds.df[a].corr(ds.df[b])) for a, b in pairs}
    keys = [f"{a}|{b}" for a, b in pairs]

    print(f"dataset: {cfg['label']}  n={ds.num_rows}")
    print(f"pairs ({len(pairs)}), by |true correlation|:")
    for k in sorted(keys, key=lambda k: -abs(truth[tuple(k.split("|"))])):
        print(f"   {k:<38} {truth[tuple(k.split('|'))]:+.4f}")
    arms = ["none"] + keys
    print(f"\narms: {len(arms)} (one per measured pair, plus a no-two-way floor)")
    print(
        f"grid: {len(arms)} x {len(EPS_GRID)} eps x {len(SEEDS)} seeds = "
        f"{len(arms) * len(EPS_GRID) * len(SEEDS)} fits\n"
    )

    t0 = time.time()
    obs = []
    for arm in arms:
        workload = [] if arm == "none" else [tuple(arm.split("|"))]
        for eps in EPS_GRID:
            for seed in SEEDS:
                errs = run_arm(ds, workload, eps, seed, pairs, truth)
                for k in keys:
                    obs.append(
                        {
                            "measured": arm,
                            "evaluated": k,
                            "target_eps": eps,
                            "seed": seed,
                            "corr_err": errs[k],
                            "was_measured": arm == k,
                        }
                    )
        print(f"  arm measured={arm:<38} done  ({time.time() - t0:.0f}s)", flush=True)

    # ---- the effect of measuring a pair, with the evaluated pair held fixed --------------
    effects = {}
    for k in keys:
        on = [o["corr_err"] for o in obs if o["evaluated"] == k and o["was_measured"]]
        off = [
            o["corr_err"]
            for o in obs
            if o["evaluated"] == k and not o["was_measured"] and o["measured"] != "none"
        ]
        on = [v for v in on if np.isfinite(v)]
        off = [v for v in off if np.isfinite(v)]
        if not on or not off:
            continue
        effects[k] = {
            "true_corr": truth[tuple(k.split("|"))],
            "abs_true_corr": abs(truth[tuple(k.split("|"))]),
            "err_when_measured": float(np.mean(on)),
            "err_when_not_measured": float(np.mean(off)),
            "effect": float(np.mean(on) - np.mean(off)),
            "relative_effect": float(
                (np.mean(on) - np.mean(off)) / np.mean(off) if np.mean(off) else float("nan")
            ),
            "n_measured": len(on),
            "n_not_measured": len(off),
        }

    print("\n" + "=" * 82)
    print("EFFECT OF MEASURING A PAIR  (evaluated pair held fixed -> dependence held fixed)")
    print("=" * 82)
    print(f"{'pair':<38} {'|corr|':>7} {'measured':>9} {'not meas':>9} {'effect':>9} {'rel':>7}")
    for k, e in sorted(effects.items(), key=lambda kv: -kv[1]["abs_true_corr"]):
        print(
            f"{k:<38} {e['abs_true_corr']:>7.4f} {e['err_when_measured']:>9.4f} "
            f"{e['err_when_not_measured']:>9.4f} {e['effect']:>+9.4f} {e['relative_effect']:>+7.1%}"
        )

    xs = [e["abs_true_corr"] for e in effects.values()]
    ys = [e["effect"] for e in effects.values()]
    rel = [e["relative_effect"] for e in effects.values()]
    r_abs = float(np.corrcoef(xs, ys)[0, 1]) if len(xs) > 2 and len(set(ys)) > 1 else float("nan")
    r_rel = float(np.corrcoef(xs, rel)[0, 1]) if len(xs) > 2 and len(set(rel)) > 1 else float("nan")

    helped = [k for k, e in effects.items() if e["effect"] < 0]
    print(f"\npairs where measuring HELPED (effect < 0): {len(helped)}/{len(effects)}")
    print(f"corr(|true corr|, absolute effect)  = {r_abs:+.3f}")
    print(f"corr(|true corr|, relative effect)  = {r_rel:+.3f}")

    # ---- verdict, against the criterion fixed in the docstring ---------------------------
    if len(effects) < 3:
        verdict = "INCONCLUSIVE: too few pairs with both states to compare."
    elif len(helped) <= 1:
        verdict = (
            "MEASUREMENT DOES NOT RELIABLY HELP. Measuring a pair lowered its error for "
            f"only {len(helped)} of {len(effects)} pairs, so the selected-vs-unselected gap in "
            "run_clique_confound.py is not explained by measurement at all. The confound "
            "reading is NOT supported."
        )
    elif np.isfinite(r_abs) and r_abs < -0.5:
        verdict = (
            "DEPENDENCE EXPLAINS IT. Measuring helps markedly more on strongly dependent "
            f"pairs (corr = {r_abs:+.3f}). AIM selects the dependent pairs, so its advantage "
            "on them is the mechanism working as designed, NOT an artefact of selection. The "
            "rival explanation of Chen, Gong & Wang (arXiv:2511.13893) stands and the "
            "project's confound reading must be withdrawn."
        )
    elif np.isfinite(r_abs) and abs(r_abs) <= 0.5:
        verdict = (
            "MEASUREMENT HELPS BROADLY. Measuring a pair lowers its error at a rate roughly "
            f"independent of that pair's true dependence (corr = {r_abs:+.3f}). 'A mechanism "
            "does better on what it measured' is then a general property of measurement, not "
            "a discovery about selection. What survives is only the EVALUATION-DESIGN claim: "
            "a benchmark scoring one fixed pair reports the selector's choice, not fidelity."
        )
    else:
        verdict = (
            f"UNEXPECTED: measuring helps MORE on weakly dependent pairs (corr = {r_abs:+.3f}). "
            "Diagnose before reporting."
        )

    print("\n" + "=" * 82)
    print("VERDICT")
    print("=" * 82)
    print(verdict)

    out = {
        "dataset": args.dataset,
        "dataset_label": cfg["label"],
        "n_rows": ds.num_rows,
        "eps_grid": list(EPS_GRID),
        "seeds": list(SEEDS),
        "true_correlations": {k: truth[tuple(k.split("|"))] for k in keys},
        "effects": effects,
        "corr_abs_true_vs_effect": r_abs,
        "corr_abs_true_vs_relative_effect": r_rel,
        "pairs_where_measuring_helped": len(helped),
        "pairs_compared": len(effects),
        "verdict": verdict,
        "elapsed_seconds": round(time.time() - t0, 1),
        "observations": obs,
    }
    Path(cfg["out"]).parent.mkdir(parents=True, exist_ok=True)
    Path(cfg["out"]).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nwritten to {cfg['out']}  ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
