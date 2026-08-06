"""FastAPI Backend Service for SynthProof Platform and Live Attack Console."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from synthproof.data.dataset import TabularDataset
from synthproof.frontier.certificate import FrontierEngine
from synthproof.ledger.ledger import Ledger
from synthproof.ledger.types import LedgerEntry


app = FastAPI(
    title="SynthProof API",
    description="Synthetic Data That Ships With Its Proof — API & Live Attack Console",
    version="0.1.0"
)

# NOTE: wildcard origins and allow_credentials=True are mutually incompatible under the
# CORS spec (browsers reject the combination). Credentials are disabled here because this
# service has no authentication to carry. Adding auth is prerequisite to enabling them.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

GLOBAL_LEDGER = Ledger(db_path=":memory:")


class SynthesizeRequest(BaseModel):
    mechanism: str = "AIM / MST"
    target_eps: float = 1.0
    num_samples: int = 100


@app.get("/api/health")
def health_check():
    return {"status": "ok", "ledger_verified": GLOBAL_LEDGER.verify()}


@app.get("/api/ledger")
def get_ledger():
    entries = GLOBAL_LEDGER.get_entries()
    return {
        "verified": GLOBAL_LEDGER.verify(),
        "latest_hash": GLOBAL_LEDGER.get_latest_hash(),
        "entries": [entry.__dict__ for entry in entries]
    }


@app.post("/api/synthesize")
def synthesize_data(req: SynthesizeRequest):
    ds = TabularDataset.create_synthetic_toy(num_rows=req.num_samples)
    engine = FrontierEngine(seed=42)
    # `mechanism` is now honoured. It was previously accepted and silently ignored:
    # every request ran AIM regardless of what the caller asked for.
    datasheet = engine.run_sweep(ds, eps_grid=[req.target_eps], mechanism=req.mechanism)

    # Append to global ledger
    latest_pt = datasheet.frontier_curve[-1] if datasheet.frontier_curve else {}
    GLOBAL_LEDGER.append(LedgerEntry(
        dataset_id=ds.name,
        run_id="run_" + str(req.target_eps),
        mechanism_name=req.mechanism,
        eps_spent=latest_pt.get("proved_eps", req.target_eps),
        delta=1e-5
    ))

    return {
        "success": True,
        "datasheet": datasheet.__dict__,
        "ledger_verified": GLOBAL_LEDGER.verify()
    }


# Mount static directory for frontend
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", response_class=HTMLResponse)
def serve_index():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>SynthProof API Service Running</h1><p>Visit /docs for API documentation.</p>"
