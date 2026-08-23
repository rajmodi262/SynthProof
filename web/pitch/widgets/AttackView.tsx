import { useMemo, useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'

import { DATA } from '../data'
import { maxProvableEpsilon } from '../ceiling'

/**
 * What the attacker actually sees.
 *
 * Every number here is a measurement from `results/detection_floor.json`: we planted a known
 * fraction of records verbatim into the release and asked the auditor to find them. The grid
 * renders the measured true-positive and false-positive rates as individual guesses, so
 * "the adversary is at chance" stops being a phrase and becomes a picture of a board that is
 * half right and half wrong.
 *
 * The pairs (leak, r) shown are exactly the cells that were run. There is no interpolation:
 * moving a control jumps to another measured cell.
 */

const LEAKS = [0, 0.01, 0.05, 0.25, 1] as const
const RS = [10, 25, 50, 100, 200, 400, 800] as const

const LEAK_LABEL: Record<string, string> = {
  '0': 'nothing copied — our sanity check',
  '0.01': '1% of records copied exactly',
  '0.05': '5% of records copied exactly',
  '0.25': '25% of records copied exactly',
  '1': 'every record copied — a totally broken system',
}

export function AttackView() {
  const [li, setLi] = useState(3)
  const [ri, setRi] = useState(3)
  const reduce = useReducedMotion()

  const leak = LEAKS[li]
  const r = RS[ri]

  const cell = useMemo(
    () => DATA.floor.cells.find((c) => c.leak === leak && c.r === r),
    [leak, r],
  )

  // 60 tiles is enough to read a rate at a glance and few enough to animate on a projector.
  const TILES = 60
  const tiles = useMemo(() => {
    if (!cell) return []
    const half = TILES / 2
    const hits = Math.round(cell.tpr * half) // members correctly identified
    const falseAlarms = Math.round(cell.fpr * half) // non-members wrongly flagged
    return Array.from({ length: TILES }, (_, i) => {
      const isMember = i < half
      if (isMember) return i < hits ? 'hit' : 'miss'
      return i - half < falseAlarms ? 'false' : 'correct-reject'
    })
  }, [cell])

  const ceiling = maxProvableEpsilon(r)

  return (
    <div className="card" style={{ display: 'grid', gap: '1rem' }}>
      <div className="cols cols-2" style={{ gap: '2rem' }}>
        <label style={{ display: 'grid', gap: '0.3rem' }}>
          <span className="eyebrow">how leaky is the system?</span>
          <input
            type="range"
            min={0}
            max={LEAKS.length - 1}
            step={1}
            value={li}
            onChange={(e) => setLi(Number(e.target.value))}
            aria-label="Leak fraction"
          />
          <span style={{ fontSize: 15, color: 'var(--ink)' }}>{LEAK_LABEL[String(leak)]}</span>
        </label>
        <label style={{ display: 'grid', gap: '0.3rem' }}>
          <span className="eyebrow">
            test records we hid · r = <span className="mono">{r}</span>
          </span>
          <input
            type="range"
            min={0}
            max={RS.length - 1}
            step={1}
            value={ri}
            onChange={(e) => setRi(Number(e.target.value))}
            aria-label="Number of canaries"
          />
          <span style={{ fontSize: 15, color: 'var(--ink-3)' }}>
            biggest leak this can ever prove: ε <span className="mono">{ceiling.toFixed(2)}</span>
          </span>
        </label>
      </div>

      {!cell ? (
        <p className="small">We did not run this combination, so there is nothing to show.</p>
      ) : (
        <>
          <div>
            <div className="eyebrow" style={{ marginBottom: '0.45rem' }}>
              the attacker's guesses · LEFT half were really in the data · RIGHT half were not
            </div>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(30, 1fr)',
                gap: 3,
              }}
              role="img"
              aria-label={`Measured true positive rate ${cell.tpr}, false positive rate ${cell.fpr}`}
            >
              {tiles.map((t, i) => (
                <motion.span
                  key={i}
                  initial={false}
                  animate={{
                    backgroundColor:
                      t === 'hit'
                        ? 'var(--coral)'
                        : t === 'false'
                          ? 'var(--red)'
                          : t === 'miss'
                            ? 'rgba(25,20,39,0.28)'
                            : 'rgba(25,20,39,0.10)',
                  }}
                  transition={{ duration: reduce ? 0 : 0.28, delay: reduce ? 0 : i * 0.004 }}
                  style={{ aspectRatio: '1', display: 'block', borderRadius: 2 }}
                />
              ))}
            </div>
            <div
              className="mono"
              style={{ display: 'flex', gap: '1.4rem', flexWrap: 'wrap', fontSize: 11, color: 'var(--ink-3)', marginTop: '0.5rem' }}
            >
              <span>
                <Swatch c="var(--coral)" /> caught a real member
              </span>
              <span>
                <Swatch c="rgba(25,20,39,0.28)" /> missed one
              </span>
              <span>
                <Swatch c="var(--red)" /> false accusation
              </span>
              <span>
                <Swatch c="rgba(25,20,39,0.10)" /> correctly left alone
              </span>
            </div>
          </div>

          <div className="cols cols-3" style={{ gap: '1.2rem' }}>
            <Stat label="found the real ones" value={cell.tpr.toFixed(3)} hint="0.5 means pure guessing" />
            <Stat label="wrongly accused" value={cell.fpr.toFixed(3)} hint="0.5 means pure guessing" />
            <Stat
              label="leak we could prove"
              value={cell.meanEps.toFixed(3)}
              hint={`detected in ${(cell.detectionRate * 100).toFixed(0)}% of 5 seeds · ceiling ${ceiling.toFixed(2)}`}
              colour={cell.meanEps > 0 ? 'var(--coral)' : 'var(--ink-3)'}
            />
          </div>

          <p className="small" style={{ margin: 0 }}>
            {leak === 0 ? (
              <>
                <strong style={{ color: 'var(--ink)' }}>The negative control.</strong> Nothing
                was copied, so the test should find nothing — and it does in 34 of these
                35 runs. The one exception is a single seed at r = 100. That is not a bug: at
                α = 0.05 we accept a 5% false-alarm rate by construction, and 1 in 35 is 2.9%.
                A control that reported zero <em>every</em> time would suggest a test too
                conservative to detect anything.
              </>
            ) : leak === 1 ? (
              <>
                <strong style={{ color: 'var(--ink)' }}>A totally broken system is caught instantly</strong>{' '}
                — every guess right, from just 10 hidden records. This is what attacking is
                genuinely good for.
              </>
            ) : leak >= 0.25 ? (
              <>
                A partial leak needs <strong style={{ color: 'var(--ink)' }}>400 hidden records</strong>{' '}
                before we spot it most of the time — and even then it proves only a tiny leak.
              </>
            ) : (
              <>
                At this leak level our test{' '}
                <strong style={{ color: 'var(--ink)' }}>never reliably detects anything</strong>,
                no matter how many records we hid. That is the measured floor, and it is why
                finding nothing here says as much about the test as about the system.
              </>
            )}{' '}
            Measured in <span className="mono">{DATA.floor.source}</span>, 5 seeds, n ={' '}
            {DATA.floor.nRows.toLocaleString('en-US')}, α = {DATA.floor.alpha}.
          </p>
        </>
      )}
    </div>
  )
}

function Swatch({ c }: { c: string }) {
  return (
    <span
      style={{ display: 'inline-block', width: 9, height: 9, background: c, marginRight: 5 }}
    />
  )
}

function Stat({
  label,
  value,
  hint,
  colour = 'var(--ink)',
}: {
  label: string
  value: string
  hint: string
  colour?: string
}) {
  return (
    <div style={{ borderTop: '1px solid var(--ink)', paddingTop: '0.55rem' }}>
      <div className="eyebrow">{label}</div>
      <div className="mono" style={{ fontSize: '1.9rem', color: colour, lineHeight: 1.1 }}>
        {value}
      </div>
      <div style={{ fontSize: 13, color: 'var(--ink-3)' }}>{hint}</div>
    </div>
  )
}
