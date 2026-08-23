import { useCallback, useEffect, useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'

import { SLIDES } from './slides'

/**
 * Nine slides, content-first.
 *
 * No AnimatePresence anywhere, deliberately: under React 18 StrictMode its exit callback can
 * be swallowed by the double-invoked effect, which either wedges the deck (the counter
 * advances, the content does not) or leaks mounted slides into the DOM. Both were reproduced
 * on this project. Only the incoming slide animates, which reads the same to a room and
 * cannot fail on the day.
 */
export function Deck() {
  const [i, setI] = useState(0)
  const [notes, setNotes] = useState(false)
  const reduce = useReducedMotion()

  const go = useCallback((n: number) => {
    setI(Math.max(0, Math.min(SLIDES.length - 1, n)))
  }, [])

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      // Sliders and dropdowns live on these slides; typing into one must not page the deck
      // out from under the presenter.
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
      else if (/^[1-9]$/.test(e.key)) go(Number(e.key) - 1)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [i, go])

  const slide = SLIDES[i]

  return (
    <>
      <div className="wash" aria-hidden="true" />

      <div className="deck">
        <div className="stage">
          <motion.section
            key={slide.id}
            className="slide"
            data-centre={slide.centre ? '1' : '0'}
            initial={{ opacity: 0, y: reduce ? 0 : 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: reduce ? 0 : 0.28, ease: [0.22, 0.61, 0.36, 1] }}
            aria-label={slide.title}
          >
            <slide.Body />
          </motion.section>

          {notes && (
            <motion.aside
              className="notes"
              initial={{ y: reduce ? 0 : '100%' }}
              animate={{ y: 0 }}
              transition={{ duration: reduce ? 0 : 0.22, ease: 'easeOut' }}
              aria-label="Speaker notes"
            >
              <slide.Notes />
            </motion.aside>
          )}
        </div>

        <div className="rail">
          <span className="rlabel">
            SynthProof · {String(i + 1).padStart(2, '0')} of {SLIDES.length} · {slide.title}
          </span>
          <div className="rsteps">
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
          <span className="rlabel">← → move · 1-9 jump · N notes</span>
        </div>
      </div>
    </>
  )
}
