import { Fragment } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import type { ReactNode } from 'react'

/**
 * Flowchart primitives.
 *
 * A picture of "what happens in what order" beats a paragraph describing it, especially for
 * a panel that does not know the field. These are deliberately chunky — thick outlines, hard
 * shadows, solid arrowheads — because everything here has to survive being projected and
 * read from the back of a room.
 *
 * Nodes reveal one after another so the presenter can talk over the sequence instead of
 * facing a finished diagram all at once.
 */

export type Tone = 'plain' | 'violet' | 'coral' | 'cyan' | 'yellow' | 'green' | 'red'

const TONE_CLASS: Record<Tone, string> = {
  plain: '',
  violet: 'card-violet',
  coral: 'card-coral',
  cyan: 'card-cyan',
  yellow: 'card-yellow',
  green: 'card-green',
  red: 'card-red',
}

export type Step = {
  title: string
  sub?: string
  tone?: Tone
  /** Small pill on the node — "FREE", "COSTS BUDGET", "STOP". */
  tag?: { text: string; kind?: 'free' | 'cost' | 'stop' }
}

/**
 * A left-to-right chain of boxes joined by arrows.
 * `onPick` makes the boxes clickable, which is how the pipeline slide works.
 */
export function Flow({
  steps,
  active,
  onPick,
  compact = false,
}: {
  steps: Step[]
  active?: number
  onPick?: (i: number) => void
  compact?: boolean
}) {
  const reduce = useReducedMotion()
  return (
    <div className="flow" style={{ gap: compact ? 0 : undefined }}>
      {steps.map((s, i) => (
        <Fragment key={s.title + i}>
          {i > 0 && (
            <motion.div
              className="flow-arrow"
              initial={{ opacity: reduce ? 1 : 0, scaleX: reduce ? 1 : 0.3 }}
              animate={{ opacity: 1, scaleX: 1 }}
              transition={{ duration: reduce ? 0 : 0.25, delay: reduce ? 0 : i * 0.12 - 0.06 }}
              style={{ transformOrigin: 'left center' }}
              aria-hidden="true"
            />
          )}
          <motion.div
            initial={{ opacity: reduce ? 1 : 0, y: reduce ? 0 : 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: reduce ? 0 : 0.32, delay: reduce ? 0 : i * 0.12 }}
            style={{ flex: '1 1 0', minWidth: 108, display: 'flex' }}
          >
            {onPick ? (
              <button
                className={`flow-node ${TONE_CLASS[s.tone ?? 'plain']}`}
                aria-pressed={active === i}
                onClick={() => onPick(i)}
                style={{ width: '100%' }}
              >
                <NodeInner step={s} />
              </button>
            ) : (
              <div
                className={`flow-node ${TONE_CLASS[s.tone ?? 'plain']}`}
                style={{ width: '100%' }}
              >
                <NodeInner step={s} />
              </div>
            )}
          </motion.div>
        </Fragment>
      ))}
    </div>
  )
}

function NodeInner({ step }: { step: Step }) {
  return (
    <>
      <span className="flow-title">{step.title}</span>
      {step.sub && <span className="flow-sub">{step.sub}</span>}
      {step.tag && (
        <span className={`tag tag-${step.tag.kind ?? 'free'}`}>{step.tag.text}</span>
      )}
    </>
  )
}

/** A top-to-bottom chain, for when the story is a sequence of consequences. */
export function FlowDown({ steps }: { steps: Step[] }) {
  const reduce = useReducedMotion()
  return (
    <div style={{ display: 'grid', justifyItems: 'stretch' }}>
      {steps.map((s, i) => (
        <Fragment key={s.title + i}>
          {i > 0 && (
            <motion.div
              className="flow-down"
              initial={{ opacity: reduce ? 1 : 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: reduce ? 0 : 0.2, delay: reduce ? 0 : i * 0.14 - 0.07 }}
              aria-hidden="true"
            />
          )}
          <motion.div
            className={`flow-node ${TONE_CLASS[s.tone ?? 'plain']}`}
            initial={{ opacity: reduce ? 1 : 0, x: reduce ? 0 : -12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: reduce ? 0 : 0.3, delay: reduce ? 0 : i * 0.14 }}
          >
            <NodeInner step={s} />
          </motion.div>
        </Fragment>
      ))}
    </div>
  )
}

/**
 * Two boxes that do not connect, with the gap called out between them.
 * Used on slide 2, where the whole point is that the two halves never meet.
 */
export function Gap({
  left,
  right,
  middle,
}: {
  left: ReactNode
  right: ReactNode
  middle: string
}) {
  const reduce = useReducedMotion()
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'minmax(0,1fr) auto minmax(0,1fr)',
        gap: '0.9rem',
        alignItems: 'center',
      }}
    >
      <motion.div
        initial={{ opacity: reduce ? 1 : 0, x: reduce ? 0 : -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: reduce ? 0 : 0.4 }}
        style={{ height: '100%' }}
      >
        {left}
      </motion.div>

      <motion.div
        initial={{ opacity: reduce ? 1 : 0, scale: reduce ? 1 : 0.7 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: reduce ? 0 : 0.35, delay: reduce ? 0 : 0.35 }}
        style={{ display: 'grid', placeItems: 'center', gap: 4 }}
      >
        <span
          style={{
            fontSize: 30,
            fontWeight: 900,
            color: 'var(--red)',
            lineHeight: 1,
          }}
          aria-hidden="true"
        >
          ⇹
        </span>
        <span
          style={{
            fontSize: 11,
            fontWeight: 800,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            background: 'var(--red)',
            color: '#fff',
            padding: '3px 8px',
            borderRadius: 999,
            border: '2.5px solid var(--ink)',
            whiteSpace: 'nowrap',
          }}
        >
          {middle}
        </span>
      </motion.div>

      <motion.div
        initial={{ opacity: reduce ? 1 : 0, x: reduce ? 0 : 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: reduce ? 0 : 0.4, delay: reduce ? 0 : 0.15 }}
        style={{ height: '100%' }}
      >
        {right}
      </motion.div>
    </div>
  )
}
