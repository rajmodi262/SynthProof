"""Every relative link in a tracked Markdown document must point at a file that exists.

Moving a document (the 2026-10-16 consolidation archived about a dozen) silently breaks every link
to it, and nothing else notices. This checks `[text](relative/path)` links -- not URLs, not
in-page anchors -- in every tracked .md file, resolving each against the linking file's folder.

    python scripts/check_links.py          # exit 1 and list every broken link
"""

import re
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"\[[^\]\n]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
FENCE = re.compile(r"^\s*(```|~~~)")


def tracked_markdown() -> List[Path]:
    out = subprocess.run(
        ["git", "ls-files", "--", "*.md"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.split()
    return [ROOT / p for p in out]


def broken_links(path: Path) -> List[Tuple[int, str]]:
    bad, in_fence = [], False
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for target in LINK.findall(line):
            if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I) or target.startswith("#"):
                continue  # a URL (http:, mailto:, ...) or an in-page anchor
            rel = unquote(target.split("#", 1)[0].split("?", 1)[0])
            if not rel:
                continue
            resolved = (ROOT / rel.lstrip("/")) if rel.startswith("/") else (path.parent / rel)
            if not resolved.exists():
                bad.append((i, target))
    return bad


def main() -> None:
    total = 0
    for doc in tracked_markdown():
        bad = broken_links(doc)
        for line, target in bad:
            print(f"{doc.relative_to(ROOT).as_posix()}:{line}: {target}")
        total += len(bad)
    if total:
        print(f"\nFAILED: {total} broken relative link(s).")
        sys.exit(1)
    print("OK - every relative link in every tracked Markdown file resolves.")


if __name__ == "__main__":
    main()
