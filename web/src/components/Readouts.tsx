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

      {undetected && (
        <div className="mt-3 border-t border-stage-line pt-3">
          <p className="text-[11px] leading-relaxed text-graphite-faint">
            <span className="font-mono text-audited-lift">ε_audited = 0</span> means the audit
            found no statistically significant leakage
            {audit ? ` (p = ${audit.p_value.toFixed(3)}, ${audit.num_members} canaries)` : ''} —
            not that leakage is absent. This auditor&rsquo;s detection floor has not yet been
            measured, so the gap above is currently uninformative.
          </p>
        </div>
      )}
    </div>
  )
}

/** Budget drawdown, updated live from the accountant as each stage charges. */
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
  return (
    <div className="panel p-4">
      <div className="flex items-baseline justify-between">
        <span className="label">Budget drawdown</span>
        <span className="tnum font-mono text-xs text-graphite-soft dark:text-bone">
          {spent.toFixed(3)} / {total.toFixed(2)}
        </span>
      </div>
      <div className="relative mt-3 h-2 overflow-hidden rounded-sm bg-bone-deep dark:bg-stage-deep">
        <motion.div
          className="absolute inset-y-0 left-0 bg-proved"
          initial={false}
          animate={{ width: `${frac * 100}%` }}
          transition={{ type: 'spring', stiffness: 120, damping: 22 }}
        />
      </div>
      <p className="mt-2 font-mono text-[11px] text-graphite-faint">
        {stage ? `charging: ${stage}` : 'idle'}
      </p>
    </div>
  )
}

/** A single labelled measurement. `hint` carries the caveat, never the headline. */
export function Metric({
  label,
  value,
  hint,
  tone = 'neutral',
}: {
  label: string
  value: string
  hint?: string
  tone?: 'neutral' | 'proved' | 'audited' | 'warn'
}) {
  const toneClass = {
    neutral: 'text-graphite dark:text-bone',
    proved: 'text-proved dark:text-proved-lift',
    audited: 'text-audited dark:text-audited-lift',
    warn: 'text-signal-warn',
  }[tone]

  return (
    <div className="panel p-4">
      <span className="label">{label}</span>
      <div className={`tnum mt-1.5 font-mono text-2xl ${toneClass}`}>{value}</div>
      {hint && <p className="mt-1.5 text-[11px] leading-snug text-graphite-faint">{hint}</p>}
    </div>
  )
}
