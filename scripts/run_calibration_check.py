"""Calibration accuracy, written to a results file so the thesis's calibration numbers have a
source.

`docs/thesis/ch05-implementation.md` §5.4 and `ch07-results.md` §7.1 quoted a single-stage
result (target 8.0 -> 7.999605) and a two-stage composition that existed only in a code comment
in `synthproof/accounting/calibration.py`. This recomputes them, plus the 24-configuration grid
the CI `calibration-guard` job asserts, and writes `results/calibration_check.json`.

Deterministic: no data and no randomness are involved, only the accountant's composition.

    python -m scripts.run_calibration_check
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from synthproof.accounting.accountant import Accountant  # noqa: E402
from synthproof.accounting.calibration import (  # noqa: E402
    BudgetPlan,
    calibrate_noise_scale,
    epsilon_for_noise_scale,
)
from synthproof.accounting.types import MechanismSpec  # noqa: E402

DELTA = 1e-5
TARGETS = (0.5, 1.0, 2.0, 4.0, 8.0)
OUT = REPO_ROOT / "results" / "calibration_check.json"


def _two_stage(total: float, first_frac: float) -> float:
    """Each stage calibrated to its LINEAR share, then composed by the accountant."""
    acct = Accountant(budget_eps=float("inf"), budget_delta=DELTA)
    for share in (first_frac * total, (1.0 - first_frac) * total):
        scale = calibrate_noise_scale(share, DELTA, "gaussian", 1.0, 1)
        acct.charge(MechanismSpec(name="gaussian", noise_scale=scale, sensitivity=1.0))
    return float(acct.total(DELTA))


def main() -> None:
    single = []
    for t in TARGETS:
        s = calibrate_noise_scale(t, DELTA, "gaussian", 1.0, 1)
        got = epsilon_for_noise_scale(s, DELTA, "gaussian", 1.0, 1)
        single.append({"target_eps": t, "noise_scale": s, "achieved_eps": got, "ratio": got / t})

    two_stage = [
        {"target_eps": t, "split": [0.2, 0.8], "composed_eps": c, "ratio": c / t}
        for t in TARGETS
        for c in [_two_stage(t, 0.2)]
    ]
    budget_plan = [
        {"target_eps": t, "split": [0.1, 0.9], "composed_eps": c, "ratio": c / t}
        for t in TARGETS
        for c in [BudgetPlan.split(t, DELTA).composed_eps]
    ]

    # The same grid the CI `calibration-guard` job runs (.github/workflows/ci.yml).
    ci_grid = []
    for name in ("gaussian", "laplace"):
        for steps in (1, 5, 20):
            for t in (0.5, 1.0, 2.0, 8.0):
                s = calibrate_noise_scale(t, DELTA, name, 1.0, steps)
                got = epsilon_for_noise_scale(s, DELTA, name, 1.0, steps)
                ci_grid.append(
                    {"mechanism": name, "steps": steps, "target_eps": t, "ratio": got / t}
                )
    ratios = [c["ratio"] for c in ci_grid]

    out = {
        "delta": DELTA,
        "single_stage_gaussian": single,
        "two_stage_linear_split": two_stage,
        "budget_plan_default": budget_plan,
        "ci_guard_grid": ci_grid,
        "ci_guard_summary": {
            "configurations": len(ci_grid),
            "min_ratio": min(ratios),
            "max_ratio": max(ratios),
            "bounds_asserted_by_ci": [0.99, 1.001],
        },
        "bisection": {
            "stopping_rule": "relative bracket width hi - lo <= tol * hi",
            "tol": 1e-4,
            "max_iter": 200,
            "returns": "the conservative end of the bracket (achieved eps <= target)",
        },
    }
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    for row in single:
        print(f"single  {row['target_eps']:>4} -> {row['achieved_eps']:.6f}")
    for row in two_stage:
        print(f"0.2/0.8 {row['target_eps']:>4} -> {row['composed_eps']:.6f}  ({row['ratio']:.4f})")
    print(f"CI grid: {len(ci_grid)} configs, ratio {min(ratios):.6f}..{max(ratios):.6f}")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
