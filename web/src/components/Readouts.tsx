import { motion } from 'framer-motion'
import type { AuditResult, Measurements } from '@/types'

/**
 * The gap between the formal upper bound and the empirical lower bound, drawn to scale.
 *
 * This is the project's whole thesis rendered as one component. The band is the region no
 * evidence currently occupies: privacy loss is provably no worse than ε_proved, and was
 * measured to be at least ε_audited. Everything in between is unknown, and how wide it is
 * says either "the bound is loose" or "the attack is weak" — which is exactly the question
 * the discussion chapter has to answer.
 */
export function BoundsGauge({
  measurements,
  audit,
  targetEps,
}: {
  measurements: Measurements | null
  audit: AuditResult | null
  targetEps: number
}) {
  const proved = measurements?.proved_eps ?? 0
  const audited = measurements?.audited_eps ?? 0
  const scale = Math.max(proved, targetEps, 1) * 1.12
  const pct = (v: number) => `${Math.min(100, (v / scale) * 100)}%`
  const undetected = audited === 0 && !!measurements

  return (
    <div className="display p-5">
      <div className="mb-4 flex items-baseline justify-between">
        <span className="label text-graphite-faint">Privacy loss, both sides</span>
        <span className="label text-graphite-faint">δ = 1e-5</span>
      </div>

      <div className="relative h-16">
        {/* axis */}
        <div className="absolute inset-x-0 top-9 h-px bg-stage-line" />

        {/* the unverified gap */}
        <motion.div
          className="absolute top-[26px] h-4 rounded-[1px]"
          style={{
            background:
              'repeating-linear-gradient(115deg, rgba(143,138,240,0.20) 0 6px, rgba(143,138,240,0.05) 6px 12px)',
            borderLeft: '1px solid rgba(232,150,76,0.7)',
            borderRight: '1px solid rgba(143,138,240,0.9)',
          }}
          initial={false}
          animate={{ left: pct(audited), width: pct(Math.max(0, proved - audited)) }}
          transition={{ type: 'spring', stiffness: 90, damping: 20 }}
        />

        {/* The auditor's ceiling. Above this line the instrument physically cannot report,
            regardless of how much the mechanism leaks. Drawing it is what stops the gap
            from being read as evidence about the mechanism. */}
        {audit && audit.ceiling < scale && (
          <div
            className="absolute top-4 flex -translate-x-1/2 flex-col items-center"
            style={{ left: pct(audit.ceiling) }}
          >
            <div
              className="h-9 w-px"
              style={{
                backgroundImage:
                  'repeating-linear-gradient(to bottom, #8A93A6 0 3px, transparent 3px 6px)',
              }}
            />
            <span className="mt-1 whitespace-nowrap font-mono text-[9px] uppercase tracking-[0.1em] text-graphite-faint">
              audit ceiling
            </span>
          </div>
        )}

        {/* audited marker */}
        <motion.div
          className="absolute top-5 flex -translate-x-1/2 flex-col items-center"
          initial={false}
          animate={{ left: pct(audited) }}
          transition={{ type: 'spring', stiffness: 90, damping: 20 }}
        >
          <div className="h-7 w-[2px] bg-audited-lift" />
          <span className="tnum mt-1 font-mono text-[11px] text-audited-lift">
            {audited.toFixed(2)}
          </span>
        </motion.div>

        {/* proved marker */}
        <motion.div
          className="absolute top-5 flex -translate-x-1/2 flex-col items-center"
          initial={false}
          animate={{ left: pct(proved) }}
          transition={{ type: 'spring', stiffness: 90, damping: 20 }}
        >
          <div className="h-7 w-[2px] bg-proved-lift" />
          <span className="tnum mt-1 font-mono text-[11px] text-proved-lift">
            {proved.toFixed(3)}
          </span>
        </motion.div>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-3 border-t border-stage-line pt-3">
        <div>
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-audited-lift" />
            <span className="label !tracking-[0.1em] text-graphite-faint">ε audited</span>
          </div>
          <p className="mt-1 text-[11px] leading-snug text-graphite-faint">
            Measured lower bound from held-out canaries, 95% Clopper-Pearson.
          </p>
        </div>
        <div>
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-proved-lift" />
            <span className="label !tracking-[0.1em] text-graphite-faint">ε proved</span>
          </div>
          <p className="mt-1 text-[11px] leading-snug text-graphite-faint">
            Formal upper bound, RDP composition via dp_accounting.
          </p>
        </div>
      </div>

      {undetected && audit && (
        <div className="mt-3 border-t border-stage-line pt-3">
          <p className="text-[11px] leading-relaxed text-graphite-faint">
            <span className="font-mono text-audited-lift">ε_audited = 0</span> means the audit
            found no statistically significant leakage (p = {(audit.p_value ?? 0).toFixed(3)},{' '}
            {audit.num_members ?? (audit as any).num_canaries ?? '—'} canaries) — <strong className="font-medium">not</strong> that
            leakage is absent.
          </p>
          <p className="mt-2 text-[11px] leading-relaxed text-graphite-faint">
            At this canary count the instrument cannot report above{' '}
            <span className="tnum font-mono text-bone">ε ≈ {(audit.ceiling ?? 0).toFixed(2)}</span>{' '}
            even against a release that is 100% verbatim training data
            {proved > (audit.ceiling ?? 0) && (
              <>
                , which is <strong className="font-medium text-bone">below the proved bound
                of {proved.toFixed(2)}</strong>. The gap above is therefore a property of the
                measurement, not of the mechanism
              </>
            )}
            .{' '}
            {audit.detects_leak_above !== null && audit.detects_leak_above !== undefined
              ? `It detects leakage above roughly ${(audit.detects_leak_above * 100).toFixed(0)}% verbatim copying.`
              : 'No leak level tested was reliably detectable at this count.'}
          </p>
        </div>
      )}
    </div>
  )
}

export function BudgetMeter({
  spent,
  total,
  stage,
}: {
  spent: number
  total: number
  stage: string | null
}) {
  const frac = total > 0 ? Math.min(1, spent / total) : 0
  const pct = (frac * 100).toFixed(1)
  return (
    <div className="glass-panel p-4.5">
      <div className="flex items-baseline justify-between">
        <div className="flex items-center gap-2">
          <span className="label">Budget Drawdown</span>
          <span className="rounded-full bg-proved/15 px-1.5 py-0.2 font-mono text-[9px] font-semibold text-proved dark:text-proved-lift">
            {pct}%
          </span>
        </div>
        <span className="tnum font-mono text-xs font-semibold text-graphite-soft dark:text-bone">
          {spent.toFixed(3)} <span className="font-normal text-graphite-faint">/</span> {total.toFixed(2)} ε
        </span>
      </div>
      <div className="relative mt-3 h-2.5 overflow-hidden rounded-full bg-bone-deep shadow-inner dark:bg-stage-deep">
        <motion.div
          className="absolute inset-y-0 left-0 bg-gradient-to-r from-proved via-[#6366f1] to-proved-lift shadow-sm"
          initial={false}
          animate={{ width: `${frac * 100}%` }}
          transition={{ type: 'spring', stiffness: 120, damping: 22 }}
        />
      </div>
      <div className="mt-2.5 flex items-center justify-between font-mono text-[11px]">
        <span className="flex items-center gap-1.5 text-graphite-faint">
          <span className={`h-1.5 w-1.5 rounded-full ${stage ? 'bg-proved animate-pulse' : 'bg-graphite-faint/50'}`} />
          <span>{stage ? `charging: ${stage}` : 'accountant idle'}</span>
        </span>
        <span className="text-[10px] text-graphite-faint">Composition: Sublinear RDP</span>
      </div>
    </div>
  )
}

/** A single labelled measurement card with modern glassmorphism. */
export function Metric({
  label,
  value,
  hint,
  tone = 'neutral',
  icon,
}: {
  label: string
  value: string
  hint?: string
  tone?: 'neutral' | 'proved' | 'audited' | 'warn'
  icon?: string
}) {
  const toneConfig = {
    neutral: {
      text: 'text-graphite dark:text-bone',
      border: 'border-bone-edge dark:border-stage-line',
      bg: '',
    },
    proved: {
      text: 'text-proved dark:text-proved-lift',
      border: 'border-proved/30 dark:border-proved/40',
      bg: 'hover:shadow-proved/10',
    },
    audited: {
      text: 'text-audited dark:text-audited-lift',
      border: 'border-audited/30 dark:border-audited/40',
      bg: 'hover:shadow-audited/10',
    },
    warn: {
      text: 'text-signal-warn',
      border: 'border-signal-warn/30 dark:border-signal-warn/40',
      bg: 'hover:shadow-signal-warn/10',
    },
  }[tone]

  return (
    <div className={`glass-panel p-4.5 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md ${toneConfig.border} ${toneConfig.bg}`}>
      <div className="flex items-center justify-between">
        <span className="label">{label}</span>
        {icon && <span className="text-sm">{icon}</span>}
      </div>
      <div className={`tnum mt-2 font-mono text-2xl font-semibold tracking-tight ${toneConfig.text}`}>
        {value}
      </div>
      {hint && (
        <p className="mt-2 text-[11px] leading-relaxed text-graphite-faint">
          {hint}
        </p>
      )}
    </div>
  )
}

