"""Validate an emitted Croissant record against the OFFICIAL MLCommons validator.

WHY THIS IS A SCRIPT AND NOT A TEST. `mlcroissant` cannot be installed into this project's
environment. It pulls a dependency tree that conflicts with `numpy >= 2`, which `jax`, `mbi`
and therefore real AIM require — the same conflict that made `anonymeter` unusable on
2026-08-23, where a silent numpy downgrade to 1.26.4 broke AIM outright. Choosing between the
reference validator and the project's flagship mechanism is not a real choice.

So the check runs OUT OF BAND, in a throwaway virtual environment this script builds itself,
and its result is recorded rather than assumed. `synthproof.frontier.croissant.validate_structure`
is a structural check with no dependencies and is NOT this; it never claims to be.

Usage:
    python scripts/validate_croissant.py path/to/record.json

    # build the isolated env first (once, ~30s, needs network):
    python scripts/validate_croissant.py --setup

Exit codes:
    0  the record validated
    1  the record failed validation
    2  the isolated environment is not available, so NOTHING WAS CHECKED

Exit code 2 is deliberately distinct from 0. An unrun check must never look like a passed one.
"""

import argparse
import json
import subprocess
import sys
import venv
from pathlib import Path

ENV_DIR = Path(__file__).resolve().parent.parent / ".venv-croissant"

# The validation runs inside the isolated interpreter, so it is passed as source text rather
# than imported here. Importing mlcroissant into THIS process is the thing we are avoiding.
_VALIDATE_SRC = r"""
import json, sys
from pathlib import Path

path = Path(sys.argv[1])
record = json.loads(path.read_text(encoding="utf-8"))

try:
    import mlcroissant as mlc
except ImportError as exc:
    print(f"UNAVAILABLE: {exc}")
    raise SystemExit(2)

print(f"mlcroissant {getattr(mlc, '__version__', 'unknown')}")

try:
    dataset = mlc.Dataset(jsonld=record)
except Exception as exc:
    print("FAILED")
    print(f"  {type(exc).__name__}: {exc}")
    raise SystemExit(1)

issues = getattr(dataset.metadata, "issues", None)
errors = sorted(getattr(issues, "errors", set()) or set())
warnings = sorted(getattr(issues, "warnings", set()) or set())

for w in warnings:
    print(f"  WARNING: {w}")

if errors:
    print("FAILED")
    for e in errors:
        print(f"  ERROR: {e}")
    raise SystemExit(1)

print("VALIDATED")
print(f"  name        {dataset.metadata.name}")
print(f"  conformsTo  {record.get('conformsTo')}")
print(f"  warnings    {len(warnings)}")
raise SystemExit(0)
"""


def _python() -> Path:
    """The isolated interpreter."""
    if sys.platform == "win32":
        return ENV_DIR / "Scripts" / "python.exe"
    return ENV_DIR / "bin" / "python"


def setup() -> int:
    """Builds the isolated environment and installs the reference validator."""
    print(f"Creating isolated environment at {ENV_DIR} ...")
    venv.create(ENV_DIR, with_pip=True, clear=True)
    print("Installing mlcroissant (isolated -- this cannot affect the project env) ...")
    proc = subprocess.run(
        [str(_python()), "-m", "pip", "install", "--quiet", "mlcroissant"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        print("Install failed:")
        print(proc.stdout[-2000:])
        print(proc.stderr[-2000:])
        return 2
    print("Ready. Re-run without --setup to validate a record.")
    return 0


def validate(record_path: Path) -> int:
    if not _python().exists():
        print(
            f"NOT CHECKED: no isolated environment at {ENV_DIR}.\n"
            "Run `python scripts/validate_croissant.py --setup` first.\n"
            "This is exit code 2, not 0 -- the record has NOT been validated."
        )
        return 2

    runner = ENV_DIR / "_validate_impl.py"
    runner.write_text(_VALIDATE_SRC, encoding="utf-8")

    proc = subprocess.run(
        [str(_python()), str(runner), str(record_path)], capture_output=True, text=True
    )
    print(proc.stdout.rstrip())
    if proc.stderr.strip():
        print(proc.stderr.rstrip(), file=sys.stderr)
    return proc.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", nargs="?", type=Path, help="Croissant record JSON to validate.")
    parser.add_argument("--setup", action="store_true", help="Build the isolated environment.")
    args = parser.parse_args()

    if args.setup:
        return setup()
    if not args.record:
        parser.error("give a record path, or --setup")
    if not args.record.exists():
        print(f"No such file: {args.record}")
        return 2

    # Sanity: refuse to validate something that is not one of ours, so a green result cannot
    # be quoted about the wrong file.
    record = json.loads(args.record.read_text(encoding="utf-8"))
    if "dp:privacyDataSheet" not in record:
        print(
            f"{args.record} carries no `dp:privacyDataSheet`. This script validates SynthProof "
            "release records; it is not a general Croissant linter."
        )
        return 2

    return validate(args.record)


if __name__ == "__main__":
    raise SystemExit(main())
