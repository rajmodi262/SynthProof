"""What this service can synthesise from, and what it can synthesise with.

`/api/health` is deliberately unauthenticated: a readiness probe must not need a secret, and
this is where an operator finds out whether the service is open. It reports `auth: "disabled"`
loudly rather than staying quiet about it.

`/api/upload` is the only endpoint that accepts arbitrary user data, so the limits on it --
size, row count, and how many uploads are retained -- are enforced here rather than trusted to
the caller.
"""

import io
import json
import os
import uuid
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from synthproof.api import state
from synthproof.api.descriptions import MECHANISM_INFO, NOT_IMPLEMENTED_ATTACKS
from synthproof.api.state import require_api_key
from synthproof.data.dataset import TabularDataset
from synthproof.data.schema import Schema
from synthproof.frontier.experiment import MECHANISMS

router = APIRouter()

# --------------------------------------------------------------------------- datasets


@router.get("/api/health")
def health():
    """Readiness, and an honest statement of whether this service is protected.

    Deliberately unauthenticated: a readiness probe must not need a secret, and this is where
    an operator finds out whether the service is open. Reporting `auth: "disabled"` loudly is
    the point — an open service that does not say so is worse than one that does.

    Returns `status`, `auth` (`required` | `disabled`), an `auth_note` spelling out the
    consequence, `demo_mode`, `ledger_verified` and the ledger head.
    """
    return {
        "status": "ok",
        "auth": "required" if state.AUTH_ENABLED else "disabled",
        "auth_note": (
            "A shared API key is required on data and ledger endpoints."
            if state.AUTH_ENABLED
            else "NO AUTHENTICATION. Anyone who can reach this port can upload data, spend "
            "budget and read the ledger. Set SYNTHPROOF_API_KEY before exposing it."
        ),
        "demo_mode": state.DEMO_MODE,
        "ledger_verified": state.GLOBAL_LEDGER.verify(),
        "ledger_head": state.GLOBAL_LEDGER.get_latest_hash(),
        "mechanisms_available": sorted(MECHANISMS),
    }


@router.get("/api/mechanisms", dependencies=[Depends(require_api_key)])
def mechanisms():
    """Mechanisms this build can actually run, plus honest notes on the ones it cannot."""
    out = []
    for key, info in MECHANISM_INFO.items():
        out.append(
            {
                **info,
                "key": key,
                "available": key in MECHANISMS,
                "unavailable_reason": (
                    None
                    if key in MECHANISMS
                    else "private-pgm (package `mbi`) is not installed in this environment."
                ),
            }
        )
    return {"mechanisms": out, "attacks_not_implemented": NOT_IMPLEMENTED_ATTACKS}


@router.get("/api/datasets", dependencies=[Depends(require_api_key)])
def datasets():
    """Lists the datasets this service can synthesise from.

    `rows` is null for anything not yet loaded rather than a literal. A hardcoded 30162 would
    keep being reported after the pinned artefact or the drop-missing convention changed, and
    the console has no way to notice — which is the same class of defect as a fabricated
    metric, just in metadata.

    Each entry carries `id`, `label`, `rows`, `kind` and a `note` naming what the table is
    good for; the toy table's note says outright that its columns are independent, so utility
    numbers measured on it mean little.
    """
    built_in = [
        {
            "id": "toy",
            "label": "Toy table (3 columns)",
            "rows": None,
            "kind": "built-in",
            "note": "Columns are drawn INDEPENDENTLY — there is no structure to preserve. "
            "Useful for a fast demo, meaningless for utility claims.",
        },
        {
            "id": "adult",
            "label": "UCI Adult",
            "rows": None,
            "kind": "built-in",
            "note": "SHA-256 verified on load. Hand-declared public schema. Numeric "
            "correlations are weak, so mechanism families may not separate on it.",
        },
    ]
    state._init_demo_datasets()
    demos = [
        {
            "id": k,
            "label": f"Demo: {k.replace('_', ' ').title()}",
            "rows": v.num_rows,
            "kind": "demo",
            "note": (
                f"Pre-packaged capstone demo dataset "
                f"({v.num_rows} rows, {v.num_cols} features)."
            ),
        }
        for k, v in state._DEMO_DATASETS.items()
    ]
    uploads = [
        {"id": k, "label": v.name, "rows": v.num_rows, "kind": "upload", "note": None}
        for k, v in state._UPLOADS.items()
    ]
    return {"datasets": built_in + demos + uploads}


@router.post("/api/upload", dependencies=[Depends(require_api_key)])
async def upload(file: UploadFile = File(...), schema_json: Optional[str] = None):
    """Accepts a CSV and registers it for this session.

    Without a declared public schema the column kinds and numeric bounds are inferred FROM
    THE DATA, which leaks and is not safe for a real release. The response says so, and the
    console is expected to surface that warning rather than bury it.
    """
    if not (file.filename or "").lower().endswith((".csv", ".txt")):
        raise HTTPException(400, "Upload a .csv file.")

    # Read in chunks and abort as soon as the cap is passed. `await file.read()` would pull
    # the entire body into memory FIRST and only then reject it, so a 2 GB upload is already
    # resident by the time the 413 is raised — the limit would not limit anything.
    buf = io.BytesIO()
    size = 0
    while chunk := await file.read(state._UPLOAD_CHUNK):
        size += len(chunk)
        if size > state._MAX_UPLOAD_BYTES:
            raise HTTPException(413, f"File exceeds {state._MAX_UPLOAD_BYTES // (1024 * 1024)} MB.")
        buf.write(chunk)
    buf.seek(0)

    try:
        df = pd.read_csv(buf, skipinitialspace=True, na_values=["?", ""])
    except Exception as exc:
        raise HTTPException(400, f"Could not parse CSV: {exc}") from exc

    df = df.dropna(axis=0, how="any").reset_index(drop=True)
    if df.empty:
        raise HTTPException(400, "No complete rows after dropping missing values.")
    if len(df) > state._MAX_UPLOAD_ROWS:
        df = df.sample(n=state._MAX_UPLOAD_ROWS, random_state=0).reset_index(drop=True)

    inferred = schema_json is None
    if schema_json:
        # A caller-supplied schema is untrusted input. Unguarded, a malformed body surfaced
        # as a 500 from json.loads or a KeyError from from_dict.
        try:
            schema = Schema.from_dict(json.loads(schema_json))
        except Exception as exc:
            raise HTTPException(
                400, f"Could not parse schema_json: {type(exc).__name__}: {exc}"
            ) from exc
    else:
        schema = Schema.infer_nonprivate(df)

    # The filename is attacker-controlled and ends up in responses and ledger entries.
    # Keep only the stem, and only characters that cannot be mistaken for a path.
    raw_name = os.path.basename(file.filename or "upload").rsplit(".", 1)[0]
    name = "".join(c for c in raw_name if c.isalnum() or c in "-_")[:64] or "upload"

    try:
        ds = TabularDataset(df, name=name, schema=schema)
    except ValueError as exc:
        raise HTTPException(400, f"Schema does not match the CSV: {exc}") from exc

    upload_id = f"upload:{uuid.uuid4().hex[:8]}"
    state._register_upload(upload_id, ds)

    return {
        "id": upload_id,
        "dataset": state._describe(ds),
        "schema": schema.to_dict(),
        "schema_inferred": inferred,
        "warning": (
            (
                "Bounds were READ FROM YOUR DATA, so they leak. This is fine for exploring a "
                "table you already own; for a real release, edit the bounds to publishable "
                "facts about the domain and re-upload with a declared schema."
            )
            if inferred
            else None
        ),
    }
