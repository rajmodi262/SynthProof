import { useState } from 'react'
import type { ReactNode } from 'react'

import type { Shape } from './field'

/**
 * Six slides. Each one is a single moment, and each one drives the shared particle field —
 * the same ~2,600 points spell the name, become a crowd, become two tables, stream through
 * the machine, compact into a certificate, and settle into the closing line.
 *
 * Because the field never unmounts, the transitions ARE the argument: the room watches the
 * data it was just looking at turn into the next idea.
 *
 * This is a proposal deck. Nothing on screen is presented as an experimental result: every
 * figure is either a published finding (attributed in the notes) or an illustration of the
 * design, and every illustration carries a flag.
 */

export type SlideProps = {
  /** Lets a slide re-shape the field in response to an interaction. */
  setShape: (s: Shape) => void
}

export type Slide = {
  id: string
  title: string
  /** The field's resting shape when this slide opens. */
  shape: Shape
  lay: 'centre' | 'bottom' | 'split'
  ivory?: boolean
  Body: (p: SlideProps) => ReactNode
  Notes: () => ReactNode
}

/* ── 1 · the name ────────────────────────────────────────────────────────── */

const S1: Slide = {
  id: 's1',
  title: 'SynthProof',
  shape: { kind: 'word', text: 'SYNTHPROOF', clarity: 1 },
  lay: 'bottom',
  Body: ({ setShape }) => {
    const [clarity, setClarity] = useState(1)
    const set = (v: number) => {
      setClarity(v)
      setShape({ kind: 'word', text: 'SYNTHPROOF', clarity: v })
    }
    const readable = clarity > 0.6
    return (
      <>
        <div className="panel" style={{ maxWidth: 560, marginInline: 'auto', width: '100%' }}>
          <div className="ends" style={{ marginBottom: 4 }}>
            <span className="crimson">private · useless</span>
            <span className="gold">useful · exposed</span>
          </div>
          <input
            type="range"
            min={0}
            max={1}
            step={0.01}
            value={clarity}
            onChange={(e) => set(Number(e.target.value))}
            aria-label="Privacy versus usefulness"
          />
        </div>
        <p className="sub" style={{ textAlign: 'center', marginInline: 'auto', minHeight: '2.5em' }}>
          {readable ? (
            <>
              You can read our name. <strong className="crimson">So can an attacker read the
              people inside.</strong>
            </>
          ) : (
            <>
              Perfectly private — and <strong className="gold">completely useless.</strong>
            </>
          )}
        </p>
        <p className="note" style={{ textAlign: 'center', marginInline: 'auto' }}>
          Every dot is one person&rsquo;s record. Every dataset in the world sits somewhere on
          that slider, and nobody tells you where. · MIT-WPU CSE-AIDS Capstone 2026-27
        </p>
      </>
    )
  },
  Notes: () => (
    <>
      <h4>say — drag it, do not describe it</h4>
      <p>
        Open with the name assembled. First words: <strong>"Every dot on that screen is one
        person's record."</strong>
      </p>
      <p>
        Drag the slider hard LEFT. The name dissolves. "That is perfect privacy — and it is
        completely useless. You cannot even read our name."
      </p>
      <p>
        Drag hard RIGHT. "Now you can read it perfectly. And so can an attacker read the people
        inside."
      </p>
      <p>
        Leave it in the middle and land the line:{' '}
        <strong>"Every dataset in the world is somewhere on that slider. Nobody tells you
        where. That is what we are building."</strong> Then move on — do not explain further.
      </p>
      <h4>the thing to notice</h4>
      <p>
        Those same dots stay with us for all six slides. They become the crowd, the tables, the
        machine, and the certificate. Nothing is ever added or removed.
      </p>
    </>
  ),
}

/* ── 2 · this is you ─────────────────────────────────────────────────────── */

const PINS = ['411004', '411007', '411016', '411021', '411027', '411030', '411033',
  '411038', '411041', '411045', '411048', '411052', '411057', '411061', '411067']
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
const DAYS = Array.from({ length: 31 }, (_, i) => String(i + 1))
const YEARS = Array.from({ length: 60 }, (_, i) => String(2006 - i))

// Sizes of each filter, in order. The counter is 1,00,000 divided by these one after
// another — arithmetic anyone can check, not a lookup in anybody's records.
const BUCKETS = [PINS.length, MONTHS.length, DAYS.length, YEARS.length]
const START = 100_000

const S2: Slide = {
  id: 's2',
  title: 'This is you',
  shape: { kind: 'crowd', survivorsFrac: 1, found: false },
  lay: 'bottom',
  Body: ({ setShape }) => {
    const [v, setV] = useState<string[]>(['', '', '', ''])
    let chosen = 0
    for (const x of v) {
      if (!x) break
      chosen++
    }

    let exact = START
    for (let i = 0; i < chosen; i++) exact /= BUCKETS[i]
    const found = chosen === BUCKETS.length
    const shown = found ? 1 : Math.max(1, Math.round(exact))

    const pick = (i: number) => (e: React.ChangeEvent<HTMLSelectElement>) => {
      const next = [...v]
      next[i] = e.target.value
      for (let k = i + 1; k < next.length; k++) next[k] = ''
      setV(next)
      let c = 0
      for (const x of next) {
        if (!x) break
        c++
      }
      let frac = 1
      for (let k = 0; k < c; k++) frac /= BUCKETS[k]
      setShape({ kind: 'crowd', survivorsFrac: frac, found: c === BUCKETS.length })
    }

    const opts = [PINS, MONTHS, DAYS, YEARS]
    const labels = ['PIN code', 'born', 'day', 'year']

    return (
      <>
        <div className="pickers">
          {labels.map((l, i) => (
            <label key={l}>
              <span className="rail-label">{l}</span>
              <select value={v[i]} onChange={pick(i)} disabled={i > 0 && !v[i - 1]}>
                <option value="">…</option>
                {opts[i].map((o) => (
                  <option key={o}>{o}</option>
                ))}
              </select>
            </label>
          ))}
        </div>

        <div style={{ display: 'flex', gap: '1.4rem', alignItems: 'baseline', justifyContent: 'center', flexWrap: 'wrap' }}>
          <span className="rail-label">people who still match</span>
          <span className={`huge-num ${found ? 'crimson' : 'gold'}`}>
            {shown.toLocaleString('en-IN')}
          </span>
        </div>

        <p className="sub" style={{ textAlign: 'center', marginInline: 'auto', minHeight: '2.4em' }}>
          {found ? (
            <>
              That is <strong className="crimson">one person.</strong> The file had no names in
              it — only a PIN code and a birthday.
            </>
          ) : (
            <>Pick all four. Watch the crowd disappear.</>
          )}
        </p>

        <p className="note" style={{ textAlign: 'center', marginInline: 'auto' }}>
          <span className="flag">illustration</span> A drawn crowd, and 1,00,000 divided by{' '}
          {BUCKETS.join(' × ')} — arithmetic on your own choices, not a lookup in anyone&rsquo;s
          records. The finding it illustrates is Sweeney (2000).
        </p>
      </>
    )
  },
  Notes: () => (
    <>
      <h4>say — hand this to the panel, do not drive it yourself</h4>
      <p>
        <strong>Ask a panel member for their PIN code.</strong> Set it. Then their birth month,
        day, year. Read the counter aloud as it drops: one lakh → six thousand → five hundred →
        eighteen → <strong>one</strong>.
      </p>
      <p>
        Then, quietly: <strong>"That file had no names in it. It had a PIN code and a birthday
        — and it just pointed at one person in this room."</strong>
      </p>
      <p>
        Watch the field while you do it: those are the same dots that spelled our name thirty
        seconds ago. Nothing was added. They just spread out into a city.
      </p>
      <h4>if they push</h4>
      <p>
        Yes, this is a drawing, and the flag on screen says so — the arithmetic is 1,00,000
        divided by the four dropdown sizes, which anyone can check. The published result behind
        it is Sweeney (2000): a handful of ordinary fields usually identifies exactly one
        person. That is why "we removed the names" is not a privacy guarantee.
      </p>
    </>
  ),
}

/* ── 3 · the trap ────────────────────────────────────────────────────────── */

const REAL_ROW = '96 · F · Warje · Amyloidosis'

const S3: Slide = {
  id: 's3',
  title: 'The trap',
  shape: { kind: 'tables', leakRow: null },
  lay: 'bottom',
  Body: ({ setShape }) => {
    const [checked, setChecked] = useState(false)
    const run = () => {
      setChecked(true)
      setShape({ kind: 'tables', leakRow: 1 })
    }
    const reset = () => {
      setChecked(false)
      setShape({ kind: 'tables', leakRow: null })
    }
    return (
      <>
        <div className="tablecap" style={{ maxWidth: 760, marginInline: 'auto', width: '100%' }}>
          <span className="gold">real records</span>
          <span className="gold">&ldquo;synthetic&rdquo; output</span>
        </div>

        <div style={{ display: 'flex', gap: '0.8rem', justifyContent: 'center', alignItems: 'center', flexWrap: 'wrap' }}>
          {!checked ? (
            <button className="btn btn-lg" data-on="1" onClick={run}>
              compare them, row by row
            </button>
          ) : (
            <button className="btn" onClick={reset}>
              ↻ again
            </button>
          )}
        </div>

        <p className="sub" style={{ textAlign: 'center', marginInline: 'auto', minHeight: '3.2em' }}>
          {checked ? (
            <>
              One row is <strong className="crimson">a real patient, copied word for word</strong>{' '}
              — <span className="mono">{REAL_ROW}</span>. The file was labelled synthetic.
            </>
          ) : (
            <>
              Most teams say: <em>generate fake data, problem solved.</em> Both of these look
              perfectly reasonable.
            </>
          )}
        </p>

        <p className="note" style={{ textAlign: 'center', marginInline: 'auto' }}>
          {checked ? (
            <>
              It is always the same kind of row: the 96-year-old with the rare diagnosis. A model
              memorises outliers, because for an outlier <strong>the pattern is the person</strong>.
              The people most at risk are the ones a generator is most likely to reprint.
            </>
          ) : (
            <>
              <span className="flag">invented rows</span> Written for this slide. Printing real
              records in a pitch deck would be a small version of the failure we are describing.
            </>
          )}
        </p>
      </>
    )
  },
  Notes: () => (
    <>
      <h4>say</h4>
      <p>
        Set it up before pressing anything: "Most teams propose generating fake data and
        stopping there. Here are two tables. One is real, one is generated. Both look completely
        reasonable."
      </p>
      <p>
        Press the button. One row in the field ignites crimson.{' '}
        <strong>"That is a real patient. Copied word for word into a file labelled
        synthetic."</strong>
      </p>
      <p>
        Then the mechanism, because it is the part they will remember: it is always the
        96-year-old with the rare diagnosis. A model memorises outliers, because for an outlier
        the pattern IS the person. <strong>The people most at risk are exactly the ones a
        generator is most likely to reprint.</strong>
      </p>
      <p>
        Close: "Nothing in 'make me a similar table' forbids this. You need a guarantee that
        makes it impossible — not a hope that it will not happen."
      </p>
    </>
  ),
}

/* ── 4 · the machine ─────────────────────────────────────────────────────── */

const STAGES = [
  { name: 'Check', line: 'Reads your column names and row count — never your data. An ID column is refused by name, with a fix.', tag: 'free' },
  { name: 'Refuse', line: 'Unsafe columns are turned away before a single value is read. A check that read your data to decide if your data was safe would be the bug it exists to prevent.', tag: 'free' },
  { name: 'Count + blur', line: 'Count the groups, then add measured noise to every count. The real table stops here and goes no further.', tag: 'costs' },
  { name: 'Rebuild', line: 'A new table, built only from the blurred counts. This costs nothing — once data is private, anything you calculate from it stays private.', tag: 'free' },
  { name: 'Attack', line: 'We hide known records and hunt them in our own output, before anyone outside gets the chance.', tag: '' },
]

const S4: Slide = {
  id: 's4',
  title: 'The machine',
  shape: { kind: 'pipeline', stage: 0 },
  lay: 'bottom',
  Body: ({ setShape }) => {
    const [i, setI] = useState(0)
    const go = (n: number) => {
      setI(n)
      setShape({ kind: 'pipeline', stage: n })
    }
    return (
      <>
        <div className="stagebar" style={{ maxWidth: 820, marginInline: 'auto', width: '100%' }}>
          {STAGES.map((s, n) => (
            <button key={s.name} className="stagebtn" data-on={i === n ? '1' : '0'} onClick={() => go(n)}>
              {n + 1}. {s.name}
              {s.tag && (
                <span className={s.tag === 'costs' ? 'crimson' : 'jade'} style={{ marginLeft: 6 }}>
                  {s.tag === 'costs' ? '· costs' : '· free'}
                </span>
              )}
            </button>
          ))}
        </div>

        <p className="sub" style={{ textAlign: 'center', marginInline: 'auto', minHeight: '3.2em' }}>
          <strong className="gold">{STAGES[i].name}.</strong> {STAGES[i].line}
        </p>

        <div className="cols c4" style={{ maxWidth: 900, marginInline: 'auto' }}>
          {[
            ['Privacy maths', 'Google dp_accounting'],
            ['Generators', 'private-PGM · marginals'],
            ['Attacks', 'canary audit · density ratio'],
            ['Product', 'Python · FastAPI · React'],
          ].map(([k, val]) => (
            <div key={k} className="panel" style={{ padding: '0.45rem 0.6rem' }}>
              <div className="rail-label">{k}</div>
              <div style={{ fontSize: '0.92rem', fontWeight: 700, marginTop: 2 }}>{val}</div>
            </div>
          ))}
        </div>

        <p className="note" style={{ textAlign: 'center', marginInline: 'auto' }}>
          <span className="flag">illustration</span> We do not write our own privacy
          mathematics — it is delegated to Google&rsquo;s library and cross-checked against a
          second one. <strong>If we cannot cite it, we do not claim it.</strong>
        </p>
      </>
    )
  },
  Notes: () => (
    <>
      <h4>say — click, do not read</h4>
      <p>
        Step through the five buttons and let the field do the talking. On <strong>Refuse</strong>{' '}
        a chunk of the dots go dark: "those are rows we turn away." On{' '}
        <strong>Count + blur</strong> the tidy lanes shatter: "that is where privacy is actually
        bought." On <strong>Rebuild</strong> they re-form into tidy rows again — "a NEW table,
        not the one we started with."
      </p>
      <p>
        The one surprise worth stating out loud: <strong>rebuilding is FREE.</strong> Once data
        has been made private, anything you calculate from it stays private. That is a theorem,
        not a shortcut — and it is why only two of the five stages cost anything.
      </p>
      <p>
        The four chips are the stack. Lead with the first: we do not write our own privacy
        mathematics. That answers the sharpest question an examiner has — <em>how do I know your
        numbers are right?</em> — with: attack Google's library, not our arithmetic. Volunteer
        that AIM comes from the private-PGM authors; we integrate it, we did not invent it.
      </p>
    </>
  ),
}

/* ── 5 · the receipt ─────────────────────────────────────────────────────── */

const FACTS: Array<{ k: string; v: string; strong?: boolean; why: string }> = [
  { k: 'Records released', v: '6,000', why: 'How many rows are in the file you were handed.' },
  { k: 'Privacy budget spent', v: '0.91', strong: true, why: 'One number for how much of this dataset’s privacy was used up producing the file. Smaller is safer.' },
  { k: '— finding out what columns hold', v: '0.18', why: 'A question about real people, so it goes on the bill. Most tools do this for free and never tell you.' },
  { k: '— counting the groups', v: '0.73', why: 'Counting people, with noise added to every count.' },
  { k: 'We attacked it ourselves', v: 'nothing found', why: 'We hide known records and hunt for them in our own output before anyone else can.' },
  { k: 'Limit of that attack', v: '2.25', strong: true, why: 'The most our attack could EVER have found. Printed right under the line above, because a zero nobody can interpret is worse than no number at all. This is the decision we are proudest of.' },
  { k: 'Columns you declared', v: '12 of 12', why: 'Declared columns are free — they reveal nothing about any individual.' },
  { k: 'Signed', v: 'yes', why: 'Anyone with our public key can check this file was not edited after it was produced.' },
]

const S5: Slide = {
  id: 's5',
  title: 'The receipt',
  shape: { kind: 'label' },
  lay: 'split',
  Body: () => {
    const [open, setOpen] = useState(5)
    return (
      <div className="cols c2" style={{ alignItems: 'start' }}>
        <div className="panel panel-gold">
          <div className="rail-label" style={{ marginBottom: 6 }}>
            privacy facts · one release
          </div>
          <hr className="rule" style={{ marginBottom: 6 }} />
          <div className="facts">
            {FACTS.map((f, n) => (
              <button
                key={f.k}
                className={`fact ${f.strong ? 'fact-strong' : ''}`}
                data-on={open === n ? '1' : '0'}
                onClick={() => setOpen(n)}
              >
                <span className="fact-k">{f.k}</span>
                <span className="fact-v">{f.v}</span>
              </button>
            ))}
          </div>
        </div>

        <div style={{ display: 'grid', gap: '0.7rem' }}>
          <h2 className="big">
            Food tells you what is inside.{' '}
            <span className="mark gold">Data should too.</span>
          </h2>
          <div className="panel">
            <div className="rail-label gold">{FACTS[open].k}</div>
            <p className="sub" style={{ margin: '0.35rem 0 0', maxWidth: 'none' }}>
              {FACTS[open].why}
            </p>
          </div>
          <p className="note">
            <span className="flag">example label</span> Illustrative values, to show the format
            we are designing. Tap any line.
          </p>
        </div>
      </div>
    )
  },
  Notes: () => (
    <>
      <h4>say</h4>
      <p>
        Open on the metaphor: <strong>"Every packet of food in this building lists its
        ingredients. No dataset anywhere does."</strong>
      </p>
      <p>
        Then tap exactly two lines. <strong>Privacy budget spent</strong> — one number for the
        whole file. Then <strong>Limit of that attack</strong>, and explain why it sits directly
        under the attack result: if your attack finds nothing, that could mean nothing leaked,
        or that your attack was too small to see it. Everyone reports the first. We work out
        which it was and print it.
      </p>
      <p>
        That is the single most defensible design decision in the project, so give it the time.
      </p>
      <h4>they will ask</h4>
      <p>
        <strong>"Who reads this?"</strong> — Three people: the data owner deciding whether to
        release, the researcher deciding whether the data is fit for their study, and an auditor
        checking the claim afterwards. The signature is for the third one.
      </p>
    </>
  ),
}

/* ── 6 · the close ───────────────────────────────────────────────────────── */

const S6: Slide = {
  id: 's6',
  title: 'The ask',
  shape: { kind: 'close', text: 'SHARE IT' },
  lay: 'bottom',
  Body: () => (
    <>
      <h2 className="big" style={{ textAlign: 'center' }}>
        Data you can share, <span className="mark gold">with the receipt attached.</span>
      </h2>

      <div className="cols c3" style={{ maxWidth: 1000, marginInline: 'auto' }}>
        <div className="panel panel-jade">
          <div className="rail-label jade">ships first</div>
          <p className="sub" style={{ fontSize: '1.5rem', margin: '0.3rem 0 0', maxWidth: 'none' }}>
            One table in, one certified table out.
          </p>
        </div>
        <div className="panel">
          <div className="rail-label">deliberately not in v1</div>
          <p className="sub" style={{ fontSize: '1.5rem', margin: '0.3rem 0 0', maxWidth: 'none' }}>
            Many joined tables · images · text · shared budgets. Each is a project on its own.
          </p>
        </div>
        <div className="panel panel-crimson">
          <div className="rail-label crimson">what we want from you</div>
          <p className="sub" style={{ fontSize: '1.5rem', margin: '0.3rem 0 0', maxWidth: 'none' }}>
            Attack our limit-of-the-attack claim. It is the one we most want tested.
          </p>
        </div>
      </div>

      <p className="note" style={{ textAlign: 'center', marginInline: 'auto' }}>
        Raj Modi · Krishna Renuse · Aaditya Kumar Sinha · Levinesh G R — MIT-WPU CSE-AIDS,
        Panel B
      </p>
    </>
  ),
  Notes: () => (
    <>
      <h4>say</h4>
      <p>
        The dots settle into the words SHARE IT. Let that land before you speak.
      </p>
      <p>
        Then the middle card first, not the left. <strong>What you refuse to build is more
        persuasive than what you promise.</strong> "Many tables, images, shared budgets — each
        is a project on its own. Claiming all of them is the fastest way to build none."
      </p>
      <p>
        Then the right card: ask them for something specific. A panel that is asked a real
        question engages; a panel asked "any questions?" judges.
      </p>
      <p>Then the headline, and stop. Do not add anything after it.</p>
      <h4>the three questions most likely to come</h4>
      <p>
        <strong>"Has anyone done this?"</strong> — The two halves exist separately, in different
        research communities. Shipping both on one release, with the limit of the measurement
        printed beside it, is ours.
      </p>
      <p>
        <strong>"Is this just a wrapper?"</strong> — The generators and the privacy arithmetic
        are existing work and we say so. The refusal gate, the self-attack, the receipt and the
        limit calculation are the project.
      </p>
      <p>
        <strong>"Can a hospital use it tomorrow?"</strong> — No. Single table, one shared key,
        no budget across sessions. It is an instrument for checking releases, and we would
        rather say that than oversell it.
      </p>
    </>
  ),
}

export const SLIDES: Slide[] = [S1, S2, S3, S4, S5, S6]
