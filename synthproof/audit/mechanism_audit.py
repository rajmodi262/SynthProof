"""The mechanism-level GDP audit, as it travels inside a signed Privacy Data Sheet (W9).

A release's sheet carries its proved epsilon and, since W9, what a strong membership adversary
could CERTIFY about the same mechanism, with the instrument's ceiling beside it -- the three
numbers the project argues must never be separated.

WHAT IT IS NOT. The audit runs thousands of fits on a fixed worst-case instance (10 identical
records plus one target, three binary columns; `scripts/run_gdp_audit.py`), at the
preregistered budgets in `docs/prereg/W9_gdp_audit.md`. It is evidence about the MECHANISM's
implementation and accounting, not a measurement on this release's data, and the block says so
in its own `scope` field so the distinction cannot be lost when the sheet is quoted.

Only cells run under the committed preregistration (`preregistration_sha256` present) are
embedded, each with the SHA-256 of its result file so a reader can check the numbers against
the published JSON byte for byte.
"""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

GDP_RESULTS = Path(__file__).resolve().parents[2] / "results" / "gdp"

SCOPE = (
    "mechanism-level audit on a fixed worst-case instance (10 identical records plus one target "
    "record, three binary columns); evidence about the mechanism's implementation and "
    "accounting, NOT a measurement on this release's data"
)

# Copied verbatim from each result file; nothing here is recomputed.
_FIELDS = (
    "target_eps",
    "proved_eps",
    "delta",
    "runs_per_world",
    "bounded_per_world",
    "alpha",
    "mu_emp",
    "eps_emp",
    "ceiling_at_this_n",
    "eps_ceiling_at_this_n",
    "violation_flagged",
    "violation_claimed",
    "preregistration_sha256",
)


def mechanism_audit_for(
    mechanism: str, results_dir: Optional[Path] = None
) -> Optional[Dict[str, Any]]:
    """The signed-sheet block for `mechanism`, or None when no preregistered cell exists.

    None is reported as null in the sheet rather than omitted, so "not audited" is visible.
    """
    root = GDP_RESULTS if results_dir is None else Path(results_dir)
    if not root.is_dir():
        return None
    cells: List[Dict[str, Any]] = []
    for path in sorted(root.glob(f"{mechanism}_eps*.json")):
        raw = path.read_bytes()
        data = json.loads(raw)
        if data.get("mechanism") != mechanism or not data.get("preregistration_sha256"):
            continue
        if any(k not in data for k in _FIELDS):
            continue
        cell = {k: data[k] for k in _FIELDS}
        cell["result_file"] = f"results/gdp/{path.name}"
        cell["result_sha256"] = hashlib.sha256(raw).hexdigest()
        cells.append(cell)
    if not cells:
        return None
    cells.sort(key=lambda c: c["target_eps"])
    return {
        "mechanism": mechanism,
        "estimator": "gdp-heldout-threshold",
        "scope": SCOPE,
        "cells": cells,
    }
