"""Worst-case GDP audit of SynthProof's own mechanism, after Ganev, Annamalai & Kulynych.

WHAT THIS IS. A replication, in this codebase, of the auditing framework in *Tight Auditing of
Differential Privacy in MST and AIM* (TPDP 2026, [arXiv:2604.18352](https://arxiv.org/abs/2604.18352)
-- title, authors and headline numbers verified against the arXiv abstract on 2026-08-25).

It is **not a novelty claim**. It is an independent check that this project's mechanism and its
accountant agree with each other, run against the strongest published auditing method for this
mechanism family. Three outcomes, and none of them is null:

  * `mu_emp` comes out near the mechanism's own `mu`  -> independent evidence the private-PGM
    integration, the noise sampler and the RDP accounting are right.
  * `mu_emp` comes out ABOVE the mechanism's `mu`     -> a real violation somewhere in OUR code,
    found by us. That is the strongest possible result and it must be reported as a defect.
  * `mu_emp` comes out at ~0                           -> our audit is weaker than theirs, which
    is informative about the AUDIT and says nothing reassuring about the mechanism.

WHY THE PROJECT'S EXISTING ZEROS ARE NOT THE WHOLE STORY. Every canary audit here reports
`eps_audited = 0.000`, and `results/DETECTION_FLOOR.md` reads that as an instrument ceiling.
Ganev et al. diagnose a second cause: unstable threshold selection picks overly small thresholds,
inflating FPR and collapsing the bound to zero, "which explains why prior work reports
eps_emp = 0 results in the strong-privacy regime". Their Fig. 3 ablation shows Clopper-Pearson
going to 0.00 where their estimator reaches 0.43. **SynthProof uses Clopper-Pearson.**

THE WORST-CASE SETUP, following the paper:
  * `D_out` = 10 identical records `[0, 0, 0]` over three binary columns.
  * `D_in`  = `D_out` plus one target record `[1, 1, 1]`.
  * Synthetic output of 50 rows per run.
  * Many independent runs per world; the adversary scores each synthetic table.

HONEST DEVIATIONS, restated from `synthproof/audit/gdp.py`:
  * Their adversary is XGBoost over query features plus white-box marginal counts. `xgboost` is
    not installed here, so this uses a small set of explicit sufficient statistics and, when
    scikit-learn is available, a gradient-boosting score. A weaker adversary yields a SMALLER
    `mu_emp`, so this errs toward under-claiming.
  * Their estimator is Bayesian (90% posterior mass, and they note it "does not necessarily
    yield valid frequentist coverage"). This uses one-sided Clopper-Pearson bounds on FPR and
    FNR -- deliberately, because the point is to show that the ESTIMATOR is not the only thing
    standing between this project and a non-zero audit.
  * They run 10,000 models. The default here is smaller for laptop runtime; `--runs` sets it,
    and the ceiling for whatever count is used is always reported beside the result.

Usage:
    python -m scripts.run_gdp_audit --runs 2000
    python -m scripts.run_gdp_audit --runs 5000 --mechanism fixed_workload --eps 1.0 --delta 1e-2
"""

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from synthproof.accounting.accountant import Accountant
from synthproof.audit.gdp import (
    audit_against_proof,
    max_provable_mu,
    mu_from_gaussian_composition,
)
from synthproof.data.dataset import TabularDataset
from synthproof.data.profiler import DPDomainProfiler
from synthproof.data.schema import CATEGORICAL, ColumnSpec, Schema
from synthproof.frontier.experiment import MECHANISMS

COLS = ("a", "b", "c")
N_BASE = 10  # identical records in D_out
SYNTH_ROWS = 50


def worst_case_datasets():
    """`D_out` (10 x [0,0,0]) and `D_in` (that plus one [1,1,1]), with a PUBLIC schema.

    The schema declares the binary domain, so the profiler charges nothing for discovering it
    and the audit measures the synthesis mechanism rather than the profiler.
    """
    schema = Schema(
        columns=[ColumnSpec(name=c, kind=CATEGORICAL, categories=["0", "1"]) for c in COLS]
    )
    out = pd.DataFrame({c: ["0"] * N_BASE for c in COLS})
    inn = pd.concat([out, pd.DataFrame({c: ["1"] for c in COLS})], ignore_index=True)
    return (
        TabularDataset(out, name="gdp_worst_case_out", schema=schema),
        TabularDataset(inn, name="gdp_worst_case_in", schema=schema),
        schema,
    )


def features(synth: pd.DataFrame) -> np.ndarray:
    """Sufficient statistics an adversary can compute from the synthetic table alone.

    The target record is the only `1` anywhere, so everything informative is a count of ones:
    per-column rates, and the rate of the full `[1,1,1]` pattern the target would contribute.
    """
    ones = [float((synth[c] == "1").mean()) for c in COLS]
    all_ones = float(((synth["a"] == "1") & (synth["b"] == "1") & (synth["c"] == "1")).mean())
    return np.array([*ones, all_ones, float(np.mean(ones))], dtype=float)


def run_once(ds, schema, mechanism, eps, delta, seed, profile_eps):
    """One release. Returns (features, noise_multiplier) or None if the mechanism refused."""
    acc = Accountant(budget_eps=eps * 1.05, budget_delta=delta)
    profile = DPDomainProfiler(
        accountant=acc, eps_budget=profile_eps, schema_declared=True
    ).profile(ds, seed=seed)
    gen = MECHANISMS[mechanism](seed=seed)
    gen.fit(ds, profile, acc, target_eps=eps)
    synth = gen.generate(num_samples=SYNTH_ROWS)
    sigma = getattr(gen, "meas_sigma_", None) or getattr(gen, "noise_scale_", None)
    scales = getattr(gen, "noise_scales_", None)
    if sigma is None and scales:
        sigma = float(np.mean(list(scales.values())))
    return features(synth), sigma


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs", type=int, default=2000, help="Runs PER WORLD.")
    ap.add_argument("--mechanism", default="independent", choices=sorted(MECHANISMS))
    ap.add_argument("--eps", type=float, default=1.0)
    ap.add_argument("--delta", type=float, default=1e-2)
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--out", default="results/gdp_audit.json")
    args = ap.parse_args()

    ds_out, ds_in, schema = worst_case_datasets()
    profile_eps = args.eps * 0.02  # tiny: the schema is public, so this buys almost nothing

    print(f"mechanism  : {args.mechanism}")
    print(f"worst case : D_out = {N_BASE} x [0,0,0]   D_in = D_out + [1,1,1]")
    print(f"target     : (eps, delta) = ({args.eps}, {args.delta:g})")
    print(f"runs       : {args.runs} per world  ({2 * args.runs} fits)")
    print(
        f"ceiling    : max provable mu at this run count = "
        f"{max_provable_mu(args.runs, args.runs, args.alpha):.4f}\n"
    )

    t0 = time.time()
    fin, fout, sigmas = [], [], []
    for i in range(args.runs):
        a, s1 = run_once(ds_in, schema, args.mechanism, args.eps, args.delta, i, profile_eps)
        b, s2 = run_once(
            ds_out, schema, args.mechanism, args.eps, args.delta, i + 10**6, profile_eps
        )
        fin.append(a)
        fout.append(b)
        for s in (s1, s2):
            if s:
                sigmas.append(float(s))
        if (i + 1) % max(1, args.runs // 10) == 0:
            print(f"  {i + 1}/{args.runs} per world  ({time.time() - t0:.0f}s)", flush=True)

    X_in, X_out = np.array(fin), np.array(fout)

    # ---- adversary -------------------------------------------------------------------
    # Trained on half, scored on the other half, so the threshold is not chosen on the data
    # it is evaluated on -- the failure Ganev et al. identify as the cause of collapsed bounds.
    half = len(X_in) // 2
    scores_in = scores_out = None
    try:
        from sklearn.ensemble import GradientBoostingClassifier

        Xtr = np.vstack([X_in[:half], X_out[:half]])
        ytr = np.r_[np.ones(half), np.zeros(half)]
        clf = GradientBoostingClassifier(random_state=0, n_estimators=60, max_depth=2).fit(Xtr, ytr)
        scores_in = clf.predict_proba(X_in[half:])[:, 1]
        scores_out = clf.predict_proba(X_out[half:])[:, 1]
        adversary = "sklearn GradientBoosting on held-out half"
    except ImportError:  # pragma: no cover
        scores_in, scores_out = X_in[half:, 3], X_out[half:, 3]
        adversary = "single statistic: rate of the [1,1,1] pattern"

    res = audit_against_proof(scores_in, scores_out, args.eps, args.delta, alpha=args.alpha)
    ceiling = max_provable_mu(len(scores_in), len(scores_out), args.alpha)

    mech_mu = None
    if sigmas:
        mech_mu = mu_from_gaussian_composition(len(COLS), float(np.mean(sigmas)))

    print("\n" + "=" * 74)
    print("GDP AUDIT")
    print("=" * 74)
    print(f"  adversary            {adversary}")
    print(f"  scored runs/world    {len(scores_in)}")
    print(f"  FPR / FNR            {res.fpr:.4f} / {res.fnr:.4f}")
    print(f"  mu_emp (lower bound) {res.mu_emp:.4f}")
    print(f"  ceiling at this n    {ceiling:.4f}")
    print(
        f"  implied mu from      {res.implied_mu:.4f}   "
        f"(inverting the released (eps, delta) -- the LOOSE comparator)"
    )
    if mech_mu:
        print(
            f"  mechanism mu         {mech_mu:.4f}   "
            f"(sqrt({len(COLS)})/sigma, sigma = {np.mean(sigmas):.3f} -- the TIGHT comparator)"
        )

    if res.exceeds_implied:
        verdict = (
            f"VIOLATION FLAGGED. mu_emp = {res.mu_emp:.4f} EXCEEDS the implied "
            f"mu = {res.implied_mu:.4f}. Either the mechanism, the accounting, or this audit is "
            "wrong. Do not report this as a success; investigate before anything else."
        )
    elif res.mu_emp <= 0:
        verdict = (
            "AUDIT DETECTED NOTHING. mu_emp = 0. Given a ceiling of "
            f"{ceiling:.4f}, the instrument COULD have reported more, so this is a statement "
            "about the adversary and estimator used here, NOT evidence that the mechanism is "
            "private. Ganev et al. reach ~0.43 with a stronger adversary and a Bayesian "
            "estimator; that gap is the finding."
        )
    else:
        verdict = (
            f"AUDIT INFORMATIVE. mu_emp = {res.mu_emp:.4f} against a ceiling of {ceiling:.4f} "
            f"and an implied mu of {res.implied_mu:.4f}. The empirical bound sits below the "
            "proved bound, which is the expected and correct ordering."
        )
    print("\n" + "=" * 74)
    print("VERDICT")
    print("=" * 74)
    print(verdict)

    out = {
        "replication_of": "Ganev, Annamalai & Kulynych, TPDP 2026, arXiv:2604.18352",
        "is_novelty_claim": False,
        "mechanism": args.mechanism,
        "target_eps": args.eps,
        "delta": args.delta,
        "runs_per_world": args.runs,
        "scored_per_world": int(len(scores_in)),
        "adversary": adversary,
        "mu_emp": res.mu_emp,
        "ceiling_at_this_n": ceiling,
        "implied_mu_from_eps_delta": res.implied_mu,
        "mechanism_mu_from_composition": mech_mu,
        "mean_noise_multiplier": float(np.mean(sigmas)) if sigmas else None,
        "fpr": res.fpr,
        "fnr": res.fnr,
        "threshold": res.threshold,
        "alpha": args.alpha,
        "exceeds_implied": res.exceeds_implied,
        "verdict": verdict,
        "elapsed_seconds": round(time.time() - t0, 1),
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nwritten to {args.out}  ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
