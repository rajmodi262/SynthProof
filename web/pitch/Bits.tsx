import { useEffect, useRef, useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import type { ReactNode } from 'react'

/** Shared display pieces. Kept in one file so the visual language stays consistent
 *  across ten slides rather than being re-invented on each. */

/**
 * A number that counts up when it appears.
 *
 * Used only where the magnitude is the point — 436 tests, 4,711 canaries. A count-up on a
 * number nobody is meant to compare is just motion for its own sake, so most figures in the
 * deck are static.
 */
export function CountUp({
  to,
  decimals = 0,
  duration = 1.1,
  prefix = '',
  suffix = '',
}: {
  to: number
  decimals?: number
  duration?: number
  prefix?: string
  suffix?: string
}) {
  const reduce = useReducedMotion()
  const [v, setV] = useState(reduce ? to : 0)
  const ref = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    if (reduce) {
      setV(to)
      return
    }
    let raf = 0
    const t0 = performance.now()
    const tick = (now: number) => {
      const p = Math.min(1, (now - t0) / (duration * 1000))
      // Ease-out cubic: fast arrival, slow settle, which reads as a value landing
      // rather than a slot machine spinning down.
      setV(to * (1 - Math.pow(1 - p, 3)))
      if (p < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [to, duration, reduce])

  return (
    <span ref={ref} className="mono">
      {prefix}
      {v.toLocaleString('en-US', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      })}
      {suffix}
    </span>
  )
}

/** Staggered entrance for a slide's blocks. */
export function Stagger({ children }: { children: ReactNode }) {
  const reduce = useReducedMotion()
  return (
    <motion.div
      initial="hide"
      animate="show"
      variants={{ show: { transition: { staggerChildren: reduce ? 0 : 0.075 } } }}
      style={{ display: 'contents' }}
    >
      {children}
    </motion.div>
  )
}

export function Line({ children }: { children: ReactNode }) {
  const reduce = useReducedMotion()
  return (
    <motion.div
      variants={{
        hide: { opacity: 0, y: reduce ? 0 : 14, filter: reduce ? 'none' : 'blur(5px)' },
        show: {
          opacity: 1,
          y: 0,
          filter: 'blur(0px)',
          transition: { duration: reduce ? 0 : 0.5, ease: [0.22, 0.61, 0.36, 1] },
        },
      }}
    >
      {children}
    </motion.div>
  )
}

/**
 * A horizontal bar that fills on mount, in one of the two colour ramps.
 * `frac` is a 0..1 share of the axis; the caller owns the scale so two bars on one
 * axis stay comparable.
 */
export function Bar({
  frac,
  ramp,
  height = 16,
  delay = 0,
}: {
  frac: number
  ramp: 'p' | 'a' | 'bad'
  height?: number
  delay?: number
}) {
  const reduce = useReducedMotion()
  const bg = ramp === 'p' ? 'var(--violet)' : ramp === 'a' ? 'var(--coral)' : 'var(--red)'
  return (
    <div
      style={{
        height,
        borderRadius: 999,
        background: '#fff',
        overflow: 'hidden',
        border: '2.5px solid var(--ink)',
      }}
    >
      <motion.div
        initial={{ width: reduce ? `${frac * 100}%` : 0 }}
        animate={{ width: `${Math.min(100, frac * 100)}%` }}
        transition={{ duration: reduce ? 0 : 0.75, delay: reduce ? 0 : delay, ease: [0.22, 0.61, 0.36, 1] }}
        style={{ height: '100%', background: bg }}
      />
    </div>
  )
}

/** A headline figure with its label and a caption. The workhorse of the numeric slides. */
export function Stat({
  value,
  label,
  hint,
  ramp = 'p',
  size = 'clamp(2.2rem, 3.6vw, 3.1rem)',
}: {
  value: ReactNode
  label: string
  hint?: ReactNode
  ramp?: 'p' | 'a' | 'ok' | 'bad' | 'plain'
  size?: string
}) {
  const cls =
    ramp === 'p'
      ? 'violet'
      : ramp === 'a'
        ? 'coral'
        : ramp === 'ok'
          ? 'green'
          : ramp === 'bad'
            ? 'red'
            : ''
  return (
    <div>
      <div className="eyebrow" style={{ marginBottom: '0.35rem' }}>
        {label}
      </div>
      <div className={`hero-num ${cls}`} style={{ fontSize: size }}>
        {value}
      </div>
      {hint && (
        <div style={{ fontSize: 13, color: 'var(--ink-3)', marginTop: '0.4rem', lineHeight: 1.4 }}>
          {hint}
        </div>
      )}
    </div>
  )
}

/** Inline source path, used throughout the speaker notes. */
export function Src({ children }: { children: ReactNode }) {
  return <span className="mono">{children}</span>
}
