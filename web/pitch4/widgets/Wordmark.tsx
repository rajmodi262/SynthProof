import { useCallback, useEffect, useRef } from 'react'

/**
 * The wordmark on slide 1, assembled from particles.
 *
 * The only decorative animation left in the deck. It buys ten seconds of attention at the
 * start and then gets out of the way — every other slide is a diagram or a table, because a
 * review panel needs to leave knowing what the project IS.
 *
 * Physics is separate from painting so the word can be settled and drawn in one call.
 * requestAnimationFrame is throttled to nothing whenever the page is not compositing, and a
 * title that never forms would be a poor first impression.
 */

type P = { hx: number; hy: number; x: number; y: number; r: number; s: number }

function mulberry(seed: number) {
  let t = seed >>> 0
  return () => {
    t += 0x6d2b79f5
    let x = Math.imul(t ^ (t >>> 15), 1 | t)
    x ^= x + Math.imul(x ^ (x >>> 7), 61 | x)
    return ((x ^ (x >>> 14)) >>> 0) / 4294967296
  }
}

export function Wordmark({ text = 'SYNTHPROOF' }: { text?: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const psRef = useRef<P[]>([])
  const drawRef = useRef<null | (() => void)>(null)

  const build = useCallback(
    (w: number, h: number) => {
      const off = document.createElement('canvas')
      off.width = Math.max(1, Math.floor(w))
      off.height = Math.max(1, Math.floor(h))
      const c = off.getContext('2d')!
      let size = Math.floor(h * 0.74)
      c.textBaseline = 'middle'
      for (; size > 8; size -= 2) {
        c.font = `900 ${size}px "Geist Sans", system-ui, sans-serif`
        if (c.measureText(text).width <= w * 0.94) break
      }
      const tw = c.measureText(text).width
      c.fillStyle = '#fff'
      c.fillText(text, (w - tw) / 2, h / 2)

      const img = c.getImageData(0, 0, off.width, off.height).data
      const rnd = mulberry(1997)
      const ps: P[] = []
      const stepPx = Math.max(2, Math.round(Math.sqrt((w * h * 0.2) / 1500)))
      for (let y = 0; y < off.height; y += stepPx) {
        for (let x = 0; x < off.width; x += stepPx) {
          if (img[(y * off.width + x) * 4 + 3] > 128) {
            ps.push({
              hx: x,
              hy: y,
              x: w / 2 + (rnd() - 0.5) * w * 1.2,
              y: h / 2 + (rnd() - 0.5) * h * 3,
              r: 0.9 + rnd() * 1.2,
              s: rnd(),
            })
          }
        }
      }
      psRef.current = ps
    },
    [text],
  )

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

    const step = () => {
      for (const p of psRef.current) {
        p.x += (p.hx - p.x) * 0.12
        p.y += (p.hy - p.y) * 0.12
      }
    }

    const paint = () => {
      ctx.clearRect(0, 0, w, h)
      for (const p of psRef.current) {
        const drift = Math.sin(t * 0.6 + p.s * 9) * 0.5
        ctx.beginPath()
        ctx.arc(p.x, p.y + drift, p.r, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(232,186,102,${0.55 + p.s * 0.45})`
        ctx.fill()
      }
    }

    const settle = () => {
      for (let k = 0; k < 70; k++) step()
      paint()
    }

    const frame = () => {
      t += 0.016
      step()
      paint()
      if (live) handle = requestAnimationFrame(frame)
    }

    resize()
    const ro = new ResizeObserver(resize)
    ro.observe(canvas)
    drawRef.current = settle
    paint()
    handle = requestAnimationFrame(frame)

    // Rasterising before the webfont resolves measures a fallback face and the letters come
    // out as a blob — invisible in dev where the font is cached, obvious in a fresh build.
    document.fonts?.ready?.then(() => {
      if (live) resize()
    })

    const onVisible = () => {
      if (!document.hidden) settle()
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

  return (
    <canvas
      ref={canvasRef}
      style={{ display: 'block', width: '100%', height: 'clamp(72px, 13vh, 130px)' }}
      role="img"
      aria-label={text}
    />
  )
}
