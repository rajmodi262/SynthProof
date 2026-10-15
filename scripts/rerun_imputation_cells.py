"""Re-runs exactly the imputation-audit cells whose arm code changed, in place.

Arms A2, A3 and A4_CHARGED changed on 2026-10-11 (A3's sum sensitivity, declared-only
candidates, A4_CHARGED's Laplace(2/eps) votes and public distance fills, A2's mean). Every other
cell is untouched, so this re-runs only the committed cells of those arms, with the same seeds,
n and auditors as `run_imputation_audit.py`, and rewrites them in `results/imputation_audit.json`.

    python -m scripts.rerun_imputation_cells [--arms A2,A3,A4_CHARGED]

Re-run 2026-10-16 (tag "2026-10-16") after the W5 DP fixes: A3 and A4_CHARGED (real-valued sums
now released on an integer grid; A4's sum now shifted) and every DP-VAE cell (Poisson batches):

  python -m scripts.rerun_imputation_cells --arms A3,A4_CHARGED --mechanisms dpvae --tag 2026-10-16
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
    parser.add_argument(
        "--mechanisms", default="", help="also re-run every cell of these mechanisms, any arm"
    )
    parser.add_argument("--tag", default="2026-10-11", help="recorded in each re-run cell")
    args = parser.parse_args()
    arms = {a.strip() for a in args.arms.split(",") if a.strip()}

    out_path = Path(args.out)
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    mechs = {m.strip() for m in args.mechanisms.split(",") if m.strip()}
    todo = [
        k
        for k, v in payload["cells"].items()
        if (v["arm"] in arms or v["mechanism"] in mechs) and v.get("rerun") != args.tag
    ]
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
        cell["rerun"] = args.tag
        payload["cells"][key] = cell
        payload["meta"][f"rerun_{args.tag.replace('-', '_')}"] = sorted(arms | mechs)
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(
            f"[{i}/{len(todo)}] {key}: distMIA={cell['distance_mia']['mean']:.4f} "
            f"({time.time() - t0:.0f}s)",
            flush=True,
        )


if __name__ == "__main__":
    main()
