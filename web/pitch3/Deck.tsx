import { useCallback, useEffect, useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'

import { ParticleField } from './ParticleField'
import { SLIDES } from './slides'
import type { Shape } from './field'

/**
 * Six slides over one persistent particle field.
 *
 * The field is mounted here, ONCE, and never unmounts — that is what makes the particles
 * continuous across slides. Changing slide sets a new target shape; a slide can also re-shape
 * the field from an interaction via `setShape`.
 *
 * No AnimatePresence anywhere: under React 18 StrictMode its exit callback can be swallowed
 * by the double-invoked effect, which either wedges the deck or leaks mounted slides. Both
 * were reproduced on this project. Only the incoming slide animates.
 */
export function Deck() {
  const [i, setI] = useState(0)
  const [notes, setNotes] = useState(false)
  const [shape, setShape] = useState<Shape>(SLIDES[0].shape)
  const reduce = useReducedMotion()

  const go = useCallback((next: number) => {
    const n = Math.max(0, Math.min(SLIDES.length - 1, next))
    setI(n)
    setShape(SLIDES[n].shape)
  }, [])

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const el = e.target as HTMLElement | null
      const typing =
        el?.tagName === 'INPUT' || el?.tagName === 'SELECT' || el?.tagName === 'TEXTAREA'
      if (typing && e.key !== 'Escape') return
      if (e.key === 'ArrowRight' || e.key === ' ' || e.key === 'PageDown') {
        e.preventDefault()
        go(i + 1)
      } else if (e.key === 'ArrowLeft' || e.key === 'PageUp') {
        e.preventDefault()
        go(i - 1)
      } else if (e.key === 'Home') go(0)
      else if (e.key === 'End') go(SLIDES.length - 1)
      else if (e.key === 'n' || e.key === 'N') setNotes((v) => !v)
      else if (/^[1-6]$/.test(e.key)) go(Number(e.key) - 1)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [i, go])

  const slide = SLIDES[i]

  return (
    <>
      <ParticleField shape={shape} />
      <div className="veil" aria-hidden="true" />

      <div className="deck">
        <div className="stage">
          <motion.section
            key={slide.id}
            className="slide"
            data-lay={slide.lay}
            data-ivory={slide.ivory ? '1' : '0'}
            initial={{ opacity: 0, y: reduce ? 0 : 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: reduce ? 0 : 0.4, ease: [0.22, 0.61, 0.36, 1] }}
            aria-label={slide.title}
          >
            <slide.Body setShape={setShape} />
          </motion.section>

          {notes && (
            <motion.aside
              className="notes"
              initial={{ y: reduce ? 0 : '100%' }}
              animate={{ y: 0 }}
              transition={{ duration: reduce ? 0 : 0.24, ease: 'easeOut' }}
              aria-label="Speaker notes"
            >
              <slide.Notes />
            </motion.aside>
          )}
        </div>

        <div className="rail">
          <span className="rail-label">
            {String(i + 1).padStart(2, '0')} — {slide.title}
          </span>
          <div className="rail-steps">
            {SLIDES.map((s, n) => (
              <button
                key={s.id}
                className="tick"
                data-state={n === i ? 'here' : n < i ? 'seen' : 'ahead'}
                onClick={() => go(n)}
                aria-current={n === i ? 'step' : undefined}
                aria-label={`Slide ${n + 1}: ${s.title}`}
              />
            ))}
          </div>
          <span className="rail-label">← → move · N notes</span>
        </div>
      </div>
    </>
  )
}
