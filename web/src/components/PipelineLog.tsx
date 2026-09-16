import { AnimatePresence, motion } from 'framer-motion'
import { STAGE_ORDER, type StageEvent, type StageName } from '@/types'

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
  attack_domias: 'Density-ratio attack (DOMIAS)',
}

function chargedAmount(e: StageEvent, previousSpend: number): number | null {
  const spend = e.eps_spent
  if (typeof spend !== 'number') return null
  const delta = spend - previousSpend
  return delta > 1e-9 ? delta : null
}

function summarise(e: StageEvent): string {
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
    case 'attack_domias':
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

  let runningSpend = 0
  const charges = stages.map((s) => {
    const delta = chargedAmount(s, runningSpend)
    if (typeof s.eps_spent === 'number') runningSpend = s.eps_spent
    return delta
  })

  return (
    <div className="relative flex h-full flex-col rounded-xl border border-line bg-card p-4 shadow-e0">
      <div className="mb-3 flex items-center justify-between border-b border-line pb-2">
        <div className="flex items-center gap-1.5">
          <span className="font-mono text-[10px] font-medium uppercase tracking-[0.14em] text-faint">
            AUDIT TIMELINE
          </span>
          <span className="font-sans text-xs font-semibold text-ink">Streamed Execution</span>
        </div>
        {running && (
          <span className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wider text-brass font-medium">
            <span className="h-1.5 w-1.5 rounded-full bg-brass animate-pulse" />
            Executing
          </span>
        )}
      </div>

      <ol
        className="thin-scroll flex-1 space-y-0 overflow-y-auto pr-1"
        aria-live="polite"
        aria-relevant="additions"
        aria-busy={running}
      >
        <AnimatePresence initial={false}>
          {stages.map((s, i) => (
            <motion.li
              key={`${s.stage}-${i}`}
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.18, ease: 'easeOut' }}
              className="border-b border-line/50 py-2.5 last:border-0"
            >
              <div className="flex items-baseline gap-2">
                <span className="tnum font-mono text-[11px] font-medium text-faint">
                  {String(i + 1).padStart(2, '0')}
                </span>
                <span className="flex-1 font-sans text-xs font-medium text-ink">
                  {STAGE_LABELS[s.stage] ?? s.stage}
                </span>
                {charges[i] !== null && (
                  <span
                    className="tnum rounded border border-brass/40 bg-brass/10 px-1.5 py-0.5 font-mono text-[9px] font-medium uppercase tracking-wider text-brass"
                    title="Increase in composed epsilon attributable to this stage"
                  >
                    +{charges[i]!.toFixed(3)} ε
                  </span>
                )}
              </div>
              <p className="mt-0.5 pl-6 font-mono text-[11px] leading-relaxed text-muted">
                {summarise(s)}
              </p>
            </motion.li>
          ))}
        </AnimatePresence>

        {running && nextPending && (
          <li className="py-2.5">
            <div className="flex items-baseline gap-2 opacity-50">
              <span className="tnum font-mono text-[11px] text-faint">
                {String(stages.length + 1).padStart(2, '0')}
              </span>
              <span className="flex-1 font-sans text-xs text-muted">
                {STAGE_LABELS[nextPending]}
              </span>
            </div>
            <div className="mt-1.5 ml-6 h-0.5 overflow-hidden rounded-full bg-paper-2">
              <div className="h-full w-1/3 animate-pulse bg-brass/80" />
            </div>
          </li>
        )}

        {!stages.length && !running && (
          <li className="py-8 text-center font-mono text-[11px] text-faint">
            No pipeline run recorded. Trigger a release to stream stages.
          </li>
        )}
      </ol>
    </div>
  )
}
