"""K3 kill-check for the missing-data / imputation audit (research/11_pivot_scout).

THE QUESTION. Before running a 180-cell imputation experiment whose headline could be a NULL
result ("imputation does not leak"), we must show the instrument can see a leak at all at the n we
intend to use. If a membership-inference auditor cannot separate a KNOWN leak from a KNOWN-private
release at that n, a null is uninterpretable and the imputation audit (arm 3A) is dead.

THE DESIGN. At each n:
  * KNOWN-PRIVATE arm  -- `independent` at eps=1 (fully DP; the auditor should read ~0.5 AUC).
  * KNOWN-LEAK arms    -- `LeakyGenerator` copying a fraction of the training rows verbatim.
      leak=1.00 is the trivial worst case; leak=0.50 and leak=0.25 are the honest test, because a
      real imputation leak would be PARTIAL, not the whole table.
  * Auditors: DOMIAS (density-ratio) and the distance-MIA baseline, member vs non-member AUC.
  * Over S seeds per arm (fresh disjoint member/non-member split each time) we report mean AUC and a
    95% bootstrap CI over seeds.

PASS / FAIL, stated in advance:
  PASS at n if the auditor resolves a PARTIAL leak: leak=0.25's CI lies clearly above the private
       arm's CI (non-overlapping) for at least one auditor. Then a null in the imputation grid is
       meaningful.
  MARGINAL if only leak>=0.50 is resolved (subtle imputation leaks may be missed; report with care).
  FAIL if even leak=1.00 does not separate from private -- the instrument is blind at this n and 3A
       must be abandoned.

Not canary insertion: our own prior result was that planting canaries destroyed most of the signal
(memory: canary-contamination). This uses the member/non-member construction instead.
"""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from synthproof.accounting.accountant import Accountant  # noqa: E402
from synthproof.attacks.distance_mia import DistanceMIABaseline  # noqa: E402
from synthproof.attacks.domias import DOMIAS  # noqa: E402
from synthproof.data.profiler import DPDomainProfiler  # noqa: E402
from synthproof.generators.independent import IndependentMarginalGenerator  # noqa: E402
from synthproof.generators.leaky import LeakyGenerator  # noqa: E402

EPS = 1.0
DELTA = 1e-5
SEEDS = list(range(12))
N_GRID = [1000, 2000, 4000]
OUT = Path("research/imputation_audit")


def load_adult_numeric():
    from synthproof.data.datasets import load_adult

    ds = load_adult()
    return ds


def one_run(ds, n, arm, seed):
    """Fit an arm on n members, attack it, return (domias_auc, distance_auc)."""
    from synthproof.data.dataset import TabularDataset

    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(ds.df))
    members = ds.df.iloc[idx[:n]].reset_index(drop=True)
    nonmembers = ds.df.iloc[idx[n : 2 * n]].reset_index(drop=True)
    member_ds = TabularDataset(members, name=ds.name, schema=ds.schema)

    acc = Accountant(budget_eps=EPS * 1.05, budget_delta=DELTA)
    if arm == "private_independent":
        prof = DPDomainProfiler(accountant=acc, eps_budget=0.1 * EPS).profile(member_ds, seed=seed)
        gen = IndependentMarginalGenerator(seed=seed)
        gen.fit(member_ds, prof, acc, target_eps=0.9 * EPS)
    else:
        frac = float(arm.split("_")[1])
        gen = LeakyGenerator(seed=seed, leak_fraction=frac)
        prof = DPDomainProfiler(accountant=acc, eps_budget=0.1 * EPS).profile(member_ds, seed=seed)
        gen.fit(member_ds, prof, acc, target_eps=0.9 * EPS)
    synth = gen.generate(num_samples=n)

    try:
        d_auc = DOMIAS(seed=seed, max_records=min(n, 1500)).evaluate(synth, members, nonmembers).auc
    except Exception:
        d_auc = float("nan")
    try:
        m_auc = (
            DistanceMIABaseline(seed=seed, max_records=min(n, 1500))
            .evaluate(synth, members, nonmembers)
            .auc
        )
    except Exception:
        m_auc = float("nan")
    return d_auc, m_auc


def boot_ci(vals, iters=4000, seed=0):
    vals = np.asarray([v for v in vals if not np.isnan(v)], dtype=float)
    if len(vals) == 0:
        return (float("nan"), float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    means = [rng.choice(vals, len(vals), replace=True).mean() for _ in range(iters)]
    return float(vals.mean()), float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ds = load_adult_numeric()
    arms = ["private_independent", "leaky_0.25", "leaky_0.5", "leaky_1.0"]
    results = []
    for n in N_GRID:
        print(f"\n===== n = {n} (members) =====", flush=True)
        per_arm = {}
        for arm in arms:
            domias, dist = [], []
            for s in SEEDS:
                da, ma = one_run(ds, n, arm, s)
                domias.append(da)
                dist.append(ma)
            per_arm[arm] = {
                "domias": boot_ci(domias),
                "distance_mia": boot_ci(dist),
                "domias_raw": [round(x, 4) for x in domias],
                "distance_raw": [round(x, 4) for x in dist],
            }
            dm, dl, dh = per_arm[arm]["domias"]
            mm, ml, mh = per_arm[arm]["distance_mia"]
            print(
                f"  {arm:22} DOMIAS {dm:.3f} [{dl:.3f},{dh:.3f}]   "
                f"distMIA {mm:.3f} [{ml:.3f},{mh:.3f}]",
                flush=True,
            )
        # verdict at this n: does leaky_0.25 separate from private (either auditor)?
        priv = per_arm["private_independent"]
        leak25 = per_arm["leaky_0.25"]
        leak50 = per_arm["leaky_0.5"]

        def sep(leak, auditor, priv=priv):
            _, _, priv_hi = priv[auditor]
            _, leak_lo, _ = leak[auditor]
            return leak_lo > priv_hi

        resolves_25 = sep(leak25, "domias") or sep(leak25, "distance_mia")
        resolves_50 = sep(leak50, "domias") or sep(leak50, "distance_mia")
        verdict = "PASS" if resolves_25 else ("MARGINAL" if resolves_50 else "FAIL")
        print(f"  --> K3 verdict at n={n}: {verdict} "
              f"(resolves 25% leak: {resolves_25}; 50% leak: {resolves_50})")
        results.append({"n": n, "verdict": verdict, "resolves_25pct": resolves_25,
                        "resolves_50pct": resolves_50, "arms": per_arm})

    (OUT / "k3_audit_power.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("\n" + "=" * 70)
    print("K3 SUMMARY:", {r["n"]: r["verdict"] for r in results})
    print(f"wrote {OUT/'k3_audit_power.json'}")


if __name__ == "__main__":
    main()
