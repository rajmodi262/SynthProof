"""Two adversaries, the same releases: does an algorithm-aware attack see more?

Task 4.1 of docs/ROAD_TO_TEN.md, and the item the project's own roadmap called "the one open
item that could change a published number". Both existing auditors score a record by its
similarity to the nearest synthetic row, which is algorithm-agnostic. Every epsilon this
project has ever audited is therefore a lower bound produced by ONE attack, and a weak attack
makes a weak bound look like a strong guarantee.

WHAT IS COMPARED. For each (mechanism, epsilon, seed) cell, one release is produced and both
adversaries score the SAME release against the SAME members and non-members:

  distance   the auditor's current adversary -- similarity to the nearest synthetic record.
  aware      the zeta score of Golob, Pentyala, Maratkhan & De Cock (SaTML 2025,
             arXiv:2410.05506), computed on the marginals the generator actually measured,
             with the focal points read from the fitted model rather than shadow-modelled.
             See synthproof/attacks/marginal_ratio.py for exactly how this differs from the
             attack the authors call MAMA-MIA, and why that makes it stronger rather than
             weaker.

AUC is the reported quantity because it needs no threshold and no calibration: it is the
probability that a member outranks a non-member. 0.5 is a coin flip.

    python -m scripts.run_adversary_comparison
    python -m scripts.run_adversary_comparison --quick    # 2 seeds, 2 epsilons
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

from synthproof.accounting.accountant import Accountant
from synthproof.attacks.marginal_ratio import MarginalRatioScorer, focal_points_of
from synthproof.data.dataset import TabularDataset
from synthproof.data.profiler import DPDomainProfiler
from synthproof.data.schema import Schema
from synthproof.frontier.experiment import MECHANISMS

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "results" / "adversary_comparison.json"
OUT_MD = ROOT / "results" / "ADVERSARY_COMPARISON.md"

DEFAULT_SEEDS = (0, 1, 2, 3, 4)
DEFAULT_EPS = (1.0, 4.0, 8.0)
DEFAULT_MECHANISMS = ("independent", "pairwise")
N_ROWS = 2000
N_TARGETS = 150


def _population(n: int, seed: int) -> pd.DataFrame:
    """A table with genuine pairwise dependence, so a 2-way marginal carries information.

    Synthetic rather than UCI Adult on purpose: this measures the ATTACKS against each other,
    and a controlled generator lets the dependence structure be known instead of assumed. The
    committed H1 grid is where real data belongs.
    """
    rng = np.random.default_rng(seed)
    age = rng.integers(18, 80, n)
    hours = np.clip((age * 0.4 + rng.normal(20, 8, n)).astype(int), 1, 80)
    education = rng.choice(["hs", "college", "grad"], n, p=[0.5, 0.35, 0.15])
    region = rng.choice(["north", "south", "east", "west"], n)
    return pd.DataFrame({"age": age, "hours": hours, "education": education, "region": region})


def _distance_scores(targets: pd.DataFrame, synthetic: pd.DataFrame) -> np.ndarray:
    """The auditor's current adversary, in the shape `canary.py` uses it."""
    num = [c for c in targets.columns if pd.api.types.is_numeric_dtype(synthetic[c])]
    if not num:
        return np.zeros(len(targets))
    s = synthetic[num].to_numpy(dtype=float)
    scale = np.nanstd(s, axis=0)
    scale[~np.isfinite(scale) | (scale == 0)] = 1.0
    t = targets[num].to_numpy(dtype=float)
    return np.array(
        [
            1.0 / (1.0 + float(np.min(np.linalg.norm((s - t[i]) / scale, axis=1))))
            for i in range(len(t))
        ]
    )


def _auc(member: np.ndarray, holdout: np.ndarray) -> float:
    """P(member outranks non-member), ties at half. No threshold, no calibration."""
    if len(member) == 0 or len(holdout) == 0:
        return float("nan")
    wins = sum(float(np.sum(m > holdout)) + 0.5 * float(np.sum(m == holdout)) for m in member)
    return wins / (len(member) * len(holdout))


def _cell(mechanism: str, eps: float, seed: int) -> Dict[str, float]:
    train = _population(N_ROWS, seed=20 + seed)
    holdout = _population(N_ROWS // 2, seed=900 + seed)

    ds = TabularDataset(train.copy(), name="adv", schema=Schema.infer_nonprivate(train))
    accountant = Accountant(budget_eps=eps * 4, budget_delta=1e-5)
    profile = DPDomainProfiler(accountant=accountant, eps_budget=eps * 0.1).profile(ds, seed=seed)

    generator = MECHANISMS[mechanism](seed=seed)
    generator.fit(ds, profile, accountant, target_eps=eps)
    synth = generator.generate(num_samples=N_ROWS)

    members = train.iloc[:N_TARGETS]
    non_members = holdout.iloc[:N_TARGETS]

    focal = focal_points_of(generator, list(train.columns))
    scorer = MarginalRatioScorer()
    aware = _auc(
        scorer.score(members, synth, holdout, focal).scores,
        scorer.score(non_members, synth, holdout, focal).scores,
    )
    distance = _auc(_distance_scores(members, synth), _distance_scores(non_members, synth))

    return {
        "aware_auc": float(aware),
        "distance_auc": float(distance),
        "n_focal_points": len(focal.cliques),
        "focal_source": focal.source,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--quick", action="store_true", help="2 seeds and 2 epsilons")
    args = ap.parse_args()

    seeds = (0, 1) if args.quick else DEFAULT_SEEDS
    eps_grid = (1.0, 8.0) if args.quick else DEFAULT_EPS
    mechanisms = [m for m in DEFAULT_MECHANISMS if m in MECHANISMS]
    for extra in ("aim", "fixed_workload"):
        if extra in MECHANISMS:
            mechanisms.append(extra)

    started = time.time()
    cells: List[dict] = []
    for mech in mechanisms:
        for eps in eps_grid:
            per_seed = []
            for seed in seeds:
                try:
                    per_seed.append(_cell(mech, eps, seed))
                except Exception as exc:  # a mechanism that cannot fit is reported, not hidden
                    print(f"  {mech} eps={eps} seed={seed}: FAILED ({type(exc).__name__}: {exc})")
            if not per_seed:
                continue
            aware = [c["aware_auc"] for c in per_seed]
            dist = [c["distance_auc"] for c in per_seed]
            cell = {
                "mechanism": mech,
                "target_eps": eps,
                "seeds": len(per_seed),
                "aware_auc_mean": float(np.mean(aware)),
                "aware_auc_sd": float(np.std(aware, ddof=1)) if len(aware) > 1 else 0.0,
                "distance_auc_mean": float(np.mean(dist)),
                "distance_auc_sd": float(np.std(dist, ddof=1)) if len(dist) > 1 else 0.0,
                "delta_auc": float(np.mean(aware) - np.mean(dist)),
                "n_focal_points": per_seed[0]["n_focal_points"],
                "focal_source": per_seed[0]["focal_source"],
            }
            cells.append(cell)
            print(
                f"  {mech:<16} eps={eps:<5} aware={cell['aware_auc_mean']:.3f} "
                f"distance={cell['distance_auc_mean']:.3f} delta={cell['delta_auc']:+.3f}"
            )

    elapsed = round(time.time() - started, 1)
    payload = {
        "cells": cells,
        "n_rows": N_ROWS,
        "n_targets": N_TARGETS,
        "seeds": list(seeds),
        "eps_grid": list(eps_grid),
        "elapsed_seconds": elapsed,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT_JSON.relative_to(ROOT)}  ({elapsed}s)")


if __name__ == "__main__":
    main()
