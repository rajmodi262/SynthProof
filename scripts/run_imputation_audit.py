"""Main experiment runner for the missing-data / imputation privacy audit.

Executes the pre-registered imputation audit across mechanisms, privacy budgets,
and missingness conditions. Computes membership inference AUCs:
  - MarginalRatioScorer (primary auditor for categorical conditions)
  - DistanceMIABaseline (auditor for numeric columns)
  - DOMIAS (density-ratio auditor for numeric columns)

With 95% percentile bootstrap confidence intervals over seeds.
Results are saved to `results/imputation_audit.json`.
"""

import argparse
import itertools
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from synthproof.accounting.accountant import Accountant  # noqa: E402
from synthproof.attacks.distance_mia import DistanceMIABaseline  # noqa: E402
from synthproof.attacks.domias import DOMIAS  # noqa: E402
from synthproof.attacks.marginal_ratio import (  # noqa: E402
    FocalPoints,
    MarginalRatioScorer,
)
from synthproof.data.dataset import TabularDataset  # noqa: E402
from synthproof.data.datasets import adult_schema  # noqa: E402
from synthproof.data.imputation import impute_arm  # noqa: E402
from synthproof.data.missingness import (  # noqa: E402
    inject_missingness,
    load_adult_raw,
)
from synthproof.data.profiler import DPDomainProfiler  # noqa: E402
from synthproof.generators.aim import AIMGenerator  # noqa: E402
from synthproof.generators.base import BaseGenerator  # noqa: E402
from synthproof.generators.dpvae import DPVAEGenerator  # noqa: E402
from synthproof.generators.independent import IndependentMarginalGenerator  # noqa: E402
from synthproof.generators.leaky import LeakyGenerator  # noqa: E402

DELTA = 1e-5


def boot_ci(vals: List[float], iters: int = 4000, seed: int = 0) -> Tuple[float, float, float]:
    """Computes mean and 95% percentile bootstrap confidence interval over seeds."""
    clean = np.asarray([v for v in vals if not np.isnan(v)], dtype=float)
    if len(clean) == 0:
        return (float("nan"), float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    means = [rng.choice(clean, len(clean), replace=True).mean() for _ in range(iters)]
    return (
        float(np.mean(clean)),
        float(np.percentile(means, 2.5)),
        float(np.percentile(means, 97.5)),
    )


def _auc(member: np.ndarray, holdout: np.ndarray) -> float:
    """Mann-Whitney U rank-sum AUC: P(member outranks non-member), ties at half."""
    if len(member) == 0 or len(holdout) == 0:
        return float("nan")
    wins = sum(float(np.sum(m > holdout)) + 0.5 * float(np.sum(m == holdout)) for m in member)
    return float(wins / (len(member) * len(holdout)))


def make_generator(mech_name: str, seed: int) -> BaseGenerator:
    """Instantiates a generator for a given mechanism name."""
    name = mech_name.lower()
    if name == "independent":
        return IndependentMarginalGenerator(seed=seed)
    elif name == "dpvae":
        return DPVAEGenerator(seed=seed)
    elif name == "aim":
        return AIMGenerator(seed=seed)
    else:
        raise ValueError(f"Unknown generator mechanism: {mech_name!r}")


def prepare_missing_dataset(raw_df: pd.DataFrame, condition: str, seed: int) -> pd.DataFrame:
    """Prepares the dataset with the requested missingness condition."""
    if condition == "native":
        return raw_df.copy()

    parts = condition.split("_")
    mech = parts[0].lower()  # mcar, mar, mnar
    rate = float(parts[1]) / 100.0 if len(parts) > 1 else 0.10

    # Start from complete cases to have clean controlled injected missingness
    complete = raw_df.dropna().reset_index(drop=True)
    return inject_missingness(complete, mechanism=mech, rate=rate, seed=seed)


def run_single_cell(
    arm: str,
    mech_name: str,
    eps: float,
    condition: str,
    raw_df: pd.DataFrame,
    schema: Any,
    n: int,
    seed: int,
) -> Dict[str, float]:
    """Executes a single pipeline cell: split -> impute -> synthesize -> attack -> metrics."""
    df_missing = prepare_missing_dataset(raw_df, condition, seed=seed)

    # Disjoint member / non-member / auxiliary split
    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(df_missing))
    members = df_missing.iloc[idx[:n]].reset_index(drop=True)
    nonmembers = df_missing.iloc[idx[n : 2 * n]].reset_index(drop=True)
    auxiliary = df_missing.iloc[idx[2 * n : 3 * n]].reset_index(drop=True)

    acc = Accountant(budget_eps=eps * 1.05, budget_delta=DELTA)

    # Execute imputation arm
    if arm == "sanity_leak":
        # Planted 100% leak sanity check
        gen = LeakyGenerator(seed=seed, leak_fraction=1.0)
        clean_members = members.dropna().reset_index(drop=True)
        imputed_ds = TabularDataset(clean_members, name="adult_audit", schema=schema)
        prof = DPDomainProfiler(accountant=acc, eps_budget=0.1 * eps).profile(imputed_ds, seed=seed)
        gen.fit(imputed_ds, prof, acc, target_eps=0.9 * eps)
        synth = gen.generate(num_samples=n)
    else:
        eps_imp = 0.1 * eps
        eps_prof = 0.1 * eps
        arm_upper = arm.upper()

        if arm_upper == "A0":
            clean_members = impute_arm("A0", members, schema)
            target_eps_gen = 0.9 * eps
        elif arm_upper == "A1":
            clean_members = impute_arm("A1", members, schema)
            target_eps_gen = 0.9 * eps
        elif arm_upper == "A2":
            clean_members = impute_arm("A2", members, schema)
            target_eps_gen = 0.9 * eps
        elif arm_upper == "A3":
            clean_members = impute_arm(
                "A3", members, schema, accountant=acc, eps_imp=eps_imp, seed=seed
            )
            target_eps_gen = 0.8 * eps
        elif arm_upper == "A4":
            clean_members = impute_arm("A4", members, schema)
            target_eps_gen = 0.9 * eps
        elif arm_upper == "A4_CHARGED":
            clean_members = impute_arm(
                "A4_CHARGED", members, schema, accountant=acc, eps_imp=eps_imp, seed=seed
            )
            target_eps_gen = 0.8 * eps
        else:
            raise ValueError(f"Unknown arm {arm!r}")

        imputed_ds = TabularDataset(clean_members, name="adult_audit", schema=schema)
        prof = DPDomainProfiler(accountant=acc, eps_budget=eps_prof).profile(imputed_ds, seed=seed)
        gen = make_generator(mech_name, seed=seed)
        gen.fit(imputed_ds, prof, acc, target_eps=target_eps_gen)
        synth = gen.generate(num_samples=n)

    # 1. Marginal Ratio evaluation (primary auditor for categorical conditions)
    try:
        cats = [c for c in clean_members.columns if c in schema.categorical]
        cliques = (
            [(c,) for c in cats]
            + list(itertools.combinations(cats, 2))
            + list(itertools.combinations(cats, 3))
        )
        if hasattr(gen, "measured_cliques_") and gen.measured_cliques_:
            for cl in gen.measured_cliques_:
                t_cl = tuple(cl)
                if t_cl not in cliques:
                    cliques.append(t_cl)
        fp = FocalPoints(cliques, [1.0] * len(cliques), source="categorical_and_measured_cliques")
        scorer = MarginalRatioScorer()
        m_sc = scorer.score(targets=members, synthetic=synth, auxiliary=auxiliary, focal=fp).scores
        nm_sc = scorer.score(
            targets=nonmembers, synthetic=synth, auxiliary=auxiliary, focal=fp
        ).scores
        mr_auc = _auc(m_sc, nm_sc)
    except Exception as err:
        print(f"Warning: MarginalRatio failed on {arm}-{mech_name}-{eps}-{seed}: {err}")
        mr_auc = float("nan")

    # 2. Distance MIA evaluation (numeric columns)
    try:
        dist_res = DistanceMIABaseline(seed=seed, max_records=min(n, 1500)).evaluate(
            synth, members, nonmembers
        )
        dist_auc = float(dist_res.auc)
    except Exception as err:
        print(f"Warning: DistanceMIA failed on {arm}-{mech_name}-{eps}-{seed}: {err}")
        dist_auc = float("nan")

    # 3. DOMIAS evaluation (numeric density ratio)
    try:
        num_cols = [c for c in members.columns if c in schema.numerical]
        m_eval = members[num_cols].fillna(members[num_cols].median())
        nm_eval = nonmembers[num_cols].fillna(nonmembers[num_cols].median())
        domias_res = DOMIAS(seed=seed, max_records=min(n, 1500)).evaluate(
            synth[num_cols], m_eval, nm_eval
        )
        domias_auc = float(domias_res.auc)
    except Exception as err:
        print(f"Warning: DOMIAS failed on {arm}-{mech_name}-{eps}-{seed}: {err}")
        domias_auc = float("nan")

    return {
        "marginal_ratio": mr_auc,
        "distance_mia": dist_auc,
        "domias": domias_auc,
    }


def run_numeric_sanity_gate(
    raw_df: pd.DataFrame, schema: Any, n: int = 1500, seeds: List[int] = None
) -> Tuple[bool, Dict[str, Any]]:
    """Sanity check: confirms DistanceMIA resolves a planted numeric leak above chance."""
    if seeds is None:
        seeds = [0, 1, 2, 3]

    print("\n" + "=" * 70)
    print("RUNNING NUMERIC SANITY GATE (Planted 100% LeakyGenerator vs DistanceMIA)...")
    print("=" * 70)

    aucs = []
    for s in seeds:
        res = run_single_cell(
            arm="sanity_leak",
            mech_name="independent",
            eps=1.0,
            condition="native",
            raw_df=raw_df,
            schema=schema,
            n=n,
            seed=s,
        )
        aucs.append(res["distance_mia"])
        print(f"  Seed {s}: DistanceMIA AUC = {res['distance_mia']:.4f}")

    mean_auc, ci_lo, ci_hi = boot_ci(aucs)
    print(f"Numeric Sanity Gate Result: mean AUC = {mean_auc:.4f} [{ci_lo:.4f}, {ci_hi:.4f}]")

    stats = {"mean": mean_auc, "ci_95": [ci_lo, ci_hi], "raw": aucs}
    if mean_auc < 0.60:
        print("FAIL: Numeric sanity gate failed! Planted leak did not separate from chance.")
        return False, stats

    print("PASS: Numeric sanity gate confirmed. DistanceMIA detects numeric leakage.")
    print("=" * 70 + "\n")
    return True, stats


def run_categorical_sanity_gate(
    raw_df: pd.DataFrame, schema: Any, n: int = 1500, seeds: List[int] = None
) -> Tuple[bool, Dict[str, Any]]:
    """Sanity check: confirms MarginalRatioScorer resolves a known categorical leak above null.

    Constructs:
      - Known categorical leak: release where categorical columns are verbatim member values.
      - Known null baseline: synthetic release drawn entirely from holdout population.
    Evaluates:
      - MarginalRatioScorer over 1-way, 2-way, and 3-way categorical cliques.
    Pass condition:
      - Non-overlapping 95% bootstrap CIs with the null baseline (~0.50) and leak mean >= 0.58.
    """
    if seeds is None:
        seeds = [0, 1, 2, 3]

    print("\n" + "=" * 70)
    print("RUNNING CATEGORICAL SANITY GATE (Known Categorical Leak vs MarginalRatio)...")
    print("=" * 70)

    cats = [c for c in schema.categorical if c in raw_df.columns]
    cliques = (
        [(c,) for c in cats]
        + list(itertools.combinations(cats, 2))
        + list(itertools.combinations(cats, 3))
    )
    fp = FocalPoints(cliques, [1.0] * len(cliques), source="categorical_cliques")
    scorer = MarginalRatioScorer()

    leak_aucs = []
    null_aucs = []

    for s in seeds:
        rng = np.random.default_rng(s)
        idx = rng.permutation(len(raw_df))
        members = raw_df.iloc[idx[:n]].reset_index(drop=True)
        nonmembers = raw_df.iloc[idx[n : 2 * n]].reset_index(drop=True)
        auxiliary = raw_df.iloc[idx[2 * n : 3 * n]].reset_index(drop=True)
        synth_null = raw_df.iloc[idx[3 * n : 4 * n]].reset_index(drop=True)

        # Planted categorical leak: members' categorical columns verbatim
        synth_leak = synth_null.copy()
        for c in cats:
            synth_leak[c] = members[c].values

        m_leak = scorer.score(members, synth_leak, auxiliary, fp).scores
        nm_leak = scorer.score(nonmembers, synth_leak, auxiliary, fp).scores
        l_auc = _auc(m_leak, nm_leak)
        leak_aucs.append(l_auc)

        m_null = scorer.score(members, synth_null, auxiliary, fp).scores
        nm_null = scorer.score(nonmembers, synth_null, auxiliary, fp).scores
        n_auc = _auc(m_null, nm_null)
        null_aucs.append(n_auc)

        print(f"  Seed {s}: Leak AUC = {l_auc:.4f} | Null AUC = {n_auc:.4f}")

    mean_leak, l_lo, l_hi = boot_ci(leak_aucs)
    mean_null, n_lo, n_hi = boot_ci(null_aucs)

    print(f"Categorical Leak Result: mean AUC = {mean_leak:.4f} [{l_lo:.4f}, {l_hi:.4f}]")
    print(f"Categorical Null Result: mean AUC = {mean_null:.4f} [{n_lo:.4f}, {n_hi:.4f}]")

    stats = {
        "leak": {"mean": mean_leak, "ci_95": [l_lo, l_hi], "raw": leak_aucs},
        "null": {"mean": mean_null, "ci_95": [n_lo, n_hi], "raw": null_aucs},
    }

    if l_lo <= n_hi or mean_leak < 0.58:
        print("FAIL: Categorical sanity gate failed! Categorical leak does not separate from null.")
        return False, stats

    print(
        "PASS: Categorical sanity gate confirmed. MarginalRatioScorer resolves categorical leakage."
    )
    print("=" * 70 + "\n")
    return True, stats


def main():
    parser = argparse.ArgumentParser(description="Run missing-data imputation privacy audit.")
    parser.add_argument(
        "--mechanisms",
        type=str,
        default="independent,dpvae,aim",
        help="Comma-separated generator mechanisms.",
    )
    parser.add_argument(
        "--arms",
        type=str,
        default="A0,A1,A2,A3,A4,A4_CHARGED",
        help="Comma-separated arms.",
    )
    parser.add_argument(
        "--eps",
        type=str,
        default="1.0,4.0",
        help="Comma-separated epsilon values.",
    )
    parser.add_argument(
        "--conditions",
        type=str,
        default="native,mcar_10,mar_10,mnar_10",
        help="Comma-separated missingness conditions.",
    )
    parser.add_argument(
        "--num_seeds", type=int, default=8, help="Number of random seeds (default 8)."
    )
    parser.add_argument(
        "--n", type=int, default=1500, help="Number of members/non-members (default 1500)."
    )
    parser.add_argument(
        "--out",
        type=str,
        default="results/imputation_audit.json",
        help="Output JSON path.",
    )
    parser.add_argument("--skip_sanity", action="store_true", help="Skip sanity gates.")
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    mechanisms = [m.strip() for m in args.mechanisms.split(",") if m.strip()]
    arms = [a.strip() for a in args.arms.split(",") if a.strip()]
    eps_list = [float(e.strip()) for e in args.eps.split(",") if e.strip()]
    conditions = [c.strip() for c in args.conditions.split(",") if c.strip()]
    seeds = list(range(args.num_seeds))

    # Load raw Adult with native missingness
    raw_ds = load_adult_raw()
    raw_df = raw_ds.df
    schema = adult_schema()

    gate_results: Dict[str, Any] = {}

    if not args.skip_sanity:
        num_ok, num_stats = run_numeric_sanity_gate(raw_df, schema, n=args.n, seeds=seeds[:4])
        cat_ok, cat_stats = run_categorical_sanity_gate(raw_df, schema, n=args.n, seeds=seeds[:4])
        gate_results["numeric_gate"] = {"passed": num_ok, **num_stats}
        gate_results["categorical_gate"] = {"passed": cat_ok, **cat_stats}

        if not num_ok:
            print("Aborting experiment due to numeric sanity gate failure.")
            sys.exit(1)
        if not cat_ok:
            print("Aborting experiment due to categorical sanity gate failure.")
            sys.exit(1)

    # Load existing results if resuming
    existing_results: Dict[str, Any] = {}
    if out_path.exists():
        try:
            with open(out_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict) and "cells" in loaded:
                    existing_results = loaded["cells"]
                    if "sanity_gates" in loaded:
                        gate_results = loaded["sanity_gates"]
        except Exception:
            existing_results = {}

    total_cells = len(mechanisms) * len(eps_list) * len(conditions) * len(arms)
    print(
        f"Starting Imputation Audit Grid: {total_cells} cells "
        f"({len(arms)} arms x {len(mechanisms)} mechs x {len(eps_list)} eps x "
        f"{len(conditions)} conds), seeds={len(seeds)}, n={args.n}"
    )

    cell_counter = 0
    start_time = time.time()

    for mech in mechanisms:
        for eps in eps_list:
            for cond in conditions:
                for arm in arms:
                    cell_key = f"{arm}_{mech}_eps{eps}_{cond}"
                    cell_counter += 1

                    # Check if already completed with all 3 auditors
                    if (
                        cell_key in existing_results
                        and "marginal_ratio" in existing_results[cell_key]
                    ):
                        print(f"[{cell_counter}/{total_cells}] Skipping completed cell: {cell_key}")
                        continue

                    print(
                        f"\n[{cell_counter}/{total_cells}] Running cell: {cell_key} "
                        f"(arm={arm}, mech={mech}, eps={eps}, cond={cond})",
                        flush=True,
                    )

                    mr_raw = []
                    dist_raw = []
                    domias_raw = []

                    for s in seeds:
                        res = run_single_cell(
                            arm=arm,
                            mech_name=mech,
                            eps=eps,
                            condition=cond,
                            raw_df=raw_df,
                            schema=schema,
                            n=args.n,
                            seed=s,
                        )
                        mr_raw.append(res["marginal_ratio"])
                        dist_raw.append(res["distance_mia"])
                        domias_raw.append(res["domias"])
                        print(
                            f"  seed {s}: marginal_ratio={res['marginal_ratio']:.4f}  "
                            f"distMIA={res['distance_mia']:.4f}  "
                            f"domias={res['domias']:.4f}",
                            flush=True,
                        )

                    mean_mr, mr_lo, mr_hi = boot_ci(mr_raw)
                    mean_d, d_lo, d_hi = boot_ci(dist_raw)
                    mean_dom, dom_lo, dom_hi = boot_ci(domias_raw)

                    cell_summary = {
                        "arm": arm,
                        "mechanism": mech,
                        "epsilon": eps,
                        "condition": cond,
                        "n_members": args.n,
                        "num_seeds": len(seeds),
                        "marginal_ratio": {
                            "mean": mean_mr,
                            "ci_95": [mr_lo, mr_hi],
                            "raw": mr_raw,
                        },
                        "distance_mia": {
                            "mean": mean_d,
                            "ci_95": [d_lo, d_hi],
                            "raw": dist_raw,
                        },
                        "domias": {
                            "mean": mean_dom,
                            "ci_95": [dom_lo, dom_hi],
                            "raw": domias_raw,
                        },
                    }
                    existing_results[cell_key] = cell_summary

                    print(
                        f"  --> {cell_key} SUMMARY: "
                        f"MarginalRatio={mean_mr:.4f} [{mr_lo:.4f}, {mr_hi:.4f}] | "
                        f"distMIA={mean_d:.4f} [{d_lo:.4f}, {d_hi:.4f}] | "
                        f"DOMIAS={mean_dom:.4f} [{dom_lo:.4f}, {dom_hi:.4f}]",
                        flush=True,
                    )

                    # Persist intermediate checkpoint after every cell
                    payload = {
                        "meta": {
                            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "n": args.n,
                            "total_cells": total_cells,
                            "completed_cells": len(existing_results),
                        },
                        "sanity_gates": gate_results,
                        "cells": existing_results,
                    }
                    with open(out_path, "w", encoding="utf-8") as f:
                        json.dump(payload, f, indent=2)

    elapsed = time.time() - start_time
    print(f"\nAudit grid complete! Elapsed: {elapsed / 60.0:.2f} minutes.")
    print(f"Results written to {out_path}")


if __name__ == "__main__":
    main()
