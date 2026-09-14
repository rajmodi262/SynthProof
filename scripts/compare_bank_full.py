"""Compare H1 results across Adult, ACS, and Bank Marketing.

Reads the three result files:
  results/h1_all_families.json
  results/acs/h1_all_families.json
  results/bank/h1_all_families.json
and formats the cross-dataset comparison tables at epsilon = 8.
"""

import json
from pathlib import Path


def load_cell(json_path: Path, mechanism: str, target_eps: float = 8.0) -> dict:
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    for c in data.get("cells", []):
        if c.get("mechanism") == mechanism and abs(c.get("target_eps", 0) - target_eps) < 1e-4:
            return c
    raise ValueError(f"Cell for {mechanism} at eps={target_eps} not found in {json_path}")


def main():
    root = Path(__file__).resolve().parents[1]
    results_dir = root / "results"

    datasets = [
        ("Adult", results_dir / "h1_all_families.json"),
        ("ACSIncome", results_dir / "acs" / "h1_all_families.json"),
        ("Bank Marketing", results_dir / "bank" / "h1_all_families.json"),
    ]

    print("Correlation error at eps = 8 (mean [95% CI]):\n")
    print(
        f"{'Dataset':<16} | {'true corr':>9} | {'independent':<25} | {'pairwise':<25} | {'aim':<25}"
    )
    print("-" * 115)

    for label, path in datasets:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        true_corr = d.get("true_correlation", 0.0)

        ind = load_cell(path, "independent", 8.0)["correlation_error"]
        pw = load_cell(path, "pairwise", 8.0)["correlation_error"]
        aim = load_cell(path, "aim", 8.0)["correlation_error"]

        ind_str = f"{ind['mean']:.4f} [{ind['lo']:.3f}, {ind['hi']:.3f}]"
        pw_str = f"{pw['mean']:.4f} [{pw['lo']:.3f}, {pw['hi']:.3f}]"
        aim_str = f"{aim['mean']:.4f} [{aim['lo']:.3f}, {aim['hi']:.3f}]"

        print(f"{label:<16} | {true_corr:>+9.4f} | {ind_str:<25} | {pw_str:<25} | {aim_str:<25}")

    print("\n" + "=" * 80 + "\n")
    print("TSTR F1 at eps = 8 (mean):\n")
    print(f"{'Dataset':<16} | {'TRTR':>8} | {'independent':>11} | {'pairwise':>8} | {'aim':>8}")
    print("-" * 65)

    for label, path in datasets:
        ind = load_cell(path, "independent", 8.0)
        pw = load_cell(path, "pairwise", 8.0)
        aim = load_cell(path, "aim", 8.0)

        trtr = ind.get("trtr_f1", {}).get("mean", 0.0)
        ind_f1 = ind["tstr_f1"]["mean"]
        pw_f1 = pw["tstr_f1"]["mean"]
        aim_f1 = aim["tstr_f1"]["mean"]

        print(f"{label:<16} | {trtr:>8.4f} | {ind_f1:>11.4f} | {pw_f1:>8.4f} | {aim_f1:>8.4f}")


if __name__ == "__main__":
    main()
