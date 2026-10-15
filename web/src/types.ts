// The API's response shapes. Generated, not hand-written: `src/api/schema.d.ts` is produced
// from the server's OpenAPI document (synthproof/api/schemas.py -> scripts/export_openapi.py ->
// `npm run gen:api`), and CI fails if it is stale. These were hand-written until 2026-10-16 and
// had drifted from the server: no `demo` dataset kind, no ledger `actor`, no `attacks_run`, ten
// measurement fields missing.
import type { components } from './api/schema'

type Schemas = components['schemas']

export type DatasetInfo = Schemas['DatasetInfo']
export type DatasetOption = Schemas['DatasetOption']
export type Mechanism = Schemas['MechanismInfo']
export type NotImplementedAttack = Schemas['NotImplementedAttack']
export type Measurements = Schemas['Measurements']
/** How to read `correlation_error` and the utility figures honestly. */
export type EvaluationContext = Schemas['EvaluationContext']
export type AuditResult = Schemas['AuditResult']
export type AttackResult = Schemas['AttackResult']
export type Cloud = Schemas['Cloud']
export type Histogram = Schemas['Histogram']
export type Spend = Schemas['Spend']
export type LedgerRef = Schemas['LedgerRef']
/** The run stream's final `done` frame. */
export type RunResult = Schemas['RunDoneFrame']
export type TamperResult = Schemas['TamperResult']
/** The run stream's `start` frame. */
export type StartEvent = Schemas['RunStartFrame']
export type LedgerEntry = Schemas['LedgerEntry']
export type LedgerState = Schemas['LedgerState']
export type UploadResult = Schemas['UploadResult']
export type RunRequest = Schemas['RunRequest']

export type Point3 = [number, number, number]

export type AttackType = 'modify_eps' | 'truncate' | 'corrupt_hash' | 'corrupt_signature'

/**
 * Colour only. There is deliberately no "safe" outcome: the verdict answers whether an audit
 * could have certified a claim, never whether a release is safe. See synthproof/audit/ceiling.py.
 */
export type RangeTone = 'ok' | 'warn' | 'fail'

// The certificate verifier returns two shapes (a verdict, or an error record) and is not yet in
// the generated contract; this type is still kept by hand.
export interface CertificateVerifyResult {
  signature_valid: boolean
  publisher_authenticated: boolean
  key_source: 'supplied' | 'embedded' | null
  key_fingerprint: string | null
  claim_in_audit_range: boolean
  range_code: string
  range_tone: RangeTone
  range_explanation: string
  lod_status: string
  error: string | null
  details: {
    proved_eps?: number
    audited_eps?: number
    audit_ceiling?: number
    mechanism?: string
    dataset_name?: string
    num_rows?: number
    ledger_hash?: string
  }
}

/** Pipeline stages, in the order the server emits them (synthproof/frontier/experiment.py). */
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
  'attack_singling_out',
  'attack_linkability',
  'attack_attribute_inference',
] as const

export type StageName = (typeof STAGE_ORDER)[number]

export interface StageEvent {
  stage: StageName
  [key: string]: unknown
}
