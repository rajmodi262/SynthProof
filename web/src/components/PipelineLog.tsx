import { AnimatePresence, motion } from 'framer-motion'
import { STAGE_ORDER, type StageEvent, type StageName } from '@/types'

/**
 * The pipeline, stage by stage, as the server finishes each one.
 *
 * These arrive over SSE from the real `run_cell` callback, so a stage appears when it has
 * genuinely completed rather than on a timer. That matters here more than it usually would:
 * the argument this project makes is that nothing reads the sensitive table without charging
 * the accountant, and this log is where a viewer can watch that happen.
 */

const STAGE_LABELS: Record<StageName, string> = {
  split: 'Split fit / holdout',
  budget: 'Allocate budget',
  canaries: 'Plant canaries',
  profile: 'DP domain profile',
  fit: 'Fit mechanism',
  generate: 'Sample synthetic',
  audit: 'Canary audit',
  utility_fit: 'Re-fit without canaries',
  utility: 'Downstream utility',
  attack: 'Membership inference',
}

/**
 * Whether a stage actually charged the accountant, read from the stage payload.
 *
 * This was a hardcoded `Set(['profile', 'fit'])`. That is a client-side assertion about
 * privacy accounting — the one class of claim this project exists to stop anyone making
 * without evidence. If a future stage started charging, or `profile` stopped, the badge
 * would keep saying whatever the constant said. The server reports `eps_spent`, so the
 * badge is derived from a rise in it rather than from a guess.
 */
function chargedAmount(e: StageEvent, previousSpend: number): number | null {
  const spend = e.eps_spent
  if (typeof spend !== 'number') return null
  const delta = spend - previousSpend
  return delta > 1e-9 ? delta : null
}

function summarise(e: StageEvent): string {
  // Stage payloads are open-ended (`[key: string]: unknown`), so every field is narrowed
  // before use rather than trusted. A missing field renders as an em dash instead of
  // "undefined" leaking into the console.
  const n = (k: string, d = 3): string => {
    const v = e[k]
    return typeof v === 'number' ? v.toFixed(d) : '—'
  }
  const i = (k: string): string => {
    const v = e[k]
    return typeof v === 'number' || typeof v === 'string' ? String(v) : '—'
  }

  switch (e.stage) {
    case 'split':
      return `${i('fit_rows')} fit · ${i('holdout_rows')} holdout`
    case 'budget':
      return `profile ${n('profile_eps')} + synthesis ${n('synthesis_eps')}`
    case 'canaries':
      return `${i('planted')} planted · ${i('holdout')} held out as null`
    case 'profile':
      return `ε spent ${n('eps_spent')} · ${i('public_ranges')} public ranges · ${i('suppressed_categories')} rare categories suppressed`
    case 'fit':
      return `ε spent ${n('eps_spent')} · ${i('charges')} charges to the accountant`
    case 'generate':
      return `${i('rows')} synthetic rows`
    case 'utility_fit':
      return e.source === 'clean_fit'
        ? 'second fit on the clean split, so utility is measured canary-free'
        : 'reusing the canary-trained fit — utility figures are contaminated'
    case 'audit':
      return `ε audited ${n('audited_eps')} · TPR ${n('tpr', 2)} vs FPR ${n('fpr', 2)} · p ${n('p_value')}`
    case 'utility':
      return `TSTR ${n('tstr_f1')} vs TRTR ${n('trtr_f1')}`
    case 'attack':
      return `AUC ${n('auc')} · TPR@1%FPR ${n('tpr_at_1pct_fpr')}`
    default:
      return ''
  }
}

export function PipelineLog({
  stages,
  running,
}: {
  stages: StageEvent[]
  running: boolean
}) {
  const seen = new Set(stages.map((s) => s.stage))
  const nextPending = STAGE_ORDER.find((s) => !seen.has(s))

  // Running spend, so each stage's badge reflects what it actually cost.
  let runningSpend = 0
  const charges = stages.map((s) => {
    const delta = chargedAmount(s, runningSpend)
    if (typeof s.eps_spent === 'number') runningSpend = s.eps_spent
    return delta
  })

  return (
    <div className="display flex h-full flex-col p-5">
      <div className="mb-4 flex items-center justify-between">
        <span className="label text-graphite-faint">Pipeline</span>
        {running && (
          <span className="flex items-center gap-1.5 font-mono text-2xs uppercase tracking-[0.12em] text-audited-lift">
            <span className="h-1.5 w-1.5 animate-blink rounded-full bg-audited-lift" />
            running
          </span>
        )}
      </div>

      {/* The log updates as the run streams. Without a live region a screen-reader user
          gets silence for the whole run and then a finished page. */}
      <ol
        className="thin-scroll flex-1 space-y-0 overflow-y-auto"
        aria-live="polite"
        aria-relevant="additions"
        aria-busy={running}
      >
        <AnimatePresence initial={false}>
          {stages.map((s, i) => (
            <motion.li
              key={`${s.stage}-${i}`}
              initial={{ opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.22, ease: 'easeOut' }}
              className="border-b border-stage-line/60 py-2.5 last:border-0"
            >
              <div className="flex items-baseline gap-2">
                <span className="tnum font-mono text-2xs text-graphite-faint">
                  {String(i + 1).padStart(2, '0')}
                </span>
                <span className="flex-1 font-sans text-[13px] text-bone">
                  {STAGE_LABELS[s.stage] ?? s.stage}
                </span>
                {charges[i] !== null && (
                  <span
                    className="tnum rounded-[2px] border border-proved-lift/40 px-1 font-mono text-[9px] uppercase tracking-[0.1em] text-proved-lift"
                    title="Increase in composed epsilon attributable to this stage"
                  >
                    charged +{charges[i]!.toFixed(3)}
                  </span>
                )}
              </div>
              <p className="mt-0.5 pl-6 font-mono text-[11px] leading-relaxed text-graphite-faint">
                {summarise(s)}
              </p>
            </motion.li>
          ))}
        </AnimatePresence>

        {running && nextPending && (
          <li className="py-2.5">
            <div className="flex items-baseline gap-2 opacity-45">
              <span className="tnum font-mono text-2xs text-graphite-faint">
                {String(stages.length + 1).padStart(2, '0')}
              </span>
              <span className="flex-1 font-sans text-[13px] text-bone">
                {STAGE_LABELS[nextPending]}
              </span>
            </div>
            <div className="mt-2 ml-6 h-px overflow-hidden bg-stage-line">
              <div className="h-full w-1/3 animate-sweep bg-audited-lift/70" />
            </div>
          </li>
        )}

        {!stages.length && !running && (
          <li className="py-8 text-center font-mono text-[11px] text-graphite-faint">
            No run yet. Choose a mechanism and a budget, then run a release.
          </li>
        )}
      </ol>
    </div>
  )
}
