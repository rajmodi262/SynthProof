"""Summarizes imputation audit results from results/imputation_audit.json."""

import json
from pathlib import Path


def main():
    path = Path("results/imputation_audit.json")
    if not path.exists():
        print("No results file found.")
        return

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    cells = data.get("cells", {})
    print(f"Total cells completed: {len(cells)}")
    print("=" * 110)
    hdr = (
        f"{'Cell Key':38} | {'distMIA Mean':12} | {'distMIA 95% CI':22} | "
        f"{'DOMIAS Mean':12} | {'DOMIAS 95% CI':22}"
    )
    print(hdr)
    print("-" * 110)

    for k in sorted(cells.keys()):
        v = cells[k]
        d = v["distance_mia"]
        dom = v["domias"]
        d_mean = f"{d['mean']:.4f}"
        d_ci = f"[{d['ci_95'][0]:.4f}, {d['ci_95'][1]:.4f}]"
        dom_mean = f"{dom['mean']:.4f}"
        dom_ci = f"[{dom['ci_95'][0]:.4f}, {dom['ci_95'][1]:.4f}]"
        print(f"{k:38} | {d_mean:12} | {d_ci:22} | {dom_mean:12} | {dom_ci:22}")

    print("=" * 110)


if __name__ == "__main__":
    main()
