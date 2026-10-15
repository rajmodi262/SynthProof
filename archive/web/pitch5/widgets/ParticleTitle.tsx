import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * The title card, and the whole idea, in one object.
 *
 * The word SYNTHPROOF is made of ~2,600 particles, and every particle stands for one record
 * in a dataset. A slider underneath controls how much noise is added to each one. Drag it
 * towards privacy and the letters dissolve into unreadable mush; drag it towards usefulness
 * and they snap sharp.
 *
 * The panel learns the entire trade-off by trying to read the project name. No definitions,
 * no jargon, no epsilon — they simply discover that safety and usefulness pull against each
 * other, which is the one idea everything else in the deck rests on.
 *
 * Canvas 2D, not WebGL: there is no GPU context to lose on an unfamiliar projector.
 * Everything paints synchronously as well as on a frame, because requestAnimationFrame is
 * throttled to nothing whenever the page is not compositing and a blank title card would be
 * a bad first ten seconds.
 */

type P = {
  /** Home position — where this particle sits when the data is perfectly sharp. */
  hx: number
  hy: number
  /** Current position. */
  x: number
  y: number
  /** Per-particle random direction, so the blur looks like noise and not like a zoom. */
  ax: number
  ay: number
  r: number
  hue: number
}

/** Deterministic PRNG: the same title every rehearsal and every machine. */
function mulberry(seed: number) {
  let t = seed >>> 0
  return () => {
    t += 0x6d2b79f5
    let x = Math.imul(t ^ (t >>> 15), 1 | t)
    x ^= x + Math.imul(x ^ (x >>> 7), 61 | x)
    return ((x ^ (x >>> 14)) >>> 0) / 4294967296
  }
}

const WORD = 'SYNTHPROOF'

export function ParticleTitle() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const ptsRef = useRef<P[]>([])
  const drawRef = useRef<null | (() => void)>(null)
  // 0 = maximum privacy (unreadable), 1 = maximum usefulness (sharp).
  const clarityRef = useRef(0)
  const [clarity, setClarity] = useState(0)
  const [settled, setSettled] = useState(false)

  /** Rasterises the word offscreen and samples the lit pixels for particle homes. */
  const build = useCallback((w: number, h: number) => {
    const off = document.createElement('canvas')
    off.width = Math.max(1, Math.floor(w))
    off.height = Math.max(1, Math.floor(h))
    const octx = off.getContext('2d')!

    // Fit the word to the width with a little breathing room.
    let size = Math.floor(h * 0.72)
    octx.textBaseline = 'middle'
    for (; size > 8; size -= 2) {
      octx.font = `900 ${size}px "Geist Sans", system-ui, sans-serif`
      if (octx.measureText(WORD).width <= w * 0.94) break
    }
    const tw = octx.measureText(WORD).width
    octx.fillStyle = '#fff'
    octx.fillText(WORD, (w - tw) / 2, h / 2)

    const img = octx.getImageData(0, 0, off.width, off.height).data
    const rnd = mulberry(19970801)
    const pts: P[] = []
    // Step chosen so the word lands near ~2,600 particles at any sensible width.
    const step = Math.max(2, Math.round(Math.sqrt((w * h * 0.16) / 2600)))
    for (let y = 0; y < off.height; y += step) {
      for (let x = 0; x < off.width; x += step) {
        if (img[(y * off.width + x) * 4 + 3] > 128) {
          const a = rnd() * Math.PI * 2
          pts.push({
            hx: x,
            hy: y,
            // Start scattered: the first thing the room sees is raw, formless data.
            x: w / 2 + (rnd() - 0.5) * w * 1.1,
            y: h / 2 + (rnd() - 0.5) * h * 2.4,
            ax: Math.cos(a),
            ay: Math.sin(a),
            r: 1.1 + rnd() * 1.5,
            hue: rnd(),
          })
        }
      }
    }
    ptsRef.current = pts
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

    // Physics and painting are SEPARATE.
    //
    // The easing below moves each particle 14% of the way to its target per tick, which looks
    // right at 60fps. But requestAnimationFrame is throttled to nothing whenever the page is
    // not compositing, and then a single on-demand repaint would advance the easing exactly
    // once — the letters would never actually resolve, and dragging the slider would appear
    // to do almost nothing. Keeping `step` callable without painting lets an interaction
    // settle the system fully and then draw once.
    const step = () => {
      const c = clarityRef.current
      // Noise falls away as clarity rises. Squared so the last stretch of the slider is
      // where the letters actually resolve — the same shape as the real trade-off.
      const spread = (1 - c) * (1 - c) * Math.min(w, h) * 0.55
      for (const p of ptsRef.current) {
        const wob = Math.sin(t * 0.6 + p.hue * 9) * 0.5 + 0.5
        const tx = p.hx + p.ax * spread * (0.45 + wob * 0.75)
        const ty = p.hy + p.ay * spread * (0.45 + wob * 0.75)
        p.x += (tx - p.x) * 0.14
        p.y += (ty - p.y) * 0.14
      }
    }

    const paint = () => {
      ctx.clearRect(0, 0, w, h)
      const c = clarityRef.current
      for (const p of ptsRef.current) {
        // Crimson where the data is noised into uselessness, gold where it is sharp — the
        // same two hues the rest of this deck already uses, introduced before anyone has been
        // told what they mean.
        const mix = c * 0.75 + p.hue * 0.25
        const R = Math.round(184 + (232 - 184) * mix)
        const G = Math.round(56 + (186 - 56) * mix)
        const B = Math.round(43 + (102 - 43) * mix)
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(${R},${G},${B},${0.62 + c * 0.38})`
        ctx.fill()
      }
    }

    /** Runs the easing to convergence, then paints once. Used by every interaction. */
    const settle = () => {
      for (let i = 0; i < 60; i++) step()
      paint()
    }

    const draw = settle

    const frame = () => {
      t += 0.016
      step()
      paint()
      if (live) handle = requestAnimationFrame(frame)
    }

    resize()
    const ro = new ResizeObserver(resize)
    ro.observe(canvas)

    // Belt and braces on the measurement.
    //
    // If the very first measurement lands while the window is still settling — a projector
    // being attached, a pane being resized, a slide mid-entrance — the canvas gets sized to a
    // fraction of its real width and the wordmark comes out tiny. A ResizeObserver is meant to
    // correct that, and usually does, but it was observed failing to fire after a hot reload
    // swapped the node underneath it. These two timer-driven re-measures cost nothing and
    // close the window in which a bad first reading can survive. Timers rather than frames,
    // because requestAnimationFrame is throttled whenever the page is not compositing.
    const recheck = [setTimeout(resize, 250), setTimeout(resize, 900)]
    window.addEventListener('resize', resize)

    // Rasterising the word before the webfont has loaded measures a fallback face, and the
    // sampled particle homes end up as a shapeless blob that never resolves into letters.
    // This is invisible in dev, where the font is already cached, and shows up in a fresh
    // single-file build where the data-URI faces resolve a beat later.
    if (document.fonts?.ready) {
      document.fonts.ready.then(() => {
        if (live) {
          resize()
          drawRef.current?.()
        }
      })
    }
    drawRef.current = draw
    draw()
    handle = requestAnimationFrame(frame)

    // The assembly: particles fly from the scattered cloud into the letters shortly after
    // the slide opens. Driven by timeouts, not frames, so it still happens on a machine
    // where rAF never fires.
    const t1 = setTimeout(() => {
      clarityRef.current = 1
      setClarity(1)
      drawRef.current?.()
    }, 700)
    const t2 = setTimeout(() => setSettled(true), 1800)

    const onVisible = () => {
      if (!document.hidden) draw()
    }
    document.addEventListener('visibilitychange', onVisible)

    return () => {
      live = false
      cancelAnimationFrame(handle)
      clearTimeout(t1)
      clearTimeout(t2)
      ro.disconnect()
      recheck.forEach(clearTimeout)
      window.removeEventListener('resize', resize)
      document.removeEventListener('visibilitychange', onVisible)
      drawRef.current = null
    }
  }, [build])

  const set = (v: number) => {
    clarityRef.current = v
    setClarity(v)
    drawRef.current?.()
  }

  const readable = clarity > 0.62
  return (
    <div style={{ display: 'grid', gap: '0.5rem' }}>
      <canvas
        ref={canvasRef}
        style={{ display: 'block', width: '100%', height: 'clamp(150px, 27vh, 280px)' }}
        role="img"
        aria-label="SYNTHPROOF, spelled out in particles representing data records"
      />

      <div className="pt-slider">
        <span className="pt-end pt-end-private">
          totally private
          <em>useless</em>
        </span>
        <input
          type="range"
          min={0}
          max={1}
          step={0.01}
          value={clarity}
          onChange={(e) => set(Number(e.target.value))}
          aria-label="Privacy versus usefulness"
        />
        <span className="pt-end pt-end-useful">
          perfectly useful
          <em>no privacy</em>
        </span>
      </div>

      <p className="pt-caption" data-readable={readable ? '1' : '0'}>
        {settled ? (
          readable ? (
            <>
              You can read our name. <strong>So can an attacker read the people inside.</strong>
            </>
          ) : (
            <>
              Perfectly private — and <strong>completely useless.</strong> Every dataset lives
              somewhere on this slider.
            </>
          )
        ) : (
          <>Every dot is one person&rsquo;s record.</>
        )}
      </p>
    </div>
  )
}
