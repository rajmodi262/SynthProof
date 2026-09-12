"""Emits `web/pitch/data.ts` from the committed results files.

No number in the deck is typed by hand. Every field below names the file it was read from,
and that path is surfaced in the slide's speaker notes, so a panellist who asks "where does
that come from" gets an answer that can be opened in front of them.

Run from the repository root:

    python web/pitch/build_data.py

Reads only. Writes only `web/pitch/data.ts`.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "data.ts"


def load(rel: str) -> dict:
    with (ROOT / rel).open(encoding="utf-8") as fh:
        return json.load(fh)


def stat(cell: dict, key: str) -> dict:
    s = cell[key]
    return {"mean": s["mean"], "lo": s["lo"], "hi": s["hi"], "n": s["n"]}


def h1_block(rel: str) -> dict:
    d = load(rel)
    return {
        "source": rel,
        "dataset": d["dataset"],
        "label": d["dataset_label"],
        "nRows": d["n_rows"],
        "seeds": len(d["seeds"]),
        "epsGrid": d["eps_grid"],
        "mechanisms": d["mechanisms"],
        "corrCols": d["corr_cols"],
        "trueCorrelation": d["true_correlation"],
        "trtrF1": d["cells"][0]["trtr_f1"]["mean"],
        "cells": [
            {
                "mechanism": c["mechanism"],
                "eps": c["target_eps"],
                "proved": c["proved_eps"]["mean"],
                "audited": c["audited_eps"]["mean"],
                "corrErr": stat(c, "correlation_error"),
                "tstrF1": stat(c, "tstr_f1"),
                "miaAuc": c["mia_auc"]["mean"],
            }
            for c in d["cells"]
        ],
    }


def h2_block(rel: str) -> dict:
    d = load(rel)
    det = d["detectability"]
    m = d["multiplicity"]
    return {
        "source": rel,
        "nTests": len(m["labels"]),
        "survivingBh": sum(1 for x in m["bh_reject"] if x),
        "survivingBonferroni": sum(1 for x in m["bonferroni_reject"] if x),
        "minRawP": min(m["raw_p"]),
        "numCanaries": det["num_canaries"],
        "alpha": det["alpha"],
        "ceiling": det["ceiling"],
        "mdeEpsilon": det["mde_epsilon"],
        "mdeAccuracy": det["mde_accuracy"],
        "observedMaxEpsilon": det["observed_max_epsilon"],
        "observedMaxAccuracy": det["observed_max_accuracy"],
        "fractionOfRange": det["fraction_of_range_used"],
        "seeds": d["source_seeds"],
        "nRows": d["source_n_rows"],
    }


def confound_block(rel: str) -> dict:
    d = load(rel)
    c = d["summary"]["conditional"]

    def opt(x):
        return None if x is None else {"mean": x["mean"], "lo": x["lo"], "hi": x["hi"], "n": x["n"]}

    return {
        "source": rel,
        "label": d["dataset_label"],
        "confirmed": d["confound_confirmed"],
        "verdict": d["verdict"],
        "selectedPairs": c["selected_pairs"],
        "unselectedPairs": c["unselected_pairs"],
        "aimOnSelected": opt(c["aim_on_selected"]),
        "indepOnSelected": opt(c["independent_on_selected"]),
        "aimOnUnselected": opt(c["aim_on_unselected"]),
        "indepOnUnselected": opt(c["independent_on_unselected"]),
    }


def floor_block(rel: str) -> dict:
    d = load(rel)
    return {
        "source": rel,
        "alpha": d["alpha"],
        "nRows": d["rows"],
        "floors": {k: v for k, v in d["floors"].items()},
        "cells": [
            {
                "leak": c["leak_fraction"],
                "r": c["num_canaries"],
                "detectionRate": c["detection_rate"],
                "meanEps": c["mean_audited_eps"],
                "tpr": c["mean_tpr"],
                "fpr": c["mean_fpr"],
            }
            for c in d["cells"]
        ],
    }


def h3_block(rel: str) -> dict:
    d = load(rel)
    return {
        "source": rel,
        "label": d["dataset_label"],
        "priorityWeight": d["priority_weight"],
        "weightsSource": d["weights_source"],
        "verdict": d["verdict"],
        "nCells": len(d["cells"]),
    }


# The ceiling is a closed form, so it is recomputed here from the same expression the
# auditor uses (synthproof/audit/steinke.py:max_provable_epsilon) rather than copied from a
# table. Keeping the two in one place means the calculator on slide 6 cannot drift from the
# instrument.
def max_provable_epsilon(r: int, alpha: float = 0.05) -> float:
    a = alpha ** (1.0 / r)
    return math.log(a / (1.0 - a))


def canaries_needed_for(eps: float, alpha: float = 0.05) -> int:
    p = math.exp(eps) / (1.0 + math.exp(eps))
    return max(1, math.ceil(math.log(alpha) / math.log(p)))


def main() -> None:
    payload = {
        "generatedFrom": "committed results files; see each block's `source`",
        "h1": {"adult": h1_block("results/h1_all_families.json"),
               "acs": h1_block("results/acs/h1_all_families.json")},
        "h2": {"adult": h2_block("results/h2_analysis.json"),
               "acs": h2_block("results/acs/h2_analysis.json")},
        "h3": {"adult": h3_block("results/h3_allocation.json"),
               "acs": h3_block("results/acs/h3_allocation.json")},
        "confound": {"adult": confound_block("results/clique_confound.json"),
                     "acs": confound_block("results/acs/clique_confound.json")},
        "floor": floor_block("results/detection_floor.json"),
        "mutation": {
            **load("results/mutation_probe.json"),
            "source": "results/mutation_probe.json",
        },
        "ceilingCurve": [
            {"r": r, "epsMax": max_provable_epsilon(r)}
            for r in [5, 10, 15, 20, 25, 30, 40, 44, 50, 60, 80, 100, 120, 160, 200, 300,
                      400, 600, 800, 1200, 2000, 3000, 5000]
        ],
        "canariesNeeded": [
            {"eps": e, "r": canaries_needed_for(e)}
            for e in [0.5, 1.0, 2.0, 4.0, 6.543, 7.356, 8.0]
        ],
    }

    body = json.dumps(payload, indent=2)
    OUT.write_text(
        "// GENERATED FILE — do not edit by hand.\n"
        "// Produced by `python web/pitch/build_data.py`, which reads only the committed\n"
        "// results/*.json files. Every `source` field below is a real path in this repo.\n"
        "// If a number on a slide is questioned, open the file named in its `source`.\n\n"
        f"export const DATA = {body} as const\n\n"
        "export type Data = typeof DATA\n",
        encoding="utf-8",
    )
    print(f"wrote {OUT.relative_to(ROOT)}  ({len(body):,} bytes of committed numbers)")


if __name__ == "__main__":
    main()
