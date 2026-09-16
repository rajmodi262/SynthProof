import type { AuditResult, Measurements } from '@/types'

interface AuditRangeProps {
  measurements: Measurements | null
  audit: AuditResult | null
  targetEps: number
  onOpenExplainer: () => void
}

export function AuditRange({ measurements, audit, targetEps, onOpenExplainer }: AuditRangeProps) {
  const proved = measurements?.proved_eps ?? targetEps
  const ceiling = audit?.ceiling ?? null
  const audited = measurements?.audited_eps ?? audit?.audited_eps ?? 0

  // The ceiling marks the detection frontier
  const maxScale = Math.max(proved * 1.25, (ceiling ?? 3) * 1.15, 2.0)
  const provedPct = Math.min(100, Math.max(0, (proved / maxScale) * 100))
  const ceilingPct = ceiling ? Math.min(100, Math.max(0, (ceiling / maxScale) * 100)) : null
  const auditedPct = Math.min(100, Math.max(0, (audited / maxScale) * 100))

  const isExceeded = ceiling !== null && proved > ceiling
  const isInformative = audit?.detects_leak_above !== null

  return (
    <div className="relative rounded-xl border border-line bg-card p-4 shadow-e0">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <span className="font-mono text-[10px] font-medium uppercase tracking-[0.14em] text-faint">
            AUDIT RANGE
          </span>
          <span className="font-sans text-xs font-semibold text-ink">Detection Reach (MIQE)</span>
        </div>
        <button
          type="button"
          onClick={onOpenExplainer}
          title="Audit ceiling and detection resolution theorem"
          className="text-faint hover:text-brass"
        >
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </button>
      </div>

      {/* Horizontal gauge track */}
      <div className="mt-4">
        <div className="relative h-6 w-full rounded-md border border-line bg-paper-2 overflow-hidden shadow-inset">
          {/* Detectable zone under ceiling */}
          {ceilingPct !== null && ceiling !== null && (
            <div
              className="absolute left-0 top-0 bottom-0 bg-verify/10 border-r border-verify/40"
              style={{ width: `${ceilingPct}%` }}
              title={`Empirically verifiable range up to ε = ${ceiling.toFixed(2)}`}
            />
          )}

          {/* Unverifiable hatched seal zone beyond ceiling */}
          {ceilingPct !== null && (
            <div
              className="absolute top-0 bottom-0 right-0 bg-seal/10"
              style={{
                left: `${ceilingPct}%`,
                backgroundImage: 'repeating-linear-gradient(45deg, transparent, transparent 4px, rgba(196, 99, 92, 0.2) 4px, rgba(196, 99, 92, 0.2) 8px)',
              }}
              title="Beyond empirical auditor reach"
            />
          )}

          {/* Audited lower bound indicator */}
          {measurements && (
            <div
              className="absolute top-1 bottom-1 w-1 bg-verify rounded-full z-10"
              style={{ left: `${auditedPct}%` }}
              title={`Audited lower bound: ε = ${audited.toFixed(3)}`}
            />
          )}

          {/* Proved epsilon needle/marker */}
          {measurements && (
            <div
              className={`absolute top-0 bottom-0 w-1.5 z-20 ${
                isExceeded ? 'bg-seal' : 'bg-brass'
              }`}
              style={{ left: `calc(${provedPct}% - 3px)` }}
              title={`Proved upper bound: ε = ${proved.toFixed(3)}`}
            />
          )}
        </div>

        {/* Axis labels */}
        <div className="mt-1.5 flex justify-between font-mono text-[10px] text-faint">
          <span>0.0</span>
          {ceiling !== null && (
            <span style={{ marginLeft: `${ceilingPct! - 20}%` }} className="text-muted font-medium">
              Ceiling: {ceiling.toFixed(2)}
            </span>
          )}
          <span>{maxScale.toFixed(1)}</span>
        </div>
      </div>

      {/* Honesty readout / verdict */}
      <div className="mt-3 rounded-lg border border-line/80 bg-paper-2/50 p-2.5">
        <div className="flex items-start gap-2">
          <span className="text-sm">
            {isExceeded ? '⚠️' : isInformative ? '✓' : 'ℹ️'}
          </span>
          <div className="text-[11px] leading-tight">
            {isExceeded ? (
              <p className="font-medium text-seal">
                Proved ε ({proved.toFixed(2)}) exceeds audit reach ({ceiling?.toFixed(2)}). The audit could NOT have certified this claim.
              </p>
            ) : ceiling !== null ? (
              <p className="font-medium text-verify">
                Proved ε is within the empirical detection ceiling ({ceiling.toFixed(2)}).
              </p>
            ) : (
              <p className="text-muted">
                Run a release to compute the empirical detection frontier.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
