import { useEffect, useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import type { ReactNode } from 'react'

/**
 * Layout primitives that give the deck a RANGE of rhythms.
 *
 * The previous version's real failure was not colour, it was sameness: ten slides with an
 * identical shape — label, headline, cards, caption — read as a brochure whatever palette
 * they wore. A deck feels alive when a full-bleed single sentence sits next to a dense data
 * slide next to a quiet close. That variation is the energy.
 *
 * So these exist to be visually unlike each other, and each slide picks the one its content
 * actually needs.
 */

/* ── the scoreboard ──────────────────────────────────────────────────────────
   The deck's recurring motif. Two numbers appear once the system is explained,
   and follow the story from then on. On the turn slide the second number is
   struck through — the same object the room has been trusting for three slides
   is revoked in front of them. A motif that changes meaning is worth more than
   any single slide.                                                            */

export function Scoreboard({
  proved,
  audited,
  revoked = false,
  dark = false,
}: {
  proved: number
  audited: number
  revoked?: boolean
  dark?: boolean
}) {
  const reduce = useReducedMotion()
  return (
    <motion.div
      className="scoreboard"
      data-dark={dark ? '1' : '0'}
      initial={{ opacity: 0, y: reduce ? 0 : -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: reduce ? 0 : 0.4 }}
    >
      <div className="sb-cell">
        <span className="sb-label">what we PROVED</span>
        <span className="sb-num violet">{proved.toFixed(3)}</span>
      </div>
      <div className="sb-div" aria-hidden="true" />
      <div className="sb-cell">
        <span className="sb-label">what the ATTACK got</span>
        <span className={`sb-num ${revoked ? 'sb-struck' : 'coral'}`}>{audited.toFixed(3)}</span>
        {revoked && <span className="sb-revoked">meaningless — see the tape</span>}
      </div>
    </motion.div>
  )
}

/* ── the statement ───────────────────────────────────────────────────────────
   One sentence, as large as it will go, and nothing else on the slide. Used
   exactly three times in ten slides. Used more often it stops being a beat.  */

export function Statement({
  children,
  sub,
  align = 'left',
}: {
  children: ReactNode
  sub?: ReactNode
  align?: 'left' | 'center'
}) {
  const reduce = useReducedMotion()
  return (
    <div style={{ display: 'grid', gap: '1.1rem', justifyItems: align === 'center' ? 'center' : 'start' }}>
      <motion.h2
        className="statement"
        style={{ textAlign: align }}
        initial={{ opacity: 0, y: reduce ? 0 : 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: reduce ? 0 : 0.55, ease: [0.22, 0.61, 0.36, 1] }}
      >
        {children}
      </motion.h2>
      {sub && (
        <motion.p
          className="statement-sub"
          style={{ textAlign: align }}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: reduce ? 0 : 0.5, delay: reduce ? 0 : 0.45 }}
        >
          {sub}
        </motion.p>
      )}
    </div>
  )
}

/* ── the beat ────────────────────────────────────────────────────────────────
   A line that lands after a pause. Used on the cold open and the turn, where
   the timing is the whole effect.                                             */

export function Beat({ children, delay = 1.1 }: { children: ReactNode; delay?: number }) {
  const reduce = useReducedMotion()
  return (
    <motion.div
      initial={{ opacity: 0, y: reduce ? 0 : 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: reduce ? 0 : 0.6, delay: reduce ? 0 : delay }}
    >
      {children}
    </motion.div>
  )
}

/* ── the two-papers device ───────────────────────────────────────────────────
   The pitch's climax. Two abstracts from the same data, side by side: the one
   that would have been easy to write, and the one that is true. Nothing else
   in the deck demonstrates the project's actual argument as directly.        */

export function TwoPapers({
  fake,
  real,
}: {
  fake: { title: string; claims: string[] }
  real: { title: string; claims: string[] }
}) {
  const reduce = useReducedMotion()
  return (
    <div className="cols cols-2" style={{ alignItems: 'stretch' }}>
      <motion.div
        className="paper paper-fake"
        initial={{ opacity: 0, rotate: reduce ? 0 : -1.6, y: reduce ? 0 : 16 }}
        animate={{ opacity: 1, rotate: reduce ? 0 : -1.2, y: 0 }}
        transition={{ duration: reduce ? 0 : 0.5 }}
      >
        <span className="paper-stamp paper-stamp-fake">we did not write this</span>
        <h3 className="paper-title">{fake.title}</h3>
        <ul className="paper-list">
          {fake.claims.map((c) => (
            <li key={c}>
              <span className="paper-tick paper-tick-fake" aria-hidden="true">
                ✓
              </span>
              {c}
            </li>
          ))}
        </ul>
      </motion.div>

      <motion.div
        className="paper paper-real"
        initial={{ opacity: 0, rotate: reduce ? 0 : 1.6, y: reduce ? 0 : 16 }}
        animate={{ opacity: 1, rotate: reduce ? 0 : 0.9, y: 0 }}
        transition={{ duration: reduce ? 0 : 0.5, delay: reduce ? 0 : 0.18 }}
      >
        <span className="paper-stamp paper-stamp-real">this is our thesis</span>
        <h3 className="paper-title">{real.title}</h3>
        <ul className="paper-list">
          {real.claims.map((c) => (
            <li key={c}>
              <span className="paper-tick paper-tick-real" aria-hidden="true">
                •
              </span>
              {c}
            </li>
          ))}
        </ul>
      </motion.div>
    </div>
  )
}

/* ── the tape measure ────────────────────────────────────────────────────────
   The single image the whole project reduces to. Drawn full width so it reads
   as a physical object rather than a chart: a tape that stops, and a target it
   cannot reach.                                                               */

export function TapeMeasure({
  reach,
  target,
  reachLabel,
  targetLabel,
}: {
  reach: number
  target: number
  reachLabel: string
  targetLabel: string
}) {
  const reduce = useReducedMotion()
  // CSS transitions, NOT framer-motion, for everything positional here.
  //
  // requestAnimationFrame is throttled to nothing whenever the page is not compositing — a
  // backgrounded tab, some remote-desktop sessions, certain projector mirroring modes. A
  // JS-driven animation frozen at its start value leaves this slide showing an EMPTY tape,
  // which inverts the argument. A CSS transition degrades the other way: the final width is
  // in the style attribute, so if the transition never runs the tape is simply already
  // correct. `armed` flips on a timeout (not a frame) purely to give the reveal something
  // to animate from when the page IS compositing.
  const [armed, setArmed] = useState(false)
  useEffect(() => {
    const id = setTimeout(() => setArmed(true), 30)
    return () => clearTimeout(id)
  }, [])

  const axis = Math.max(target, reach) * 1.15
  const pct = (v: number) => (v / axis) * 100
  const ticks = Array.from({ length: Math.floor(axis) + 1 }, (_, i) => i)
  const grown = armed || reduce
  const ease = reduce ? 'none' : 'width 900ms cubic-bezier(0.22,0.61,0.36,1)'

  return (
    <div className="tape">
      <div className="tape-track">
        {ticks.map((n) => (
          <span key={n} className="tape-tick" style={{ left: `${pct(n)}%` }}>
            <i />
            <em>{n}</em>
          </span>
        ))}

        <div
          className="tape-fill"
          style={{ width: `${grown ? pct(reach) : 0}%`, transition: ease }}
        >
          <span className="tape-fill-label">{reachLabel}</span>
        </div>

        <div
          className="tape-end"
          style={{
            left: `${grown ? pct(reach) : 0}%`,
            transition: reduce ? 'none' : 'left 900ms cubic-bezier(0.22,0.61,0.36,1)',
          }}
        />

        <div className="tape-target" style={{ left: `${pct(target)}%` }}>
          <span className="tape-target-flag">{targetLabel}</span>
        </div>

        {/* The gap the tape cannot cross. Hatched, so it reads as absence. */}
        {target > reach && (
          <div
            className="tape-gap"
            style={{
              left: `${pct(reach)}%`,
              width: `${pct(target) - pct(reach)}%`,
              opacity: grown ? 1 : 0,
              transition: reduce ? 'none' : 'opacity 400ms ease 700ms',
            }}
          >
            <span>can never be measured</span>
          </div>
        )}
      </div>
    </div>
  )
}
