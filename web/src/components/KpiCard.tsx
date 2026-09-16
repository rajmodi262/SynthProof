interface KpiCardProps {
  id: string
  keyLabel: string
  value: string | number | null
  unit?: string
  laymanLabel: string
  chip?: {
    text: string
    variant: 'verify' | 'seal' | 'neutral' | 'brass'
  }
  isOpen?: boolean
  onClick: () => void
}

export function KpiCard({
  id,
  keyLabel,
  value,
  unit,
  laymanLabel,
  chip,
  isOpen,
  onClick,
}: KpiCardProps) {
  const hasValue = value !== null && value !== undefined && value !== ''

  return (
    <button
      type="button"
      id={`kpi-card-${id}`}
      onClick={onClick}
      aria-haspopup="dialog"
      aria-expanded={isOpen}
      className={`group relative flex min-h-[136px] w-full flex-col justify-between rounded-xl border bg-card p-5 text-left transition-all duration-150 focus:outline-none ${
        isOpen
          ? 'border-brass bg-paper-2/40 shadow-e1 ring-1 ring-brass'
          : 'border-line shadow-e0 hover:-translate-y-0.5 hover:border-brass/50 hover:shadow-e1'
      }`}
    >
      {/* Top eyebrow row */}
      <div className="flex w-full items-center justify-between">
        <span className="font-mono text-[11px] font-medium uppercase tracking-[0.14em] text-faint">
          {keyLabel}
        </span>
        <span
          className={`flex h-4 w-4 items-center justify-center transition-colors ${
            isOpen ? 'text-brass' : 'text-faint group-hover:text-brass'
          }`}
          title="Inspect mechanism and proof math"
        >
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        </span>
      </div>

      {/* Main hero numeral */}
      <div className="my-1.5 flex items-baseline gap-1.5">
        <span
          className={`font-display text-4xl leading-none tracking-tight sm:text-5xl ${
            hasValue ? 'text-ink tnum' : 'text-faint'
          }`}
        >
          {hasValue ? value : '—'}
        </span>
        {unit && hasValue && (
          <span className="font-mono text-xs font-medium text-muted">
            {unit}
          </span>
        )}
      </div>

      {/* Layman label + micro-state chip */}
      <div className="flex w-full flex-wrap items-center justify-between gap-1.5">
        <p className="max-w-[85%] font-sans text-[12px] leading-tight text-muted">
          {laymanLabel}
        </p>
        {chip && (
          <span
            className={`inline-flex items-center rounded-full px-2 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wider ${
              chip.variant === 'verify'
                ? 'bg-verify-bg text-verify border border-verify/30'
                : chip.variant === 'seal'
                ? 'bg-seal-bg text-seal border border-seal/30'
                : chip.variant === 'brass'
                ? 'bg-brass/10 text-brass border border-brass/30'
                : 'bg-paper-2 text-muted border border-line'
            }`}
          >
            {chip.text}
          </span>
        )}
      </div>
    </button>
  )
}
