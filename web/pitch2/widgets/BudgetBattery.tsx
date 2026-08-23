import { useState } from 'react'

/**
 * The privacy budget, as a phone battery.
 *
 * Everyone in the room already knows what a battery at 4% feels like, and that it does not
 * refill by being careful. Ask questions, watch it drain, hit zero and the system refuses.
 *
 * The point the panel should leave with is the free one: building the synthetic table costs
 * nothing. That is the surprising part, and it is much easier to believe when they have just
 * watched every other button take a bite out of the bar.
 */

type Q = { label: string; cost: number; note: string; free?: boolean }

const QUESTIONS: Q[] = [
  { label: 'Read the column names you declared', cost: 0, note: 'Public. Reveals nobody.', free: true },
  { label: 'Work out what values a column holds', cost: 18, note: 'A question about real people. Most tools do this for free.' },
  { label: 'Count patients per age group', cost: 22, note: 'A count of real people, with noise added.' },
  { label: 'Count age against diagnosis', cost: 34, note: 'A bigger question, so a bigger bite.' },
  { label: 'Build the synthetic table', cost: 0, note: 'Free — and that is a theorem, not a shortcut.', free: true },
]

export function BudgetBattery() {
  const [spent, setSpent] = useState(0)
  const [last, setLast] = useState<Q | null>(null)
  const [refused, setRefused] = useState(false)

  const left = Math.max(0, 100 - spent)
  const empty = left <= 0

  const ask = (q: Q) => {
    if (empty && !q.free) {
      setRefused(true)
      setLast(q)
      return
    }
    setRefused(false)
    setLast(q)
    setSpent((s) => Math.min(100, s + q.cost))
  }

  const tone = left > 55 ? 'jade' : left > 20 ? 'gold' : 'crimson'

  return (
    <div style={{ display: 'grid', gap: '0.6rem' }}>
      <div className="batt-row">
        <div className="batt" data-empty={empty ? '1' : '0'}>
          <div className={`batt-fill batt-${tone}`} style={{ width: `${left}%` }} />
          <span className="batt-pct">{left}%</span>
        </div>
        <span className="batt-cap" aria-hidden="true" />
      </div>

      <div className="batt-qs">
        {QUESTIONS.map((q) => (
          <button
            key={q.label}
            className="btn"
            data-on={last?.label === q.label ? '1' : '0'}
            onClick={() => ask(q)}
          >
            {q.label}
            <span className={`batt-cost ${q.free ? 'batt-free' : ''}`}>
              {q.free ? 'FREE' : `−${q.cost}%`}
            </span>
          </button>
        ))}
        <button className="btn" onClick={() => { setSpent(0); setLast(null); setRefused(false) }}>
          ↻ new dataset
        </button>
      </div>

      <div className={`card ${refused ? 'card-crimson' : empty ? 'card-crimson' : 'card-gold'}`}>
        <p className="lede" style={{ margin: 0, maxWidth: 'none' }}>
          {refused ? (
            <>
              <span className="hi hi-crimson">REFUSED.</span> The budget is gone. Not &ldquo;be
              more careful&rdquo; — <strong>gone.</strong> Any further answer would break the
              promise we made to the people in this file.
            </>
          ) : empty ? (
            <>
              <span className="hi hi-crimson">Empty.</span> Try asking another question and the
              system will refuse.
            </>
          ) : last ? (
            <>
              <strong>{last.label}.</strong> {last.note}
            </>
          ) : (
            <>
              Every dataset gets <strong>one</strong> budget. Press the buttons and watch it go.
            </>
          )}
        </p>
      </div>

      <p className="small" style={{ margin: 0, display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'baseline' }}>
        <span className="flag">illustration</span>
        <span>Costs chosen to show the shape of the idea, not measured prices.</span>
      </p>
    </div>
  )
}
