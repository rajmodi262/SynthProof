"""Turn the hand-extracted survey table into results/CEILING_SURVEY.md.

Pure arithmetic over `research/ceiling_survey_extraction.json`. It fetches nothing and infers
nothing: every value in that file was read out of a paper by hand under
`docs/CEILING_SURVEY_PROTOCOL.md`, which was frozen before any paper was read.

    python -m scripts.run_ceiling_survey
    python -m scripts.run_ceiling_survey --extraction path/to/other.json

Exits 2 -- not 0 -- when the extraction file is absent, so an unrun survey never looks like a
survey that found nothing.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

from synthproof.survey.ceiling_audit import (
    Row,
    classify_all,
    summarise,
    to_dict,
    wilson_interval,
)

DEFAULT_EXTRACTION = Path("research/ceiling_survey_extraction.json")
OUT_MD = Path("results/CEILING_SURVEY.md")
OUT_JSON = Path("results/ceiling_survey.json")

ALPHA_SWEEP = (0.01, 0.05, 0.10)


def load_rows(path: Path) -> List[Row]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [Row(**r) for r in payload["rows"]]


def _table(classified) -> str:
    head = (
        "| paper | config | estimator | budget | alpha | eps_emp | eps_proved | ceiling | class | ack? |\n"
        "|---|---|---|---:|---:|---:|---:|---:|---|---|\n"
    )
    def f(x):
        return "—" if x is None else (f"{x:g}" if isinstance(x, (int, float)) else str(x))
    rows = "".join(
        f"| {c.row.paper_id} | {c.row.config_label} | {c.row.estimator_family} | "
        f"{f(c.row.budget)} | {f(c.row.alpha)} | {f(c.row.eps_emp)} | {f(c.row.eps_proved)} | "
        f"{f(c.ceiling)} | **{c.klass}** | {c.row.acknowledged_limit} |\n"
        for c in classified
    )
    return head + rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--extraction", type=Path, default=DEFAULT_EXTRACTION)
    args = ap.parse_args()

    if not args.extraction.exists():
        print(
            f"NOT RUN: no extraction table at {args.extraction}.\n"
            f"The survey is hand-extraction under docs/CEILING_SURVEY_PROTOCOL.md; there is "
            f"nothing to compute until that file exists. Exiting 2 so this is not mistaken for "
            f"a survey that found nothing.",
            file=sys.stderr,
        )
        return 2

    rows = load_rows(args.extraction)
    classified = classify_all(rows)
    summary = summarise(classified)

    # Sensitivity 1 (protocol S9): K must not depend on our choice of alpha.
    sweep = {}
    for a in ALPHA_SWEEP:
        alt = [Row(**{**r.__dict__, "alpha": a}) if r.alpha is not None else r for r in rows]
        sweep[a] = summarise(classify_all(alt)).k

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps(
            {
                "headline": summary.headline(),
                "summary": {
                    "n_papers_included": summary.n_papers_included,
                    "k": summary.k,
                    "k_rate": summary.k_rate,
                    "k_ci_wilson_95": list(summary.k_ci),
                    "by_class": summary.by_class,
                    "n_excluded_undeterminable_estimator": summary.n_excluded_undeterminable_estimator,
                    "n_not_reported": summary.n_not_reported,
                    "n_underpowered_but_acknowledged": summary.n_underpowered_but_acknowledged,
                    "per_estimator": summary.per_estimator,
                },
                "alpha_sensitivity_k": {str(a): k for a, k in sweep.items()},
                "rows": to_dict(classified),
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    lo, hi = summary.k_ci
    md = [
        "# Ceiling survey — how many published empirical-privacy claims could have been made?",
        "",
        f"> **{summary.headline()}**",
        "",
        "> Protocol: [`docs/CEILING_SURVEY_PROTOCOL.md`](../docs/CEILING_SURVEY_PROTOCOL.md),",
        "> frozen and committed before any paper was read. Raw output:",
        "> [`ceiling_survey.json`](ceiling_survey.json). Regenerate:",
        "> `python -m scripts.run_ceiling_survey`.",
        "",
        "**This is not our mathematics.** The ceiling is a corollary of Steinke, Nasr & Jagielski",
        "(2023) Thm 2.1; Keinan, Shenfeld & Ligett ([arXiv:2503.07199](https://arxiv.org/abs/2503.07199))",
        "Thm 5.2 formalise the one-run case; and the concept is already named **\"maximum auditable",
        "epsilon\"** by Annamalai, Ganev & De Cristofaro ([arXiv:2405.10994](https://arxiv.org/abs/2405.10994))",
        "§2.2, who compute it **for their own configuration only**. Applying it per-paper across the",
        "literature is what is new here.",
        "",
        "## Headline",
        "",
        f"- **K = {summary.k} / {summary.n_papers_included}** included papers "
        f"({100 * summary.k_rate:.1f}%, 95% Wilson CI [{100 * lo:.1f}%, {100 * hi:.1f}%])",
        f"- **NOT REPORTED: {summary.n_not_reported}** — papers that state no audit configuration,",
        "  so the reach of their instrument cannot be recomputed at all. A separate finding about",
        "  reporting practice, never merged into K.",
        f"- **Excluded (undeterminable estimator): {summary.n_excluded_undeterminable_estimator}** —",
        "  the ceiling series could not be read, so the row was excluded rather than guessed.",
        f"- **Underpowered but candid: {summary.n_underpowered_but_acknowledged}** — these papers",
        "  disclosed their own limit. Restatements, not findings; excluded from K by construction.",
        "",
        "## Sensitivity — alpha sweep (protocol §9.1)",
        "",
        "| alpha | K |",
        "|---|---:|",
    ]
    md += [f"| {a} | {k} |" for a, k in sweep.items()]
    md += [
        "",
        "K must not depend on our choice of alpha. If it does, say so here and treat the result",
        "as alpha-dependent rather than as a property of the literature.",
        "",
        "## Per-estimator split (protocol §9.2)",
        "",
        "A K driven entirely by one estimator family is a finding about that family, not the field.",
        "",
        "```json",
        json.dumps(summary.per_estimator, indent=2, sort_keys=True),
        "```",
        "",
        "## The table",
        "",
        _table(classified),
        "",
        "## The objection this must survive",
        "",
        "**\"Post-hoc power is uninformative.\"** Correct, and standard — observed power is a",
        "one-to-one function of the p-value. **This is not observed power.**",
        "`eps_max(r) ~= log(r / ln(1/alpha))` depends only on the design parameters *r* and",
        "*alpha*, never on the observed outcome. It is a minimum-detectable-effect bound,",
        "computable before any data is seen.",
        "",
    ]
    OUT_MD.write_text("\n".join(md), encoding="utf-8")

    print(summary.headline())
    print(f"wrote {OUT_MD} and {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
