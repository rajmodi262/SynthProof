import { useMemo, useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'

import { ALPHA, canariesNeededFor, fmtCount, maxProvableEpsilon } from '../ceiling'
import { DATA } from '../data'

/**
 * The most persuasive object in the deck: let the panel try to break the ceiling themselves.
 *
 * The design point is that the failure must be PHYSICAL, not stated. Both bars share one
 * axis. The measurable bar ends at a lit wall it cannot cross, and dragging the canary count
 * to its maximum moves it a few pixels. Reading "you can never certify past 2.97" is an
 * assertion; watching the bar refuse to arrive is an argument, and the room remembers the
 * second one.
 */

const R_MIN = 5
const R_MAX = 2000

// Log scale: the interesting behaviour is between 10 and 200 canaries, and a linear slider
// would spend most of its travel in a region where nothing visible changes.
const toSlider = (r: number) => (Math.log(r) - Math.log(R_MIN)) / (Math.log(R_MAX) - Math.log(R_MIN))
const fromSlider = (t: number) =>
  Math.round(Math.exp(Math.log(R_MIN) + t * (Math.log(R_MAX) - Math.log(R_MIN))))

export function CeilingCalculator() {
  const [r, setR] = useState(30)
  const [target, setTarget] = useState(7.36)
  const reduce = useReducedMotion()

  const ceiling = useMemo(() => maxProvableEpsilon(r), [r])
  const needed = useMemo(() => canariesNeededFor(target), [target])
  const reachable = ceiling >= target

  const axisMax = Math.max(target, ceiling, 4) * 1.14
  const pct = (v: number) => Math.min(100, (v / axisMax) * 100)

  return (
    <div className="card card-coral" style={{ display: 'grid', gap: '0.9rem' }}>
      <div className="cols cols-2" style={{ gap: '1.8rem' }}>
        <label className="hot" style={{ display: 'grid', gap: '0.2rem' }}>
          <span className="eyebrow">
            test records you hide · r ={' '}
            <span className="mono audited" style={{ letterSpacing: 0 }}>
              {r}
            </span>
          </span>
          <input
            type="range"
            min={0}
            max={1}
            step={0.001}
            value={toSlider(r)}
            onChange={(e) => setR(fromSlider(Number(e.target.value)))}
            aria-label="Number of canaries planted"
          />
        </label>

        <label style={{ display: 'grid', gap: '0.2rem' }}>
          <span className="eyebrow">
            leak size you want to prove ={' '}
            <span className="mono proved" style={{ letterSpacing: 0 }}>
              {target.toFixed(2)}
            </span>
          </span>
          <input
            type="range"
            min={0.5}
            max={10}
            step={0.01}
            value={target}
            onChange={(e) => setTarget(Number(e.target.value))}
            aria-label="Target epsilon to certify"
          />
        </label>
      </div>

      {/* One track, two bars, and a wall drawn at the ceiling. The wall is the whole
          widget: it is why the amber bar stops where it does. */}
      <div style={{ position: 'relative', display: 'grid', gap: '0.55rem' }}>
        <motion.div
          aria-hidden="true"
          animate={{ left: `${pct(ceiling)}%` }}
          transition={{ duration: reduce ? 0 : 0.45, ease: [0.22, 0.61, 0.36, 1] }}
          style={{
            position: 'absolute',
            top: -6,
            bottom: -6,
            width: 3,
            marginLeft: -1.5,
            background: 'linear-gradient(180deg, var(--coral), var(--coral))',
            boxShadow: '0 0 22px rgba(255,92,57,0.35)',
            borderRadius: 2,
            zIndex: 2,
          }}
        />
        <TrackBar
          label="biggest leak this test can EVER prove"
          value={ceiling}
          widthPct={pct(ceiling)}
          ramp="a"
          reduce={!!reduce}
          shake={!reachable}
        />
        <TrackBar
          label="what you asked it to prove"
          value={target}
          widthPct={pct(target)}
          ramp="p"
          reduce={!!reduce}
        />
      </div>

      <motion.p
        key={reachable ? 'ok' : 'no'}
        initial={{ opacity: 0, y: reduce ? 0 : 5 }}
        animate={{ opacity: 1, y: 0 }}
        style={{
          margin: 0,
          fontSize: '1.28rem',
          lineHeight: 1.42,
          color: 'var(--ink)',
        }}
      >
        {reachable ? (
          <>
            With <span className="mono">{r}</span> hidden records you could prove a leak up to{' '}
            <span className="mono audited">{ceiling.toFixed(2)}</span> — enough to reach{' '}
            <span className="mono proved">{target.toFixed(2)}</span>, if the attacker never gets one wrong.
          </>
        ) : (
          <>
            With <span className="mono">{r}</span> hidden records you can{' '}
            <span className="grad-a" style={{ fontWeight: 500 }}>
              never
            </span>{' '}
            prove a leak bigger than{' '}
            <span className="mono audited">{ceiling.toFixed(2)}</span>. You asked for{' '}
            <span className="mono proved">{target.toFixed(2)}</span>. Reaching that needs{' '}
            <span className="mono audited glow-a">{fmtCount(needed)}</span> hidden records,{' '}
            <em>and the attacker must get every single one right</em>.
          </>
        )}
      </motion.p>

      <p className="small" style={{ margin: 0 }}>
        <span className="mono">ε_max(r) = log(a / (1 − a))</span>,{' '}
        <span className="mono">a = α^(1/r)</span>, <span className="mono">α = {ALPHA}</span> —
        from <span className="mono">synthproof/audit/steinke.py</span>. Our own runs hid r ={' '}
        <span className="mono">{DATA.h2.adult.numCanaries}</span> (limit{' '}
        <span className="mono">{DATA.h2.adult.ceiling.toFixed(2)}</span>) and r ={' '}
        <span className="mono">{DATA.h2.acs.numCanaries}</span> (limit{' '}
        <span className="mono">{DATA.h2.acs.ceiling.toFixed(2)}</span>).
      </p>
    </div>
  )
}

function TrackBar({
  label,
  value,
  widthPct,
  ramp,
  reduce,
  shake = false,
}: {
  label: string
  value: number
  widthPct: number
  ramp: 'p' | 'a'
  reduce: boolean
  shake?: boolean
}) {
  const bg =
    ramp === 'p'
      ? 'linear-gradient(90deg, var(--violet), var(--violet) 40%, var(--cyan))'
      : 'linear-gradient(90deg, var(--coral), var(--coral) 40%, var(--coral))'
  const glow = ramp === 'p' ? 'rgba(108,76,241,0.35)' : 'rgba(255,92,57,0.35)'
  return (
    <div style={{ display: 'grid', gap: '0.22rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem' }}>
        <span className="eyebrow" style={{ letterSpacing: '0.15em' }}>
          {label}
        </span>
        <span
          className={`mono ${ramp === 'p' ? 'proved' : 'audited'}`}
          style={{ fontSize: '1.1rem' }}
        >
          ε {value.toFixed(2)}
        </span>
      </div>
      <div
        style={{
          height: 20,
          borderRadius: 999,
          background: '#fff',
          border: '1px solid rgba(25,20,39,0.15)',
          overflow: 'hidden',
        }}
      >
        <motion.div
          animate={{
            width: `${widthPct}%`,
            // A short knock when the bar is pinned against the wall. It fires once per
            // change rather than looping, so it reads as an impact and not a fidget.
            x: shake && !reduce ? [0, -3, 2, -1, 0] : 0,
          }}
          transition={{ duration: reduce ? 0 : 0.42, ease: [0.22, 0.61, 0.36, 1] }}
          style={{ height: '100%', background: bg, boxShadow: `0 0 20px ${glow}` }}
        />
      </div>
    </div>
  )
}
