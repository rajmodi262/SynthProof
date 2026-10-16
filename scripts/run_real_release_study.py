"""W11: run the boundary auditor over real DP releases, as their own documentation describes them.

Input: `research/real_releases/releases.json`, one record per release, each property coded from a
fetched primary source with a short quote. Output: `results/real_release_study.json` (coverage of
the eleven properties, and what `audit_sheet` reports on the documented values), from which the
tables in `results/REAL_RELEASE_STUDY.md` are generated.

The script refuses a corpus in which a property is marked documented without a source and
evidence: a coded cell with nothing behind it is the documentation version of an unsourced
number.

    python -m scripts.run_real_release_study            # write the results
    python -m scripts.run_real_release_study --check    # fail if the committed results are stale
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from synthproof.audit.boundary import audit_sheet

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "research" / "real_releases" / "releases.json"
OUT = ROOT / "results" / "real_release_study.json"

PROPERTIES = [f"P{i}" for i in range(1, 12)]
STATUSES = ("documented", "partial", "not_documented", "not_applicable")


def validate(corpus: dict) -> list:
    """Every problem with the corpus, as strings. Empty means it may be run."""
    problems = []
    for rel in corpus["releases"]:
        rid = rel["id"]
        sources = {s["id"] for s in rel.get("sources", [])}
        for s in rel.get("sources", []):
            if not s.get("url", "").startswith("https://") or not s.get("fetched"):
                problems.append(f"{rid}: source {s.get('id')} lacks an https URL or fetch date")
        props = rel.get("properties", {})
        for p in PROPERTIES:
            cell = props.get(p)
            if cell is None:
                problems.append(f"{rid}: {p} is not coded")
                continue
            if cell.get("status") not in STATUSES:
                problems.append(f"{rid}: {p} has status {cell.get('status')!r}")
            if not cell.get("evidence"):
                problems.append(f"{rid}: {p} has no evidence")
            if cell.get("source") not in sources:
                problems.append(f"{rid}: {p} cites {cell.get('source')!r}, not a listed source")
        if not isinstance(rel.get("sheet"), dict):
            problems.append(f"{rid}: no sheet block")
    return problems


def study(corpus: dict) -> dict:
    releases, coverage = [], {p: Counter() for p in PROPERTIES}
    for rel in corpus["releases"]:
        report = audit_sheet(rel["sheet"])
        for p in PROPERTIES:
            coverage[p][rel["properties"][p]["status"]] += 1
        releases.append(
            {
                "id": rel["id"],
                "name": rel["name"],
                "release_type": rel["release_type"],
                "properties": {p: rel["properties"][p]["status"] for p in PROPERTIES},
                "audit": {
                    "leaks": len(report.leaks),
                    "unverifiable": len(report.unverifiable),
                    "findings": [
                        {"code": f.code, "severity": f.severity, "field": f.field}
                        for f in report.findings
                    ],
                },
            }
        )
    return {
        "corpus": "research/real_releases/releases.json",
        "n_releases": len(releases),
        "property_definitions": corpus["properties"],
        "coverage": {p: {s: coverage[p][s] for s in STATUSES} for p in PROPERTIES},
        "releases": releases,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    problems = validate(corpus)
    if problems:
        sys.exit("Corpus refused:\n  " + "\n  ".join(problems))
    text = json.dumps(study(corpus), indent=2) + "\n"
    if args.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
            sys.exit(
                f"{OUT.relative_to(ROOT)} is stale: run python -m scripts.run_real_release_study"
            )
        print("OK - the real-release study results match the corpus.")
        return
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(corpus['releases'])} releases)")


if __name__ == "__main__":
    main()
