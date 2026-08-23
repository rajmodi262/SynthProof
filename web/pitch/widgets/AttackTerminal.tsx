import { useEffect, useRef, useState } from 'react'

/**
 * The attacker's console.
 *
 * A defence that is asserted is forgettable; a defence you watch fail to be broken is not.
 * This types out an attacker's session against a released dataset — the same session that
 * worked on the "anonymised" file a moment earlier — and ends with the attacker unable to
 * distinguish the target from anyone else.
 *
 * The transcript is a SCRIPTED ILLUSTRATION of the design, flagged on screen. This is a
 * proposal deck; dressing invented output as a captured session would be precisely the kind
 * of overclaim the product exists to make impossible.
 *
 * Typing is driven by timers rather than frames so it still runs where rAF is throttled.
 */

type Line = { text: string; kind: 'cmd' | 'out' | 'ok' | 'bad' | 'dim' }

const SCRIPT: Line[] = [
  { text: '# Target: one patient. I know their ZIP, birthday and sex.', kind: 'dim' },
  { text: '$ attack --file anonymised_2024.csv --zip 411038 --dob 1971-04-02 --sex M', kind: 'cmd' },
  { text: 'matches found: 1', kind: 'bad' },
  { text: 'IDENTIFIED  →  diagnosis: Type II diabetes', kind: 'bad' },
  { text: '', kind: 'dim' },
  { text: '# Now the same attack against a SynthProof release.', kind: 'dim' },
  { text: '$ attack --file synthproof_release.csv --zip 411038 --dob 1971-04-02 --sex M', kind: 'cmd' },
  { text: 'matches found: 0', kind: 'ok' },
  { text: '', kind: 'dim' },
  { text: '$ attack --mode membership --target patient_00412', kind: 'cmd' },
  { text: 'confidence the target is in this dataset: 51%', kind: 'out' },
  { text: 'a coin flip is 50%.  NOT IDENTIFIED', kind: 'ok' },
]

export function AttackTerminal() {
  const [n, setN] = useState(0)
  const [running, setRunning] = useState(false)
  const boxRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!running) return
    if (n >= SCRIPT.length) {
      setRunning(false)
      return
    }
    // Command lines land slower than output — it reads like someone typing, then a machine
    // answering.
    const delay = SCRIPT[n].kind === 'cmd' ? 620 : 380
    const id = setTimeout(() => setN((v) => v + 1), delay)
    return () => clearTimeout(id)
  }, [running, n])

  useEffect(() => {
    boxRef.current?.scrollTo({ top: boxRef.current.scrollHeight })
  }, [n])

  const done = n >= SCRIPT.length

  return (
    <div style={{ display: 'grid', gap: '0.6rem' }}>
      <div className="term" ref={boxRef}>
        {SCRIPT.slice(0, n).map((l, i) => (
          <div key={i} className={`term-line term-${l.kind}`}>
            {l.text || ' '}
          </div>
        ))}
        {running && <span className="term-caret" aria-hidden="true" />}
        {n === 0 && <div className="term-line term-dim">press run to watch an attacker try</div>}
      </div>

      <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center', flexWrap: 'wrap' }}>
        <button
          className="btn btn-hot"
          data-on="1"
          onClick={() => {
            if (done) setN(0)
            setRunning(true)
          }}
          disabled={running}
        >
          {running ? 'running…' : done ? '↻ run again' : '▶ run the attack'}
        </button>
        {done && (
          <p style={{ margin: 0, fontSize: '1.15rem', fontWeight: 700 }}>
            Same attacker. Same target. <span className="hi hi-green">51% is a coin flip.</span>
          </p>
        )}
      </div>

      <p className="small" style={{ margin: 0, display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'baseline' }}>
        <span className="flag flag-illustrative">scripted illustration</span>
        <span>A worked example of the behaviour we are building, not a captured session.</span>
      </p>
    </div>
  )
}
