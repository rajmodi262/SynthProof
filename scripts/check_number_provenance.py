"""Every metric-like number in a results-bearing document must come from a committed result.

WHY. This project has repeatedly shipped numbers that no result supported: fabricated metrics in
four modules, thesis intervals that matched no file (eac2e54), a console matrix drawn from a sin()
formula. Each was caught by a reviewer, after it shipped. This check makes it a build failure.

WHAT IT CHECKS. Every decimal with at least two places (0.0105, 7.356, 0.4617) in the documents
listed in DOCS must equal, at its printed precision, some number in a TRACKED results file
(`git ls-files results research`, JSON only), or appear in the allowlist with a reason -- a citation
page range, a formula constant, a published figure from another paper. Integers and one-decimal
values are not checked: they are dominated by counts, years and section numbers.

The allowlist is per document and per value, so allowing 0.05 (alpha) in one file does not
excuse it everywhere, and an entry with no reason is rejected.

    python scripts/check_number_provenance.py            # check, exit 1 on any unmatched number
    python scripts/check_number_provenance.py --report   # list every unmatched number by file
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parents[1]
ALLOWLIST = ROOT / "scripts" / "number_provenance_allowlist.json"

# Documents whose numbers are claims about this project's results.
DOCS = [
    "README.md",
    "DEMO.md",
    "CHANGELOG.md",
    "docs/thesis/ch0*.md",
    "docs/defence/DEFENCE.md",
    "docs/explainer/EXPLAINER.md",
    "docs/simple/SIMPLE.md",
    "results/*.md",
    "results/*/*.md",
    "research/imputation_audit/*.md",
]

# A decimal with >= 2 places, not part of a version string, a hash, a path or a longer token. A
# leading minus is fine ("-0.0829" is checked); a hyphen after a word character ("v1-2.30") is not.
NUMBER = re.compile(r"(?<![\w./])(?<!\w-)(\d+\.\d{2,})(?![\w.]*\d)(?![\w/])")


def _tracked(patterns: Iterable[str]) -> List[Path]:
    out = subprocess.run(
        ["git", "ls-files", "--", *patterns], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.split()
    return [ROOT / p for p in out]


def _walk(value, sink: Set[float]) -> None:
    if isinstance(value, bool):
        return
    if isinstance(value, (int, float)):
        sink.add(float(value))
    elif isinstance(value, dict):
        for k, v in value.items():
            try:  # numeric keys are data too: an alpha sweep is stored as {"0.01": K, ...}
                sink.add(float(k))
            except ValueError:
                pass
            _walk(v, sink)
    elif isinstance(value, list):
        for v in value:
            _walk(v, sink)


def _numbers_in(paths: Iterable[Path]) -> Set[float]:
    values: Set[float] = set()
    for p in paths:
        if p.suffix != ".json" or not p.exists():
            continue
        try:
            _walk(json.loads(p.read_text(encoding="utf-8")), values)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
    return values


def result_numbers() -> Set[float]:
    """Every number in every tracked results/research JSON file (the fallback pool)."""
    return _numbers_in(_tracked(["results", "research"]))


# A document may declare exactly which results it reports:
#     <!-- provenance: results/selection_ablation.json, results/acs/h1_all_families.json -->
# Its numbers are then checked against THOSE files only. Matching against all ~700 results
# files is too permissive -- a stale table passed because its 4-digit values happened to occur
# in some unrelated file -- so a results document should always declare its sources.
PROVENANCE = re.compile(r"<!--\s*provenance:\s*(.*?)\s*-->")


def declared_sources(path: Path) -> List[Path]:
    m = PROVENANCE.search(path.read_text(encoding="utf-8"))
    if not m:
        return []
    return [ROOT / s.strip() for s in m.group(1).split(",") if s.strip()]


def _forms(values: Set[float]) -> Set[str]:
    """Printed forms a result could take: rounded or truncated to 2-6 decimals, as a value or a
    percentage, and the full repr (for numbers copied verbatim from a sheet)."""
    import math

    forms: Set[str] = set()
    for v in values:
        if v != v or v in (float("inf"), float("-inf")):
            continue
        forms.add(repr(v))
        forms.add(repr(abs(v)))
        for x in (v, abs(v), 100 * v):
            for d in range(2, 7):
                forms.add(f"{x:.{d}f}")
                t = math.trunc(x * 10**d) / 10**d
                forms.add(f"{t:.{d}f}")
    return forms


# arXiv identifiers (2405.10994) have the shape of a decimal and are not measurements.
ARXIV = re.compile(r"^\d{4}\.\d{4,5}$")


# A table between these markers is rebuilt from results JSON by `scripts/build_results_docs.py`,
# and CI fails when it is stale, so its numbers are sourced -- and prose restating one of them in
# the same document is consistent with data by construction.
GENERATED = re.compile(r"<!-- BEGIN GENERATED: ([\w-]+) -->.*?<!-- END GENERATED: \1 -->", re.S)


def generated_numbers(path: Path) -> Set[str]:
    return {
        n
        for block in GENERATED.finditer(path.read_text(encoding="utf-8"))
        for n in NUMBER.findall(block.group(0))
    }


def doc_numbers(path: Path) -> List[Tuple[int, str]]:
    found = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        for m in NUMBER.finditer(line):
            if not ARXIV.match(m.group(1)):
                found.append((i, m.group(1)))
    return found


def load_allowlist() -> Dict[str, Dict[str, str]]:
    if not ALLOWLIST.exists():
        return {}
    data = json.loads(ALLOWLIST.read_text(encoding="utf-8"))
    for doc, entries in data.items():
        for value, reason in entries.items():
            if not str(reason).strip():
                raise SystemExit(
                    f"allowlist entry {doc}:{value} has no reason; every exemption needs one"
                )
    return data


def check(docs: Optional[List[Path]] = None) -> Dict[str, List[Tuple[int, str]]]:
    """Unmatched numbers per document. `docs` defaults to every tracked file matching DOCS."""
    pool = _forms(result_numbers())
    allow = load_allowlist()
    unmatched: Dict[str, List[Tuple[int, str]]] = {}
    for doc in docs if docs is not None else _tracked(DOCS):
        rel = doc.relative_to(ROOT).as_posix() if doc.is_relative_to(ROOT) else doc.name
        sources = declared_sources(doc)
        missing = [s for s in sources if not s.exists()]
        if missing:
            unmatched[rel] = [
                (0, f"declared source missing: {m.relative_to(ROOT).as_posix()}") for m in missing
            ]
            continue
        forms = _forms(_numbers_in(sources)) if sources else pool
        allowed = set(allow.get(rel, {})) | set(allow.get("*", {})) | generated_numbers(doc)
        bad = [(ln, n) for ln, n in doc_numbers(doc) if n not in forms and n not in allowed]
        if bad:
            unmatched[rel] = bad
    return unmatched


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report", action="store_true", help="list every unmatched number")
    args = ap.parse_args()
    unmatched = check()
    total = sum(len(v) for v in unmatched.values())
    if args.report or total:
        for doc, items in sorted(unmatched.items()):
            print(f"{doc}: {len(items)}")
            for ln, n in items[:200]:
                print(f"    line {ln}: {n}")
    if total:
        print(
            f"\nFAILED: {total} number(s) in {len(unmatched)} document(s) "
            "match no committed result."
        )
        print("Generate the number from results/, correct it, or allowlist it WITH a reason.")
        sys.exit(1)
    print("OK - every checked number traces to a committed result or a reasoned exemption.")


if __name__ == "__main__":
    main()
