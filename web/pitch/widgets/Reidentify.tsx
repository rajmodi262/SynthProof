import { useCallback, useEffect, useRef, useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'

/**
 * The opening image: a crowd of people, narrowed to one, live on the wall.
 *
 * This is the 1997 Sweeney result made physical. 2,600 dots stand for a released
 * "anonymous" table. Each click applies one column the hospital did not think was
 * identifying — ZIP, then birth date, then sex — and the crowd collapses. At the end a
 * single dot is left burning red, and nobody in the room needs the argument explained.
 *
 * HONESTY: the survivor counts are the shape of Sweeney's published finding, not a
 * measurement of ours, and the dots are drawn. The panel says so on screen. Animating a
 * borrowed result as though it were our data would be exactly the kind of overclaim this
 * project exists to refuse.
 *
 * Canvas 2D rather than WebGL: 2,600 sprites is nothing, and it means there is no GPU
 * context to lose on a strange projector five minutes before the viva.
 */

type Dot = {
  x: number
  y: number
  r: number
  /** Which step this dot is eliminated at; 4 means it is the survivor. */
  dies: number
  seed: number
  /** Animated 0..1 opacity, eased towards the target each frame. */
  a: number
}

const STEPS = [
  { label: 'released table', filter: 'names and addresses removed', left: 2600 },
  { label: '+ ZIP code', filter: 'a field nobody calls identifying', left: 208 },
  { label: '+ date of birth', filter: 'still not a name', left: 7 },
  { label: '+ sex', filter: 'three ordinary columns', left: 1 },
]

/** Deterministic PRNG, so the same person is singled out on every machine and rehearsal. */
function mulberry(seed: number) {
  let t = seed >>> 0
  return () => {
    t += 0x6d2b79f5
    let x = Math.imul(t ^ (t >>> 15), 1 | t)
    x ^= x + Math.imul(x ^ (x >>> 7), 61 | x)
    return ((x ^ (x >>> 14)) >>> 0) / 4294967296
  }
}

export function Reidentify() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const dotsRef = useRef<Dot[]>([])
  const stepRef = useRef(0)
  /** Lets click handlers and the resize observer force a repaint without waiting for rAF. */
  const drawRef = useRef<null | (() => void)>(null)

  const [step, setStep] = useState(0)
  const reduce = useReducedMotion()

  const build = useCallback((w: number, h: number) => {
    const rnd = mulberry(20260817)
    const n = 2600
    const dots: Dot[] = []
    for (let i = 0; i < n; i++) {
      // Rejection-sampled into a soft ellipse so the crowd reads as a population
      // rather than a rectangle of confetti.
      let x = 0
      let y = 0
      for (let k = 0; k < 12; k++) {
        x = rnd()
        y = rnd()
        const dx = (x - 0.5) * 2
        const dy = (y - 0.5) * 2
        if (dx * dx + dy * dy * 1.55 < 1) break
      }
      // Rank decides elimination order, so the survivor is fixed rather than random
      // per render. Ranks are assigned by index against the published survivor counts.
      let dies = 1
      if (i < STEPS[1].left) dies = 2
      if (i < STEPS[2].left) dies = 3
      if (i < STEPS[3].left) dies = 4
      dots.push({
        x: x * w,
        y: y * h,
        r: 1.25 + rnd() * 1.15,
        dies,
        seed: rnd() * Math.PI * 2,
        a: 1,
      })
    }
    // The survivor sits slightly off-centre; dead centre reads as a diagram, off-centre
    // reads as a person who happened to be there.
    const hero = dots.find((d) => d.dies === 4)!
    hero.x = w * 0.62
    hero.y = h * 0.43
    hero.r = 3
    dotsRef.current = dots
  }, [])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')!
    let w = 0
    let h = 0

    // The animation handle is a CLOSURE-LOCAL, not a shared ref, and the loop checks a
    // `live` flag before rescheduling. React 18 StrictMode mounts, unmounts and remounts
    // every effect in development, and with a single shared ref one mount's cleanup can
    // cancel a different mount's frame. This is the pattern that cannot get that wrong.
    let live = true
    let handle = 0

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
    resize()
    const ro = new ResizeObserver(resize)
    ro.observe(canvas)

    let t = 0

    /** Paints exactly one frame. Separated from the loop so it can be called directly. */
    const draw = () => {
      ctx.clearRect(0, 0, w, h)
      const s = stepRef.current

      for (const d of dots()) {
        const alive = d.dies > s
        const target = alive ? 1 : 0.045
        // Eased rather than snapped: the crowd should feel like it is being sifted,
        // not like a layer was switched off.
        d.a += (target - d.a) * (reduce ? 1 : 0.075)

        const isHero = d.dies === 4
        const heroLit = isHero && s >= 3

        if (heroLit) {
          const pulse = reduce ? 1 : 0.72 + Math.sin(t * 2.6) * 0.28
          // Expanding ring, so the eye is dragged to the survivor from anywhere.
          const ring = reduce ? 16 : 16 + ((t * 34) % 62)
          const fade = reduce ? 0.5 : 1 - ((t * 34) % 62) / 62
          ctx.beginPath()
          ctx.arc(d.x, d.y, ring, 0, Math.PI * 2)
          ctx.strokeStyle = `rgba(232,59,74,${fade * 0.7})`
          ctx.lineWidth = 2.5
          ctx.stroke()

          ctx.beginPath()
          ctx.arc(d.x, d.y, d.r * 2.4, 0, Math.PI * 2)
          ctx.fillStyle = `rgba(232,59,74,${pulse})`
          ctx.shadowColor = 'rgba(232,59,74,0.9)'
          ctx.shadowBlur = 26
          ctx.fill()
          ctx.shadowBlur = 0
          continue
        }

        const drift = reduce ? 0 : Math.sin(t * 0.5 + d.seed) * 0.7
        ctx.beginPath()
        ctx.arc(d.x + drift, d.y + drift * 0.6, d.r, 0, Math.PI * 2)
        // Violet on white for a live record; near-invisible grey once ruled out.
        ctx.fillStyle = alive
          ? `rgba(108,76,241,${0.35 + d.a * 0.6})`
          : `rgba(25,20,39,${d.a * 1.6})`
        ctx.fill()
      }

    }

    const frame = () => {
      t += 0.016
      draw()
      if (live) handle = requestAnimationFrame(frame)
    }

    const dots = () => dotsRef.current

    // Paint one frame SYNCHRONOUSLY before scheduling anything. requestAnimationFrame is
    // fully throttled whenever the page is not compositing — a backgrounded tab, some
    // remote-desktop sessions, certain projector mirroring modes — and a deck whose opening
    // image is a black rectangle is a lost viva. The static frame is correct on its own; the
    // loop only adds drift and the pulsing ring.
    draw()
    handle = requestAnimationFrame(frame)

    // Repaint when the tab comes back, since nothing was drawn while it was away.
    const onVisible = () => {
      if (!document.hidden) draw()
    }
    document.addEventListener('visibilitychange', onVisible)

    drawRef.current = draw

    return () => {
      live = false
      cancelAnimationFrame(handle)
      ro.disconnect()
      document.removeEventListener('visibilitychange', onVisible)
      drawRef.current = null
    }
  }, [build, reduce])

  const go = (n: number) => {
    stepRef.current = n
    setStep(n)
    // Clicking must change the picture even where rAF never fires.
    drawRef.current?.()
  }

  const cur = STEPS[step]

  return (
    <div style={{ display: 'grid', gap: '0.7rem' }}>
      <div
        style={{
          position: 'relative',
          borderRadius: 16,
          overflow: 'hidden',
          border: '3px solid var(--ink)',
          boxShadow: 'var(--pop)',
          background: '#fff',
        }}
      >
        <canvas
          ref={canvasRef}
          style={{ display: 'block', width: '100%', height: 'clamp(170px, 30vh, 330px)' }}
          role="img"
          aria-label={`${cur.left} people people we still cannot tell apart after ${cur.label}`}
        />

        <div
          style={{
            position: 'absolute',
            left: 18,
            top: 14,
            display: 'grid',
            gap: 2,
            pointerEvents: 'none',
          }}
        >
          <span className="eyebrow" style={{ letterSpacing: '0.2em' }}>
            people we still cannot tell apart
          </span>
          <motion.span
            key={cur.left}
            initial={{ opacity: 0, y: reduce ? 0 : 8, filter: reduce ? 'none' : 'blur(6px)' }}
            animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
            transition={{ duration: reduce ? 0 : 0.4 }}
            className={`hero-num ${step >= 3 ? 'bad' : 'grad-p'}`}
            style={{ fontSize: 'clamp(2.4rem, 4.4vw, 3.6rem)' }}
          >
            {cur.left.toLocaleString('en-US')}
          </motion.span>
          <span
            className="mono"
            style={{ fontSize: 11, color: 'var(--ink-3)', letterSpacing: '0.06em' }}
          >
            {cur.label} — {cur.filter}
          </span>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap', alignItems: 'center' }}>
        {STEPS.map((s, n) => (
          <button
            key={s.label}
            className="btn"
            data-on={step === n ? '1' : '0'}
            onClick={() => go(n)}
          >
            {n === 0 ? 'start' : s.label}
          </button>
        ))}
        <span style={{ flex: 1 }} />
        {step < 3 ? (
          <button
            className="btn btn-hot"
            data-on="1"
            onClick={() => go(step + 1)}
            style={{ fontWeight: 500 }}
          >
            add one more column
          </button>
        ) : (
          <motion.span
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mono bad"
            style={{ fontSize: 13, letterSpacing: '0.04em' }}
          >
            one person. named.
          </motion.span>
        )}
      </div>
    </div>
  )
}
