"""What could each auditor have certified, at the budget we actually spent?

WHY THIS EXISTS. `results/DETECTION_FLOOR.md` established that this project's canary auditor
could not have reported above 2.97 at m = 60, against a proved epsilon of 7.36 -- so
`eps_audited = 0.000` was structurally guaranteed. The conclusion drawn at the time was that
the ceiling is a property of canary auditing.

That conclusion was too broad. Ganev, Annamalai & Kulynych (TPDP 2026,
[arXiv:2604.18352](https://arxiv.org/abs/2604.18352)) obtain tight audits with a Gaussian-DP
estimator where a threshold-and-Clopper-Pearson estimator collapses to zero, and this project
reproduced a non-zero bound (mu_emp = 0.4014, `results/GDP_AUDIT.md`). The ceiling is a
property of THE ESTIMATOR, not of auditing.

This script makes that concrete across the project's own epsilon grid: for each epsilon, what
budget does each auditor need, and what could each have certified at the budget actually spent?

    canary auditing   budget = CANARIES planted inside ONE model fit
    GDP auditing      budget = RUNS PER WORLD, each a SEPARATE model fit

**The units are not interchangeable and the comparison must never be reported as a speed-up.**
A canary audit is one fit; a GDP audit at r runs per world is 2r fits. At n = 6,000 a fit is
roughly six seconds, so 20 runs per world is about four minutes of compute -- cheap, but not
free, and not the same resource as a canary. What IS comparable is STATISTICAL reach: whether
the instrument could have produced the number being sought at all.

Usage:
    python -m scripts.run_audit_planner
"""

import json
import time
from pathlib import Path

from synthproof.audit.gdp import max_provable_mu, mu_from_eps_delta, runs_needed_for_mu
from synthproof.audit.steinke import canaries_needed_for, max_provable_epsilon

EPS_GRID = (0.5, 1.0, 2.0, 4.0, 8.0, 7.36)
DELTA = 1e-5
ALPHA = 0.05

# What the project actually spent, from results/H1_RESULTS.md and results/GDP_AUDIT.md.
CANARIES_SPENT = 60
GDP_RUNS_SPENT = 2500

OUT = "results/audit_planner.json"


def main():
    t0 = time.time()
    rows = []
    for eps in sorted(set(EPS_GRID)):
        mu = mu_from_eps_delta(eps, DELTA)
        rows.append(
            {
                "target_eps": eps,
                "equivalent_mu": mu,
                # --- canary auditing, budget measured in planted canaries ---------------
                "canaries_needed": canaries_needed_for(eps, ALPHA),
                "canary_ceiling_at_spent": max_provable_epsilon(CANARIES_SPENT, ALPHA),
                "canary_can_certify": bool(max_provable_epsilon(CANARIES_SPENT, ALPHA) >= eps),
                # --- GDP auditing, budget measured in runs PER WORLD --------------------
                "gdp_runs_needed": runs_needed_for_mu(mu, ALPHA),
                "gdp_ceiling_at_spent": max_provable_mu(GDP_RUNS_SPENT, GDP_RUNS_SPENT, ALPHA),
                "gdp_can_certify": bool(
                    max_provable_mu(GDP_RUNS_SPENT, GDP_RUNS_SPENT, ALPHA) >= mu
                ),
                # --- the like-for-like question: same NUMERIC budget, both estimators ---
                "gdp_ceiling_at_canary_budget": max_provable_mu(
                    CANARIES_SPENT, CANARIES_SPENT, ALPHA
                ),
                "gdp_can_certify_at_canary_budget": bool(
                    max_provable_mu(CANARIES_SPENT, CANARIES_SPENT, ALPHA) >= mu
                ),
            }
        )

    print(f"delta = {DELTA:g}   alpha = {ALPHA}   canaries spent = {CANARIES_SPENT}")
    print("\nWhat each auditor NEEDS, and what it could certify at the budget spent:\n")
    print(
        f"{'eps':>6} {'mu':>7} | {'canaries':>9} {'ceil@60':>8} {'ok':>3} | "
        f"{'runs':>6} {'ceil@60':>8} {'ok':>3}"
    )
    print("-" * 68)
    for r in rows:
        print(
            f"{r['target_eps']:>6.2f} {r['equivalent_mu']:>7.4f} | "
            f"{r['canaries_needed']:>9,} {r['canary_ceiling_at_spent']:>8.3f} "
            f"{'yes' if r['canary_can_certify'] else 'NO':>3} | "
            f"{r['gdp_runs_needed']:>6,} {r['gdp_ceiling_at_canary_budget']:>8.3f} "
            f"{'yes' if r['gdp_can_certify_at_canary_budget'] else 'NO':>3}"
        )

    canary_ok = sum(r["canary_can_certify"] for r in rows)
    gdp_ok = sum(r["gdp_can_certify_at_canary_budget"] for r in rows)
    print(
        f"\nAt a numeric budget of {CANARIES_SPENT}: the canary estimator can certify "
        f"{canary_ok}/{len(rows)} of these targets;"
    )
    print(f"the GDP estimator can certify {gdp_ok}/{len(rows)}.")
    print(
        "\nUNITS WARNING, which must accompany every quotation of this table:\n"
        "  a canary budget of 60 is 60 records planted in ONE fit;\n"
        "  a GDP budget of 60 is 60 runs PER WORLD = 120 separate fits.\n"
        "  These are different resources. The table compares STATISTICAL REACH at equal\n"
        "  numeric budget, NOT cost, and it is not a speed-up."
    )

    out = {
        "delta": DELTA,
        "alpha": ALPHA,
        "canaries_spent": CANARIES_SPENT,
        "gdp_runs_spent": GDP_RUNS_SPENT,
        "units_warning": (
            "A canary budget of m is m records planted inside ONE model fit. A GDP budget of r "
            "is r runs PER WORLD, i.e. 2r separate model fits. The comparison is of statistical "
            "reach at equal numeric budget, never of cost or speed."
        ),
        "rows": rows,
        "canary_targets_certifiable_at_spent_budget": canary_ok,
        "gdp_targets_certifiable_at_same_numeric_budget": gdp_ok,
        "elapsed_seconds": round(time.time() - t0, 3),
    }
    Path(OUT).parent.mkdir(parents=True, exist_ok=True)
    Path(OUT).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nwritten to {OUT}")


if __name__ == "__main__":
    main()
