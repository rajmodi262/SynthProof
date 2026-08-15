// Mirrors the FastAPI response shapes. Kept explicit rather than generated, so a change
// on the server surfaces as a type error here instead of an undefined at runtime.

export interface DatasetInfo {
  name: string
  rows: number
  cols: number
  numerical: string[]
  categorical: string[]
  has_schema: boolean
  bounds: Record<string, [number, number] | null>
}

export interface DatasetOption {
  id: string
  label: string
  rows: number | null
  kind: 'built-in' | 'upload'
  note: string | null
}

export interface Mechanism {
  key: string
  label: string
  family: 'baseline' | 'structured'
  blurb: string
  implemented: boolean
  available: boolean
  unavailable_reason: string | null
}

export interface NotImplementedAttack {
  name: string
  reason: string
}

export interface Measurements {
  proved_eps: number
  audited_eps: number
  audit_p: number
  tstr_f1: number
  trtr_f1: number
  mia_auc: number
  correlation_error: number
  /** Which table utility and structure were scored against. */
  reference: string
  /** 'clean_fit' when utility came from a second, canary-free fit. */
  utility_source: string
  /** Planted canaries as a fraction of the fit split — how contaminated the fit was. */
  canary_fraction: number
}

/** How to read `correlation_error` and the utility figures honestly. */
export interface EvaluationContext {
  reference: string
  canary_fraction: number | null
  caveat: string
}

export interface AuditResult {
  audited_eps: number
  tpr: number
  fpr: number
  tpr_lower: number
  fpr_upper: number
  p_value: number
  num_members: number
  num_holdout: number
  confidence: number
  /** Largest epsilon this auditor could report at this canary count. */
  ceiling: number
  /** Smallest known leak fraction detectable at this canary count, or null. */
  detects_leak_above: number | null
  range_note: string
}

export interface AttackResult {
  name: string
  auc: number
  advantage: number
  attack_accuracy: number
  tpr_at_1pct_fpr: number
  num_train: number
  num_test: number
  note: string
}

export type Point3 = [number, number, number]

export interface Cloud {
  axes: string[]
  method: 'pca' | 'columns' | 'unavailable'
  explained_variance: number[]
  real: Point3[]
  synthetic: Point3[]
  canaries: Point3[]
}

export interface Histogram {
  edges: number[]
  real: number[]
  synthetic: number[]
  /** Fraction of synthetic values falling outside the real column's range. */
  synthetic_out_of_range?: number
  real_out_of_range?: number
}

export interface Spend {
  run_id: string | null
  mechanism: string
  noise_scale: number
  sensitivity: number
  steps: number
  marginal_eps: number
  computed_eps: number
}

export interface LedgerRef {
  entry_id: string
  prev_hash: string
  hash: string
  signature: string
  head: string
  verified: boolean
  signed: boolean
  signature_note: string
}

export interface RunResult {
  measurements: Measurements
  evaluation: EvaluationContext
  audit: AuditResult
  attack: AttackResult
  attacks_not_implemented: NotImplementedAttack[]
  cloud: Cloud
  histograms: Record<string, Histogram>
  spends: Spend[]
  ledger: LedgerRef
}

export interface StartEvent {
  dataset: DatasetInfo
  mechanism: string
  mechanism_label: string
  target_eps: number
  delta: number
  seed: number
  target_col: string
  correlation_cols: string[]
}

/** Pipeline stages, in the order the server emits them. */
export const STAGE_ORDER = [
  'split',
  'budget',
  'canaries',
  'profile',
  'fit',
  'generate',
  'audit',
  'utility_fit',
  'utility',
  'attack',
  'attack_domias',
] as const

export type StageName = (typeof STAGE_ORDER)[number]

export interface StageEvent {
  stage: StageName
  [key: string]: unknown
}

export interface LedgerEntry {
  entry_id: string
  prev_hash: string
  hash: string
  timestamp: string
  dataset_id: string
  run_id: string
  mechanism_name: string
  eps_spent: number
  delta: number
  seed: number
  signature: string
}

export interface LedgerState {
  verified: boolean
  head: string
  count: number
  total_eps_spent: number
  entries: LedgerEntry[]
}

export interface UploadResult {
  id: string
  dataset: DatasetInfo
  schema: unknown
  schema_inferred: boolean
  warning: string | null
}

export interface RunRequest {
  dataset: string
  mechanism: string
  target_eps: number
  delta: number
  seed: number
  num_canaries: number
  rows: number
}
