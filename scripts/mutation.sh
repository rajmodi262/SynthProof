#!/usr/bin/env bash
# Mutation testing for the accounting core, on a POSIX machine (mutmut 3 needs fork).
#
#   docker run --rm -v "$PWD":/src python:3.11 bash /src/scripts/mutation.sh /src
#   bash scripts/mutation.sh .            # on Linux/macOS, from the repo root
#
# Works on a COPY so the mutants/ tree never lands in the checkout, then writes
# results/mutation/accounting.json (score and every surviving mutant) back into it.
# Exits non-zero when the score is below MIN_SCORE.
set -euo pipefail

SRC="$(cd "${1:-.}" && pwd)"
MIN_SCORE="${MIN_SCORE:-85}"
WORK="$(mktemp -d)"

# Anchored excludes: an unanchored `--exclude=data` also dropped synthproof/data.
tar -C "$SRC" --exclude=./.git --exclude='./.venv*' --exclude=node_modules --exclude=./mutants \
    --exclude=./web --exclude=./results --exclude=./data --exclude=./build -cf - . \
    | tar -C "$WORK" -xf -
mkdir -p "$WORK/results"
cd "$WORK"

python -m pip install -q --upgrade pip
python -m pip install -q -e ".[dev]" "mutmut==3.8.0"

mutmut run --max-children "$(nproc)" || true
mutmut export-cicd-stats
mutmut results > mutmut_results.txt || true

mkdir -p "$SRC/results/mutation"
python - "$SRC/results/mutation/accounting.json" "$MIN_SCORE" <<'PY'
import json, subprocess, sys
out, min_score = sys.argv[1], float(sys.argv[2])
stats = json.load(open("mutants/mutmut-cicd-stats.json"))
survivors = [l.split(":")[0].strip() for l in open("mutmut_results.txt") if "survived" in l]
# Killed (incl. timeouts, which a test also caught) over everything a test could have caught.
caught = stats["killed"] + stats.get("timeout", 0)
judged = caught + stats["survived"] + stats.get("suspicious", 0)
score = 100.0 * caught / judged if judged else 0.0
report = {
    "scope": "synthproof/accounting/",
    "tool": "mutmut 3.8.0",
    "score_percent": round(score, 2),
    "min_score_percent": min_score,
    "stats": stats,
    "surviving_mutants": survivors,
}
json.dump(report, open(out, "w"), indent=2)
print(json.dumps({k: report[k] for k in ("score_percent", "stats")}, indent=2))
print(f"{len(survivors)} surviving mutants listed in {out}")
sys.exit(0 if score >= min_score else 1)
PY
