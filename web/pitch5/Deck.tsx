import { useCallback, useEffect, useRef, useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'

import { SLIDES } from './slides'

/**
 * Deck shell.
 *
 * The navigation lives inside a heartbeat that runs along the foot of every slide — the
 * subject is medical data, and a living line keeps the stakes present without taking any
 * argument space. It goes crimson on the slides about leaks.
 *
 * No AnimatePresence anywhere, deliberately. Under React 18 StrictMode framer-motion's exit
 * callback can be swallowed by the double-invoked effect; with `mode="wait"` that wedges the
 * deck outright, and without it exited slides pile up in the DOM. Both were reproduced on
 * this project. Only the incoming slide animates, which reads the same to a room and cannot
 * fail on the day.
 */
export function Deck() {
  const [i, setI] = useState(0)
  const [notes, setNotes] = useState(false)
  const [overview, setOverview] = useState(false)
  const [dir, setDir] = useState(1)
  const stageRef = useRef<HTMLDivElement>(null)
  const reduce = useReducedMotion()

  const go = useCallback(
    (next: number) => {
      const clamped = Math.max(0, Math.min(SLIDES.length - 1, next))
      setDir(clamped >= i ? 1 : -1)
      setI(clamped)
      setOverview(false)
      stageRef.current?.scrollTo?.({ top: 0 })
    },
    [i],
  )

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      // Dropdowns and sliders live on these slides; typing into one must not page the deck
      // out from under the presenter.
      const el = e.target as HTMLElement | null
      const typing =
        el?.tagName === 'INPUT' || el?.tagName === 'TEXTAREA' || el?.tagName === 'SELECT' ||
        el?.isContentEditable
      if (typing && e.key !== 'Escape') return

      switch (e.key) {
        case 'ArrowRight':
        case 'PageDown':
        case ' ':
          e.preventDefault()
          go(i + 1)
          break
        case 'ArrowLeft':
        case 'PageUp':
          e.preventDefault()
          go(i - 1)
          break
        case 'Home':
          go(0)
          break
        case 'End':
          go(SLIDES.length - 1)
          break
        case 'Escape':
          e.preventDefault()
          setOverview((v) => !v)
          break
        case 'n':
        case 'N':
          setNotes((v) => !v)
          break
        default:
          if (/^[1-9]$/.test(e.key)) go(Number(e.key) - 1)
          if (e.key === '0') go(9)
          if (e.key === '!') go(10)
          if (e.key === '@') go(11)
          if (e.key === '#') go(12)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [i, go])

  const slide = SLIDES[i]
  const shift = reduce ? 0 : 24

  return (
    <>
      <div className="bg" aria-hidden="true" />
      <div className="grid" aria-hidden="true" />

      <div className="deck">
        <div className="stage" ref={stageRef}>
          <motion.section
            key={slide.id}
            className="slide"
            data-tone={slide.tone ?? 'light'}
            initial={{ opacity: 0, x: dir * shift }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: reduce ? 0 : 0.3, ease: [0.22, 0.61, 0.36, 1] }}
            aria-label={slide.title}
          >
            <slide.Body />
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

          {overview && (
            <motion.div
              className="overview"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: reduce ? 0 : 0.15 }}
            >
              {SLIDES.map((s, n) => (
                <button key={s.id} className="ov-card" onClick={() => go(n)}>
                  <span className="mono" style={{ fontSize: 10, fontWeight: 800, color: 'var(--gold-deep)' }}>
                    {String(n + 1).padStart(2, '0')}
                  </span>
                  <span style={{ fontSize: 15.5, fontWeight: 800, lineHeight: 1.2 }}>{s.title}</span>
                  <span style={{ fontSize: 11.5, lineHeight: 1.3, color: 'var(--ink-2)' }}>{s.blurb}</span>
                </button>
              ))}
            </motion.div>
          )}
        </div>

        <div className="pulse">
          <Heartbeat hot={!!slide.hotPulse} />
          <nav className="pulse-nav" aria-label="Slides">
            {SLIDES.map((s, n) => (
              <button
                key={s.id}
                className="dot"
                data-state={n === i ? 'here' : n < i ? 'seen' : 'ahead'}
                onClick={() => go(n)}
                aria-current={n === i ? 'step' : undefined}
                aria-label={`Slide ${n + 1}: ${s.title}`}
              >
                {n + 1}
              </button>
            ))}
            <button
              className="dot"
              onClick={() => setNotes((v) => !v)}
              aria-label="Toggle speaker notes"
              style={{ marginLeft: 6 }}
            >
              N
            </button>
          </nav>
        </div>
      </div>
    </>
  )
}

/**
 * The trace. Drawn as one long path and slid leftwards by a CSS animation rather than by
 * JavaScript, so it keeps moving without a frame loop and costs nothing when the page is not
 * compositing.
 */
function Heartbeat({ hot }: { hot: boolean }) {
  const beat = [
    [0, 0], [30, 0], [34, -4], [38, 3], [42, 0], [50, 0],
    [53, 6], [56, -22], [60, 12], [64, 0], [74, 0], [79, -8], [84, 0], [100, 0],
  ]
  const one = (off: number) => beat.map(([x, y]) => `${off + x},${28 + y}`).join(' ')
  const pts = [0, 100, 200, 300, 400, 500].map(one).join(' ')

  return (
    <svg className="pulse-svg" viewBox="0 0 300 56" preserveAspectRatio="none" aria-hidden="true">
      <polyline className={`pulse-line ${hot ? 'pulse-line-hot' : ''}`} points={pts}>
        <animateTransform
          attributeName="transform"
          type="translate"
          from="0 0"
          to="-100 0"
          dur="2.4s"
          repeatCount="indefinite"
        />
      </polyline>
    </svg>
  )
}
