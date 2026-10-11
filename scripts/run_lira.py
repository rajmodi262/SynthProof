"""LiRA against SynthProof's mechanisms on UCI Adult, gated by a positive control.

    python -m scripts.run_lira                       # default grid, writes results/lira.json
    python -m scripts.run_lira --targets 10 --shadows 8 --challenges 4    # quicker

The positive control runs FIRST: a generator that copies its training rows verbatim must be
detected (AUC >= 0.9), or the run stops before any DP mechanism is attacked. An attack that
cannot see a verbatim copy has no business reporting a null. Every AUC carries a 95% interval
resampled by target, and the shadow count is recorded beside it: a null at a small shadow count
is a bounded null (a weaker attack), never evidence of privacy.
"""

import argparse
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from synthproof.attacks.lira import LiRAAttack  # noqa: E402
from synthproof.data.datasets import load_adult  # noqa: E402
from synthproof.frontier.experiment import MECHANISMS  # noqa: E402
from synthproof.generators.leaky import LeakyGenerator  # noqa: E402

CONTROL_MIN_AUC = 0.9


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mechanisms", default="independent,pairwise,mst")
    ap.add_argument("--eps", default="1.0,8.0")
    ap.add_argument("--targets", type=int, default=20)
    ap.add_argument("--shadows", type=int, default=16)
    ap.add_argument("--challenges", type=int, default=8)
    ap.add_argument("--train-size", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="results/lira.json")
    a = ap.parse_args()

    population = load_adult()
    common = dict(
        num_targets=a.targets,
        num_shadows=a.shadows,
        num_challenges=a.challenges,
        train_size=a.train_size,
        seed=a.seed,
    )
    rows = []

    def record(res, seconds):
        lo, hi = res.auc_ci()
        row = {
            "mechanism": res.mechanism,
            "target_eps": res.target_eps,
            "auc": res.auc,
            "auc_ci_95": [lo, hi],
            "tpr_at_1pct_fpr": res.tpr_at_1pct_fpr,
            "tpr_at_10pct_fpr": res.tpr_at_10pct_fpr,
            "num_targets": res.num_targets,
            "num_shadows": res.num_shadows,
            "num_challenges": res.num_challenges,
            "train_size": res.train_size,
            "seconds": round(seconds, 1),
        }
        rows.append(row)
        print(
            f"{res.mechanism:12} eps={res.target_eps!s:5} AUC {res.auc:.3f} [{lo:.3f}, {hi:.3f}]"
            f"  TPR@1%FPR {res.tpr_at_1pct_fpr:.3f}  ({seconds:.0f}s)",
            flush=True,
        )
        return row

    t = time.time()
    control = LiRAAttack(
        lambda s: LeakyGenerator(seed=s, leak_fraction=1.0), "leaky_1.0", None, **common
    ).run(population)
    if record(control, time.time() - t)["auc"] < CONTROL_MIN_AUC:
        raise SystemExit(
            f"Positive control FAILED (AUC {control.auc:.3f} < {CONTROL_MIN_AUC}). The attack "
            "cannot see a verbatim copy, so no null below may be reported."
        )

    for mech in [m.strip() for m in a.mechanisms.split(",") if m.strip()]:
        if mech not in MECHANISMS:
            print(f"skipping {mech}: not available in this environment", flush=True)
            continue
        for eps in [float(e) for e in a.eps.split(",") if e.strip()]:
            t = time.time()
            res = LiRAAttack(lambda s, m=mech: MECHANISMS[m](seed=s), mech, eps, **common).run(
                population
            )
            record(res, time.time() - t)

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "dataset": "uci_adult",
                "attack": "LiRA (Carlini et al. 2022), shadow releases, per-target Gaussians",
                "score": "-log(1 + nearest-record distance)",
                "target_selection": "outlier",
                "control_min_auc": CONTROL_MIN_AUC,
                "rows": rows,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
