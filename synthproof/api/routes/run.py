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
import secrets
import threading
import traceback
from typing import Any, Iterator, Optional

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from synthproof.accounting.differential import cross_check_spends
from synthproof.accounting.differential import enforce as enforce_accountant_agreement
from synthproof.accounting.noise import exact_noise
from synthproof.api import projection, schemas, state
from synthproof.api.context import AppContext, get_context, require_api_key
from synthproof.api.descriptions import (  # noqa: F401  (audit_ceiling re-exported for tests)
    MECHANISM_INFO,
    NOT_IMPLEMENTED_ATTACKS,
    _audit_payload,
    audit_ceiling,
)
from synthproof.api.security import limit_key
from synthproof.audit.mechanism_audit import mechanism_audit_for
from synthproof.frontier.certificate import EVALUATION_PRIVACY
from synthproof.frontier.experiment import (
    MECHANISMS,
    default_target,
    informative_numeric_columns,
    run_cell,
)
from synthproof.frontier.sheet import mechanism_events_from_spends
from synthproof.ledger.types import LedgerEntry

router = APIRouter()

# --------------------------------------------------------------------------- models


class RunRequest(BaseModel):
    dataset: str = Field("toy", description="'toy', 'adult', or an upload id.")
    mechanism: str = Field("pairwise")
    target_eps: float = Field(1.0, gt=0, le=64)
    delta: float = Field(1e-5, gt=0, lt=1)
    seed: Optional[int] = Field(
        None,
        description="Noise seed. Leave it out and a secret one is drawn: anyone who can guess "
        "the seed can replay the release and test whether a record was in the input.",
    )
    num_canaries: int = Field(60, ge=1, le=500)
    rows: int = Field(
        2000,
        ge=100,
        le=50_000,
        description="Rows to release, declared in advance, and the subsample size.",
    )
    target: Optional[str] = Field(
        None,
        description="Categorical column the utility evaluation predicts. Omitted: `income` if "
        "present, else the table's last categorical column.",
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


def _prepare(req: RunRequest, ctx: AppContext):
    """Resolves the seed, table and target. Returns (req, seed32, ds, target_col, error)."""
    if req.seed is None:
        # Drawn here and never written to the sheet (PUBLIC_RELEASE_BOUNDARY.md, D5). The console
        # still sees it: the operator already holds the table, so it is not a release.
        req = req.model_copy(update={"seed": secrets.randbits(63)})
    assert req.seed is not None
    # pandas and the projection need a 32-bit seed. Neither draws DP noise.
    seed32 = req.seed % (2**32)

    if req.mechanism not in MECHANISMS:
        return (
            req,
            seed32,
            None,
            None,
            {
                "message": f"Mechanism {req.mechanism!r} is not available in this environment.",
                "available": sorted(MECHANISMS),
            },
        )
    try:
        ds = ctx.load_dataset(req.dataset, req.rows, seed32)
    except HTTPException as exc:
        return req, seed32, None, None, {"message": exc.detail}
    try:
        target_col = default_target(ds, req.target)
    except ValueError as exc:
        return req, seed32, ds, None, {"message": str(exc)}
    if target_col is None:
        return (
            req,
            seed32,
            ds,
            None,
            {
                "message": "This table has no categorical column to predict, "
                "so downstream utility cannot be evaluated."
            },
        )
    return req, seed32, ds, target_col, None


def _start_worker(req: RunRequest, ds, target_col, corr_cols, events) -> None:
    """`run_cell` is synchronous, so it runs on a worker thread and pushes stage events into a
    queue the stream drains -- each stage appears when it has actually finished."""

    def worker():
        try:
            # A console release is a release: exact-arithmetic noise (accounting/noise.py).
            with exact_noise():
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
                    # `rows` is declared in the request, so the release size is public whatever
                    # the table's real length is (PUBLIC_RELEASE_BOUNDARY.md, D2).
                    release_rows=req.rows,
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


def _signed_sheet(
    ctx: AppContext, req: RunRequest, ds, target_col, payload, audit, mia, measurements, spends
) -> dict:
    """The Privacy Data Sheet for this release, signed with the ledger key.

    Signing used to sit in `try: ... except Exception: pass`, so a signing failure returned an
    unsigned sheet with nothing said (found 2026-10-16). A failure now propagates and the console
    gets an error frame instead of a sheet that silently lacks the signature it is meant to carry.
    """
    from synthproof.ledger.signing import canonical_sheet_payload, public_key_hex

    # The same two fields the CLI engine signs (frontier/certificate.py). Without them a console
    # release failed its own boundary check RB5: nobody could recompose its epsilon, and no second
    # accountant had looked at it. An under-report refuses the release here, as it does there.
    agreement = enforce_accountant_agreement(cross_check_spends(spends, req.delta))

    sheet_dict = {
        # RB6: how the column bounds / category domains were obtained. Demo datasets and
        # uploads infer them from the data (a leak the boundary auditor must flag); the
        # built-in declared-schema datasets do not. Never a marketing string.
        "domain_source": ctx.domain_source_for(req.dataset),
        "contribution_bound": 1,
        # The trust assumption every epsilon here rests on: this service reads the table.
        "deployment_model": "central",
        "unit_of_privacy": "add/remove-one-record",
        # No fingerprint: this console holds no curator key, and a table name is not one.
        "input_fingerprint": None,
        "dataset_name": ds.name,
        "num_rows": req.rows,
        "release_rows_source": "declared",
        "release_rows_eps": 0.0,
        "mechanism": req.mechanism,
        "mechanism_available": True,
        "delta": req.delta,
        "seed": None,  # withheld: it replays every noise draw (D5)
        "target_column": target_col,
        "total_proved_eps": float(payload["proved_eps"]),
        "total_audited_eps": float(audit.audited_eps),
        "audit_ceiling": _audit_payload(audit, req.num_canaries).get("ceiling", 0.0),
        "audit_estimator": "one_run",
        "audit_budget": req.num_canaries,
        "audit_alpha": 0.05,
        "ledger_hash": ctx.ledger.get_latest_hash(),
        "frontier_curve": [],
        "evaluation": {
            "tstr_f1": measurements.get("tstr_f1", 0.0),
            "trtr_f1": measurements.get("trtr_f1", 0.0),
            "mia_auc": mia.auc,
            "correlation_error": measurements.get("correlation_error", 0.0),
        },
        "evaluation_privacy": EVALUATION_PRIVACY,
        "attacks_run": ["canary_audit", "distance_mia"],
        "attacks_not_implemented": NOT_IMPLEMENTED_ATTACKS,
        "mechanism_audit": mechanism_audit_for(req.mechanism),
        "accountant_agreement": agreement.to_dict(),
        "mechanism_events": mechanism_events_from_spends(spends),
    }
    sheet_dict["signature"] = ctx.ledger._private_key.sign(
        canonical_sheet_payload(sheet_dict)
    ).hex()
    sheet_dict["public_key"] = public_key_hex(ctx.ledger._public_key)
    return sheet_dict


def _ledger_frame(ctx: AppContext, entry) -> dict:
    durable = ctx.ledger_durable
    return {
        "entry_id": entry.entry_id,
        "prev_hash": entry.prev_hash,
        "hash": entry.compute_hash(),
        "signature": entry.signature,
        "head": ctx.ledger.get_latest_hash(),
        "verified": ctx.ledger.verify(),
        # Whether the signature can be verified after this process ends.
        "signed": durable,
        "signature_note": (
            "Entries are Ed25519-signed with the key in SYNTHPROOF_KEY_DIR, which persists with "
            "the ledger, so the chain and its head verify across restarts."
            if durable
            else "Entries are Ed25519-signed, but this service is running with an IN-MEMORY "
            "ledger whose key exists only for this process, so the signatures are unverifiable "
            "after a restart: a demo surface, not a durable record. Set SYNTHPROOF_LEDGER_DB and "
            "SYNTHPROOF_KEY_DIR for a durable one; the CLI path (`synthproof keygen`, "
            "`run --sign`, `verify`) also persists its key."
        ),
    }


def _attacks_run(payload: dict) -> list:
    """What actually RAN, derived from the artefacts this run produced -- the rule the certificate
    follows. Under-reporting a capability is the same defect as over-reporting one."""
    return ["canary_audit"] + [
        label
        for key, label in (
            ("_mia", "distance_mia"),
            ("_domias", "domias"),
            ("_singling_out", "exact_match_risk"),
            ("_linkability", "linkability"),
            ("_attr_inference", "attribute_inference"),
        )
        if payload.get(key) is not None
    ]


def _done_frame(
    ctx: AppContext, req: RunRequest, ds, target_col, seed32, payload: dict, actor: str
) -> dict:
    """Final frame: measurements, projected clouds, the ledger entry, and the signed sheet."""
    assert req.seed is not None  # resolved by _prepare before any fit runs
    attacks_run = _attacks_run(payload)
    synth = payload.pop("_synth")
    fit_df = payload.pop("_fit_df")
    payload.pop("_holdout_df", None)
    canaries = payload.pop("_canaries")
    spends = payload.pop("_spends")
    audit = payload.pop("_audit")
    mia = payload.pop("_mia")
    payload.pop("_profile", None)

    cloud = projection.project(
        fit_df, synth, ds.numerical_cols, canary_df=canaries.members, seed=seed32
    )
    entry = ctx.ledger.append(
        LedgerEntry(
            dataset_id=ds.name,
            run_id=f"{req.mechanism}_eps{req.target_eps}_seed{req.seed}",
            mechanism_name=req.mechanism,
            eps_spent=float(payload["proved_eps"]),
            delta=req.delta,
            seed=req.seed,
            # Who spent the budget: the principal whose key authenticated the request.
            actor=actor,
        )
    )
    measurements = {k: v for k, v in payload.items() if not k.startswith("_")}
    return {
        "measurements": measurements,
        "sheet": _signed_sheet(ctx, req, ds, target_col, payload, audit, mia, measurements, spends),
        "sample_records": synth.head(100).to_dict(orient="records"),
        # Utility and structure are scored against the fit split, not the full table. Stated in
        # the payload so the console cannot present `correlation_error` as a clean fidelity
        # measurement without also showing how contaminated the fit was.
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
        "attacks_run": attacks_run,
        "attacks_not_implemented": NOT_IMPLEMENTED_ATTACKS,
        "cloud": {
            "axes": cloud.axes,
            "method": cloud.method,
            "explained_variance": cloud.explained_variance,
            "real": cloud.real,
            "synthetic": cloud.synthetic,
            "canaries": cloud.canaries,
        },
        "histograms": projection.marginal_histograms(fit_df, synth, ds.numerical_cols[:4]),
        "correlations": projection.correlation_matrices(fit_df, synth, ds.numerical_cols[:5]),
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
        "ledger": _ledger_frame(ctx, entry),
    }


def _run_stream(
    req: RunRequest, actor: str = "anonymous", ctx: Optional[AppContext] = None
) -> Iterator[str]:
    """Streams pipeline stages as they complete."""
    ctx = ctx if ctx is not None else state.default_context()
    req, seed32, ds, target_col, error = _prepare(req, ctx)
    if error is not None:
        yield _sse("error", error)
        return

    corr_cols = informative_numeric_columns(ds.df, ds.numerical_cols)
    start = schemas.StartFrame.model_validate(
        {
            "dataset": state._describe(ds),
            "mechanism": req.mechanism,
            "mechanism_label": MECHANISM_INFO.get(req.mechanism, {}).get("label", req.mechanism),
            "target_eps": req.target_eps,
            "delta": req.delta,
            "seed": req.seed,
            "target_col": target_col,
            "correlation_cols": corr_cols,
        }
    )
    yield _sse("start", start.model_dump())

    events: "queue.Queue[Optional[tuple]]" = queue.Queue()
    _start_worker(req, ds, target_col, corr_cols, events)
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
        elif kind == "error":
            yield _sse("error", payload)
        else:
            try:
                frame = _done_frame(ctx, req, ds, target_col, seed32, payload, actor)
                # The contract (synthproof/api/schemas.py): a frame that does not match it is an
                # error here, not an `undefined` in the console.
                schemas.DoneFrame.model_validate(frame)
            except Exception as exc:  # e.g. signing failed: say so, never ship it unsigned
                yield _sse(
                    "error",
                    {
                        "message": f"The release could not be completed: {exc}",
                        "type": type(exc).__name__,
                    },
                )
                continue
            yield _sse("done", frame)


@router.post("/api/run")
def run(
    req: RunRequest,
    request: Request,
    actor: str = Depends(require_api_key),
    ctx: AppContext = Depends(get_context),
):
    """Runs one release and streams every stage as server-sent events.

    Refused BEFORE anything runs (so with a plain HTTP status, not a stream) when the caller is
    over its rate limit or the release would take it past its epsilon cap (api/security.py).
    """
    ctx.rate_limiter.check(limit_key(request, actor))
    ctx.check_budget(actor, req.target_eps)
    return StreamingResponse(
        _run_stream(req, actor, ctx),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
