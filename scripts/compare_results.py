"""Compare freshly regenerated results files against the committed versions, number by number.

The weekly reproduction workflow re-runs the fast, deterministic experiments on a clean runner
(overwriting `results/*.json` in its checkout) and then calls this. Any number that moved beyond
tolerance, any key that appeared or vanished, fails the run -- and the workflow opens an issue.

    python scripts/compare_results.py results/calibration_check.json results/auditor_comparison.json
    python scripts/compare_results.py --rtol 1e-6 --ref HEAD results/selection_ablation.json

Timing and provenance fields (elapsed_seconds, generated_at, ...) are ignored: they are expected
to differ between runs and say nothing about the result.
"""

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any, List

ROOT = Path(__file__).resolve().parents[1]
VOLATILE = {"elapsed_seconds", "generated_at", "timestamp", "wall_time_s", "hostname"}


def _diff(a: Any, b: Any, path: str, rtol: float, atol: float, out: List[str]) -> None:
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k in VOLATILE:
                continue
            if k not in a or k not in b:
                out.append(f"{path}/{k}: {'added' if k not in a else 'removed'}")
                continue
            _diff(a[k], b[k], f"{path}/{k}", rtol, atol, out)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f"{path}: length {len(a)} -> {len(b)}")
            return
        for i, (x, y) in enumerate(zip(a, b, strict=True)):
            _diff(x, y, f"{path}[{i}]", rtol, atol, out)
    elif (
        isinstance(a, bool)
        or isinstance(b, bool)
        or not (isinstance(a, (int, float)) and isinstance(b, (int, float)))
    ):
        if a != b:
            out.append(f"{path}: {a!r} -> {b!r}")
    else:
        fa, fb = float(a), float(b)
        if math.isnan(fa) and math.isnan(fb):
            return
        if not math.isclose(fa, fb, rel_tol=rtol, abs_tol=atol):
            out.append(f"{path}: {fa!r} -> {fb!r}")


def compare(rel: str, ref: str, rtol: float, atol: float) -> List[str]:
    committed = subprocess.run(
        ["git", "show", f"{ref}:{rel}"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout
    out: List[str] = []
    _diff(
        json.loads(committed),
        json.loads((ROOT / rel).read_text(encoding="utf-8")),
        "",
        rtol,
        atol,
        out,
    )
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--ref", default="HEAD", help="git revision holding the committed results")
    ap.add_argument("--rtol", type=float, default=1e-9)
    ap.add_argument("--atol", type=float, default=1e-12)
    args = ap.parse_args()
    failed = False
    for rel in args.files:
        diffs = compare(rel, args.ref, args.rtol, args.atol)
        if diffs:
            failed = True
            print(f"DIVERGED {rel}: {len(diffs)} value(s)")
            for d in diffs[:40]:
                print(f"    {d}")
        else:
            print(f"reproduced {rel}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
