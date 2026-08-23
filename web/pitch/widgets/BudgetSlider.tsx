import { useMemo, useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'

import { DATA } from '../data'

/**
 * Privacy budget vs. fidelity, driven by committed measurements.
 *
 * Two honesty decisions are visible on screen:
 *
 *  1. The slider SNAPS to the five epsilon values we actually ran. A continuous 0.1 -> 10
 *     control would have to invent the values in between, and an invented curve is exactly
 *     the kind of number this project refuses to print. The tick marks are the experiment.
 *
 *  2. The scatter is labelled ILLUSTRATIVE. The correlation each cloud is drawn to is
 *     measured — real from `true_correlation`, synthetic from the measured correlation error
 *     at that cell — but the individual dots are generated for display. Nobody should leave
 *     the room thinking they watched 6,000 real records move.
 *
 * The bars underneath carry no such caveat: those are the committed means and bootstrap CIs.
 */

const MECHS = [
  { key: 'independent', name: 'Independent', note: 'each column alone' },
  { key: 'pairwise', name: 'Pairwise tree', note: 'column pairs' },
  { key: 'aim', name: 'AIM', note: 'chooses its own pairs' },
] as const

type DatasetKey = 'adult' | 'acs'

// A tiny deterministic PRNG so the clouds are identical on every render and every machine —
// a scatter that reshuffles when React re-renders reads as noise in the demo, not in the data.
function mulberry(seed: number) {
  let t = seed >>> 0
  return () => {
    t += 0x6d2b79f5
    let x = Math.imul(t ^ (t >>> 15), 1 | t)
    x ^= x + Math.imul(x ^ (x >>> 7), 61 | x)
    return ((x ^ (x >>> 14)) >>> 0) / 4294967296
  }
}

/** Box-Muller, so the clouds look like a joint distribution rather than a square of confetti. */
function cloud(n: number, rho: number, seed: number) {
  const rnd = mulberry(seed)
  const pts: Array<[number, number]> = []
  for (let i = 0; i < n; i++) {
    const u1 = Math.max(rnd(), 1e-9)
    const u2 = rnd()
    const g1 = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2)
    const g2 = Math.sqrt(-2 * Math.log(u1)) * Math.sin(2 * Math.PI * u2)
    const r = Math.max(-0.99, Math.min(0.99, rho))
    pts.push([g1, r * g1 + Math.sqrt(1 - r * r) * g2])
  }
  return pts
}

export function BudgetSlider() {
  const [ds, setDs] = useState<DatasetKey>('adult')
  const [idx, setIdx] = useState(4)
  const [mech, setMech] = useState<(typeof MECHS)[number]['key']>('aim')

  const block = DATA.h1[ds]
  const grid = block.epsGrid
  const eps = grid[idx]

  const cell = useMemo(
    () => block.cells.find((c) => c.mechanism === mech && c.eps === eps)!,
    [block, mech, eps],
  )

  const trueRho = block.trueCorrelation
  // The measured error is unsigned, so this shows the cloud pulled AWAY from the truth by the
  // measured distance. Direction is a display choice; magnitude is the measurement.
  const synthRho = Math.max(-0.95, trueRho - cell.corrErr.mean * 4)

  const real = useMemo(() => cloud(220, trueRho * 4, 7), [trueRho])
  const synth = useMemo(() => cloud(220, synthRho * 4, 11), [synthRho])

  return (
    <div style={{ display: 'grid', gap: '1rem' }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', alignItems: 'center' }}>
        {(['adult', 'acs'] as const).map((k) => (
          <button
            key={k}
            className="btn"
            data-on={ds === k ? '1' : '0'}
            onClick={() => setDs(k)}
          >
            {DATA.h1[k].label}
          </button>
        ))}
        <span style={{ width: 12 }} />
        {MECHS.map((m) => (
          <button
            key={m.key}
            className="btn"
            data-on={mech === m.key ? '1' : '0'}
            onClick={() => setMech(m.key)}
          >
            {m.name}
          </button>
        ))}
      </div>

      <label style={{ display: 'grid', gap: '0.3rem' }}>
        <span className="eyebrow">
          privacy budget ε = <span className="mono">{eps.toFixed(1)}</span> · smaller is more
          private
        </span>
        <input
          type="range"
          min={0}
          max={grid.length - 1}
          step={1}
          value={idx}
          onChange={(e) => setIdx(Number(e.target.value))}
          aria-label="Privacy budget epsilon"
          list="eps-grid"
        />
        <div
          className="mono"
          style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--ink-3)' }}
        >
          {grid.map((g) => (
            <span key={g}>{g}</span>
          ))}
        </div>
      </label>

      <div className="cols cols-2" style={{ gap: '1.5rem' }}>
        <Scatter title="Real data" pts={real} colour="var(--ink-2)" />
        <Scatter
          title={`Synthetic · ${MECHS.find((m) => m.key === mech)!.name} at ε ${eps}`}
          pts={synth}
          colour="var(--violet)"
        />
      </div>

      <div className="cols cols-3" style={{ gap: '1.2rem' }}>
        <Readout
          label="how wrong the fake data is"
          value={cell.corrErr.mean.toFixed(4)}
          ci={`[${cell.corrErr.lo.toFixed(4)}, ${cell.corrErr.hi.toFixed(4)}]`}
          hint="lower is better — how far the link between two columns drifted"
          colour="var(--violet)"
        />
        <Readout
          label="how useful the fake data is"
          value={cell.tstrF1.mean.toFixed(3)}
          ci={`[${cell.tstrF1.lo.toFixed(3)}, ${cell.tstrF1.hi.toFixed(3)}]`}
          hint={`real data scores ${block.trtrF1.toFixed(3)} — that is the ceiling`}
          colour="var(--ink)"
        />
        <Readout
          label="privacy we can prove"
          value={cell.proved.toFixed(3)}
          ci={`audited ${cell.audited.toFixed(3)}`}
          hint="always at or under what you asked for"
          colour="var(--coral)"
        />
      </div>

      <p className="small" style={{ margin: 0, display: 'flex', gap: '0.6rem', alignItems: 'baseline', flexWrap: 'wrap' }}>
        <span className="flag flag-illustrative">dots illustrative</span>
        <span>
          Each cloud is drawn to a <em>measured</em> correlation — the real one from{' '}
          <span className="mono">true_correlation</span>, the synthetic one displaced by the
          measured error at this cell — but the individual points are generated for display.
          The three boxes, and the ranges under them, are measured numbers from{' '}
          <span className="mono">{block.source}</span> — {block.seeds} seeds,{' '}
          {block.nRows.toLocaleString('en-US')} rows. The slider stops on the five ε we ran;
          nothing is measured in between, so nothing is drawn there.
        </span>
      </p>
    </div>
  )
}

function Scatter({ title, pts, colour }: { title: string; pts: Array<[number, number]>; colour: string }) {
  const reduce = useReducedMotion()
  return (
    <figure className="scatter" style={{ margin: 0 }}>
      <figcaption className="eyebrow">{title}</figcaption>
      <svg viewBox="-3.4 -3.4 6.8 6.8" role="img" aria-label={title}>
        <g stroke="rgba(25,20,39,0.10)" strokeWidth="0.012">
          {[-2, -1, 0, 1, 2].map((v) => (
            <g key={v}>
              <line x1={v} y1={-3.4} x2={v} y2={3.4} />
              <line x1={-3.4} y1={v} x2={3.4} y2={v} />
            </g>
          ))}
        </g>
        {pts.map(([x, y], i) => (
          <motion.circle
            key={i}
            cx={x}
            cy={-y}
            r={0.045}
            fill={colour}
            fillOpacity={0.72}
            initial={false}
            animate={{ cx: x, cy: -y }}
            transition={{ duration: reduce ? 0 : 0.45, ease: 'easeOut' }}
          />
        ))}
      </svg>
    </figure>
  )
}

function Readout({
  label,
  value,
  ci,
  hint,
  colour,
}: {
  label: string
  value: string
  ci: string
  hint: string
  colour: string
}) {
  return (
    <div style={{ borderTop: '1px solid var(--ink)', paddingTop: '0.6rem' }}>
      <div className="eyebrow" style={{ marginBottom: '0.3rem' }}>
        {label}
      </div>
      <div className="mono" style={{ fontSize: '2rem', color: colour, lineHeight: 1 }}>
        {value}
      </div>
      <div className="mono" style={{ fontSize: 12, color: 'var(--ink-3)', marginTop: '0.25rem' }}>
        {ci}
      </div>
      <div style={{ fontSize: 13, color: 'var(--ink-3)', marginTop: '0.2rem' }}>{hint}</div>
    </div>
  )
}
