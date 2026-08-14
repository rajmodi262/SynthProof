import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { api } from '@/lib/api'
import type { LedgerState } from '@/types'

/**
 * The append-only spend ledger, and the tamper demonstration.
 *
 * Two things are worth saying out loud in the UI, because both are easy to overstate:
 *
 *  1. The chain is tamper-EVIDENT, not tamper-proof. Anyone holding the signing key can
 *     rewrite history and re-sign it. Key custody is an organisational control.
 *  2. The signing key is currently generated in memory per process and never persisted, so
 *     a restart makes old signatures unverifiable. The badge says so rather than implying a
 *     durable guarantee.
 */
export function LedgerChain({
  ledger,
  onRefresh,
}: {
  ledger: LedgerState | null
  onRefresh: () => void
}) {
  const [breakFrom, setBreakFrom] = useState<number | null>(null)
  const [busy, setBusy] = useState(false)

  const entries = ledger?.entries ?? []

  async function tamper(entryId: string, index: number) {
    setBusy(true)
    try {
      const res = await api.tamper(entryId)
      setBreakFrom(res.broken_from_index ?? index)
      onRefresh()
    } finally {
      setBusy(false)
    }
  }

  async function reset() {
    setBusy(true)
    try {
      await api.resetLedger()
      setBreakFrom(null)
      onRefresh()
    } finally {
      setBusy(false)
    }
  }

  const verified = ledger?.verified ?? true

  return (
    <section className="panel p-5">
      <header className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="font-display text-xl">Privacy budget ledger</h3>
          <p className="mt-0.5 text-[12px] text-graphite-faint">
            Every release charged, hash-chained and Ed25519-signed.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`flex items-center gap-1.5 rounded-sm border px-2 py-1 font-mono text-2xs uppercase tracking-[0.1em] ${
              verified
                ? 'border-signal-ok/40 text-signal-ok'
                : 'border-signal-bad/50 bg-signal-bad/10 text-signal-bad'
            }`}
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${verified ? 'bg-signal-ok' : 'bg-signal-bad'}`}
            />
            {verified ? 'chain verified' : 'chain broken'}
          </span>
          {entries.length > 0 && (
            <button className="btn-ghost !px-2.5 !py-1 !text-xs" onClick={reset} disabled={busy}>
              Reset
            </button>
          )}
        </div>
      </header>

      {entries.length > 0 && (
        <div className="mb-4 flex flex-wrap gap-x-6 gap-y-1 border-y border-bone-edge py-2 dark:border-stage-line">
          <span className="font-mono text-[11px] text-graphite-faint">
            releases <span className="tnum text-graphite dark:text-bone">{ledger?.count}</span>
          </span>
          <span className="font-mono text-[11px] text-graphite-faint">
            cumulative ε{' '}
            <span className="tnum text-proved dark:text-proved-lift">
              {ledger?.total_eps_spent.toFixed(3)}
            </span>
          </span>
          <span className="truncate font-mono text-[11px] text-graphite-faint">
            head <span className="text-graphite dark:text-bone">{ledger?.head.slice(0, 20)}…</span>
          </span>
        </div>
      )}

      {!entries.length ? (
        <p className="py-6 text-center font-mono text-[11px] text-graphite-faint">
          No spends recorded. Run a release to append the first block.
        </p>
      ) : (
        <ol className="thin-scroll max-h-72 space-y-1.5 overflow-y-auto pr-1">
          {entries.map((e, i) => {
            const broken = breakFrom !== null && i >= breakFrom
            return (
              <motion.li
                key={e.entry_id}
                layout
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                className={`group relative rounded-sm border p-2.5 transition-colors ${
                  broken
                    ? 'border-signal-bad/50 bg-signal-bad/[0.06]'
                    : 'border-bone-edge bg-bone-deep/40 dark:border-stage-line dark:bg-stage-deep/60'
                }`}
              >
                <div className="flex items-baseline justify-between gap-3">
                  <span className="tnum font-mono text-[11px] text-graphite-faint">
                    #{String(i + 1).padStart(2, '0')}
                  </span>
                  <span className="flex-1 truncate font-sans text-[13px]">{e.run_id}</span>
                  <span className="tnum font-mono text-[12px] text-proved dark:text-proved-lift">
                    ε {e.eps_spent.toFixed(3)}
                  </span>
                </div>

                <div className="mt-1 flex items-center gap-2 font-mono text-[10px] text-graphite-faint">
                  <span className="truncate">prev {e.prev_hash.slice(0, 12)}…</span>
                  <span className="text-graphite-faint/50">→</span>
                  <span className="truncate">this {e.hash.slice(0, 12)}…</span>
                </div>

                <AnimatePresence>
                  {broken && (
                    <motion.p
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                      className="mt-1.5 font-mono text-[10px] text-signal-bad"
                    >
                      {i === breakFrom
                        ? 'altered — recomputed hash no longer matches'
                        : 'invalid — commits to a hash that changed'}
                    </motion.p>
                  )}
                </AnimatePresence>

                {!broken && (
                  <button
                    onClick={() => tamper(e.entry_id, i)}
                    disabled={busy}
                    className="absolute right-2 top-2 rounded-sm border border-bone-edge bg-[#FAF9F6] px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.1em] text-graphite-faint opacity-0 transition-opacity hover:border-signal-bad hover:text-signal-bad focus-visible:opacity-100 group-hover:opacity-100 dark:border-stage-line dark:bg-stage"
                  >
                    Tamper
                  </button>
                )}
              </motion.li>
            )
          })}
        </ol>
      )}

      <p className="mt-4 border-t border-bone-edge pt-3 text-[11px] leading-relaxed text-graphite-faint dark:border-stage-line">
        Hover a block and press <span className="font-mono">Tamper</span> to rewrite its ε
        directly in SQLite, bypassing the append path. Verification fails from that block
        onward, because each block commits to its predecessor&rsquo;s SHA-256.{' '}
        <strong className="font-medium text-graphite-soft dark:text-bone">
          This shows tamper-evidence, not tamper-proofing
        </strong>{' '}
        — a holder of the signing key can rewrite and re-sign freely. The key is also
        generated per process and not yet persisted, so signatures do not survive a restart.
      </p>
    </section>
  )
}
