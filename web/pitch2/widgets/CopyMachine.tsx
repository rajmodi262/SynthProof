import { useState } from 'react'

/**
 * Why "it's fake so it's safe" is false.
 *
 * Two synthetic tables, side by side. Press the button and one of them turns out to contain a
 * real patient's row, word for word, highlighted in crimson. The other does not.
 *
 * The room's instinct is that generated data cannot leak. This is the fastest way to break
 * that instinct: nothing in "make me a similar table" forbids reprinting someone, and a
 * memorised outlier is exactly the row a model is most likely to reproduce.
 *
 * Rows are invented for this slide, flagged on screen. Printing genuine records in a pitch
 * deck would be a small version of the failure the project is about.
 */

type Row = [string, string, string, string]

const REAL: Row[] = [
  ['96', 'F', 'Warje', 'Amyloidosis'],
  ['34', 'M', 'Aundh', 'Type II diabetes'],
  ['51', 'F', 'Kothrud', 'Hypertension'],
  ['28', 'M', 'Baner', 'Asthma'],
]

const NAIVE: Row[] = [
  ['41', 'M', 'Kharadi', 'Hypertension'],
  ['96', 'F', 'Warje', 'Amyloidosis'], // the memorised outlier, copied verbatim
  ['37', 'F', 'Wakad', 'Asthma'],
  ['62', 'M', 'Camp', 'Type II diabetes'],
]

const OURS: Row[] = [
  ['44', 'M', 'Hadapsar', 'Hypertension'],
  ['58', 'F', 'Deccan', 'Type II diabetes'],
  ['31', 'M', 'Aundh', 'Asthma'],
  ['67', 'F', 'Baner', 'Hypertension'],
]

const HEAD = ['age', 'sex', 'area', 'diagnosis']

export function CopyMachine() {
  const [checked, setChecked] = useState(false)

  const isCopy = (r: Row) => REAL.some((x) => x.join('|') === r.join('|'))

  return (
    <div style={{ display: 'grid', gap: '0.6rem' }}>
      <div className="cols cols-3">
        <Table title="The real records" rows={REAL} tone="card-sand" mark={false} checked={false} />
        <Table
          title="A normal generator"
          rows={NAIVE}
          tone={checked && NAIVE.some(isCopy) ? 'card-crimson' : ''}
          mark
          checked={checked}
          isCopy={isCopy}
        />
        <Table
          title="With SynthProof"
          rows={OURS}
          tone={checked ? 'card-jade' : ''}
          mark
          checked={checked}
          isCopy={isCopy}
        />
      </div>

      <div style={{ display: 'flex', gap: '0.7rem', alignItems: 'center', flexWrap: 'wrap' }}>
        <button className="btn btn-big" data-on="1" onClick={() => setChecked((c) => !c)}>
          {checked ? '↻ reset' : '🔍 check both against the real records'}
        </button>
        {checked && (
          <p style={{ margin: 0, fontSize: '1.2rem', fontWeight: 700 }}>
            One row is <span className="hi hi-crimson">a real patient, copied word for word.</span>
          </p>
        )}
      </div>

      <p className="small" style={{ margin: 0, display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'baseline' }}>
        <span className="flag">invented rows</span>
        <span>
          Written for this slide. Printing genuine records in a pitch deck would be a small
          version of the failure this project is about.
        </span>
      </p>
    </div>
  )
}

function Table({
  title,
  rows,
  tone,
  mark,
  checked,
  isCopy,
}: {
  title: string
  rows: Row[]
  tone: string
  mark: boolean
  checked: boolean
  isCopy?: (r: Row) => boolean
}) {
  return (
    <div className={`card ${tone}`} style={{ padding: '0.6rem 0.7rem' }}>
      <span className="cm-title">{title}</span>
      <table className="cm">
        <thead>
          <tr>
            {HEAD.map((h) => (
              <th key={h}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => {
            const hit = mark && checked && isCopy?.(r)
            return (
              <tr key={i} data-hit={hit ? '1' : '0'}>
                {r.map((c, j) => (
                  <td key={j}>{c}</td>
                ))}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
