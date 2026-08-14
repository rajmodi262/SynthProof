import { motion } from 'framer-motion'
import type { AttackResult, AuditResult, NotImplementedAttack } from '@/types'

/**
 * What the adversaries actually achieved.
 *
 * Every figure here comes from the run response. Attacks that do not exist say so plainly
 * instead of rendering a verdict — an earlier console displayed four hardcoded "PASSED"
 * badges, one of them for an attack that was never written, and that is the single easiest
 * way for a demo to become dishonest.
 */

function Bar({ value, mid = 0.5, label }: { value: number; mid?: number; label: string }) {
  // Chance level is the reference, so the bar reads as "distance from chance" rather than
  // an absolute that always looks alarming.
  const above = value >= mid
  const magnitude = Math.min(1, Math.abs(value - mid) / mid)
  return (
    <div className="mt-2">
      <div className="relative h-1.5 rounded-sm bg-bone-deep dark:bg-stage-deep">
        <div className="absolute inset-y-0 left-1/2 w-px bg-graphite-faint/50" />
        <motion.div
          className={`absolute inset-y-0 rounded-sm ${above ? 'bg-audited' : 'bg-signal-ok'}`}
          initial={{ width: 0 }}
          animate={{
            width: `${magnitude * 50}%`,
            left: above ? '50%' : `${50 - magnitude * 50}%`,
          }}
          transition={{ type: 'spring', stiffness: 110, damping: 20 }}
        />
      </div>
      <p className="mt-1 font-mono text-[10px] text-graphite-faint">{label}</p>
    </div>
  )
}

export function AttackDossier({
  attack,
  audit,
  notImplemented,
}: {
  attack: AttackResult | null
  audit: AuditResult | null
  notImplemented: NotImplementedAttack[]
}) {
  return (
    <section className="panel p-5">
      <header className="mb-4">
        <h3 className="font-display text-xl">Attack dossier</h3>
        <p className="mt-0.5 text-[12px] text-graphite-faint">
          Measured adversary performance against this release. 0.5 AUC is chance.
        </p>
      </header>

      <div className="grid gap-3 sm:grid-cols-2">
        {/* Canary audit */}
        <div className="rounded-sm border-l-2 border-audited bg-bone-deep/40 p-3.5 dark:bg-stage-deep/60">
          <div className="flex items-baseline justify-between">
            <h4 className="font-sans text-sm font-medium">Canary auditor</h4>
            <span
              className={`font-mono text-2xs uppercase tracking-[0.1em] ${
                audit && audit.audited_eps > 0 ? 'text-signal-bad' : 'text-graphite-faint'
              }`}
            >
              {!audit ? 'not run' : audit.audited_eps > 0 ? 'leakage detected' : 'below floor'}
            </span>
          </div>
          {audit ? (
            <>
              <div className="tnum mt-2 font-mono text-lg text-audited dark:text-audited-lift">
                ε ≥ {audit.audited_eps.toFixed(3)}
              </div>
              <dl className="mt-2 space-y-0.5 font-mono text-[10px] text-graphite-faint">
                <div className="flex justify-between">
                  <dt>TPR / FPR</dt>
                  <dd className="tnum">
                    {audit.tpr.toFixed(2)} / {audit.fpr.toFixed(2)}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt>Fisher exact p</dt>
                  <dd className="tnum">{audit.p_value.toFixed(4)}</dd>
                </div>
                <div className="flex justify-between">
                  <dt>canaries</dt>
                  <dd className="tnum">
                    {audit.num_members} in / {audit.num_holdout} out
                  </dd>
                </div>
              </dl>
            </>
          ) : (
            <p className="mt-2 font-mono text-[11px] text-graphite-faint">awaiting a run</p>
          )}
        </div>

        {/* Distance MIA */}
        <div className="rounded-sm border-l-2 border-proved bg-bone-deep/40 p-3.5 dark:bg-stage-deep/60">
          <div className="flex items-baseline justify-between">
            <h4 className="font-sans text-sm font-medium">Distance MIA</h4>
            <span className="font-mono text-2xs uppercase tracking-[0.1em] text-graphite-faint">
              baseline
            </span>
          </div>
          {attack ? (
            <>
              <div className="tnum mt-2 font-mono text-lg text-proved dark:text-proved-lift">
                AUC {attack.auc.toFixed(3)}
              </div>
              <Bar value={attack.auc} label={`advantage ${attack.advantage.toFixed(3)} over chance`} />
              <dl className="mt-2 space-y-0.5 font-mono text-[10px] text-graphite-faint">
                <div className="flex justify-between">
                  <dt>TPR @ 1% FPR</dt>
                  <dd className="tnum">{attack.tpr_at_1pct_fpr.toFixed(4)}</dd>
                </div>
                <div className="flex justify-between">
                  <dt>members / non-members</dt>
                  <dd className="tnum">
                    {attack.num_train} / {attack.num_test}
                  </dd>
                </div>
              </dl>
              <p className="mt-2 text-[10px] leading-snug text-graphite-faint">{attack.note}</p>
            </>
          ) : (
            <p className="mt-2 font-mono text-[11px] text-graphite-faint">awaiting a run</p>
          )}
        </div>
      </div>

      {/* Honest absences */}
      <div className="mt-3 rounded-sm border border-dashed border-bone-edge p-3.5 dark:border-stage-line">
        <span className="label">Not implemented</span>
        <ul className="mt-2 space-y-1.5">
          {notImplemented.map((a) => (
            <li key={a.name} className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
              <span className="font-sans text-[13px] text-graphite-soft dark:text-bone">
                {a.name}
              </span>
              <span className="font-mono text-[10px] text-graphite-faint">— {a.reason}</span>
            </li>
          ))}
        </ul>
        {/* "two are built" was a literal that would go stale the moment an attack landed
            or was renamed — the same defect as any other hardcoded figure, and awkward in
            the one panel whose job is to be honest about what exists. Counted instead. */}
        <p className="mt-2.5 text-[11px] leading-snug text-graphite-faint">
          These are listed rather than hidden. {notImplemented.length} of the attacks named
          in the synopsis are not implemented, and this panel is where that stays visible.
        </p>
      </div>
    </section>
  )
}
