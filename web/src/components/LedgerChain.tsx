import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { api } from '@/lib/api'
import type { AttackType, LedgerState, TamperResult } from '@/types'

const ATTACK_OPTIONS: { type: AttackType; label: string; icon: string; blurb: string }[] = [
  {
    type: 'modify_eps',
    label: 'Retroactive Spend Manipulation',
    icon: '⚡',
    blurb: 'Rewrites historical epsilon budget directly in SQLite, breaking the row hash.',
  },
  {
    type: 'truncate',
    label: 'History Truncation Attack',
    icon: '✂️',
    blurb: 'Deletes recent spend blocks; caught by the signed checkpoint ledger_head.',
  },
  {
    type: 'corrupt_hash',
    label: 'Merkle Hash Corruption',
    icon: '💥',
    blurb: 'Injects fraudulent row hashes, breaking parent SHA-256 chain links.',
  },
  {
    type: 'corrupt_signature',
    label: 'Signature Forgery Attack',
    icon: '🔏',
    blurb: 'Corrupts Ed25519 signature bytes to simulate unauthenticated entries.',
  },
]

export function LedgerChain({
  ledger,
  onRefresh,
}: {
  ledger: LedgerState | null
  onRefresh: () => void
}) {
  const [selectedAttack, setSelectedAttack] = useState<AttackType>('modify_eps')
  const [attackResult, setAttackResult] = useState<TamperResult | null>(null)
  const [breakFrom, setBreakFrom] = useState<number | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const entries = ledger?.entries ?? []
  const verified: boolean | null = ledger ? ledger.verified : null

  async function executeAttack(entryId?: string, index?: number) {
    setBusy(true)
    setError(null)
    try {
      const res = await api.tamperAdvanced(selectedAttack, entryId)
      setAttackResult(res)
      setBreakFrom(res.broken_from_index ?? index ?? 0)
      onRefresh()
    } catch (err) {
      setError((err as Error).message || 'Adversarial attack request failed.')
    } finally {
      setBusy(false)
    }
  }

  async function reset() {
    setBusy(true)
    setError(null)
    try {
      await api.resetLedger()
      setAttackResult(null)
      setBreakFrom(null)
      onRefresh()
    } catch (err) {
      setError((err as Error).message || 'Reset request failed.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="panel p-5">
      <header className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-display text-xl">Privacy Budget Ledger</h3>
            <span className="rounded-full bg-proved/10 px-2 py-0.5 font-mono text-[10px] font-semibold text-proved dark:bg-proved/20 dark:text-proved-lift">
              RED-TEAM STUDIO
            </span>
          </div>
          <p className="mt-0.5 text-[12px] text-graphite-faint">
            Every release charged, hash-chained, and Ed25519-signed. Test multi-vector adversarial attacks.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`flex items-center gap-1.5 rounded-sm border px-2.5 py-1 font-mono text-2xs uppercase tracking-[0.1em] ${
              verified === null
                ? 'border-bone-edge text-graphite-faint dark:border-stage-line'
                : verified
                  ? 'border-signal-ok/40 bg-signal-ok/[0.06] text-signal-ok'
                  : 'border-signal-bad/50 bg-signal-bad/10 text-signal-bad'
            }`}
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                verified === null
                  ? 'bg-graphite-faint'
                  : verified
                    ? 'bg-signal-ok'
                    : 'bg-signal-bad animate-ping'
              }`}
            />
            {verified === null ? 'not checked' : verified ? 'chain integrity: verified' : 'attack detected: chain broken'}
          </span>
          {entries.length > 0 && (
            <button className="btn-ghost !px-2.5 !py-1 !text-xs" onClick={reset} disabled={busy}>
              Reset Chain
            </button>
          )}
        </div>
      </header>

      {/* Red-Team Attack Simulator Toolbar */}
      {entries.length > 0 && (
        <div className="mb-4 rounded-md border border-signal-bad/30 bg-signal-bad/[0.03] p-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="font-mono text-xs font-semibold text-graphite dark:text-bone">
              Adversarial Attack Simulator:
            </span>
            <div className="flex flex-wrap gap-1.5">
              {ATTACK_OPTIONS.map((opt) => (
                <button
                  key={opt.type}
                  onClick={() => setSelectedAttack(opt.type)}
                  className={`flex items-center gap-1 rounded px-2 py-1 font-mono text-[11px] transition-colors ${
                    selectedAttack === opt.type
                      ? 'bg-signal-bad text-white shadow-xs'
                      : 'border border-bone-edge bg-bone/40 text-graphite-faint hover:text-graphite dark:border-stage-line dark:bg-stage/40 dark:hover:text-bone'
                  }`}
                >
                  <span>{opt.icon}</span>
                  <span>{opt.label}</span>
                </button>
              ))}
            </div>
          </div>
          <div className="mt-2 flex items-center justify-between">
            <p className="text-[11px] text-graphite-faint">
              {ATTACK_OPTIONS.find((o) => o.type === selectedAttack)?.blurb}
            </p>
            <button
              onClick={() => executeAttack()}
              disabled={busy}
              className="btn-primary !border-signal-bad !bg-signal-bad !px-3 !py-1 !text-xs !text-white hover:!bg-signal-bad/90"
            >
              {busy ? 'Simulating Attack...' : `Launch ${ATTACK_OPTIONS.find((o) => o.type === selectedAttack)?.icon} Attack`}
            </button>
          </div>
        </div>
      )}

      {/* Live Adversarial Telemetry Banner */}
      <AnimatePresence>
        {attackResult && !attackResult.verified && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="mb-4 overflow-hidden rounded-md border border-signal-bad bg-signal-bad/[0.08] p-3 text-xs"
          >
            <div className="flex items-center justify-between">
              <span className="font-mono font-bold uppercase tracking-wider text-signal-bad">
                🚨 Cryptographic Attack Intercepted
              </span>
              <span className="font-mono text-[11px] text-signal-bad">
                Invalidated {attackResult.broken_count} downstream block(s)
              </span>
            </div>
            <p className="mt-1 font-medium text-graphite dark:text-bone">
              {attackResult.attack_description}
            </p>
            {attackResult.reason && (
              <div className="mt-2 rounded bg-black/10 p-2 font-mono text-[11px] text-signal-bad dark:bg-black/30">
                <strong>Failure Cause:</strong> {attackResult.reason}
              </div>
            )}
            <p className="mt-2 text-[11px] text-graphite-faint">
              {attackResult.explanation}
            </p>
          </motion.div>
        )}
      </AnimatePresence>

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

      {error && (
        <p
          role="alert"
          className="mb-3 rounded-sm border-l-2 border-signal-bad bg-signal-bad/[0.07] p-2.5 font-mono text-[11px] text-signal-bad"
        >
          {error}
        </p>
      )}

      {!entries.length ? (
        <p className="py-6 text-center font-mono text-[11px] text-graphite-faint">
          No spends recorded. Run a release to append the first block.
        </p>
      ) : (
        <ol className="thin-scroll max-h-80 space-y-2.5 overflow-y-auto pr-1">
          {entries.map((e, i) => {
            const broken = breakFrom !== null && i >= breakFrom
            const isOrigin = i === breakFrom
            return (
              <motion.li
                key={e.entry_id}
                layout
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className={`group relative rounded-md border p-3 transition-all ${
                  broken
                    ? isOrigin
                      ? 'border-signal-bad bg-signal-bad/[0.12] shadow-sm shadow-signal-bad/20 animate-pulse'
                      : 'border-signal-bad/50 bg-signal-bad/[0.05]'
                    : 'border-bone-edge/80 bg-white/50 hover:border-proved/40 dark:border-stage-line dark:bg-stage-deep/50'
                }`}
              >
                {/* Visual cryptographic connector between blocks */}
                {i > 0 && (
                  <div className="absolute -top-3 left-6 flex h-3 items-center">
                    <span className={`h-full w-0.5 ${broken ? 'bg-signal-bad dashed' : 'bg-proved/40'}`} />
                  </div>
                )}

                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <span className={`flex h-5 w-5 items-center justify-center rounded-full font-mono text-[10px] font-bold ${
                      broken ? 'bg-signal-bad text-white' : 'bg-proved/20 text-proved dark:text-proved-lift'
                    }`}>
                      {i + 1}
                    </span>
                    <span className="truncate font-sans text-[13px] font-medium text-graphite dark:text-bone">
                      {e.run_id}
                    </span>
                  </div>
                  <span className="tnum font-mono text-xs font-semibold text-proved dark:text-proved-lift">
                    ε {e.eps_spent.toFixed(3)}
                  </span>
                </div>

                <div className="mt-2 flex flex-wrap items-center gap-2 font-mono text-[10px] text-graphite-faint">
                  <span className="rounded bg-stage-line/30 px-1 py-0.5">
                    Parent: {e.prev_hash ? e.prev_hash.slice(0, 10) : 'GENESIS'}…
                  </span>
                  <span className="text-graphite-faint/60">⚡</span>
                  <span className={`rounded px-1 py-0.5 ${broken ? 'bg-signal-bad/20 text-signal-bad font-semibold' : 'bg-stage-line/30 text-graphite-soft dark:text-bone'}`}>
                    Hash: {e.hash.slice(0, 12)}…
                  </span>
                  <span className="ml-auto text-[9px] text-graphite-faint">
                    Seed: {e.seed}
                  </span>
                </div>

                <AnimatePresence>
                  {broken && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                      className="mt-2 rounded bg-signal-bad/10 p-1.5 font-mono text-[10px] text-signal-bad"
                    >
                      {isOrigin
                        ? `💥 [DIRECT TARGET] ${attackResult?.attack_type || 'manipulated'} — SHA-256 mismatch severing chain`
                        : '⛓️ [PROPAGATED BREAK] Downstream cryptographic verification failed due to corrupted ancestor'}
                    </motion.div>
                  )}
                </AnimatePresence>

                {!broken && (
                  <button
                    onClick={() => executeAttack(e.entry_id, i)}
                    disabled={busy}
                    aria-label={`Execute attack on ledger block ${i + 1}`}
                    className="absolute right-2.5 top-2.5 rounded border border-bone-edge/80 bg-white/90 px-2 py-0.5 font-mono text-[9px] font-semibold uppercase tracking-wider text-graphite-faint opacity-0 shadow-xs transition-all hover:border-signal-bad hover:bg-signal-bad hover:text-white focus-visible:opacity-100 group-hover:opacity-100 dark:border-stage-line dark:bg-stage-deep dark:hover:bg-signal-bad"
                  >
                    🎯 Inject Attack
                  </button>
                )}
              </motion.li>
            )
          })}
        </ol>
      )}

      <p className="mt-4 border-t border-bone-edge pt-3 text-[11px] leading-relaxed text-graphite-faint dark:border-stage-line">
        SynthProof uses SHA-256 Merkle chaining and signed checkpoint heads (<span className="font-mono">ledger_head</span>).
        Select an attack mode above to see how tampering with spends, truncating history, or corrupting signatures is
        immediately detected by independent zero-trust auditors.
      </p>
    </section>
  )
}
