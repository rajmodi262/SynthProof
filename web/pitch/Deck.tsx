import { useCallback, useEffect, useRef, useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'

import { SLIDES } from './slides'

/**
 * Deck shell: navigation, the measurement rail, speaker notes, and the overview grid.
 *
 * Everything here exists to survive a nervous presenter. Arrows and space advance, Esc opens
 * an overview to jump from, N toggles notes, and every keyboard path is also a click target
 * so a failure of memory under pressure is never a dead end. There is no autoplay and no
 * timer — nothing in the deck moves unless someone asks it to.
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
      // A slide that scrolled during rehearsal must not open half-way down in the room.
      stageRef.current?.scrollTo?.({ top: 0 })
    },
    [i],
  )

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      // Typing into the widgets (the ceiling calculator has number fields) must not page
      // the deck out from under the presenter.
      const el = e.target as HTMLElement | null
      const typing =
        el?.tagName === 'INPUT' || el?.tagName === 'TEXTAREA' || el?.isContentEditable
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
          // 1-9 jump directly; 0 means "the tenth", and shift+1..2 reach 11 and 12 so the
          // deck can grow past ten without losing keyboard jumps.
          if (/^[1-9]$/.test(e.key)) go(Number(e.key) - 1)
          if (e.key === '0') go(9)
          if (e.key === '!') go(10)
          if (e.key === '@') go(11)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [i, go])

  const slide = SLIDES[i]
  const shift = reduce ? 0 : 26

  return (
    <>
      {/* Atmosphere. Two slow aurora blooms and a grain layer sit behind every slide, so the
          deck reads as one lit object rather than ten flat pages. Both are fixed and
          pointer-events:none, and the drift stops entirely under prefers-reduced-motion. */}
      <div className="bloom" aria-hidden="true" />
      <div className="grain" aria-hidden="true" />
      <div className="deck">
      <nav className="rail" aria-label="Slides">
        {SLIDES.map((s, n) => (
          <button
            key={s.id}
            className="rail-mark"
            data-state={n === i ? 'here' : n < i ? 'seen' : 'ahead'}
            onClick={() => go(n)}
            aria-current={n === i ? 'step' : undefined}
            aria-label={`Slide ${n + 1}: ${s.title}`}
          >
            {String(n + 1).padStart(2, '0')}
          </button>
        ))}
      </nav>

      <div className="stage" ref={stageRef}>
        {/* No AnimatePresence anywhere in this shell, on purpose.
            Under React 18 StrictMode, framer-motion's exit callback can be swallowed by the
            double-invoked effect. With `mode="wait"` that wedges the deck outright — the
            counter advances and the content never changes. Without it, exited slides simply
            never unmount and pile up in the DOM. Both were reproduced here at 1280x720.
            A deck has exactly one job on the day, so the outgoing slide is not animated at
            all: the incoming one is keyed and animates in, which reads the same to a room and
            cannot fail. */}
        <motion.section
          key={slide.id}
          className="slide"
          initial={{ opacity: 0, x: dir * shift }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: reduce ? 0 : 0.3, ease: [0.22, 0.61, 0.36, 1] }}
          aria-label={slide.title}
          // Slides carry a temperature. The cold open and the turn go dark, so the bright
          // slides between them read as daylight and the turn lands as a change in the room.
          data-tone={slide.tone ?? 'light'}
        >
          <slide.Body />
        </motion.section>

        <div className="footer">
          <span>SynthProof</span>
          <span>
            {notes ? 'N notes · ' : ''}
            {'←/→ move · Esc overview · N notes'}
          </span>
          <span className="mono">
            {String(i + 1).padStart(2, '0')} / {String(SLIDES.length).padStart(2, '0')}
          </span>
        </div>

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
                <span
                  className={`mono ${n === i ? 'grad-p' : ''}`}
                  style={{ fontSize: 10, letterSpacing: '0.22em' }}
                >
                  {String(n + 1).padStart(2, '0')}
                </span>
                <span style={{ fontSize: 17, color: 'var(--ink)', lineHeight: 1.25 }}>
                  {s.title}
                </span>
                <span style={{ fontSize: 12.5, lineHeight: 1.35 }}>{s.blurb}</span>
              </button>
            ))}
          </motion.div>
        )}
        </div>
      </div>
    </>
  )
}
