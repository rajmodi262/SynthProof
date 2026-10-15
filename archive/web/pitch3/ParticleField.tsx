import { useEffect, useRef } from 'react'

import { makeParticles, paint, retarget, step, type Particle, type Shape } from './field'

/**
 * The persistent canvas that lives behind all six slides.
 *
 * It is mounted ONCE by the deck and never unmounts, which is what makes the particles
 * continuous: changing slide only changes their target positions, so the field visibly
 * re-forms from what the room was already looking at.
 *
 * `shape` is passed as a prop; the component re-targets on change and settles synchronously
 * as well as animating, so the field is correct even where requestAnimationFrame never fires.
 */
export function ParticleField({ shape }: { shape: Shape }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const psRef = useRef<Particle[]>([])
  const sizeRef = useRef<[number, number]>([0, 0])
  const shapeRef = useRef<Shape>(shape)
  const apiRef = useRef<{ settle: () => void; retarget: () => void } | null>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')!
    let live = true
    let handle = 0
    let t = 0

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      const rect = canvas.getBoundingClientRect()
      const w = rect.width
      const h = rect.height
      sizeRef.current = [w, h]
      canvas.width = Math.round(w * dpr)
      canvas.height = Math.round(h * dpr)
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      if (!psRef.current.length) psRef.current = makeParticles(w, h)
      retarget(psRef.current, shapeRef.current, w, h)
      apiRef.current?.settle()
    }

    const settle = () => {
      // 70 ticks at 0.11 easing converges to well under a pixel. This is what makes an
      // interaction correct on a machine where rAF is throttled: change the shape, settle,
      // paint once.
      for (let i = 0; i < 70; i++) step(psRef.current)
      const [w, h] = sizeRef.current
      paint(ctx, psRef.current, w, h, t)
    }

    const doRetarget = () => {
      const [w, h] = sizeRef.current
      retarget(psRef.current, shapeRef.current, w, h)
    }

    apiRef.current = { settle, retarget: doRetarget }

    const frame = () => {
      t += 0.016
      step(psRef.current)
      const [w, h] = sizeRef.current
      paint(ctx, psRef.current, w, h, t)
      if (live) handle = requestAnimationFrame(frame)
    }

    resize()
    const ro = new ResizeObserver(resize)
    ro.observe(canvas)
    handle = requestAnimationFrame(frame)

    // Rasterising text before the webfont resolves measures a fallback face, and the word
    // shapes come out as a blob. Invisible in dev where the font is cached; very visible in a
    // fresh single-file build.
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
      apiRef.current = null
    }
  }, [])

  // Re-target whenever the slide (or an interaction on it) changes the requested shape.
  useEffect(() => {
    shapeRef.current = shape
    apiRef.current?.retarget()
    apiRef.current?.settle()
  }, [shape])

  return <canvas ref={canvasRef} className="field" aria-hidden="true" />
}
