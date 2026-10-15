"""Writes the API's OpenAPI document, the source the console's TypeScript types are generated from.

    python scripts/export_openapi.py            # write web/src/api/openapi.json
    python scripts/export_openapi.py --check    # exit 1 if the committed copy is stale

Then `cd web && npm run gen:api` regenerates `web/src/api/schema.d.ts` from it. CI runs both and
fails on any difference, so a response field added on the server cannot reach the console
without the console's types changing with it (see synthproof/api/schemas.py).

The document is built from a fresh in-memory app with no configuration, so it does not depend
on the machine or the environment it is exported on.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT = ROOT / "web" / "src" / "api" / "openapi.json"


def document() -> str:
    from synthproof.api.context import build_context
    from synthproof.api.main import create_app

    spec = create_app(build_context({}), env={}).openapi()
    spec["info"].pop("version", None)  # the package version is not part of the contract
    return json.dumps(spec, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    text = document()
    if args.check:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        current = current.replace("\r\n", "\n")  # a Windows checkout must not read as stale
        if current != text:
            print(f"{OUT.relative_to(ROOT)} is stale: run `python scripts/export_openapi.py`")
            sys.exit(1)
        print("OpenAPI document up to date.")
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
