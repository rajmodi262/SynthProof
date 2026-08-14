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

import io
import json
import os
import queue
import threading
import traceback
import uuid
from typing import Dict, Iterator, Optional

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
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
# are off because this service carries no authentication; adding auth is a prerequisite to
# turning them on. The dev console runs on a different port, hence the wildcard.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

GLOBAL_LEDGER = Ledger(db_path=os.environ.get("SYNTHPROOF_LEDGER_DB", ":memory:"))

# Uploaded tables live in memory for the session. Nothing is written to disk: this service
# receives sensitive data by definition, and persisting it silently would be exactly the
# habit the project exists to argue against.
_UPLOADS: Dict[str, TabularDataset] = {}
_MAX_UPLOAD_BYTES = 25 * 1024 * 1024
_MAX_UPLOAD_ROWS = 20_000


# --------------------------------------------------------------------------- descriptions

MECHANISM_INFO = {
    "independent": {
        "label": "Independent marginals",
        "family": "baseline",
        "blurb": "One noisy 1-D marginal per column, sampled independently. Destroys all "
                 "cross-column structure by construction — the ablation baseline.",
        "implemented": True,
    },
    "copula": {
        "label": "Per-column Gaussian",
        "family": "baseline",
        "blurb": "DP-noised per-column moments. Despite the class name this is NOT a "
                 "Gaussian copula: no covariance, no rank transform, no correlation.",
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

NOT_IMPLEMENTED_ATTACKS = [
    {"name": "LiRA", "reason": "Needs 64+ shadow models; scheduled for milestone M2."},
    {"name": "DOMIAS", "reason": "Density-ratio MIA for synthetic data; scheduled for M2."},
    {"name": "Attribute inference", "reason": "No reconstruction attack exists yet (M2)."},
]


# --------------------------------------------------------------------------- models

class RunRequest(BaseModel):
    dataset: str = Field("toy", description="'toy', 'adult', or an upload id.")
    mechanism: str = Field("pairwise")
    target_eps: float = Field(1.0, gt=0, le=64)
    delta: float = Field(1e-5, gt=0, lt=1)
    seed: int = 0
    num_canaries: int = Field(60, ge=1, le=500)
    rows: int = Field(2000, ge=100, le=50_000,
                      description="Subsample size, so the console stays interactive.")


# --------------------------------------------------------------------------- datasets

def _load_dataset(name: str, rows: int, seed: int = 0) -> TabularDataset:
    if name in _UPLOADS:
        ds = _UPLOADS[name]
    elif name == "toy":
        return TabularDataset.create_synthetic_toy(num_rows=min(rows, 5000), seed=seed)
    elif name == "adult":
        from synthproof.data.datasets import load_adult
        ds = load_adult()
    else:
        raise HTTPException(404, f"Unknown dataset {name!r}. "
                                 "Use 'toy', 'adult', or an upload id from /api/upload.")

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
    return {
        "status": "ok",
        "ledger_verified": GLOBAL_LEDGER.verify(),
        "ledger_head": GLOBAL_LEDGER.get_latest_hash(),
        "mechanisms_available": sorted(MECHANISMS),
    }


@app.get("/api/mechanisms")
def mechanisms():
    """Mechanisms this build can actually run, plus honest notes on the ones it cannot."""
    out = []
    for key, info in MECHANISM_INFO.items():
        out.append({**info, "key": key, "available": key in MECHANISMS,
                    "unavailable_reason": None if key in MECHANISMS
                    else "private-pgm (package `mbi`) is not installed in this environment."})
    return {"mechanisms": out, "attacks_not_implemented": NOT_IMPLEMENTED_ATTACKS}


@app.get("/api/datasets")
def datasets():
    built_in = [
        {"id": "toy", "label": "Toy table (3 columns)", "rows": None, "kind": "built-in",
         "note": "Columns are drawn INDEPENDENTLY — there is no structure to preserve. "
                 "Useful for a fast demo, meaningless for utility claims."},
        {"id": "adult", "label": "UCI Adult", "rows": 30162, "kind": "built-in",
         "note": "SHA-256 verified on load. Hand-declared public schema; strongest numeric "
                 "correlation is only 0.093."},
    ]
    uploads = [{"id": k, "label": v.name, "rows": v.num_rows, "kind": "upload", "note": None}
               for k, v in _UPLOADS.items()]
    return {"datasets": built_in + uploads}


@app.post("/api/upload")
async def upload(file: UploadFile = File(...), schema_json: Optional[str] = None):
    """Accepts a CSV and registers it for this session.

    Without a declared public schema the column kinds and numeric bounds are inferred FROM
    THE DATA, which leaks and is not safe for a real release. The response says so, and the
    console is expected to surface that warning rather than bury it.
    """
    if not (file.filename or "").lower().endswith((".csv", ".txt")):
        raise HTTPException(400, "Upload a .csv file.")

    raw = await file.read()
    if len(raw) > _MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"File exceeds {_MAX_UPLOAD_BYTES // (1024*1024)} MB.")

    try:
        df = pd.read_csv(io.BytesIO(raw), skipinitialspace=True, na_values=["?", ""])
    except Exception as exc:
        raise HTTPException(400, f"Could not parse CSV: {exc}") from exc

    df = df.dropna(axis=0, how="any").reset_index(drop=True)
    if df.empty:
        raise HTTPException(400, "No complete rows after dropping missing values.")
    if len(df) > _MAX_UPLOAD_ROWS:
        df = df.sample(n=_MAX_UPLOAD_ROWS, random_state=0).reset_index(drop=True)

    inferred = schema_json is None
    schema = Schema.from_dict(json.loads(schema_json)) if schema_json else \
        Schema.infer_nonprivate(df)

    name = (file.filename or "upload").rsplit(".", 1)[0]
    ds = TabularDataset(df, name=name, schema=schema)

    upload_id = f"upload:{uuid.uuid4().hex[:8]}"
    _UPLOADS[upload_id] = ds

    return {
        "id": upload_id,
        "dataset": _describe(ds),
        "schema": schema.to_dict(),
        "schema_inferred": inferred,
        "warning": (
            "Bounds were READ FROM YOUR DATA, so they leak. This is fine for exploring a "
            "table you already own; for a real release, edit the bounds to publishable "
            "facts about the domain and re-upload with a declared schema."
        ) if inferred else None,
    }


# --------------------------------------------------------------------------- run (SSE)

def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, default=str)}\n\n"


def _run_stream(req: RunRequest) -> Iterator[str]:
    """Streams pipeline stages as they complete.

    `run_cell` is synchronous, so it runs on a worker thread and pushes stage events into a
    queue that this generator drains. That keeps the console's progress honest — each stage
    appears when it has actually finished, not on a timer.
    """
    events: "queue.Queue[Optional[tuple]]" = queue.Queue()

    if req.mechanism not in MECHANISMS:
        yield _sse("error", {
            "message": f"Mechanism {req.mechanism!r} is not available in this environment.",
            "available": sorted(MECHANISMS),
        })
        return

    try:
        ds = _load_dataset(req.dataset, req.rows, req.seed)
    except HTTPException as exc:
        yield _sse("error", {"message": exc.detail})
        return

    target_col = ("income" if "income" in ds.categorical_cols
                  else (ds.categorical_cols[0] if ds.categorical_cols else None))
    if target_col is None:
        yield _sse("error", {"message": "This table has no categorical column to predict, "
                                        "so downstream utility cannot be evaluated."})
        return

    corr_cols = informative_numeric_columns(ds.df, ds.numerical_cols)

    yield _sse("start", {
        "dataset": _describe(ds), "mechanism": req.mechanism,
        "mechanism_label": MECHANISM_INFO.get(req.mechanism, {}).get("label", req.mechanism),
        "target_eps": req.target_eps, "delta": req.delta, "seed": req.seed,
        "target_col": target_col, "correlation_cols": corr_cols,
    })

    def worker():
        try:
            res = run_cell(
                ds, req.mechanism, req.target_eps, seed=req.seed, delta=req.delta,
                num_canaries=req.num_canaries, target_col=target_col,
                corr_cols=corr_cols or None,
                on_stage=lambda name, payload: events.put(("stage", name, payload)),
                return_artifacts=True,
            )
            events.put(("result", "done", res))
        except Exception as exc:  # surfaced to the console rather than swallowed
            events.put(("error", "failed", {
                "message": str(exc), "type": type(exc).__name__,
                "trace": traceback.format_exc(limit=4),
            }))
        finally:
            events.put(None)

    threading.Thread(target=worker, daemon=True).start()

    while True:
        item = events.get()
        if item is None:
            break
        kind, name, payload = item

        if kind == "stage":
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

        cloud = projection.project(fit_df, synth, ds.numerical_cols,
                                   canary_df=canaries.members, seed=req.seed)
        hists = projection.marginal_histograms(fit_df, synth, ds.numerical_cols[:4])

        entry = GLOBAL_LEDGER.append(LedgerEntry(
            dataset_id=ds.name,
            run_id=f"{req.mechanism}_eps{req.target_eps}_seed{req.seed}",
            mechanism_name=req.mechanism,
            eps_spent=float(payload["proved_eps"]),
            delta=req.delta,
            seed=req.seed,
        ))

        yield _sse("done", {
            "measurements": {k: v for k, v in payload.items() if not k.startswith("_")},
            "audit": {
                "audited_eps": audit.audited_eps, "tpr": audit.tpr, "fpr": audit.fpr,
                "tpr_lower": audit.tpr_lower, "fpr_upper": audit.fpr_upper,
                "p_value": audit.p_value, "num_members": audit.num_members,
                "num_holdout": audit.num_holdout, "confidence": audit.confidence,
            },
            "attack": {
                "name": "Distance MIA baseline", "auc": mia.auc,
                "advantage": mia.advantage, "attack_accuracy": mia.attack_accuracy,
                "tpr_at_1pct_fpr": mia.tpr_at_1pct_fpr,
                "num_train": mia.num_train, "num_test": mia.num_test,
                "note": "Nearest-neighbour baseline. This is NOT LiRA.",
            },
            "attacks_not_implemented": NOT_IMPLEMENTED_ATTACKS,
            "cloud": {
                "axes": cloud.axes, "method": cloud.method,
                "explained_variance": cloud.explained_variance,
                "real": cloud.real, "synthetic": cloud.synthetic, "canaries": cloud.canaries,
            },
            "histograms": hists,
            "spends": [
                {"run_id": s.run_id, "mechanism": s.mechanism.name,
                 "noise_scale": s.mechanism.noise_scale,
                 "sensitivity": s.mechanism.sensitivity, "steps": s.mechanism.steps,
                 "marginal_eps": s.marginal_eps, "computed_eps": s.computed_eps}
                for s in spends
            ],
            "ledger": {
                "entry_id": entry.entry_id, "prev_hash": entry.prev_hash,
                "hash": entry.compute_hash(), "signature": entry.signature,
                "head": GLOBAL_LEDGER.get_latest_hash(),
                "verified": GLOBAL_LEDGER.verify(),
                "signed": False,
                "signature_note": "Entries are Ed25519-signed, but the key is generated in "
                                  "memory per process and never persisted, and the data "
                                  "sheet itself carries no signature yet.",
            },
        })


@app.post("/api/run")
def run(req: RunRequest):
    """Runs one release and streams every stage as server-sent events."""
    return StreamingResponse(
        _run_stream(req),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no",
                 "Connection": "keep-alive"},
    )


# --------------------------------------------------------------------------- ledger

@app.get("/api/ledger")
def get_ledger():
    entries = GLOBAL_LEDGER.get_entries()
    return {
        "verified": GLOBAL_LEDGER.verify(),
        "head": GLOBAL_LEDGER.get_latest_hash(),
        "count": len(entries),
        "total_eps_spent": round(sum(e.eps_spent for e in entries), 4),
        "entries": [
            {"entry_id": e.entry_id, "prev_hash": e.prev_hash, "hash": e.compute_hash(),
             "timestamp": e.timestamp, "dataset_id": e.dataset_id, "run_id": e.run_id,
             "mechanism_name": e.mechanism_name, "eps_spent": e.eps_spent,
             "delta": e.delta, "seed": e.seed, "signature": e.signature[:32]}
            for e in entries
        ],
    }


class TamperRequest(BaseModel):
    entry_id: str
    eps_spent: float = 0.01


@app.post("/api/ledger/tamper")
def tamper(req: TamperRequest):
    """Rewrites one entry's epsilon directly in SQLite, bypassing `append`.

    This exists for the demo: it shows that the chain is tamper-EVIDENT. Verification fails
    from the altered entry onward, because every later entry commits to its predecessor's
    hash. It does not show tamper-PROOF — anyone holding the signing key can rewrite and
    re-sign, which is why key custody is an organisational control, not a cryptographic one.
    """
    conn = GLOBAL_LEDGER._get_conn()
    cur = conn.execute("UPDATE ledger_entries SET eps_spent = ? WHERE entry_id = ?",
                       (req.eps_spent, req.entry_id))
    conn.commit()
    if cur.rowcount == 0:
        raise HTTPException(404, f"No ledger entry {req.entry_id!r}.")

    entries = GLOBAL_LEDGER.get_entries()
    broken_from = next((i for i, e in enumerate(entries) if e.entry_id == req.entry_id), None)
    return {
        "verified": GLOBAL_LEDGER.verify(),
        "tampered_entry": req.entry_id,
        "broken_from_index": broken_from,
        "broken_count": len(entries) - broken_from if broken_from is not None else 0,
        "explanation": "Each entry commits to its predecessor's SHA-256, so altering one "
                       "invalidates it and every entry after it.",
    }


@app.post("/api/ledger/reset")
def reset_ledger():
    """Clears the in-memory chain, so the tamper demo can be run again."""
    conn = GLOBAL_LEDGER._get_conn()
    conn.execute("DELETE FROM ledger_entries")
    conn.commit()
    return {"verified": GLOBAL_LEDGER.verify(), "head": GLOBAL_LEDGER.get_latest_hash()}


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
