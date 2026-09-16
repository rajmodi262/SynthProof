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

  const provedEps = sheet?.total_proved_eps ?? m?.proved_eps ?? null
  const auditedEps = sheet?.total_audited_eps ?? m?.audited_eps ?? null
  const ceiling = audit?.ceiling ?? null
  const correlationError = m?.correlation_error ?? null
  const rows = sheet?.num_rows ?? (sheet?.rows as number | undefined) ?? null
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
