import { KpiCard } from './KpiCard'
import type { LedgerState, RunResult } from '@/types'

interface KpiRowProps {
  result: RunResult | null
  ledger: LedgerState | null
  activeExplainer: string | null
  onOpenExplainer: (key: string) => void
}

export function KpiRow({
  result,
  ledger,
  activeExplainer,
  onOpenExplainer,
}: KpiRowProps) {
  const m = result?.measurements ?? null
  const audit = result?.audit ?? null
  const sheet = result?.sheet ?? null

  // ONE source per card, named in its `source` prop and shown on hover. The signed sheet is
  // preferred where it carries the value, because that is the artefact a third party checks.
  // There used to be fallbacks (`sheet.total_proved_eps ?? measurements.proved_eps`, and a
  // `sheet.rows` the server never sends), which made "where did this number come from" have
  // two answers. e2e/console.spec.ts resolves every `data-source` against the real run stream.
  const num = (v: unknown) => (typeof v === 'number' ? v : null)
  const provedEps = num(sheet?.total_proved_eps)
  const auditedEps = num(sheet?.total_audited_eps)
  const ceiling = audit?.ceiling ?? null
  const correlationError = m?.correlation_error ?? null
  const rows = num(sheet?.num_rows)
  const ledgerCount = ledger?.count ?? null
  const ledgerVerified = ledger?.verified ?? null

  // Honesty determination: Did proved eps fall within the audit reach?
  const auditInformative =
    typeof provedEps === 'number' && typeof ceiling === 'number'
      ? provedEps <= ceiling
      : null

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
      {/* 1. Privacy spent */}
      <KpiCard
        id="privacy-spent"
        source="run.sheet.total_proved_eps"
        keyLabel="PRIVACY · PROVED"
        value={typeof provedEps === 'number' ? provedEps.toFixed(3) : null}
        unit="ε"
        laymanLabel="Privacy budget charged to this release"
        isOpen={activeExplainer === 'epsilon'}
        onClick={() => onOpenExplainer('epsilon')}
      />

      {/* 2. Privacy audited */}
      <KpiCard
        id="privacy-audited"
        source="run.sheet.total_audited_eps"
        keyLabel="PRIVACY · AUDITED"
        value={typeof auditedEps === 'number' ? auditedEps.toFixed(3) : null}
        unit="ε"
        laymanLabel="What an attacker simulation detected"
        isOpen={activeExplainer === 'ceiling' && activeExplainer !== null}
        onClick={() => onOpenExplainer('ceiling')}
      />

      {/* 3. Audit reach */}
      <KpiCard
        id="audit-reach"
        source="run.audit.ceiling"
        keyLabel="AUDIT · CEILING"
        value={typeof ceiling === 'number' ? ceiling.toFixed(2) : null}
        unit="ε max"
        laymanLabel="The most this audit could have caught"
        chip={
          auditInformative !== null
            ? {
                text: auditInformative ? 'IN RANGE' : 'OVER REACH',
                variant: auditInformative ? 'verify' : 'seal',
              }
            : undefined
        }
        isOpen={activeExplainer === 'ceiling'}
        onClick={() => onOpenExplainer('ceiling')}
      />

      {/* 4. Faithfulness */}
      <KpiCard
        id="faithfulness"
        source="run.measurements.correlation_error"
        keyLabel="UTILITY · FIDELITY"
        value={typeof correlationError === 'number' ? correlationError.toFixed(3) : null}
        unit="MAE"
        laymanLabel="Pairwise correlation shift from real data"
        isOpen={activeExplainer === 'faithfulness'}
        onClick={() => onOpenExplainer('faithfulness')}
      />

      {/* 5. Records */}
      <KpiCard
        id="records"
        source="run.sheet.num_rows"
        keyLabel="RELEASE · SIZE"
        value={typeof rows === 'number' ? rows.toLocaleString() : null}
        unit="rows"
        laymanLabel="Records in the released synthetic table"
        isOpen={activeExplainer === 'aim'}
        onClick={() => onOpenExplainer('aim')}
      />

      {/* 6. Ledger height */}
      <KpiCard
        id="ledger-height"
        source="ledger.count"
        keyLabel="LEDGER · HEIGHT"
        value={typeof ledgerCount === 'number' ? ledgerCount : null}
        unit="sealed"
        laymanLabel="Entries committed in the hash chain"
        isOpen={activeExplainer === 'ledger'}
        onClick={() => onOpenExplainer('ledger')}
      />

      {/* 7. Seal */}
      <KpiCard
        id="seal"
        source="ledger.verified"
        keyLabel="INTEGRITY · SEAL"
        value={ledgerVerified === null ? null : ledgerVerified ? 'INTACT' : 'BROKEN'}
        laymanLabel="Is the cryptographic chain intact now?"
        chip={
          ledgerVerified !== null
            ? {
                text: ledgerVerified ? 'VERIFIED' : 'CRACKED',
                variant: ledgerVerified ? 'verify' : 'seal',
              }
            : undefined
        }
        isOpen={activeExplainer === 'seal'}
        onClick={() => onOpenExplainer('seal')}
      />
    </div>
  )
}
