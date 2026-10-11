"""Re-runs exactly the imputation-audit cells whose arm code changed, in place.

Arms A2, A3 and A4_CHARGED changed on 2026-10-11 (A3's sum sensitivity, declared-only
candidates, A4_CHARGED's Laplace(2/eps) votes and public distance fills, A2's mean). Every other
cell is untouched, so this re-runs only the committed cells of those arms, with the same seeds,
n and auditors as `run_imputation_audit.py`, and rewrites them in `results/imputation_audit.json`.

    python -m scripts.rerun_imputation_cells [--arms A2,A3,A4_CHARGED]
"""

import argparse
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.run_imputation_audit import boot_ci, run_single_cell  # noqa: E402
from synthproof.data.datasets import adult_schema  # noqa: E402
from synthproof.data.missingness import load_adult_raw  # noqa: E402

RESULTS = REPO_ROOT / "results" / "imputation_audit.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arms", default="A2,A3,A4_CHARGED")
    parser.add_argument("--out", default=str(RESULTS))
    args = parser.parse_args()
    arms = {a.strip() for a in args.arms.split(",") if a.strip()}

    out_path = Path(args.out)
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    todo = [k for k, v in payload["cells"].items() if v["arm"] in arms and not v.get("rerun")]
    print(f"{len(todo)} cells to re-run", flush=True)

    raw_df = load_adult_raw().df
    schema = adult_schema()
    for i, key in enumerate(todo, 1):
        cell = payload["cells"][key]
        t0 = time.time()
        per = {"marginal_ratio": [], "distance_mia": [], "domias": []}
        for s in range(int(cell["num_seeds"])):
            res = run_single_cell(
                arm=cell["arm"],
                mech_name=cell["mechanism"],
                eps=float(cell["epsilon"]),
                condition=cell["condition"],
                raw_df=raw_df,
                schema=schema,
                n=int(cell["n_members"]),
                seed=s,
            )
            for name in per:
                per[name].append(res[name])
        for name, raw in per.items():
            mean, lo, hi = boot_ci(raw)
            cell[name] = {"mean": mean, "ci_95": [lo, hi], "raw": raw}
        cell["rerun"] = "2026-10-11"
        payload["cells"][key] = cell
        payload["meta"]["rerun_2026_10_11"] = sorted(arms)
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(
            f"[{i}/{len(todo)}] {key}: distMIA={cell['distance_mia']['mean']:.4f} "
            f"({time.time() - t0:.0f}s)",
            flush=True,
        )


if __name__ == "__main__":
    main()
