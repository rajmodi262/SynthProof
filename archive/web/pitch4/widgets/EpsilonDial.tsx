import { useMemo, useState } from 'react'

/**
 * Epsilon, shown three ways at once, on one slider.
 *
 * Left: two answer-clouds from two datasets that differ by exactly one person. If they sit
 * apart you can tell whether that person is in the file; if they overlap you cannot. That is
 * the literal definition of the guarantee, and almost nobody draws it.
 *
 * Right: the same setting expressed as a budget, as a noise level, and as the attacker's
 * odds — because different people in a room click with different framings.
 *
 * Plain DOM and arithmetic, no canvas: this slide has to be legible before it is clever.
 * Everything here is computed from the slider and flagged as an illustration; none of it is
 * an experimental result.
 */

const EPS_STEPS = [0.1, 0.25, 0.5, 1, 2, 4, 8]

function mulberry(seed: number) {
  let t = seed >>> 0
  return () => {
    t += 0x6d2b79f5
    let x = Math.imul(t ^ (t >>> 15), 1 | t)
    x ^= x + Math.imul(x ^ (x >>> 7), 61 | x)
    return ((x ^ (x >>> 14)) >>> 0) / 4294967296
  }
}

/** Sample answers around a true count, spread inversely with epsilon. */
function cloud(base: number, eps: number, seed: number) {
  const rnd = mulberry(seed)
  const scale = 26 / eps
  return Array.from({ length: 40 }, () => base + (rnd() - rnd()) * scale)
}

export function EpsilonDial() {
  const [i, setI] = useState(3)
  const eps = EPS_STEPS[i]

  const a = useMemo(() => cloud(847, eps, 11), [eps])
  const b = useMemo(() => cloud(846, eps, 71), [eps])

  const lo = Math.min(...a, ...b)
  const hi = Math.max(...a, ...b)
  const span = Math.max(4, hi - lo)
  const pct = (v: number) => ((v - lo) / span) * 100

  const overlap =
    Math.max(0, Math.min(Math.max(...a), Math.max(...b)) - Math.max(Math.min(...a), Math.min(...b)))
  const union = Math.max(...a, ...b) - Math.min(...a, ...b)
  const hidden = union > 0 && overlap / union > 0.74

  // The odds an attacker who knows every other record can correctly guess whether you are in
  // the dataset: e^eps / (1 + e^eps).
  const odds = Math.exp(eps) / (1 + Math.exp(eps))

  return (
    <div className="cols c21" style={{ alignItems: 'start' }}>
      <div className="p">
        <span className="plabel">
          two files, identical except for one patient — can you tell them apart?
        </span>

        {[
          { l: 'File A — Priya IS in it', set: a, col: 'var(--crimson)' },
          { l: 'File B — Priya is NOT', set: b, col: 'var(--jade)' },
        ].map((row) => (
          <div key={row.l} style={{ marginBottom: 6 }}>
            <div className="nsub" style={{ marginBottom: 2 }}>
              {row.l}
            </div>
            <div
              style={{
                position: 'relative',
                height: 26,
                borderRadius: 6,
                background: 'rgba(0,0,0,0.28)',
                border: '1px solid var(--edge)',
              }}
            >
              {row.set.map((v, n) => (
                <span
                  key={n}
                  style={{
                    position: 'absolute',
                    left: `${pct(v)}%`,
                    top: `${18 + ((n * 37) % 60)}%`,
                    width: 5,
                    height: 5,
                    marginLeft: -2.5,
                    borderRadius: '50%',
                    background: row.col,
                    opacity: 0.8,
                    transition: 'left 240ms cubic-bezier(0.22,0.61,0.36,1)',
                  }}
                />
              ))}
            </div>
          </div>
        ))}

        <div
          style={{
            display: 'inline-flex',
            fontSize: 10,
            fontWeight: 800,
            letterSpacing: '0.1em',
            textTransform: 'uppercase',
            padding: '0.2rem 0.5rem',
            borderRadius: 999,
            background: hidden ? 'var(--jade)' : 'var(--crimson)',
            color: '#12100c',
          }}
        >
          {hidden ? 'you cannot tell — she is protected' : 'you can tell — her presence leaks'}
        </div>
      </div>

      <div style={{ display: 'grid', gap: '0.45rem' }}>
        <div className="p p-gold">
          <span className="plabel">
            the privacy setting · ε = <span className="mono">{eps}</span>
          </span>
          <input
            type="range"
            min={0}
            max={EPS_STEPS.length - 1}
            step={1}
            value={i}
            onChange={(e) => setI(Number(e.target.value))}
            aria-label="Epsilon"
          />
          <div
            className="mono"
            style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: 'var(--ink-3)' }}
          >
            {EPS_STEPS.map((e) => (
              <span key={e}>{e}</span>
            ))}
          </div>
        </div>

        <table className="dtable">
          <thead>
            <tr>
              <th>ε means, three ways</th>
              <th>at ε = {eps}</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>A budget you spend</td>
              <td>{eps <= 0.5 ? 'very few questions' : eps <= 2 ? 'a handful of questions' : 'many questions'}</td>
            </tr>
            <tr>
              <td>A noise dial</td>
              <td>{eps <= 0.5 ? 'heavy noise' : eps <= 2 ? 'moderate noise' : 'light noise'}</td>
            </tr>
            <tr>
              <td>A cap on your influence</td>
              <td className={odds > 0.9 ? 'crimson' : odds > 0.72 ? 'gold' : 'jade'}>
                attacker guesses you correctly {Math.round(odds * 100)} times in 100
              </td>
            </tr>
          </tbody>
        </table>

        <p className="note">
          <span className="flag">illustration</span> Clouds and wordings are generated from the
          slider. The odds row is the exact formula e<sup>ε</sup>/(1+e<sup>ε</sup>) — a coin
          flip is 50.
        </p>
      </div>
    </div>
  )
}
