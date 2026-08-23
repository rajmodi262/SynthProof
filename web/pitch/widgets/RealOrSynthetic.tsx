import { useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'

/**
 * "Which of these two tables is the real one?"
 *
 * The point of the reveal is NOT that synthetic data is indistinguishable — it is that being
 * indistinguishable by eye proves nothing about privacy. A table that copied ten real records
 * verbatim would also look perfectly plausible here. That is the whole argument for measuring
 * rather than eyeballing, and it is the sentence that follows the reveal.
 *
 * Both tables below are illustrative rows in the shape of UCI Adult, marked as such on
 * screen. Showing genuine rows from the real dataset in a slide deck would be a small
 * version of the exact failure this project is about.
 */

type Row = [string, string, string, string]

const HEAD = ['age', 'education', 'hours/wk', 'income']

const A: Row[] = [
  ['39', 'Bachelors', '40', '<=50K'],
  ['50', 'Bachelors', '13', '<=50K'],
  ['38', 'HS-grad', '40', '<=50K'],
  ['53', '11th', '40', '<=50K'],
  ['28', 'Bachelors', '40', '<=50K'],
  ['37', 'Masters', '40', '<=50K'],
]

const B: Row[] = [
  ['41', 'HS-grad', '45', '<=50K'],
  ['33', 'Some-college', '40', '<=50K'],
  ['47', 'Bachelors', '50', '>50K'],
  ['29', 'HS-grad', '38', '<=50K'],
  ['56', 'Masters', '42', '>50K'],
  ['35', 'Assoc-voc', '40', '<=50K'],
]

export function RealOrSynthetic() {
  const [picked, setPicked] = useState<'A' | 'B' | null>(null)
  const reduce = useReducedMotion()

  return (
    <div style={{ display: 'grid', gap: '1rem' }}>
      <p className="body" style={{ margin: 0, maxWidth: 'none' }}>
        One of these came out of a differentially private generator. Which one?
      </p>

      <div className="cols cols-2" style={{ gap: '1.5rem' }}>
        {(['A', 'B'] as const).map((k) => {
          const rows = k === 'A' ? A : B
          const chosen = picked === k
          return (
            <button
              key={k}
              onClick={() => setPicked(k)}
              disabled={picked !== null}
              style={{
                textAlign: 'left',
                cursor: picked ? 'default' : 'pointer',
                background: '#fff',
                border: '1px solid',
                borderRadius: 14,
                boxShadow: chosen ? '0 0 26px rgba(108,76,241,0.35)' : 'none',
                borderColor: chosen ? 'var(--violet)' : 'var(--ink)',
                padding: '0.9rem 1rem',
                color: 'inherit',
                display: 'grid',
                gap: '0.5rem',
              }}
            >
              <span className="eyebrow">table {k}</span>
              <table className="data">
                <thead>
                  <tr>
                    {HEAD.map((h) => (
                      <th key={h}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r, i) => (
                    <tr key={i}>
                      {r.map((c, j) => (
                        <td key={j} className={j === 0 || j === 2 ? 'num' : undefined}>
                          {c}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </button>
          )
        })}
      </div>

      {picked && (
        <motion.div
          className="card"
          initial={{ opacity: 0, y: reduce ? 0 : 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: reduce ? 0 : 0.25 }}
        >
          <p className="body" style={{ margin: 0, maxWidth: 'none', color: 'var(--ink)' }}>
            It doesn't matter which you picked —{' '}
            <strong>looking plausible is not the same as being safe.</strong> A generator that
            copied ten real people's rows word for word would produce a table that looks
            exactly this reasonable. You cannot see privacy. That is why the rest of this deck
            is about measuring it.
          </p>
        </motion.div>
      )}

      <p className="small" style={{ margin: 0, display: 'flex', gap: '0.6rem', alignItems: 'baseline', flexWrap: 'wrap' }}>
        <span className="flag flag-illustrative">both tables illustrative</span>
        <span>
          Rows in the shape of UCI Adult, written for this slide. Printing genuine rows from a
          real dataset in a pitch deck would be a small version of the failure this project is
          about.
        </span>
      </p>
    </div>
  )
}
