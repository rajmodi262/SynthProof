"""Rewrites the A2/A3 numbers in research/imputation_audit/RESULTS.md from the results JSON.

The document's tables were typed by hand. After the 2026-10-11 re-run of arms A2, A3 and
A4_CHARGED (`scripts/rerun_imputation_cells.py`) the A2 and A3 cells changed and nothing else
did, so this rewrites exactly those cells, row by row. It is row-aware on purpose: A1 and A2 had
identical values in some rows, and a global find-and-replace would have corrupted A1.

    python -m scripts.update_imputation_results_doc
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "research" / "imputation_audit" / "RESULTS.md"
DATA = ROOT / "results" / "imputation_audit.json"

MECH = {"Independent": "independent", "DP-VAE": "dpvae"}
COND = {
    "MCAR 10%": "mcar_10",
    "MCAR 20%": "mcar_20",
    "MAR 10%": "mar_10",
    "MAR 20%": "mar_20",
    "MNAR 10%": "mnar_10",
    "MNAR 20%": "mnar_20",
}
CI = r"\d\.\d{4} \[\d\.\d{4}, \d\.\d{4}\]"


def fmt(block: dict) -> str:
    lo, hi = block["ci_95"]
    return f"{block['mean']:.4f} [{lo:.4f}, {hi:.4f}]"


def overlaps(a: dict, b: dict) -> bool:
    return not (a["ci_95"][1] < b["ci_95"][0] or b["ci_95"][1] < a["ci_95"][0])


def main() -> None:
    cells = json.loads(DATA.read_text(encoding="utf-8"))["cells"]

    def cell(arm, mech, eps, cond):
        return cells[f"{arm}_{mech}_eps{float(eps)}_{cond}"]

    with open(DOC, encoding="utf-8", newline="") as fh:
        lines = fh.read().splitlines(keepends=True)
    changed = 0
    for i, line in enumerate(lines):
        # Primary table: | **Mechanism** | eps | **A2** | desc | dist | domias | verdict |
        m = re.match(r"\| \*\*(Independent|DP-VAE)\*\* \| ([\d.]+) \| \*\*(A2|A3)\*\* \|", line)
        if m:
            c = cell(m.group(3), MECH[m.group(1)], m.group(2), "native")
            cols = line.split("|")
            # cols: '', mech, eps, arm, desc, dist, domias, verdict, '\n'
            bold = cols[5].strip().startswith("**")
            cols[5] = f" **{fmt(c['distance_mia'])}** " if bold else f" {fmt(c['distance_mia'])} "
            cols[6] = f" {fmt(c['domias'])} "
            lines[i] = "|".join(cols)
            changed += 1
            continue
        # Overlay table: | **MCAR 10%** | eps | A2 dist | A3 dist | Overlap? | A0 dist |
        m = re.match(r"\| \*\*((?:MCAR|MAR|MNAR) \d+%)\*\* \| ([\d.]+) \|", line)
        if m:
            cond, eps = COND[m.group(1)], m.group(2)
            a2 = cell("A2", "independent", eps, cond)["distance_mia"]
            a3 = cell("A3", "independent", eps, cond)["distance_mia"]
            cols = line.split("|")
            cols[3], cols[4] = f" {fmt(a2)} ", f" {fmt(a3)} "
            cols[5] = " **YES** " if overlaps(a2, a3) else " **NO** "
            lines[i] = "|".join(cols)
            changed += 1
    text = "".join(lines)

    a2_1 = cell("A2", "independent", 1.0, "native")["distance_mia"]
    a2_4 = cell("A2", "independent", 4.0, "native")["distance_mia"]
    a3_1 = cell("A3", "independent", 1.0, "native")["distance_mia"]
    a3_4 = cell("A3", "independent", 4.0, "native")["distance_mia"]
    # Executive summary, bullet 2: the four A2/A3 native numbers, in order.
    bullet = re.search(r"2\. \*\*Both Arms Remain at Baseline Chance:\*\*[^\n]*", text)
    assert bullet, "executive summary bullet 2 not found"
    new_bullet = bullet.group(0)
    for old, new in zip(re.findall(CI, new_bullet), (a2_1, a2_4, a3_1, a3_4), strict=True):
        new_bullet = new_bullet.replace(old, fmt(new), 1)
    text = text.replace(bullet.group(0), new_bullet)
    # K3 grounding table rows for A2 and A3 (epsilon = 1, native).
    k3_rows = (("Arm A2 (Uncharged Imputation)", a2_1), ("Arm A3 (Charged DP Imputation)", a3_1))
    for label, blk in k3_rows:
        row = re.search(rf"\| \*\*{re.escape(label)}\*\* \|[^\n]*", text)
        assert row, label
        lo, hi = blk["ci_95"]
        new_row = re.sub(
            r"\*\*\d\.\d{4}\*\* \| \*\*\[\d\.\d{4}, \d\.\d{4}\]\*\*",
            f"**{blk['mean']:.4f}** | **[{lo:.4f}, {hi:.4f}]**",
            row.group(0),
        )
        text = text.replace(row.group(0), new_row)

    # Every A2/A3 pair must still overlap for the stated verdict to stand; refuse otherwise.
    for key, c in cells.items():
        if c["arm"] == "A2":
            twin = cells.get(key.replace("A2_", "A3_", 1))
            if twin and not overlaps(c["distance_mia"], twin["distance_mia"]):
                raise SystemExit(f"A2 and A3 SEPARATE at {key}; the null verdict must be revisited")

    with open(DOC, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print(f"rewrote {changed} table rows, the summary bullet and the K3 rows in {DOC.name}")


if __name__ == "__main__":
    main()
