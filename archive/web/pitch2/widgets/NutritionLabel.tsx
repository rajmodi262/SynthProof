import { useState } from 'react'

/**
 * The output, drawn as a food nutrition label.
 *
 * Every person in the room already knows how to read one of these, which is the entire
 * reason for the metaphor: it turns "machine-readable privacy certificate" into an object
 * the panel can parse in three seconds without being taught anything.
 *
 * The values shown are an EXAMPLE release, flagged as such on screen. This is a proposal
 * deck; presenting illustrative figures as measurements would be the exact failure the
 * product is designed to prevent.
 */

type Row = { label: string; value: string; sub?: string; bold?: boolean; tone?: 'ok' | 'warn' | 'bad' }

const ROWS: Row[] = [
  { label: 'Records released', value: '6,000', bold: true },
  { label: 'Columns', value: '12' },
  { label: 'Privacy budget spent', value: '0.91', sub: 'lower is safer', bold: true, tone: 'ok' },
  { label: '— on learning the columns', value: '0.18' },
  { label: '— on counting groups', value: '0.73' },
  { label: 'Attack result', value: 'nothing found', sub: 'we attacked it ourselves', tone: 'ok' },
  { label: 'Limit of that attack', value: '2.25', sub: 'we print this so the line above cannot be misread', bold: true, tone: 'warn' },
  { label: 'Columns you declared', value: '12 of 12', tone: 'ok' },
  { label: 'Columns we had to guess', value: '0', tone: 'ok' },
]

export function NutritionLabel() {
  const [open, setOpen] = useState<string | null>('Limit of that attack')

  const EXPLAIN: Record<string, string> = {
    'Records released': 'How many rows are in the synthetic table you were given.',
    Columns: 'How many fields each row has.',
    'Privacy budget spent': 'The whole point. One number for how much of the dataset’s privacy was used up producing this file. Smaller is safer.',
    '— on learning the columns': 'Working out what values a column can hold is itself a question about real people, so it goes on the bill. Most tools do this for free.',
    '— on counting groups': 'Counting how many people fall in each group, with noise added to every count.',
    'Attack result': 'We hide known records in the data and then attack our own output. This is what our attacker managed to recover.',
    'Limit of that attack': 'The most our attack could EVER have found, given how many test records we hid. Printing it next to the line above is the design decision we are proudest of: a zero nobody can interpret is worse than no number at all.',
    'Columns you declared': 'Fields whose possible values you told us up front. These cost nothing, because they reveal nothing about any individual.',
    'Columns we had to guess': 'Fields we had to work out by looking at your data. These cost budget, and we say so.',
  }

  return (
    <div className="cols cols-2" style={{ alignItems: 'start' }}>
      <div className="nl">
        <div className="nl-head">
          <span className="nl-title">Privacy Facts</span>
          <span className="nl-sub">1 synthetic dataset</span>
        </div>
        <div className="nl-rule nl-rule-thick" />
        {ROWS.map((r) => (
          <button
            key={r.label}
            className="nl-row"
            data-bold={r.bold ? '1' : '0'}
            data-open={open === r.label ? '1' : '0'}
            onClick={() => setOpen(r.label)}
          >
            <span className="nl-label">{r.label}</span>
            <span className={`nl-value ${r.tone ? 'nl-' + r.tone : ''}`}>{r.value}</span>
            {r.sub && <span className="nl-note">{r.sub}</span>}
          </button>
        ))}
        <div className="nl-rule" />
        <p className="nl-foot">
          Signed. Anyone with our public key can check this file was not edited after it was
          produced.
        </p>
      </div>

      <div style={{ display: 'grid', gap: '0.7rem' }}>
        <div className="card card-gold">
          <span className="eyebrow" style={{ background: 'var(--ink)' }}>
            {open ?? 'tap any line'}
          </span>
          <p className="body" style={{ margin: '0.5rem 0 0', maxWidth: 'none', color: 'var(--ink)' }}>
            {open ? EXPLAIN[open] : 'Tap any line on the label to see what it means.'}
          </p>
        </div>
        <div className="card card-dark">
          <p className="lede" style={{ margin: 0, maxWidth: 'none', color: 'var(--sand)' }}>
            Nobody ships data with its ingredients listed.{' '}
            <span className="hi hi-gold">We will.</span>
          </p>
        </div>
        <p className="small" style={{ margin: 0, display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'baseline' }}>
          <span className="flag">example label</span>
          <span>Illustrative values for one release, to show the format we are designing.</span>
        </p>
      </div>
    </div>
  )
}
