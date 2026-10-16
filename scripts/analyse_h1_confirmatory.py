"""W10: the preregistered analysis of the AIM-vs-pairwise confirmatory run.

Implements docs/prereg/W10_h1_confirmatory.md §3 exactly: for each dataset x epsilon, AIM vs
pairwise on correlation error -- Welch's test with Holm across the eight comparisons, TOST at
the fixed margin with a Bonferroni alpha, the minimum detectable difference at 80% power, and
one verdict out of four (AIM lower, pairwise lower, equivalent, inconclusive). Reads the
per-seed checkpoint cells; writes results/h1_confirmatory/analysis.json.

    python -m scripts.analyse_h1_confirmatory
    python -m scripts.analyse_h1_confirmatory --cells-root results --out /tmp/pilot.json  # pilot
"""

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy import stats
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.power import TTestIndPower
from statsmodels.stats.weightstats import ttost_ind

ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "docs" / "prereg" / "W10_h1_confirmatory.md"
AMENDMENTS = ROOT / "docs" / "prereg" / "W10_h1_confirmatory.amendments.md"
# Amendment A1 (docs/prereg/W10_h1_confirmatory.amendments.md): runtime cut the design to the one
# comparison the pilot left unresolved. Full plan: ("adult", "acs", "bank", "diabetes") x (1, 8).
DATASETS = ("adult",)
EPSILONS = (8.0,)
MECHANISMS = ("aim", "pairwise", "independent")
MARGIN = 0.005
ALPHA = 0.05
N_COMPARISONS = len(DATASETS) * len(EPSILONS)


def load_cells(cells_dir: Path) -> dict:
    """{(mechanism, eps): [correlation_error per seed]} from one dataset's checkpoint dir."""
    out: dict = {}
    for f in sorted(cells_dir.glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        if not d.get("completed", True):
            continue
        c = d["config"]
        key = (c["mechanism"], float(c["target_eps"]))
        out.setdefault(key, []).append(float(d["metrics"]["correlation_error"]))
    return out


def summary(x) -> dict:
    a = np.asarray(x, dtype=float)
    n = a.size
    sd = float(a.std(ddof=1)) if n > 1 else float("nan")
    half = float(stats.t.ppf(0.975, n - 1) * sd / math.sqrt(n)) if n > 1 else float("nan")
    return {"n": n, "mean": float(a.mean()), "sd": sd, "ci95": [a.mean() - half, a.mean() + half]}


def compare(aim, pairwise) -> dict:
    a, p = np.asarray(aim, float), np.asarray(pairwise, float)
    welch_p = float(stats.ttest_ind(a, p, equal_var=False).pvalue)
    tost_p = float(ttost_ind(a, p, -MARGIN, MARGIN, usevar="unequal")[0])
    pooled = math.sqrt((a.var(ddof=1) + p.var(ddof=1)) / 2.0)
    d = TTestIndPower().solve_power(nobs1=a.size, alpha=ALPHA, power=0.8, ratio=p.size / a.size)
    return {
        "difference_aim_minus_pairwise": float(a.mean() - p.mean()),
        "welch_p": welch_p,
        "tost_p": tost_p,
        "mde_at_80pct_power": float(d * pooled),
    }


def analyse(cells_root: Path, layout: str) -> dict:
    rows = []
    for ds in DATASETS:
        cells_dir = (
            cells_root / "h1_confirmatory" / f"{ds}_cells"
            if layout == "confirmatory"
            else cells_root / ("h1_cells" if ds == "adult" else f"{ds}/h1_cells")
        )
        cells = load_cells(cells_dir)
        for eps in EPSILONS:
            aim, pw = cells.get(("aim", eps), []), cells.get(("pairwise", eps), [])
            row = {
                "dataset": ds,
                "eps": eps,
                "cells": {m: summary(cells[(m, eps)]) for m in MECHANISMS if (m, eps) in cells},
            }
            if len(aim) > 1 and len(pw) > 1:
                row.update(compare(aim, pw))
            rows.append(row)

    tested = [r for r in rows if "welch_p" in r]
    if tested:
        reject, holm, _, _ = multipletests([r["welch_p"] for r in tested], ALPHA, "holm")
        for r, rej, ph in zip(tested, reject, holm, strict=True):
            r["welch_p_holm"] = float(ph)
            equivalent = r["tost_p"] < ALPHA / N_COMPARISONS
            if rej:
                r["verdict"] = (
                    "AIM lower" if r["difference_aim_minus_pairwise"] < 0 else "pairwise lower"
                )
            elif equivalent:
                r["verdict"] = "equivalent"
            else:
                r["verdict"] = "inconclusive"
    return {
        "preregistration": str(PREREG.relative_to(ROOT)).replace("\\", "/"),
        "preregistration_sha256": hashlib.sha256(PREREG.read_bytes()).hexdigest(),
        "amendments_sha256": hashlib.sha256(AMENDMENTS.read_bytes()).hexdigest(),
        "outcome": "correlation_error",
        "margin": MARGIN,
        "alpha": ALPHA,
        "tost_alpha": ALPHA / N_COMPARISONS,
        "comparisons": rows,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cells-root", default=str(ROOT / "results"))
    ap.add_argument(
        "--layout",
        choices=("confirmatory", "pilot"),
        default="confirmatory",
        help="where the per-seed cells live: results/h1_confirmatory/<ds>_cells, or the pilot's "
        "results/[<ds>/]h1_cells",
    )
    ap.add_argument("--out", default=str(ROOT / "results" / "h1_confirmatory" / "analysis.json"))
    args = ap.parse_args()
    result = analyse(Path(args.cells_root), args.layout)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    for r in result["comparisons"]:
        print(
            r["dataset"],
            r["eps"],
            r.get("verdict", "—"),
            round(r.get("welch_p_holm", float("nan")), 4),
        )


if __name__ == "__main__":
    main()
