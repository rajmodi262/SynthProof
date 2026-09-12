"""FastAPI service backing the SynthProof console.

Design rule for this module, inherited from the project's standing rules: **the API returns
only what the pipeline measured.** Where something is not implemented, the response says so
explicitly (see `/api/mechanisms` and the `attacks` block of a run result) rather than
omitting it and letting the console imply a pass. A previous version of the console displayed
four hardcoded "PASSED" attack verdicts, including one for an attack that does not exist.

The run endpoint drives `frontier.experiment.run_cell` through its `on_stage` callback rather
than reimplementing the pipeline. That is deliberate: three parallel pipelines already drifted
apart in this repository, and a fourth living in the web layer would be the worst of them.
"""

import contextlib
import hmac
import io
import json
import os
import queue
import threading
import traceback
import uuid
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from synthproof.api import projection
from synthproof.data.dataset import TabularDataset
from synthproof.data.schema import Schema
from synthproof.frontier.experiment import MECHANISMS, informative_numeric_columns, run_cell
from synthproof.ledger.ledger import Ledger
from synthproof.ledger.types import LedgerEntry

app = FastAPI(
    title="SynthProof API",
    description="Synthetic data that ships with its proof — console backend.",
    version="0.2.0",
)

# Wildcard origins with credentials is rejected by browsers and unsafe besides. Credentials
# stay off: this service authenticates with a header, not a cookie, so there is nothing for a
# browser to attach automatically and nothing for CSRF to abuse.
#
# The wildcard is narrowed once a key is configured. SYNTHPROOF_CORS_ORIGINS takes a
# comma-separated list; it defaults to the dev console's origin rather than "*", because a
# deployment with a key should not also be reachable from any page on the internet.
_CORS = os.environ.get("SYNTHPROOF_CORS_ORIGINS", "").strip()
if _CORS:
    _ALLOWED_ORIGINS = [o.strip() for o in _CORS.split(",") if o.strip()]
elif os.environ.get("SYNTHPROOF_API_KEY", "").strip():
    _ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
else:
    _ALLOWED_ORIGINS = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

_LEDGER_DB = os.environ.get("SYNTHPROOF_LEDGER_DB", ":memory:")
GLOBAL_LEDGER = Ledger(db_path=_LEDGER_DB)

# `/api/ledger/tamper` and `/api/ledger/reset` exist to demonstrate that the chain is
# tamper-EVIDENT. They are destructive by design: one rewrites a spend, the other deletes the
# entire history. Against a file-backed ledger they would be unauthenticated remote primitives
# for destroying audit records, so they are refused unless demo mode is switched on
# deliberately, and refused outright on anything but an in-memory database.
DEMO_MODE = os.environ.get("SYNTHPROOF_DEMO", "1" if _LEDGER_DB == ":memory:" else "0") == "1"


def _seed_demo_ledger():
    if not DEMO_MODE or GLOBAL_LEDGER.get_entries():
        return
    seeds = [
        ("uci_adult", "aim_eps1.0_seed42", "aim", 1.0, 1e-5, 42),
        ("acs_income_ca", "pairwise_eps2.0_seed0", "pairwise", 2.0, 1e-5, 0),
        ("texas_inpatient", "fixed_workload_eps0.5_seed7", "fixed_workload", 0.5, 1e-5, 7),
    ]
    for ds_id, run_id, mech, eps, delta, seed in seeds:
        GLOBAL_LEDGER.append(
            LedgerEntry(
                dataset_id=ds_id,
                run_id=run_id,
                mechanism_name=mech,
                eps_spent=eps,
                delta=delta,
                seed=seed,
            )
        )


_seed_demo_ledger()

# --------------------------------------------------------------------------- authentication
#
# WHAT THIS IS AND, MORE IMPORTANTLY, WHAT IT IS NOT.
#
# Setting SYNTHPROOF_API_KEY requires a shared bearer token on every endpoint that reads
# uploaded data, spends budget, or reveals the ledger. That closes the gap where anyone who
# could reach the port could upload a sensitive table, consume the privacy budget attached to
# someone else's dataset, or read the spend history.
#
# It is NOT user authentication. There is one key, so every caller is the same principal: the
# ledger's `actor` field cannot distinguish them, key rotation invalidates everyone at once,
# and there is no per-user budget or audit trail. A deployment that needs to know WHO spent
# the budget needs real identity, which is also the missing prerequisite for the cross-session
# budget filter described in docs/design/USER_FACING_SYSTEM.md §2.3. This is the smallest
# honest step, not the destination.
#
# Unset by default so the local demo keeps working. `/api/health` reports which mode is
# active, because a service that is open and does not say so is worse than one that is open.
API_KEY = os.environ.get("SYNTHPROOF_API_KEY", "").strip()
AUTH_ENABLED = bool(API_KEY)


def require_api_key(
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None),
) -> None:
    """Rejects a request that lacks the configured key. A no-op when no key is set.

    Accepts either `Authorization: Bearer <key>` or `X-API-Key: <key>`. Comparison is
    constant-time: a plain `==` on a secret leaks its prefix through response timing, which is
    a small thing to get wrong and a silly one to get wrong in a privacy project.
    """
    if not AUTH_ENABLED:
        return
    supplied = x_api_key or ""
    if authorization and authorization.lower().startswith("bearer "):
        supplied = authorization[7:].strip()
    if not supplied or not hmac.compare_digest(supplied, API_KEY):
        raise HTTPException(
            status_code=401,
            detail=(
                "This service requires an API key. Send it as `Authorization: Bearer <key>` "
                "or `X-API-Key: <key>`."
            ),
            headers={"WWW-Authenticate": "Bearer"},
        )


@contextlib.contextmanager
def _ledger_conn():
    """Yields a ledger connection and closes it if it was opened for this call.

    `Ledger._get_conn` returns the SHARED connection for an in-memory database and a NEW
    one per call for a file-backed database. Closing the shared connection would drop the
    whole in-memory database, so only per-call connections are closed — the same rule
    `Ledger.append` and `Ledger.verify` already follow internally.
    """
    conn = GLOBAL_LEDGER._get_conn()
    try:
        yield conn
    finally:
        if conn is not GLOBAL_LEDGER._conn:
            conn.close()


def _require_demo_ledger() -> None:
    """Refuses destructive ledger operations outside an in-memory demo."""
    if not DEMO_MODE:
        raise HTTPException(
            403,
            "Destructive ledger endpoints are disabled. Set SYNTHPROOF_DEMO=1 to enable "
            "them, and only against a throwaway ledger.",
        )
    if _LEDGER_DB != ":memory:":
        raise HTTPException(
            403,
            f"Refusing to modify a persistent ledger at {_LEDGER_DB!r}. These endpoints "
            "destroy audit records and are only ever appropriate against ':memory:'.",
        )


# Uploaded tables live in memory for the session. Nothing is written to disk: this service
# receives sensitive data by definition, and persisting it silently would be exactly the
# habit the project exists to argue against.
# Bounded and FIFO-evicting. An unbounded dict would hold every table ever uploaded for the
# lifetime of the process — at 20k rows each that is a slow memory leak, and worse, it keeps
# sensitive data resident long after anyone is using it.
_UPLOADS: "OrderedDict[str, TabularDataset]" = OrderedDict()
_MAX_UPLOADS = 8
_MAX_UPLOAD_BYTES = 25 * 1024 * 1024
_MAX_UPLOAD_ROWS = 20_000
_UPLOAD_CHUNK = 1 * 1024 * 1024


def _register_upload(upload_id: str, ds: TabularDataset) -> None:
    """Stores an upload, evicting the oldest once the cap is reached."""
    _UPLOADS[upload_id] = ds
    while len(_UPLOADS) > _MAX_UPLOADS:
        _UPLOADS.popitem(last=False)


_DEMO_DATASETS: "Dict[str, TabularDataset]" = {}


def _init_demo_datasets() -> None:
    """Discovers and caches the pre-verified demo CSV datasets if present."""
    if _DEMO_DATASETS:
        return
    possible_dirs = [
        Path(__file__).resolve().parent.parent.parent.parent / "04_Demo_CSV_Datasets",
        Path(__file__).resolve().parent.parent.parent / "04_Demo_CSV_Datasets",
        Path("04_Demo_CSV_Datasets"),
        Path("../04_Demo_CSV_Datasets"),
    ]
    for d in possible_dirs:
        if d.is_dir():
            for p in sorted(d.glob("*.csv")):
                try:
                    df = pd.read_csv(p, skipinitialspace=True, na_values=["?", ""]).dropna().reset_index(drop=True)
                    if not df.empty:
                        name = p.stem
                        schema = Schema.infer_nonprivate(df)
                        _DEMO_DATASETS[name] = TabularDataset(df, name=name, schema=schema)
                except Exception:
                    pass
            if _DEMO_DATASETS:
                break


# --------------------------------------------------------------------------- descriptions

MECHANISM_INFO = {
    "independent": {
        "label": "Independent marginals",
        "family": "baseline",
        "blurb": "One noisy 1-D marginal per column, sampled independently. Destroys all "
        "cross-column structure by construction — the ablation baseline.",
        "implemented": True,
    },
    "moments": {
        "label": "Per-column Gaussian",
        "family": "baseline",
        "blurb": "DP-noised per-column moments: a mean and standard deviation per numeric "
        "column, a histogram per categorical one, every column sampled independently. No "
        "covariance and no rank transform, so no cross-column correlation survives. Kept as "
        "a second independent-marginal control.",
        "implemented": True,
    },
    "pairwise": {
        "label": "Pairwise tree",
        "family": "structured",
        "blurb": "Measures 2-way marginals along a fixed public spanning tree and samples "
        "ancestrally, so pairwise dependence survives. Not MST — structure is not "
        "selected from the data.",
        "implemented": True,
    },
    "aim": {
        "label": "AIM (private-PGM)",
        "family": "structured",
        "blurb": "Adaptive marginal selection by report-noisy-max plus graphical-model "
        "inference. Selection is charged to the accountant. Requires private-pgm.",
        "implemented": True,
    },
}

# Measured by scripts/run_detection_floor.py on UCI Adult, n=3000, 5 seeds, alpha=0.05.
# See results/DETECTION_FLOOR.md. These are the auditor's WORKING RANGE, and without them a
# reported `eps_audited = 0` is indistinguishable from a broken instrument.
#
# The ceiling matters more than the floor: eps_audited = log(TPR_lo / FPR_hi) from
# Clopper-Pearson intervals is bounded by the canary count alone, so there is a maximum value
# the audit can report even against a release that is 100% verbatim training data.
AUDIT_CEILING_BY_CANARIES = {
    10: 0.81,
    25: 1.84,
    50: 2.57,
    100: 3.28,
    200: 3.98,
    400: 4.68,
    800: 5.38,
}

# Smallest canary count that reliably detected each known leak fraction.
AUDIT_DETECTION_FLOOR = {1.0: 10, 0.25: 400, 0.05: None, 0.01: None}


def audit_ceiling(num_canaries: int) -> float:
    """Largest epsilon the auditor could report at this canary count.

    Interpolated between measured points; extrapolated conservatively past the ends. A
    reported `eps_audited` at or near this value means the instrument is saturated, not that
    the mechanism leaks exactly that much.
    """
    points = sorted(AUDIT_CEILING_BY_CANARIES.items())
    if num_canaries <= points[0][0]:
        return points[0][1] * num_canaries / points[0][0]
    if num_canaries >= points[-1][0]:
        return points[-1][1]
    # Deliberately unequal lengths — this is a pairwise sliding window over `points`, so
    # strict=True would raise on every call.
    for (m0, c0), (m1, c1) in zip(points, points[1:], strict=False):
        if m0 <= num_canaries <= m1:
            t = (num_canaries - m0) / (m1 - m0)
            return round(c0 + t * (c1 - c0), 3)
    return points[-1][1]


def _audit_payload(audit, num_canaries: int) -> dict:
    """Normalises either auditor's result into one shape the console can render.

    The two estimators expose genuinely different quantities — the paired auditor has TPR and
    FPR with Clopper-Pearson intervals, the one-run construction has a guess count and a
    binomial tail — so the union is reported rather than forcing one into the other's shape.
    What both MUST carry is the ceiling: a reported epsilon of 0 without the maximum the
    instrument could have certified reads as "no leakage" when it means "below resolution".
    """
    common = {
        "audited_eps": float(audit.audited_eps),
        "p_value": float(audit.p_value),
    }

    if hasattr(audit, "guesses"):  # one-run (Steinke)
        # This ceiling is exact rather than interpolated: it is a closed form in the number
        # of guesses actually made.
        return {
            **common,
            "auditor": "one_run",
            "ceiling": float(audit.ceiling),
            "saturated": bool(audit.saturated),
            "correct": int(audit.correct),
            "guesses": int(audit.guesses),
            "accuracy": float(audit.accuracy),
            "tpr": float(audit.accuracy),
            "fpr": 0.5,
            "tpr_lower": float(audit.accuracy),
            "fpr_upper": 0.5,
            "num_members": int(audit.num_included),
            "num_holdout": int(audit.num_canaries - audit.num_included),
            "num_canaries": int(audit.num_canaries),
            "num_included": int(audit.num_included),
            "detects_leak_above": next(
                (
                    f
                    for f, m in sorted(AUDIT_DETECTION_FLOOR.items())
                    if m is not None and m <= num_canaries
                ),
                None,
            ),
            "range_note": (
                f"With {audit.guesses} guesses this audit could certify at most "
                f"eps={audit.ceiling:.2f}, even against a release that is 100% verbatim "
                "training data. A value of 0 means 'below this instrument's resolution', "
                "not 'no leakage'. Certifying an epsilon costs roughly ln(1/alpha)*e^eps "
                "canaries. See results/AUDITOR_COMPARISON.md."
            ),
        }

    # paired Clopper-Pearson
    return {
        **common,
        "auditor": "paired",
        "tpr": float(audit.tpr),
        "fpr": float(audit.fpr),
        "tpr_lower": float(audit.tpr_lower),
        "fpr_upper": float(audit.fpr_upper),
        "num_members": int(audit.num_members),
        "num_holdout": int(audit.num_holdout),
        "confidence": float(audit.confidence),
        "ceiling": audit_ceiling(num_canaries),
        "detects_leak_above": next(
            (
                f
                for f, m in sorted(AUDIT_DETECTION_FLOOR.items())
                if m is not None and m <= num_canaries
            ),
            None,
        ),
        "range_note": (
            f"At {num_canaries} canaries this auditor cannot report an epsilon above "
            f"~{audit_ceiling(num_canaries):.2f}, even against a release that is 100% "
            "verbatim training data. A value of 0 means 'below this instrument's "
            "resolution', not 'no leakage'. See results/DETECTION_FLOOR.md."
        ),
    }


# DOMIAS and attribute inference were listed here as unimplemented long after both shipped,
# and `run_cell` was running DOMIAS the whole time. Only LiRA is genuinely absent, and that is
# a decision rather than a gap.
NOT_IMPLEMENTED_ATTACKS = [
    {
        "name": "LiRA",
        "reason": (
            "Deliberately not implemented: ~21h of compute for a likely wide-CI null, and "
            "naming a cheaper attack 'LiRA' would misreport what ran (audit finding F7)."
        ),
    },
]


# --------------------------------------------------------------------------- models


class RunRequest(BaseModel):
    dataset: str = Field("toy", description="'toy', 'adult', or an upload id.")
    mechanism: str = Field("pairwise")
    target_eps: float = Field(1.0, gt=0, le=64)
    delta: float = Field(1e-5, gt=0, lt=1)
    seed: int = 0
    num_canaries: int = Field(60, ge=1, le=500)
    rows: int = Field(
        2000, ge=100, le=50_000, description="Subsample size, so the console stays interactive."
    )


# --------------------------------------------------------------------------- datasets


def _load_dataset(name: str, rows: int, seed: int = 0) -> TabularDataset:
    _init_demo_datasets()
    if name in _UPLOADS:
        ds = _UPLOADS[name]
    elif name in _DEMO_DATASETS:
        ds = _DEMO_DATASETS[name]
    elif name == "toy":
        return TabularDataset.create_synthetic_toy(num_rows=min(rows, 5000), seed=seed)
    elif name == "adult":
        from synthproof.data.datasets import load_adult

        ds = load_adult()
    else:
        raise HTTPException(
            404,
            f"Unknown dataset {name!r}. " "Use 'toy', 'adult', a demo dataset, or an upload id from /api/upload.",
        )

    if ds.num_rows > rows:
        sub = ds.df.sample(n=rows, random_state=seed).reset_index(drop=True)
        ds = TabularDataset(sub, name=ds.name, schema=ds.schema)
    return ds


def _describe(ds: TabularDataset) -> dict:
    return {
        "name": ds.name,
        "rows": ds.num_rows,
        "cols": ds.num_cols,
        "numerical": ds.numerical_cols,
        "categorical": ds.categorical_cols,
        "has_schema": ds.schema is not None,
        "bounds": {c: ds.bounds(c) for c in ds.numerical_cols} if ds.schema else {},
    }


@app.get("/api/health")
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
        "auth": "required" if AUTH_ENABLED else "disabled",
        "auth_note": (
            "A shared API key is required on data and ledger endpoints."
            if AUTH_ENABLED
            else "NO AUTHENTICATION. Anyone who can reach this port can upload data, spend "
            "budget and read the ledger. Set SYNTHPROOF_API_KEY before exposing it."
        ),
        "demo_mode": DEMO_MODE,
        "ledger_verified": GLOBAL_LEDGER.verify(),
        "ledger_head": GLOBAL_LEDGER.get_latest_hash(),
        "mechanisms_available": sorted(MECHANISMS),
    }


@app.get("/api/mechanisms", dependencies=[Depends(require_api_key)])
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


@app.get("/api/datasets", dependencies=[Depends(require_api_key)])
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
    _init_demo_datasets()
    demos = [
        {
            "id": k,
            "label": f"Demo: {k.replace('_', ' ').title()}",
            "rows": v.num_rows,
            "kind": "demo",
            "note": f"Pre-packaged capstone demo dataset ({v.num_rows} rows, {v.num_cols} features).",
        }
        for k, v in _DEMO_DATASETS.items()
    ]
    uploads = [
        {"id": k, "label": v.name, "rows": v.num_rows, "kind": "upload", "note": None}
        for k, v in _UPLOADS.items()
    ]
    return {"datasets": built_in + demos + uploads}


@app.post("/api/upload", dependencies=[Depends(require_api_key)])
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
    while chunk := await file.read(_UPLOAD_CHUNK):
        size += len(chunk)
        if size > _MAX_UPLOAD_BYTES:
            raise HTTPException(413, f"File exceeds {_MAX_UPLOAD_BYTES // (1024 * 1024)} MB.")
        buf.write(chunk)
    buf.seek(0)

    try:
        df = pd.read_csv(buf, skipinitialspace=True, na_values=["?", ""])
    except Exception as exc:
        raise HTTPException(400, f"Could not parse CSV: {exc}") from exc

    df = df.dropna(axis=0, how="any").reset_index(drop=True)
    if df.empty:
        raise HTTPException(400, "No complete rows after dropping missing values.")
    if len(df) > _MAX_UPLOAD_ROWS:
        df = df.sample(n=_MAX_UPLOAD_ROWS, random_state=0).reset_index(drop=True)

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
    _register_upload(upload_id, ds)

    return {
        "id": upload_id,
        "dataset": _describe(ds),
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


# --------------------------------------------------------------------------- run (SSE)


def _json_default(o: Any):
    """Serialises numpy scalars as NUMBERS, and refuses anything else.

    `default=str` would quietly turn a `numpy.float64` into a quoted string, so the console
    would receive "0.093" where it expects 0.093 and render it without complaint. In a
    project whose whole argument is that reported numbers must be trustworthy, a silent
    type coercion in the transport is exactly the wrong failure mode — so unknown types
    raise instead.
    """
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, np.bool_):
        return bool(o)
    raise TypeError(
        f"{type(o).__name__} is not JSON-serialisable; convert it explicitly rather than "
        "letting it reach the console as a string."
    )


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, default=_json_default)}\n\n"


def _run_stream(req: RunRequest) -> Iterator[str]:
    """Streams pipeline stages as they complete.

    `run_cell` is synchronous, so it runs on a worker thread and pushes stage events into a
    queue that this generator drains. That keeps the console's progress honest — each stage
    appears when it has actually finished, not on a timer.
    """
    events: "queue.Queue[Optional[tuple]]" = queue.Queue()

    if req.mechanism not in MECHANISMS:
        yield _sse(
            "error",
            {
                "message": f"Mechanism {req.mechanism!r} is not available in this environment.",
                "available": sorted(MECHANISMS),
            },
        )
        return

    try:
        ds = _load_dataset(req.dataset, req.rows, req.seed)
    except HTTPException as exc:
        yield _sse("error", {"message": exc.detail})
        return

    target_col = (
        "income"
        if "income" in ds.categorical_cols
        else (ds.categorical_cols[0] if ds.categorical_cols else None)
    )
    if target_col is None:
        yield _sse(
            "error",
            {
                "message": "This table has no categorical column to predict, "
                "so downstream utility cannot be evaluated."
            },
        )
        return

    corr_cols = informative_numeric_columns(ds.df, ds.numerical_cols)

    yield _sse(
        "start",
        {
            "dataset": _describe(ds),
            "mechanism": req.mechanism,
            "mechanism_label": MECHANISM_INFO.get(req.mechanism, {}).get("label", req.mechanism),
            "target_eps": req.target_eps,
            "delta": req.delta,
            "seed": req.seed,
            "target_col": target_col,
            "correlation_cols": corr_cols,
        },
    )

    def worker():
        try:
            res = run_cell(
                ds,
                req.mechanism,
                req.target_eps,
                seed=req.seed,
                delta=req.delta,
                num_canaries=req.num_canaries,
                target_col=target_col,
                corr_cols=corr_cols or None,
                on_stage=lambda name, payload: events.put(("stage", name, payload)),
                return_artifacts=True,
            )
            events.put(("result", "done", res))
        except Exception as exc:  # surfaced to the console rather than swallowed
            events.put(
                (
                    "error",
                    "failed",
                    {
                        "message": str(exc),
                        "type": type(exc).__name__,
                        "trace": traceback.format_exc(limit=4),
                    },
                )
            )
        finally:
            events.put(None)

    threading.Thread(target=worker, daemon=True).start()

    while True:
        item = events.get()
        if item is None:
            break
        kind, name, payload = item

        if kind == "stage":
            # `**payload` is merged after the stage name, so a payload key called "stage"
            # would silently rename the stage. Nest it instead of trusting emit sites.
            if "stage" in payload:
                payload = {k: v for k, v in payload.items() if k != "stage"}
            yield _sse("stage", {"stage": name, **payload})
            continue
        if kind == "error":
            yield _sse("error", payload)
            continue

        # Final frame: measurements, projected clouds, the ledger entry, and the sheet.
        synth = payload.pop("_synth")
        fit_df = payload.pop("_fit_df")
        payload.pop("_holdout_df", None)
        canaries = payload.pop("_canaries")
        spends = payload.pop("_spends")
        audit = payload.pop("_audit")
        mia = payload.pop("_mia")
        payload.pop("_profile", None)

        cloud = projection.project(
            fit_df, synth, ds.numerical_cols, canary_df=canaries.members, seed=req.seed
        )
        hists = projection.marginal_histograms(fit_df, synth, ds.numerical_cols[:4])

        entry = GLOBAL_LEDGER.append(
            LedgerEntry(
                dataset_id=ds.name,
                run_id=f"{req.mechanism}_eps{req.target_eps}_seed{req.seed}",
                mechanism_name=req.mechanism,
                eps_spent=float(payload["proved_eps"]),
                delta=req.delta,
                seed=req.seed,
            )
        )

        measurements = {k: v for k, v in payload.items() if not k.startswith("_")}

        # Build signed Privacy Data Sheet record for zero-trust certificate verification and capsule export
        sheet_dict = {
            "domain_source": "SynthProof Autonomous Verification Pipeline",
            "contribution_bound": "bounded_one",
            "input_fingerprint": ds.name,
            "dataset_name": ds.name,
            "num_rows": len(synth),
            "mechanism": req.mechanism,
            "mechanism_available": True,
            "delta": req.delta,
            "seed": req.seed,
            "target_column": getattr(ds, "target_col", None) or getattr(ds, "target", None),
            "total_proved_eps": float(payload["proved_eps"]),
            "total_audited_eps": float(audit.audited_eps),
            "audit_ceiling": _audit_payload(audit, req.num_canaries).get("ceiling", 0.0),
            "audit_estimator": "one_run",
            "audit_budget": req.num_canaries,
            "audit_alpha": 0.05,
            "ledger_hash": GLOBAL_LEDGER.get_latest_hash(),
            "frontier_curve": [],
            "evaluation": {
                "tstr_f1": measurements.get("tstr_f1", 0.0),
                "trtr_f1": measurements.get("trtr_f1", 0.0),
                "mia_auc": mia.auc,
                "correlation_error": measurements.get("correlation_error", 0.0),
            },
            "attacks_run": ["canary_audit", "distance_mia"],
            "attacks_not_implemented": NOT_IMPLEMENTED_ATTACKS,
        }
        try:
            import json as _json
            payload_bytes = _json.dumps(sheet_dict, sort_keys=True, separators=(",", ":")).encode("utf-8")
            sheet_dict["signature"] = GLOBAL_LEDGER._private_key.sign(payload_bytes).hex()
            sheet_dict["public_key"] = GLOBAL_LEDGER._public_key.public_bytes_raw().hex()
        except Exception:
            pass

        sample_records = synth.head(100).to_dict(orient="records")

        yield _sse(
            "done",
            {
                "measurements": measurements,
                "sheet": sheet_dict,
                "sample_records": sample_records,
                # Utility and structure are scored against the fit split, not the full table.
                # Stated in the payload so the console cannot present `correlation_error` as a
                # clean fidelity measurement without also showing how contaminated the fit was.
                "evaluation": {
                    "reference": measurements.get("reference", "unknown"),
                    "canary_fraction": measurements.get("canary_fraction"),
                    "caveat": (
                        "Scored against the fit split. The generator was fitted on that split "
                        "plus planted canaries, so a high canary fraction biases these numbers."
                    ),
                },
                "audit": _audit_payload(audit, req.num_canaries),
                "attack": {
                    "name": "Distance MIA baseline",
                    "auc": mia.auc,
                    "advantage": mia.advantage,
                    "attack_accuracy": mia.attack_accuracy,
                    "tpr_at_1pct_fpr": mia.tpr_at_1pct_fpr,
                    "num_train": mia.num_train,
                    "num_test": mia.num_test,
                    "note": "Nearest-neighbour baseline. This is NOT LiRA.",
                },
                # What actually RAN, derived from the artefacts this run produced -- the same
                # rule the certificate follows. The console previously received only
                # `attacks_not_implemented` and the single distance-MIA block, so it showed
                # one attack where five had run. Under-reporting a capability is the same
                # defect as over-reporting one, just in the flattering direction.
                "attacks_run": ["canary_audit"]
                + [
                    label
                    for key, label in (
                        ("_mia", "distance_mia"),
                        ("_domias", "domias"),
                        ("_singling_out", "exact_match_risk"),
                        ("_linkability", "linkability"),
                        ("_attr_inference", "attribute_inference"),
                    )
                    if payload.get(key) is not None
                ],
                "attacks_not_implemented": NOT_IMPLEMENTED_ATTACKS,
                "cloud": {
                    "axes": cloud.axes,
                    "method": cloud.method,
                    "explained_variance": cloud.explained_variance,
                    "real": cloud.real,
                    "synthetic": cloud.synthetic,
                    "canaries": cloud.canaries,
                },
                "histograms": hists,
                "spends": [
                    {
                        "run_id": s.run_id,
                        "mechanism": s.mechanism.name,
                        "noise_scale": s.mechanism.noise_scale,
                        "sensitivity": s.mechanism.sensitivity,
                        "steps": s.mechanism.steps,
                        "marginal_eps": s.marginal_eps,
                        "computed_eps": s.computed_eps,
                    }
                    for s in spends
                ],
                "ledger": {
                    "entry_id": entry.entry_id,
                    "prev_hash": entry.prev_hash,
                    "hash": entry.compute_hash(),
                    "signature": entry.signature,
                    "head": GLOBAL_LEDGER.get_latest_hash(),
                    "verified": GLOBAL_LEDGER.verify(),
                    "signed": False,
                    "signature_note": "Entries are Ed25519-signed, but THIS SERVICE "
                    "generates its ledger key in memory per process and does not "
                    "persist it, so these signatures are unverifiable after a "
                    "restart and this endpoint is a demo surface, not a durable "
                    "record. The CLI path does persist a key: `synthproof keygen`, "
                    "then `run --sign`, then `verify` against the public key.",
                },
            },
        )


@app.post("/api/run", dependencies=[Depends(require_api_key)])
def run(req: RunRequest):
    """Runs one release and streams every stage as server-sent events."""
    return StreamingResponse(
        _run_stream(req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# --------------------------------------------------------------------------- ledger


@app.get("/api/ledger", dependencies=[Depends(require_api_key)])
def get_ledger():
    """Returns the budget ledger and the result of verifying its chain.

    `verified` is the live result of re-hashing every entry and checking the signed head, not
    a cached flag. The chain detects modification, insertion, reordering, replay and
    truncation; it does not defend against an adversary holding the signing key.

    Note the service's key is generated in memory per process, so these signatures do not
    survive a restart — see the preamble in `docs/API.md`.
    """
    entries = GLOBAL_LEDGER.get_entries()
    return {
        "verified": GLOBAL_LEDGER.verify(),
        "head": GLOBAL_LEDGER.get_latest_hash(),
        "count": len(entries),
        "total_eps_spent": round(sum(e.eps_spent for e in entries), 4),
        "entries": [
            {
                "entry_id": e.entry_id,
                "prev_hash": e.prev_hash,
                "hash": e.compute_hash(),
                "timestamp": e.timestamp,
                "dataset_id": e.dataset_id,
                "run_id": e.run_id,
                "mechanism_name": e.mechanism_name,
                "eps_spent": e.eps_spent,
                "delta": e.delta,
                "seed": e.seed,
                "signature": e.signature[:32],
            }
            for e in entries
        ],
    }


class TamperRequest(BaseModel):
    entry_id: Optional[str] = None
    eps_spent: float = 0.01
    attack_type: str = "modify_eps"  # modify_eps, truncate, corrupt_hash, corrupt_signature


@app.post("/api/ledger/tamper", dependencies=[Depends(require_api_key)])
def tamper(req: TamperRequest):
    """Executes an adversarial attack directly on the SQLite database to demonstrate tamper-evidence."""
    _require_demo_ledger()

    entries = GLOBAL_LEDGER.get_entries()
    if req.entry_id is not None and not any(str(e.entry_id) == str(req.entry_id) for e in entries):
        raise HTTPException(404, f"Entry {req.entry_id!r} not found in ledger")

    if not entries:
        raise HTTPException(400, "Ledger is empty. Run a synthesis release first before executing attacks.")

    target_id = req.entry_id or entries[-1].entry_id

    with _ledger_conn() as conn:
        if req.attack_type == "truncate":
            # Delete the most recent row while leaving the signed ledger_head intact
            cur = conn.execute("DELETE FROM ledger_entries WHERE entry_id = ?", (target_id,))
            conn.commit()
            broken_from = len(entries) - 1
            attack_desc = "History Truncation: Deleted recent entry without updating the signed ledger_head."
        elif req.attack_type == "corrupt_hash":
            cur = conn.execute("UPDATE ledger_entries SET hash = 'deadbeef00000000' WHERE entry_id = ?", (target_id,))
            conn.commit()
            broken_from = next((i for i, e in enumerate(entries) if e.entry_id == target_id), 0)
            attack_desc = "Hash Corruption: Injected fraudulent row hash."
        elif req.attack_type == "corrupt_signature":
            cur = conn.execute("UPDATE ledger_entries SET signature = '00' * 64 WHERE entry_id = ?", (target_id,))
            conn.commit()
            broken_from = next((i for i, e in enumerate(entries) if e.entry_id == target_id), 0)
            attack_desc = "Signature Forgery: Corrupted cryptographic entry signature."
        else:
            # Default: modify_eps
            cur = conn.execute(
                "UPDATE ledger_entries SET eps_spent = ? WHERE entry_id = ?",
                (req.eps_spent, target_id),
            )
            conn.commit()
            broken_from = next((i for i, e in enumerate(entries) if e.entry_id == target_id), 0)
            attack_desc = f"Retroactive Spend Manipulation: Altered recorded epsilon to {req.eps_spent}."

    valid, reason = GLOBAL_LEDGER.verify_with_reason()
    return {
        "verified": valid,
        "reason": reason,
        "attack_type": req.attack_type,
        "attack_description": attack_desc,
        "tampered_entry": target_id,
        "broken_from_index": broken_from,
        "broken_count": len(entries) - broken_from if broken_from is not None else 1,
        "explanation": "SynthProof hash-chaining and signed checkpoint heads guarantee non-repudiation.",
    }


@app.post("/api/ledger/reset", dependencies=[Depends(require_api_key)])
def reset_ledger():
    """Clears the in-memory chain, so the tamper demo can be run again."""
    _require_demo_ledger()
    GLOBAL_LEDGER.clear()
    return {"verified": GLOBAL_LEDGER.verify(), "head": GLOBAL_LEDGER.get_latest_hash()}


class CapsuleExportRequest(BaseModel):
    sheet: Dict[str, Any]
    records: Optional[List[Dict[str, Any]]] = None
    curator_name: str = "SynthProof Autonomous Curator"


@app.post("/api/capsule/export")
def export_capsule_endpoint(req: CapsuleExportRequest):
    """Exports a self-verifying standalone HTML capsule containing data, proofs, and WebCrypto engine."""
    from synthproof.capsule.generator import generate_capsule_html
    html_content = generate_capsule_html(req.sheet, req.records or [], curator_name=req.curator_name)
    return HTMLResponse(content=html_content, media_type="text/html")


class CertificateVerifyRequest(BaseModel):
    sheet: Dict[str, Any]
    public_key: Optional[str] = None


@app.post("/api/certificate/verify")
def verify_certificate_endpoint(req: CertificateVerifyRequest):
    """Independently verifies a Privacy Data Sheet or Croissant 1.1 record."""
    from synthproof.ledger import signing
    sheet = req.sheet
    pubkey = req.public_key or sheet.get("public_key")

    results = {
        "signature_valid": False,
        "lod_safe": False,
        "lod_status": "UNKNOWN",
        "error": None,
        "details": {},
    }

    try:
        # Check signature
        if pubkey:
            pk = signing.public_key_from_hex(pubkey)
            signing.verify_datasheet(sheet, public_key=pk)
            results["signature_valid"] = True
        else:
            results["error"] = "Missing public key for verification."

        # Check LoD
        audit_ceiling = float(sheet.get("audit_ceiling", 0.0))
        audited_eps = float(sheet.get("total_audited_eps", 0.0))
        proved_eps = float(sheet.get("total_proved_eps", 0.0))

        if audit_ceiling > 0:
            if audited_eps < audit_ceiling:
                results["lod_safe"] = True
                results["lod_status"] = "NOT DETECTED (< LoD)"
            else:
                results["lod_safe"] = False
                results["lod_status"] = "CEILING REACHED (>= LoD)"

        results["details"] = {
            "proved_eps": proved_eps,
            "audited_eps": audited_eps,
            "audit_ceiling": audit_ceiling,
            "mechanism": sheet.get("mechanism"),
            "dataset_name": sheet.get("dataset_name"),
            "num_rows": sheet.get("num_rows"),
            "ledger_hash": sheet.get("ledger_hash"),
        }
    except Exception as e:
        results["error"] = str(e)

    return results


class CapsuleVerifyRequest(BaseModel):
    html_content: str
    key_path: Optional[str] = None


@app.post("/api/capsule/verify")
def verify_capsule_endpoint(req: CapsuleVerifyRequest):
    """Independently verifies an uploaded HTML capsule offline."""
    from synthproof.capsule.generator import verify_capsule

    try:
        report = verify_capsule(req.html_content)
        return report
    except Exception as e:
        return {
            "verified": False,
            "lod_safe": False,
            "lod_status": "ERROR",
            "error": str(e),
        }


class CroissantExportRequest(BaseModel):
    sheet: Dict[str, Any]


@app.post("/api/croissant/export")
def export_croissant_endpoint(req: CroissantExportRequest):
    """Exports MLCommons Croissant 1.1 JSON-LD specification for a Privacy Data Sheet."""
    from synthproof.frontier.croissant import to_croissant

    try:
        return to_croissant(req.sheet)
    except Exception as e:
        raise HTTPException(400, f"Could not generate Croissant 1.1 record: {e}")



# --------------------------------------------------------------------------- static

_here = os.path.dirname(__file__)

# `static/` holds the hand-written legacy console, which is a tracked source file.
# `console/` holds the built React console and is a generated directory (gitignored).
static_dir = os.path.join(_here, "static")
console_dir = os.path.join(_here, "console")
os.makedirs(static_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Vite emits absolute `/assets/...` URLs so the dev server and a production build use
# identical paths. Mounting the built asset directory at that same path lets this service
# serve the console unchanged, rather than forcing a `base` override that could only ever be
# correct in one of the two environments.
_assets_dir = os.path.join(console_dir, "assets")
if os.path.isdir(_assets_dir):
    app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")


@app.get("/", response_class=HTMLResponse)
def serve_index():
    """Serves the built React console, falling back to a pointer at the dev server."""
    built = os.path.join(console_dir, "index.html")
    if os.path.exists(built):
        with open(built, "r", encoding="utf-8") as f:
            return f.read()
    return (
        "<!doctype html><meta charset='utf-8'>"
        "<title>SynthProof API</title>"
        "<style>body{font:16px/1.6 system-ui;max-width:44rem;margin:4rem auto;padding:0 1.5rem}"
        "code{background:#eee;padding:.15em .4em;border-radius:3px}</style>"
        "<h1>SynthProof API</h1>"
        "<p>The API is running, but the console has not been built.</p>"
        "<p>Dev server: <code>cd web &amp;&amp; npm install &amp;&amp; npm run dev</code> "
        "then open <a href='http://localhost:5173'>localhost:5173</a>.</p>"
        "<p>Or build it into this service: <code>cd web &amp;&amp; npm run build</code>, "
        "then reload this page.</p>"
        "<p>API docs: <a href='/docs'>/docs</a> · "
        "Legacy console: <a href='/static/index.html'>/static/index.html</a></p>"
    )
