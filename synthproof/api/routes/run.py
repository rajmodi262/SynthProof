"""The release pipeline, streamed to the console over SSE.

This endpoint drives `frontier.experiment.run_cell` through its `on_stage` callback rather
than reimplementing the pipeline. That is deliberate and load-bearing: three parallel
pipelines have already drifted apart in this repository, and a fourth living in the web layer
would be the worst of them, because it is the one a demonstration runs on.

The `descriptions` block below travels with the pipeline because it is the pipeline's
vocabulary -- what each mechanism is, and what the auditor can and cannot see. The audit
ceiling in particular is not decoration: an `eps_audited` of 0 reported without the maximum
the instrument could have certified reads as "no leakage" when it means "below resolution".
"""

import json
import queue
import threading
import traceback
from typing import Any, Iterator, Optional

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from synthproof.api import projection, state
from synthproof.api.descriptions import (  # noqa: F401  (audit_ceiling re-exported for tests)
    MECHANISM_INFO,
    NOT_IMPLEMENTED_ATTACKS,
    _audit_payload,
    audit_ceiling,
)
from synthproof.api.state import require_api_key
from synthproof.frontier.experiment import MECHANISMS, informative_numeric_columns, run_cell
from synthproof.ledger.types import LedgerEntry

router = APIRouter()

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
        ds = state._load_dataset(req.dataset, req.rows, req.seed)
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
            "dataset": state._describe(ds),
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

        entry = state.GLOBAL_LEDGER.append(
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

        # Build the signed Privacy Data Sheet record used for zero-trust certificate
        # verification and capsule export.
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
            "ledger_hash": state.GLOBAL_LEDGER.get_latest_hash(),
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

            payload_bytes = _json.dumps(sheet_dict, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
            sheet_dict["signature"] = state.GLOBAL_LEDGER._private_key.sign(payload_bytes).hex()
            sheet_dict["public_key"] = state.GLOBAL_LEDGER._public_key.public_bytes_raw().hex()
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
                    "head": state.GLOBAL_LEDGER.get_latest_hash(),
                    "verified": state.GLOBAL_LEDGER.verify(),
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


@router.post("/api/run", dependencies=[Depends(require_api_key)])
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
