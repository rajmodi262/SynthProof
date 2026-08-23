import { useMemo, useState } from 'react'

/**
 * The definition of differential privacy, made visible.
 *
 * Two datasets, identical except that one contains Priya and the other does not. Ask both the
 * same question. If you can tell the answers apart, Priya's presence leaked. If you cannot,
 * it did not.
 *
 * That is literally the whole definition, and almost nobody ever draws it. The slider adds
 * noise: at the left the two answers are obviously different and the verdict reads YOU CAN
 * TELL; at the right they overlap into the same smear and it reads YOU CANNOT.
 *
 * Numbers here are arithmetic on the slider, not measurements — the flag on screen says so.
 */

const TRUE_WITH = 847
const TRUE_WITHOUT = 846

function mulberry(seed: number) {
  let t = seed >>> 0
  return () => {
    t += 0x6d2b79f5
    let x = Math.imul(t ^ (t >>> 15), 1 | t)
    x ^= x + Math.imul(x ^ (x >>> 7), 61 | x)
    return ((x ^ (x >>> 14)) >>> 0) / 4294967296
  }
}

/** Draws 60 sample answers per side so the reader sees a spread, not one lucky number. */
function samples(base: number, scale: number, seed: number) {
  const rnd = mulberry(seed)
  const out: number[] = []
  for (let i = 0; i < 60; i++) {
    // Two uniforms differenced gives a symmetric, Laplace-ish spread — enough to show the
    // idea without pretending to be the real sampler.
    out.push(base + (rnd() - rnd()) * scale)
  }
  return out
}

export function TwoHouses() {
  const [noise, setNoise] = useState(0)

  // Scale grows fast so the overlap arrives in the middle of the slider's travel.
  const scale = 1 + noise * noise * 120

  const withP = useMemo(() => samples(TRUE_WITH, scale, 7), [scale])
  const withoutP = useMemo(() => samples(TRUE_WITHOUT, scale, 99), [scale])

  const lo = Math.min(...withP, ...withoutP)
  const hi = Math.max(...withP, ...withoutP)
  const span = Math.max(6, hi - lo)
  const pct = (v: number) => ((v - lo) / span) * 100

  // Overlap is what the verdict turns on: how much the two clouds share ground.
  const wMin = Math.min(...withP)
  const wMax = Math.max(...withP)
  const oMin = Math.min(...withoutP)
  const oMax = Math.max(...withoutP)
  const overlap = Math.max(0, Math.min(wMax, oMax) - Math.max(wMin, oMin))
  const union = Math.max(wMax, oMax) - Math.min(wMin, oMin)
  const hidden = union > 0 && overlap / union > 0.72

  return (
    <div style={{ display: 'grid', gap: '0.65rem' }}>
      <div className="cols cols-2">
        {[
          { label: 'Hospital A — Priya IS in this file', set: withP, tone: 'card-crimson', dotc: 'var(--crimson)' },
          { label: 'Hospital B — Priya is NOT', set: withoutP, tone: 'card-jade', dotc: 'var(--jade)' },
        ].map((side) => (
          <div key={side.label} className={`card ${side.tone}`} style={{ padding: '0.6rem 0.8rem' }}>
            <span className="th-side">{side.label}</span>
            <div className="th-track">
              {side.set.map((v, i) => (
                <span
                  key={i}
                  className="th-dot"
                  style={{ left: `${pct(v)}%`, background: side.dotc }}
                />
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="th-q">
        <span>
          Both are asked: <strong>&ldquo;how many patients here have diabetes?&rdquo;</strong>
        </span>
        <span className={`th-verdict ${hidden ? 'th-safe' : 'th-leak'}`}>
          {hidden ? 'you cannot tell them apart' : 'you can tell them apart'}
        </span>
      </div>

      <label style={{ display: 'grid', gap: '0.2rem' }}>
        <span className="th-slider-label">
          <span>no noise — the truth</span>
          <span>lots of noise — protected</span>
        </span>
        <input
          type="range"
          min={0}
          max={1}
          step={0.01}
          value={noise}
          onChange={(e) => setNoise(Number(e.target.value))}
          aria-label="How much noise is added to the answer"
        />
      </label>

      <p className="lede" style={{ margin: 0, maxWidth: 'none' }}>
        {hidden ? (
          <>
            The two clouds sit on top of each other.{' '}
            <span className="hi hi-jade">Priya is safe</span> — the answer would look the same
            whether or not she were ever in the file.
          </>
        ) : (
          <>
            The two clouds are apart, so the answer{' '}
            <span className="hi hi-crimson">reveals whether Priya is in the file.</span> Nobody
            needed her name.
          </>
        )}
      </p>

      <p className="small" style={{ margin: 0, display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'baseline' }}>
        <span className="flag">illustration</span>
        <span>Sixty sample answers per side, generated from the slider. A drawing of the idea.</span>
      </p>
    </div>
  )
}
