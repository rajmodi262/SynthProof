"""The API's response contract, as Pydantic models.

WHY (W6, 2026-10-16). The console's TypeScript types were written by hand "so a change on the
server surfaces as a type error" -- but nothing connected them to the server, and they had
drifted: no `demo` dataset kind, no ledger `actor` or `eps_by_actor`, no `attacks_run`, ten
measurement fields missing, and a stage list that stopped before the last four attacks. These
models are the contract instead. JSON endpoints declare them as `response_model`; the run
stream's start and done frames are validated against them before they are sent, and injected
into the OpenAPI document. `scripts/export_openapi.py` writes that document and the console's
types are generated from it (`web/src/api/schema.d.ts`); CI fails when either is stale.

Every model forbids extra fields, so a value added on the server cannot reach the console
without being added here first.
"""

from typing import Any, Dict, List, Literal, Optional, Tuple, Type

from pydantic import BaseModel, ConfigDict, Field


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------- service and datasets


class Health(_Strict):
    status: Literal["ok"]
    auth: Literal["required", "disabled"]
    auth_mode: Literal["per-user", "shared", "disabled"]
    auth_note: str
    demo_mode: bool
    ledger_verified: bool
    ledger_head: str
    mechanisms_available: List[str]


class MechanismInfo(_Strict):
    key: str
    label: str
    family: Literal["baseline", "structured", "control", "deep"]
    blurb: str
    implemented: bool
    available: bool
    unavailable_reason: Optional[str]


class NotImplementedAttack(_Strict):
    name: str
    reason: str


class Mechanisms(_Strict):
    mechanisms: List[MechanismInfo]
    attacks_not_implemented: List[NotImplementedAttack]


class DatasetOption(_Strict):
    id: str
    label: str
    rows: Optional[int]
    kind: Literal["built-in", "demo", "upload"]
    note: Optional[str]


class Datasets(_Strict):
    datasets: List[DatasetOption]


class DatasetInfo(_Strict):
    name: str
    rows: int
    cols: int
    numerical: List[str]
    categorical: List[str]
    has_schema: bool
    bounds: Dict[str, Optional[Tuple[float, float]]]


class UploadResult(_Strict):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str
    dataset: DatasetInfo
    # `schema` would shadow BaseModel.schema, so the attribute is renamed and the wire name kept.
    schema_: Dict[str, Any] = Field(alias="schema")
    schema_inferred: bool
    warning: Optional[str]


# ---------------------------------------------------------------- the ledger


class LedgerEntry(_Strict):
    entry_id: str
    prev_hash: str
    hash: str
    timestamp: str
    dataset_id: str
    run_id: str
    mechanism_name: str
    eps_spent: float
    delta: float
    seed: Optional[int]
    actor: str
    signature: str


class LedgerState(_Strict):
    verified: bool
    head: str
    count: int
    total_eps_spent: float
    eps_by_actor: Dict[str, float]
    entries: List[LedgerEntry]


class LedgerReset(_Strict):
    verified: bool
    head: str


class TamperResult(_Strict):
    verified: bool
    reason: Optional[str]
    attack_type: str
    attack_description: str
    tampered_entry: Optional[str]
    broken_from_index: Optional[int]
    broken_count: int
    explanation: str


# ---------------------------------------------------------------- the run stream


class StartFrame(_Strict):
    dataset: DatasetInfo
    mechanism: str
    mechanism_label: str
    target_eps: float
    delta: float
    seed: int
    target_col: str
    correlation_cols: List[str]


class Measurements(_Strict):
    proved_eps: float
    audited_eps: float
    audit_p: float
    tstr_f1: float
    marginal_w1: float
    trtr_f1: float
    usefulness_multi: float
    mia_auc: float
    domias_auc: float
    domias_tpr_at_1pct: float
    singling_out_risk: float
    linkability_rate: float
    linkability_excess: float
    attr_inference_accuracy: float
    attr_leakage_vs_conditional: float
    correlation_error: float
    structure_error_all: float
    pair_tvd: float
    reference: str
    auditor: Literal["one_run", "paired"]
    audit_ceiling: float
    utility_source: Literal["clean_fit", "audit_fit"]
    canary_fraction: float


class EvaluationContext(_Strict):
    reference: str
    canary_fraction: Optional[float]
    caveat: str


class AuditResult(_Strict):
    audited_eps: float
    p_value: float
    auditor: Literal["one_run", "paired"]
    ceiling: float
    detects_leak_above: Optional[float]
    range_note: str
    tpr: float
    fpr: float
    tpr_lower: float
    fpr_upper: float
    num_members: int
    num_holdout: int
    # one-run only
    saturated: Optional[bool] = None
    correct: Optional[int] = None
    guesses: Optional[int] = None
    accuracy: Optional[float] = None
    num_canaries: Optional[int] = None
    num_included: Optional[int] = None
    # paired only
    confidence: Optional[float] = None


class AttackResult(_Strict):
    name: str
    auc: float
    advantage: float
    attack_accuracy: float
    tpr_at_1pct_fpr: float
    num_train: int
    num_test: int
    note: str


Point3 = Tuple[float, float, float]


class Cloud(_Strict):
    # Always three coordinates: with fewer than three numeric columns the projection zero-pads
    # (api/projection.py), so a point is a fixed triple, not a list of unknown length.
    axes: List[str]
    method: Literal["pca", "columns", "unavailable"]
    explained_variance: List[float]
    real: List[Point3]
    synthetic: List[Point3]
    canaries: List[Point3]


class Histogram(_Strict):
    edges: List[float]
    real: List[float]
    synthetic: List[float]
    synthetic_out_of_range: Optional[float] = None
    real_out_of_range: Optional[float] = None


class Correlations(_Strict):
    columns: List[str]
    real: List[List[float]]
    synth: List[List[float]]


class Spend(_Strict):
    run_id: Optional[str]
    mechanism: str
    noise_scale: float
    sensitivity: float
    steps: int
    marginal_eps: float
    computed_eps: float


class LedgerRef(_Strict):
    entry_id: str
    prev_hash: str
    hash: str
    signature: str
    head: str
    verified: bool
    signed: bool
    signature_note: str


class DoneFrame(_Strict):
    measurements: Measurements
    sheet: Dict[str, Any]
    sample_records: List[Dict[str, Any]]
    evaluation: EvaluationContext
    audit: AuditResult
    attack: AttackResult
    attacks_run: List[str]
    attacks_not_implemented: List[NotImplementedAttack]
    cloud: Cloud
    histograms: Dict[str, Histogram]
    correlations: Optional[Correlations]
    spends: List[Spend]
    ledger: LedgerRef


# The frames the run stream sends, exported into the OpenAPI document (FastAPI cannot infer an
# SSE body) so the console's types are generated from the same source as everything else.
STREAM_FRAMES: Dict[str, Type[BaseModel]] = {"RunStartFrame": StartFrame, "RunDoneFrame": DoneFrame}
