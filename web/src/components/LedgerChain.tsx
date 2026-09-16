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

interface LedgerChainProps {
  ledger: LedgerState | null
  onRefresh: () => void
  onOpenBlockExplainer?: (index: number) => void
}

export function LedgerChain({
  ledger,
  onRefresh,
  onOpenBlockExplainer,
}: LedgerChainProps) {
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

  const currentAttackOpt = ATTACK_OPTIONS.find((o) => o.type === selectedAttack)

  return (
    <section className="rounded-xl border border-line bg-card p-6 shadow-e0">
      {/* Header with section title, measured divider, and live seal chip */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2.5">
            <h3 className="font-display text-2xl text-ink">The Ledger</h3>
            <span className="rounded-full border border-brass/30 bg-brass/10 px-2.5 py-0.5 font-mono text-[10px] font-semibold text-brass">
              IMMUTABLE CHAIN
            </span>
          </div>
          <p className="mt-1 font-sans text-xs text-muted">
            Every release charged, SHA-256 hash-chained, and Ed25519-signed. Tamper-evident spine with live attack simulation.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Status badge - required for component tests */}
          <span
            className={`flex items-center gap-1.5 rounded-full border px-3 py-1 font-mono text-xs font-semibold uppercase tracking-wider ${
              verified === null
                ? 'border-line text-faint bg-paper-2'
                : verified
                ? 'border-verify/40 bg-verify-bg text-verify'
                : 'border-seal/50 bg-seal-bg text-seal'
            }`}
          >
            <span
              className={`h-2 w-2 rounded-full ${
                verified === null
                  ? 'bg-faint'
                  : verified
                  ? 'bg-verify'
                  : 'bg-seal animate-ping'
              }`}
            />
            {verified === null
              ? 'not checked'
              : verified
              ? 'chain integrity: verified'
              : 'attack detected: chain broken'}
          </span>

          {entries.length > 0 && (
            <button
              onClick={reset}
              disabled={busy}
              className="btn-verify !px-3 !py-1 !text-xs"
            >
              Reset Chain
            </button>
          )}
        </div>
      </div>

      {/* Measured divider */}
      <div className="measured-divider my-4" />

      {/* Tamper Studio Control Strip */}
      {entries.length > 0 && (
        <div className="mb-5 rounded-lg border border-line bg-paper-2/60 p-3.5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="font-mono text-[11px] font-semibold uppercase tracking-wider text-muted">
                Adversarial Attack Simulator:
              </span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {ATTACK_OPTIONS.map((opt) => (
                <button
                  key={opt.type}
                  onClick={() => setSelectedAttack(opt.type)}
                  className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 font-mono text-[11px] font-medium transition-all ${
                    selectedAttack === opt.type
                      ? 'border border-seal bg-seal text-white shadow-xs'
                      : 'border border-line bg-card text-muted hover:border-seal/60 hover:text-seal'
                  }`}
                >
                  <span>{opt.icon}</span>
                  <span>{opt.label}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="mt-2.5 flex flex-wrap items-center justify-between gap-2 border-t border-line/50 pt-2">
            <p className="max-w-2xl font-sans text-xs text-muted">
              {currentAttackOpt?.blurb}
            </p>
            <button
              onClick={() => executeAttack()}
              disabled={busy}
              className="btn-seal !bg-seal !text-white hover:!bg-[#943834] !px-3.5 !py-1.5 !text-xs font-semibold shadow-xs"
            >
              {busy
                ? 'Simulating Attack...'
                : `Launch ${currentAttackOpt?.icon} Attack`}
            </button>
          </div>
        </div>
      )}

      {/* Attack Results Banner */}
      <AnimatePresence>
        {attackResult && !attackResult.verified && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="mb-5 overflow-hidden rounded-lg border border-seal bg-seal-bg/70 p-3.5 text-xs"
          >
            <div className="flex items-center justify-between">
              <span className="font-mono font-bold uppercase tracking-wider text-seal">
                🚨 Cryptographic Attack Intercepted
              </span>
              <span className="font-mono text-[11px] font-semibold text-seal">
                Invalidated {attackResult.broken_count} downstream block(s)
              </span>
            </div>
            <p className="mt-1 font-sans font-medium text-ink">
              {attackResult.attack_description}
            </p>
            {attackResult.reason && (
              <div className="mt-2 rounded bg-seal/10 p-2 font-mono text-[11px] text-seal">
                <strong>Failure Cause:</strong> {attackResult.reason}
              </div>
            )}
            <p className="mt-1.5 font-sans text-xs text-muted">
              {attackResult.explanation}
            </p>
          </motion.div>
        )}
      </AnimatePresence>

      {error && (
        <p
          role="alert"
          className="mb-4 rounded-md border-l-2 border-seal bg-seal-bg/40 p-2.5 font-mono text-[11px] text-seal"
        >
          {error}
        </p>
      )}

      {/* Horizontal Block Spine (2.5D visual chain) */}
      {!entries.length ? (
        <div className="well flex h-32 items-center justify-center p-6 text-center font-mono text-xs text-muted">
          No entries recorded. Run a release to append the first cryptographic block.
        </div>
      ) : (
        <div className="well thin-scroll overflow-x-auto p-4">
          <div className="flex items-center gap-3">
            {entries.map((e, i) => {
              const isIllustrative = e.run_id?.startsWith('illustrative-') ?? false
              const isBroken = breakFrom !== null && i >= breakFrom
              const isOrigin = i === breakFrom

              return (
                <div key={e.entry_id} className="flex items-center">
                  {/* Connector link glyph between blocks */}
                  {i > 0 && (
                    <div
                      className={`flex w-6 items-center justify-center transition-all ${
                        isBroken ? 'text-seal -translate-y-0.5' : 'text-brass'
                      }`}
                      title={isBroken ? 'Cryptographic hash chain severed' : 'SHA-256 link valid'}
                    >
                      <span className={`text-base font-bold ${isBroken ? 'animate-bounce' : ''}`}>
                        {isBroken ? '⚡' : '⛓️'}
                      </span>
                    </div>
                  )}

                  {/* Individual Block Card */}
                  <button
                    type="button"
                    onClick={() => onOpenBlockExplainer?.(i)}
                    className={`group relative flex h-28 w-44 shrink-0 flex-col justify-between rounded-lg border p-3 text-left transition-all duration-150 focus:outline-none ${
                      isBroken
                        ? isOrigin
                          ? 'border-seal bg-seal-bg ring-1 ring-seal shadow-e1'
                          : 'border-seal/60 bg-seal-bg/40'
                        : isIllustrative
                        ? 'border-line/70 bg-card/60 opacity-80 hover:opacity-100 hover:border-brass/50'
                        : 'border-line bg-card shadow-e0 hover:-translate-y-0.5 hover:border-brass hover:shadow-e1'
                    }`}
                  >
                    {/* Illustrative Ribbon or Block Index */}
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-[10px] font-semibold text-faint">
                        #{i + 1}
                      </span>
                      {isIllustrative ? (
                        <span className="rounded bg-paper-2 px-1.5 py-0.5 font-mono text-[9px] font-medium uppercase tracking-wider text-muted border border-line">
                          ILLUSTRATIVE
                        </span>
                      ) : (
                        <span className="font-mono text-[10px] font-semibold text-brass">
                          ε {e.eps_spent.toFixed(3)}
                        </span>
                      )}
                    </div>

                    {/* Mechanism & Run ID */}
                    <div>
                      <div className="truncate font-sans text-xs font-semibold text-ink">
                        {e.mechanism_name}
                      </div>
                      <div className="truncate font-mono text-[10px] text-muted" title={e.run_id}>
                        {e.run_id}
                      </div>
                    </div>

                    {/* Hashes */}
                    <div className="border-t border-line/60 pt-1 flex items-center justify-between font-mono text-[9px] text-faint">
                      <span>Hash: {e.hash.slice(0, 8)}…</span>
                      <span className="text-brass group-hover:underline">Math →</span>
                    </div>
                  </button>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Footer explanation */}
      <div className="mt-4 flex flex-wrap items-center justify-between gap-2 text-[11px] font-mono text-muted">
        <span>
          Total Releases: <strong className="text-ink font-sans">{ledger?.count ?? 0}</strong> · Total Spent: <strong className="text-brass">Σε {ledger?.total_eps_spent.toFixed(2) ?? '0.00'}</strong>
        </span>
        <span className="text-faint">
          Tip Hash: {ledger?.head ? ledger.head.slice(0, 24) + '…' : '—'}
        </span>
      </div>
    </section>
  )
}
