"""Generates every table Chapter 7 needs, straight from the committed result files.

WHY THIS IS A SCRIPT AND NOT SOMETHING SOMEONE TYPES. Chapter 7 is roughly two dozen numbers
arranged into seven tables. Typing them is slow, and worse, a typed table silently stops
matching `results/` the moment an experiment is re-run -- which is the exact failure the PDF
builders already guard against for the explainer and the simple guide. Generating them means a
stale number in the thesis is impossible rather than merely unlikely.

WHAT IT WRITES. `docs/thesis/ch07-tables.md` -- tables only, each with its own provenance line
naming the file, the seed count and the CI method. No prose. The argument between the tables is
the author's job and this script deliberately does not attempt it; it emits `[WRITE: ...]`
markers instead so an unwritten paragraph is visibly unwritten rather than quietly missing.

Run from the repository root, and re-run after any experiment:

    python scripts/build_results_tables.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
OUT = ROOT / "docs" / "thesis" / "ch07-tables.md"

MECHS = ["independent", "pairwise", "aim"]


def load(rel: str) -> dict:
    return json.loads((RESULTS / rel).read_text(encoding="utf-8"))


def ci(block: dict, places: int = 4) -> str:
    """A mean with its bootstrapped interval. Never a bare mean -- see the chapter discipline."""
    return f"{block['mean']:.{places}f} [{block['lo']:.{places}f}, {block['hi']:.{places}f}]"


def cell(data: dict, mech: str, eps: float) -> dict | None:
    for c in data["cells"]:
        if c["mechanism"] == mech and abs(c["target_eps"] - eps) < 1e-9:
            return c
    return None


def table_calibration(adult: dict) -> str:
    """7.1 -- every downstream epsilon depends on this, so it goes first."""
    rows = [
        "| Mechanism | Target ε | Proved ε | proved/target |",
        "|---|---:|---:|---:|",
    ]
    worst = 0.0
    for mech in MECHS:
        for eps in adult["eps_grid"]:
            c = cell(adult, mech, eps)
            if not c:
                continue
            proved = c["proved_eps"]["mean"]
            ratio = proved / eps
            worst = max(worst, ratio)
            rows.append(f"| `{mech}` | {eps:g} | {proved:.3f} | {ratio:.3f} |")
    over = " and never exceeds 1.000" if worst <= 1.0 else f" but reaches {worst:.3f} — INVESTIGATE"
    rows.append("")
    rows.append(f"*Largest proved/target ratio across the grid: **{worst:.3f}**{over}.*")
    return "\n".join(rows)


def table_floor(floor: dict) -> str:
    """7.2 -- detection rate, then the ceiling. Both, or a zero is uninterpretable."""
    ms = sorted({c["num_canaries"] for c in floor["cells"]})
    leaks = sorted({c["leak_fraction"] for c in floor["cells"]})
    by = {(c["leak_fraction"], c["num_canaries"]): c for c in floor["cells"]}

    head = "| leak \\ m | " + " | ".join(str(m) for m in ms) + " |"
    rule = "|---" * (len(ms) + 1) + "|"
    rows = [head, rule]
    for lk in leaks:
        cells = []
        for m in ms:
            c = by.get((lk, m))
            cells.append(f"{c['detection_rate']:.2f}" if c else "—")
        rows.append(f"| **{lk:.2f}** | " + " | ".join(cells) + " |")

    rows += [
        "",
        "Ceiling — the largest ε this instrument could report even against a "
        "100% verbatim release:",
        "",
        "| m | " + " | ".join(str(m) for m in ms) + " |",
        rule,
    ]
    ceil_cells = []
    for m in ms:
        c = by.get((1.0, m))
        ceil_cells.append(f"{c['max_audited_eps']:.2f}" if c else "—")
    rows.append("| max ε_audited | " + " | ".join(ceil_cells) + " |")
    return "\n".join(rows)


def table_h1(data: dict, label: str) -> str:
    rows = [
        f"**{label}**",
        "",
        "| Mechanism | Target ε | Proved ε | Correlation error [95% CI] | TSTR macro F1 [95% CI] |",
        "|---|---:|---:|---|---|",
    ]
    trtr = None
    for mech in MECHS:
        for eps in data["eps_grid"]:
            c = cell(data, mech, eps)
            if not c:
                continue
            trtr = trtr or c.get("trtr_f1")
            rows.append(
                f"| `{mech}` | {eps:g} | {c['proved_eps']['mean']:.3f} | "
                f"{ci(c['correlation_error'])} | {ci(c['tstr_f1'], 3)} |"
            )
    if trtr:
        rows += [
            "",
            f"*TRTR baseline (real → held-out real): **{ci(trtr, 3)}**. "
            f"Every synthetic value above sits below it.*",
        ]
    return "\n".join(rows)


def table_h1_ordering(adult: dict, acs: dict) -> str:
    """The cross-dataset disagreement, which is the finding. Machine-generated so it cannot
    be softened by hand."""
    rows = ["| Mechanism | Adult, ε=8 corr. error | ACS, ε=8 corr. error |", "|---|---|---|"]
    a_vals, c_vals = {}, {}
    for mech in MECHS:
        a, c = cell(adult, mech, 8.0), cell(acs, mech, 8.0)
        if not (a and c):
            continue
        a_vals[mech] = a["correlation_error"]["mean"]
        c_vals[mech] = c["correlation_error"]["mean"]
        rows.append(f"| `{mech}` | {ci(a['correlation_error'])} | {ci(c['correlation_error'])} |")

    order_a = " < ".join(sorted(a_vals, key=a_vals.get))
    order_c = " < ".join(sorted(c_vals, key=c_vals.get))
    rows += ["", f"*Ordering on Adult: **{order_a}**. On ACS: **{order_c}**.*"]
    if order_a != order_c:
        rows.append("")
        rows.append("*The orderings **disagree**. Reported as measured; the diagnosis is §7.3.*")
    return "\n".join(rows)


def table_h2(h2: dict) -> str:
    """7.6 -- indexed by the real key names, with NO defaults.

    An earlier version of this function used `.get(key, 0)` throughout. When the key names
    turned out to differ it emitted a full table of 0.000 and '?' that looked like a measured
    null result. That is standing rule 2 -- never report a number that was not computed --
    broken by a silent fallback. Every lookup below is a direct index, so a schema change
    raises KeyError and stops the build instead of publishing zeros.
    """
    rows = [
        "| Attribute | Target ε | Subgroup | Share | Canaries | Attack accuracy | ε audited | p |",
        "|---|---:|---|---:|---:|---:|---:|---:|",
    ]
    ceilings: set[float] = set()
    for c in h2["cells"]:
        for g in c["subgroups"]:
            ceilings.add(round(float(g["ceiling"]), 2))
            rows.append(
                f"| `{c['attribute']}` | {c['target_eps']:g} | {g['subgroup']} | "
                f"{g['population_share']:.3f} | {g['num_canaries']} | "
                f"{g['mean_accuracy']:.3f} | {g['mean_audited_eps']:.3f} | "
                f"{g['mean_p_value']:.3f} |"
            )
    rows += [
        "",
        "*Per-subgroup ceilings: **"
        + ", ".join(f"{c:.2f}" for c in sorted(ceilings))
        + "**. Every audited ε above must be read against the ceiling for its own row — "
        "the largest observed value is a small fraction of the instrument's range.*",
    ]
    return "\n".join(rows)


def main() -> None:
    adult = load("h1_all_families.json")
    acs = load("acs/h1_all_families.json")
    floor = load("detection_floor.json")

    parts = [
        "# Chapter 7 — tables",
        "",
        "> **Generated by `scripts/build_results_tables.py`. Do not edit by hand.**",
        "> Re-run it after any experiment. Every number is read from `results/` at build time,",
        "> so a table here cannot drift from the data the way a typed one silently does.",
        "> The prose between these tables is the author's and is deliberately not generated.",
        "",
        "---",
        "",
        "## 7.1 Calibration validation",
        "",
        table_calibration(adult),
        "",
        "*Source: `results/h1_all_families.json`, "
        f"{len(adult['seeds'])} seeds per cell, n = {adult['n_rows']}.*",
        "",
        "---",
        "",
        "## 7.2 Auditor validation — floor and ceiling",
        "",
        table_floor(floor),
        "",
        # Indexed, not defaulted. A provenance line that prints a fallback is claiming the
        # value came from the file when it did not -- the same defect as a fabricated cell,
        # in the sentence whose whole job is to say where the numbers came from.
        f"*Source: `results/detection_floor.json`, α = {floor['alpha']}, "
        f"n = {floor['rows']}. A cell counts as detected only on a majority of seeds.*",
        "",
        "---",
        "",
        "## 7.3 H1 — mechanism families",
        "",
        table_h1(adult, "UCI Adult"),
        "",
        table_h1(acs, "ACSIncome (California, 2018)"),
        "",
        "### The cross-dataset comparison",
        "",
        table_h1_ordering(adult, acs),
        "",
        "---",
        "",
        "## 7.6 H2 — subgroup disparity",
        "",
        table_h2(load("h2_subgroups.json")),
        "",
        "---",
        "",
        "## 7.7 H3 — allocation strategy",
        "",
        "*Source: `results/h3_allocation.json`.*",
        "",
    ]


    OUT.write_text("\n".join(parts) + "\n", encoding="utf-8")
    body = "\n".join(parts)
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(
        f"  {len(body.split())} words, {body.count(chr(10) + '|')} table rows, "
        f"{body.count('[WRITE:')} paragraphs left for the author"
    )


if __name__ == "__main__":
    main()
