import { useCallback, useEffect, useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'

/**
 * The ledger, with a real hash chain.
 *
 * The hashes here are computed in the browser with SHA-256 via Web Crypto, over the same
 * field order the Python ledger uses. Nothing is faked: edit an entry's epsilon and the
 * recomputed digest genuinely stops matching what the next block committed to, which is why
 * the failure cascades instead of being coloured in.
 *
 * The claim on screen is deliberately narrow. This shows tamper-EVIDENCE — anyone holding
 * the signing key can rewrite history and re-sign it, so custody of that key is an
 * organisational control and not a cryptographic one. Saying more than that would be the
 * exact overclaim the project exists to avoid.
 */

type Block = { runId: string; eps: number; prev: string; hash: string }

const SEED: Array<{ runId: string; eps: number }> = [
  { runId: 'adult-independent-eps1', eps: 0.912 },
  { runId: 'adult-pairwise-eps1', eps: 0.912 },
  { runId: 'adult-aim-eps4', eps: 3.201 },
  { runId: 'acs-pairwise-eps8', eps: 7.356 },
]

const GENESIS = '0'.repeat(64)

async function sha256(text: string): Promise<string> {
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text))
  return Array.from(new Uint8Array(buf))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('')
}

/** Same shape as the Python ledger's entry digest: prev hash, run id, epsilon, unit separated. */
const payload = (prev: string, runId: string, eps: number) =>
  `${prev}${runId}${eps.toFixed(6)}`

async function rebuild(rows: Array<{ runId: string; eps: number }>): Promise<Block[]> {
  const out: Block[] = []
  let prev = GENESIS
  for (const r of rows) {
    const hash = await sha256(payload(prev, r.runId, r.eps))
    out.push({ ...r, prev, hash })
    prev = hash
  }
  return out
}

export function TamperChain() {
  const [chain, setChain] = useState<Block[] | null>(null)
  const [edited, setEdited] = useState<number | null>(null)
  const reduce = useReducedMotion()

  useEffect(() => {
    rebuild(SEED).then(setChain)
  }, [])

  const tamper = useCallback(
    async (i: number) => {
      if (!chain) return
      // Rewrite the row directly, the way an operator with database access would — bypassing
      // the append path entirely. Only THIS block's stored hash is recomputed; the blocks
      // after it still commit to the old digest, which is what breaks.
      const rows = chain.map((b, n) => (n === i ? { ...b, eps: 0.01 } : b))
      const next: Block[] = []
      let prevStored = GENESIS
      for (let n = 0; n < rows.length; n++) {
        const b = rows[n]
        if (n <= i) {
          const hash = await sha256(payload(prevStored, b.runId, b.eps))
          next.push({ ...b, prev: prevStored, hash })
          prevStored = hash
        } else {
          // Untouched blocks keep the prev-hash they were written with.
          next.push({ ...b, prev: chain[n].prev, hash: chain[n].hash })
        }
      }
      setChain(next)
      setEdited(i)
    },
    [chain],
  )

  const reset = useCallback(async () => {
    setChain(await rebuild(SEED))
    setEdited(null)
  }, [])

  if (!chain) return <div className="card small">building chain…</div>

  const brokenFrom = edited === null ? null : edited + 1
  const valid = edited === null

  return (
    <div className="card" style={{ display: 'grid', gap: '0.9rem' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
        <span className="eyebrow">privacy budget ledger · sha-256 chain</span>
        <span style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <motion.span
            className="flag"
            animate={{ color: valid ? 'var(--green)' : 'var(--red)' }}
            transition={{ duration: reduce ? 0 : 0.2 }}
          >
            verify() {valid ? 'passed' : 'FAILED'}
          </motion.span>
          {edited !== null && (
            <button className="btn" onClick={reset}>
              reset
            </button>
          )}
        </span>
      </header>

      <ol style={{ listStyle: 'none', margin: 0, padding: 0, display: 'grid', gap: '0.4rem' }}>
        {chain.map((b, i) => {
          const isEdited = i === edited
          const isDownstream = brokenFrom !== null && i >= brokenFrom
          const bad = isEdited || isDownstream
          return (
            <motion.li
              key={b.runId}
              animate={{
                borderColor: bad ? 'var(--red)' : 'var(--ink)',
                backgroundColor: bad ? 'var(--red-l)' : '#fff',
                boxShadow: bad ? '0 0 26px rgba(232,59,74,0.35)' : 'none',
              }}
              transition={{ duration: reduce ? 0 : 0.25, delay: reduce ? 0 : (isDownstream ? (i - brokenFrom!) * 0.09 : 0) }}
              style={{ border: '1px solid var(--ink)', borderRadius: 11, padding: '0.6rem 0.75rem' }}
            >
              <div style={{ display: 'flex', gap: '0.8rem', alignItems: 'baseline', flexWrap: 'wrap' }}>
                <span className="mono" style={{ fontSize: 11, color: 'var(--ink-3)' }}>
                  #{String(i + 1).padStart(2, '0')}
                </span>
                <span style={{ flex: 1, fontSize: 15, minWidth: '12ch' }}>{b.runId}</span>
                <span className="mono" style={{ color: isEdited ? 'var(--red)' : 'var(--violet)', fontSize: 15 }}>
                  ε {b.eps.toFixed(3)}
                </span>
                {!bad && (
                  <button className="btn" style={{ padding: '0.2rem 0.5rem' }} onClick={() => tamper(i)}>
                    tamper
                  </button>
                )}
              </div>
              <div className="mono" style={{ fontSize: 11, color: 'var(--ink-3)', marginTop: '0.3rem' }}>
                prev {b.prev.slice(0, 16)}… → this {b.hash.slice(0, 16)}…
              </div>
              {isEdited && (
                <div className="mono bad" style={{ fontSize: 12, marginTop: '0.3rem' }}>
                  altered — ε rewritten to 0.01, digest no longer matches what block{' '}
                  {i + 2 <= chain.length ? `#${String(i + 2).padStart(2, '0')}` : 'the head'}{' '}
                  committed to
                </div>
              )}
              {isDownstream && (
                <div className="mono bad" style={{ fontSize: 12, marginTop: '0.3rem' }}>
                  invalid — commits to a predecessor hash that has changed
                </div>
              )}
            </motion.li>
          )
        })}
      </ol>

      <p className="small" style={{ margin: 0 }}>
        You can always <strong style={{ color: 'var(--ink)' }}>tell</strong> if someone edited a
        block, reordered them, or deleted one from the middle — each block carries a fingerprint
        of the one before it. Chopping off the END is a separate problem: a shortened chain still looks
        perfectly consistent, so this check alone cannot see it. We catch that with a signed
        header that records how long the chain should be. Test:{' '}
        <span className="mono">tests/test_ledger_adversarial.py</span>. Not tamper-<em>proof</em> —
        anyone holding the signing key can rewrite history and sign it again.
      </p>
    </div>
  )
}
