"""Checks every citation key in the thesis resolves, and that no work is entered twice.

THREE FAILURES THIS CATCHES, in descending order of embarrassment.

1. **A dangling key.** `\\cite{foo2025bar}` with no entry renders as a bold [?] in the PDF.
   Cheap to introduce -- a key typed from memory while drafting -- and invisible until the
   build runs.

2. **The same work entered twice under different keys.** Introduced on 2026-08-23: the Robin
   Hood paper existed as `ganev2021robinhood` (@article, the arXiv year) in the thesis bib and
   was added again as `ganev2022robinhood` (@inproceedings, the ICML year) in the protocol bib.
   Both are defensible readings of the same paper; together they would print it twice and
   suggest two separate results.

3. **A key defined twice.** BibTeX resolves silently to one of them, so the wrong venue can
   appear with no warning at all.

WHAT IT DOES NOT CHECK. Whether the entry is *correct* -- that requires reading the paper, and
much of what arrived on 2026-08-22/23 was read at abstract level and is marked as such in the
bib files. A resolving key is not a read paper.

Run from the repository root:

    python scripts/check_citations.py
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THESIS = ROOT / "docs" / "thesis"

BIB_FILES = [
    THESIS / "references.bib",
    THESIS / "references-additions.bib",
    ROOT / "research" / "BIBLIOGRAPHY.bib",
]

KEY_RE = re.compile(r"^@\w+\{\s*([^,\s]+)\s*,", re.M)
TITLE_RE = re.compile(r"^\s*title\s*=\s*[{\"](.+?)[}\"]\s*,?\s*$", re.M | re.S)
AUTHOR_RE = re.compile(r"^\s*author\s*=\s*[{\"](.+?)[}\"]\s*,?\s*$", re.M | re.S)
ENTRY_RE = re.compile(r"@\w+\{[^,]+,.*?(?=\n@|\Z)", re.S)
# Markdown-style [key2025word] and LaTeX \cite{key}
CITE_RE = re.compile(r"\[([a-z][a-z0-9]*\d{4}[a-z0-9]+)\]|\\cite\w*\{([^}]+)\}")


def normalise(title: str) -> str:
    """Lowercase, strip braces and punctuation, collapse whitespace."""
    t = re.sub(r"[{}\\$]", " ", title).lower()
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    return " ".join(t.split())


def collect_bib() -> tuple[dict[str, list[Path]], dict[str, list[tuple[str, Path, str]]]]:
    """(key -> files defining it, normalised title -> [(key, file, first author)])."""
    keys: dict[str, list[Path]] = defaultdict(list)
    titles: dict[str, list[tuple[str, Path, str]]] = defaultdict(list)
    for path in BIB_FILES:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for entry in ENTRY_RE.findall(text):
            km = KEY_RE.search(entry)
            if not km:
                continue
            key = km.group(1)
            keys[key].append(path)
            tm = TITLE_RE.search(entry)
            if tm:
                am = AUTHOR_RE.search(entry)
                first = normalise(am.group(1).split(" and ")[0]) if am else ""
                titles[normalise(tm.group(1))].append((key, path, first))
    return keys, titles


def collect_cites() -> dict[str, list[str]]:
    """key -> ['ch02-literature-review.md:178', ...]"""
    cites: dict[str, list[str]] = defaultdict(list)
    for path in sorted(THESIS.glob("ch0*.md")):
        for i, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
            for m in CITE_RE.finditer(line):
                raw = m.group(1) or m.group(2)
                for key in (k.strip() for k in raw.split(",")):
                    if key:
                        cites[key].append(f"{path.name}:{i}")
    return cites


def main() -> None:
    keys, titles = collect_bib()
    cites = collect_cites()
    problems: list[str] = []

    for key, where in sorted(cites.items()):
        if key not in keys:
            problems.append(
                f"DANGLING  [{key}]  cited at {', '.join(where[:3])}\n"
                f"    No entry in any of: {', '.join(p.name for p in BIB_FILES)}. "
                "It will render as [?]."
            )

    for key, files in sorted(keys.items()):
        if len(files) > 1:
            problems.append(
                f"DUPLICATE KEY  {key}  defined in {', '.join(p.name for p in files)}\n"
                "    BibTeX picks one silently, so the wrong venue can appear with no warning."
            )

    for title, entries in sorted(titles.items()):
        # A shared title is NOT enough. "Verifiable Differential Privacy" is both Narayan et
        # al. (EuroSys 2015) and Biswas & Cormode (2022) — different papers, same name. Only
        # flag when the first author matches too.
        by_author: dict[str, set[str]] = defaultdict(set)
        for key, _path, first in entries:
            by_author[first].add(key)
        for first, dup_keys in by_author.items():
            if len(dup_keys) > 1:
                listed = ", ".join(f"{k} ({p.name})" for k, p, a in entries if a == first)
                problems.append(
                    f"SAME WORK, TWO KEYS  {title[:64]!r}\n"
                    f"    {listed}\n"
                    "    It would print twice and read as two separate results. Keep one."
                )

    if not problems:
        print(
            f"OK - {len(cites)} distinct keys cited, all resolve; "
            f"{len(keys)} entries, no duplicates."
        )
        print("     A resolving key is not a read paper. Entries added 2026-08-22/23 were read")
        print("     at abstract level and are marked as such -- read before citing.")
        return

    print(f"FOUND {len(problems)} citation problem(s):\n")
    for p in problems:
        print(f"  - {p}\n")
    sys.exit(1)


if __name__ == "__main__":
    main()
