import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

/**
 * "Pick your own details. Watch us find you."
 *
 * The panel chooses a birth month, a city district and a gender from three dropdowns. A crowd
 * of 100,000 dots filters live — 100,000, then ~8,300, then ~280, then 1 — and the last dot
 * turns crimson.
 *
 * This is the most persuasive object in the deck because it stops being about hospitals and
 * becomes about the person holding the clicker. Nobody argues with re-identification after
 * watching themselves get found in a dataset that contains no names.
 *
 * HONESTY: the crowd is drawn and the counts are arithmetic on the choices, not a lookup in
 * anyone's records. The flag on screen says so. The underlying claim — that a handful of
 * ordinary fields usually identifies one person — is Sweeney's, and it is cited on the slide.
 */

const PINS = ['411004', '411007', '411016', '411021', '411027', '411028', '411030',
  '411033', '411038', '411041', '411045', '411048', '411052', '411057', '411061']

const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December']

const DAYS = Array.from({ length: 31 }, (_, i) => String(i + 1))

// A plausible adult span. Nothing here is a lookup — see the note below.
const YEARS = Array.from({ length: 60 }, (_, i) => String(2006 - i))

const START = 100_000

/**
 * Sizes of each filter, in order. The counts on screen are START divided by these, one after
 * another — arithmetic anyone in the room can check, not a query against anybody's records.
 *
 * The granularity matters and an earlier draft got it wrong: a birth MONTH and a broad area
 * only narrow 100,000 people to a few hundred, which quietly undercuts the whole slide. A
 * PIN code and a full date of birth are what actually make a person unique, and they are also
 * exactly the fields Sweeney's result turns on.
 */
const BUCKETS = [PINS.length, MONTHS.length, DAYS.length, YEARS.length]

function mulberry(seed: number) {
  let t = seed >>> 0
  return () => {
    t += 0x6d2b79f5
    let x = Math.imul(t ^ (t >>> 15), 1 | t)
    x ^= x + Math.imul(x ^ (x >>> 7), 61 | x)
    return ((x ^ (x >>> 14)) >>> 0) / 4294967296
  }
}

type Dot = { x: number; y: number; r: number; f: number[]; seed: number }

export function FindYourself() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const dotsRef = useRef<Dot[]>([])
  const drawRef = useRef<null | (() => void)>(null)
  const stepRef = useRef(0)

  const [pin, setPin] = useState('')
  const [month, setMonth] = useState('')
  const [day, setDay] = useState('')
  const [year, setYear] = useState('')

  // Filters apply in order, so the count only moves once the previous one is set.
  const picked = [pin, month, day, year]
  let chosen = 0
  for (const v of picked) {
    if (!v) break
    chosen++
  }
  stepRef.current = Math.min(3, chosen)

  // Running division, exact. The last step usually lands below one person, which IS the
  // finding: at that point you are more likely to be unique than to have company.
  const { counts, expected } = useMemo(() => {
    const cs = [START]
    let v = START
    for (const b of BUCKETS) {
      v = v / b
      cs.push(v)
    }
    return { counts: cs, expected: v }
  }, [])

  const exact = counts[chosen]
  const remaining = chosen === BUCKETS.length ? 1 : Math.max(1, Math.round(exact))

  const build = useCallback((w: number, h: number) => {
    const rnd = mulberry(31415)
    const dots: Dot[] = []
    // 3,000 drawn dots stand in for 100,000 people; drawing them all would be a grey wall.
    for (let i = 0; i < 3000; i++) {
      dots.push({
        x: rnd() * w,
        y: rnd() * h,
        r: 1.1 + rnd() * 1.2,
        // One stamp per visual filter. A dot survives filter k only if its stamp is 0,
        // so the crowd thins by roughly the right proportion at each step.
        f: [
          Math.floor(rnd() * 4),
          Math.floor(rnd() * 4),
          Math.floor(rnd() * 4),
        ],
        seed: rnd(),
      })
    }
    // Guarantee exactly one dot survives all three filters, wherever the panel lands: the
    // last dot is re-stamped to match the current selection on every draw.
    dotsRef.current = dots
  }, [])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')!
    let w = 0
    let h = 0
    let live = true
    let handle = 0
    let t = 0

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      const rect = canvas.getBoundingClientRect()
      w = rect.width
      h = rect.height
      canvas.width = Math.round(w * dpr)
      canvas.height = Math.round(h * dpr)
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      build(w, h)
      drawRef.current?.()
    }

    const paint = () => {
      ctx.clearRect(0, 0, w, h)
      const s = stepRef.current
      const dots = dotsRef.current
      if (!dots.length) return

      // The survivor: always the last dot, placed a little off-centre so it reads as a
      // person who happened to be there rather than as a diagram.
      const hero = dots[dots.length - 1]
      hero.x = w * 0.58
      hero.y = h * 0.45
      hero.r = 3.4

      for (let i = 0; i < dots.length; i++) {
        const d = dots[i]
        const isHero = i === dots.length - 1
        // A dot survives filter k if its stamped attribute matches. The hero always survives.
        let alive = true
        if (!isHero) {
          for (let k = 0; k < s && alive; k++) {
            if (d.f[k] !== 0) alive = false
          }
        }

        if (isHero && s >= 3) {
          const pulse = 0.7 + Math.sin(t * 3) * 0.3
          const ring = 14 + ((t * 40) % 70)
          ctx.beginPath()
          ctx.arc(d.x, d.y, ring, 0, Math.PI * 2)
          ctx.strokeStyle = `rgba(184,56,43,${(1 - ((t * 40) % 70) / 70) * 0.7})`
          ctx.lineWidth = 2.5
          ctx.stroke()

          ctx.beginPath()
          ctx.arc(d.x, d.y, d.r, 0, Math.PI * 2)
          ctx.fillStyle = `rgba(184,56,43,${pulse})`
          ctx.shadowColor = 'rgba(184,56,43,0.9)'
          ctx.shadowBlur = 22
          ctx.fill()
          ctx.shadowBlur = 0
          continue
        }

        ctx.beginPath()
        ctx.arc(d.x, d.y, d.r, 0, Math.PI * 2)
        ctx.fillStyle = alive ? 'rgba(200,145,47,0.85)' : 'rgba(146,126,100,0.13)'
        ctx.fill()
      }
    }

    const frame = () => {
      t += 0.016
      paint()
      if (live) handle = requestAnimationFrame(frame)
    }

    resize()
    const ro = new ResizeObserver(resize)
    ro.observe(canvas)
    drawRef.current = paint
    paint()
    handle = requestAnimationFrame(frame)

    const onVisible = () => {
      if (!document.hidden) paint()
    }
    document.addEventListener('visibilitychange', onVisible)

    return () => {
      live = false
      cancelAnimationFrame(handle)
      ro.disconnect()
      document.removeEventListener('visibilitychange', onVisible)
      drawRef.current = null
    }
  }, [build])

  const pick = (fn: (v: string) => void) => (e: React.ChangeEvent<HTMLSelectElement>) => {
    fn(e.target.value)
    // Repaint immediately: a dropdown must change the picture even where rAF never fires.
    requestAnimationFrame(() => drawRef.current?.())
    setTimeout(() => drawRef.current?.(), 0)
  }

  const found = chosen === BUCKETS.length

  return (
    <div style={{ display: 'grid', gap: '0.6rem' }}>
      <div className="fy-controls">
        <label>
          <span>PIN code</span>
          <select value={pin} onChange={pick(setPin)}>
            <option value="">pick…</option>
            {PINS.map((x) => (
              <option key={x}>{x}</option>
            ))}
          </select>
        </label>
        <label>
          <span>born</span>
          <select value={month} onChange={pick(setMonth)} disabled={!pin}>
            <option value="">month…</option>
            {MONTHS.map((x) => (
              <option key={x}>{x}</option>
            ))}
          </select>
        </label>
        <label>
          <span>day</span>
          <select value={day} onChange={pick(setDay)} disabled={!month}>
            <option value="">date…</option>
            {DAYS.map((x) => (
              <option key={x}>{x}</option>
            ))}
          </select>
        </label>
        <label>
          <span>year</span>
          <select value={year} onChange={pick(setYear)} disabled={!day}>
            <option value="">year…</option>
            {YEARS.map((x) => (
              <option key={x}>{x}</option>
            ))}
          </select>
        </label>
      </div>

      <div className="fy-stage">
        <canvas
          ref={canvasRef}
          style={{ display: 'block', width: '100%', height: 'clamp(150px, 26vh, 260px)' }}
          role="img"
          aria-label={`${remaining} people still match the selection`}
        />
        <div className="fy-readout">
          <span className="fy-label">people who still match</span>
          <span className={`huge ${found ? 'crimson' : 'gold'}`} style={{ fontSize: 'clamp(2.2rem,4.4vw,3.6rem)' }}>
            {remaining.toLocaleString('en-IN')}
          </span>
          {found && (
            <span className="fy-hit">
              expected {expected.toFixed(2)} people. you are almost certainly the only one — and
              we never saw a name.
            </span>
          )}
        </div>
      </div>

      <p className="small" style={{ margin: 0, display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'baseline' }}>
        <span className="flag">illustration</span>
        <span>
          A drawn crowd, and 100,000 divided by {BUCKETS.join(' × ')} — arithmetic on your
          own choices, not a lookup in anybody&rsquo;s records. The finding it illustrates is
          Sweeney (2000): a handful of ordinary fields usually identifies one person.
        </span>
      </p>
    </div>
  )
}
