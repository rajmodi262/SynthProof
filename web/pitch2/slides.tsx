import type { ComponentType, ReactNode } from 'react'
import { motion, useReducedMotion } from 'framer-motion'

import { BudgetBattery } from './widgets/BudgetBattery'
import { CopyMachine } from './widgets/CopyMachine'
import { FindYourself } from './widgets/FindYourself'
import { NutritionLabel } from './widgets/NutritionLabel'
import { ParticleTitle } from './widgets/ParticleTitle'
import { TwoHouses } from './widgets/TwoHouses'

/**
 * Thirteen slides, framed as a proposal.
 *
 * Each one carries a single object the panel can touch, and no two are the same shape — the
 * failure mode of a pitch deck is thirteen slides with an identical layout, whatever the
 * palette. Dark slides bracket the argument: the cold open, the leak, and the close.
 *
 * Nothing here is presented as an experimental result. Every figure on screen is either a
 * published finding from the literature (attributed in the notes) or an illustration of the
 * design — and every illustration carries a flag saying so.
 */

export type Slide = {
  id: string
  title: string
  blurb: string
  tone?: 'light' | 'dark'
  /** Turns the heartbeat crimson: used on the slides about leaks. */
  hotPulse?: boolean
  Body: ComponentType
  Notes: ComponentType
}

/* ── small shared pieces ─────────────────────────────────────────────────── */

function Rise({ children, delay = 0 }: { children: ReactNode; delay?: number }) {
  const reduce = useReducedMotion()
  return (
    <motion.div
      initial={{ opacity: 0, y: reduce ? 0 : 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: reduce ? 0 : 0.45, delay: reduce ? 0 : delay, ease: [0.22, 0.61, 0.36, 1] }}
    >
      {children}
    </motion.div>
  )
}

function Steps({
  items,
}: {
  items: Array<{ name: string; sub?: string; tag?: 'free' | 'cost'; tone?: string }>
}) {
  return (
    <div className="steps">
      {items.map((s, i) => (
        <div key={s.name} style={{ display: 'contents' }}>
          {i > 0 && <div className="arrow" aria-hidden="true" />}
          <div className={`step ${s.tone ?? ''}`}>
            <span className="step-name">{s.name}</span>
            {s.sub && <span className="step-sub">{s.sub}</span>}
            {s.tag && (
              <span className={`tag tag-${s.tag}`}>{s.tag === 'free' ? 'free' : 'costs'}</span>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

function Src({ children }: { children: ReactNode }) {
  return <span className="mono">{children}</span>
}

/* ── 01 ──────────────────────────────────────────────────────────────────── */

const S1: Slide = {
  id: 's1',
  title: 'SynthProof',
  blurb: 'The name, built out of data. Drag the slider to see the whole problem.',
  tone: 'dark',
  Body: () => (
    <>
      <ParticleTitle />
      <Rise delay={2.2}>
        <div style={{ display: 'grid', gap: '0.45rem', justifyItems: 'center', textAlign: 'center' }}>
          <p className="lede" style={{ margin: 0, maxWidth: '54ch', color: 'var(--sand)' }}>
            Synthetic data that ships with{' '}
            <span className="hi hi-gold">a receipt for its own privacy.</span>
          </p>
          <p className="small" style={{ margin: 0 }}>
            MIT-WPU · CSE-AIDS Capstone 2026-27 · Panel B
          </p>
        </div>
      </Rise>
    </>
  ),
  Notes: () => (
    <>
      <h4>say — let the slide do the work first</h4>
      <p>
        Open on the assembly. The dots fly together and spell the name on their own:{' '}
        <strong>say nothing for those two seconds.</strong> Then: "Every dot is one
        person&rsquo;s record."
      </p>
      <p>
        Now grab the slider and drag it all the way LEFT. The name becomes unreadable. "That is
        perfect privacy. It is also completely useless — you cannot even read our name."
      </p>
      <p>
        Drag it all the way RIGHT. "Now you can read it perfectly. And so can an attacker read
        the people inside."
      </p>
      <p>
        Then land it: <strong>"Every dataset in the world sits somewhere on that slider. Nobody
        tells you where. That is the problem we are solving."</strong> Leave it in the middle
        and move on — do not explain the title any further.
      </p>
      <h4>why this is slide 1</h4>
      <p>
        The panel has now understood the core trade-off without hearing a single definition, and
        they understood it by trying to read your project name. Everything after this is detail.
      </p>
    </>
  ),
}

/* ── 02 ──────────────────────────────────────────────────────────────────── */

const S2: Slide = {
  id: 's2',
  title: 'Find yourself',
  blurb: 'The panel picks three ordinary facts. We find one person.',
  hotPulse: true,
  Body: () => (
    <>
      <Rise>
        <span className="eyebrow eyebrow-crimson">try it on yourself</span>
      </Rise>
      <Rise delay={0.08}>
        <h2 className="title">
          Pick three ordinary facts about yourself.{' '}
          <span className="hi hi-crimson">Watch us find you.</span>
        </h2>
      </Rise>
      <Rise delay={0.16}>
        <FindYourself />
      </Rise>
    </>
  ),
  Notes: () => (
    <>
      <h4>say — hand this to a panel member</h4>
      <p>
        Do not demo it yourself. <strong>Ask someone on the panel for their birth month.</strong>{' '}
        Set it. Then their area. Then gender. Read the number out loud as it falls: one lakh →
        eight thousand → seven hundred → <strong>one</strong>.
      </p>
      <p>
        Then the line: <strong>"That file had no names in it. It had a birth month, an area
        and a gender — and it just pointed at one person in this room."</strong>
      </p>
      <p>
        If they push: yes, real datasets are messier, and yes this is a drawing. The published
        finding behind it is Sweeney (2000) — roughly 87% of people are unique on three fields
        of this kind. The flag on screen says the crowd is illustrative.
      </p>
      <h4>why this is slide 2</h4>
      <p>
        Nobody argues with re-identification after watching it happen to them. Every later slide
        is easier because of this one.
      </p>
    </>
  ),
}

/* ── 03 ──────────────────────────────────────────────────────────────────── */

const S3: Slide = {
  id: 's3',
  title: 'So the data stays locked',
  blurb: 'What the caution actually costs.',
  Body: () => (
    <>
      <Rise>
        <span className="eyebrow">the cost of doing nothing</span>
      </Rise>
      <Rise delay={0.08}>
        <h2 className="title-sm">
          So hospitals do the safe thing. <span className="hi hi-line">They share nothing.</span>
        </h2>
      </Rise>
      <Rise delay={0.16}>
        <div className="cols cols-3">
          {[
            {
              head: 'The researcher',
              body: 'Waits a year for an ethics decision, then gets a refusal, then studies a smaller foreign dataset instead.',
              cls: 'card-sand',
            },
            {
              head: 'The hospital',
              body: 'Has no way to prove a release was safe, so the safest answer is always no. Nobody is ever blamed for saying no.',
              cls: 'card-gold',
            },
            {
              head: 'The patient',
              body: 'Gets neither the research nor the privacy — because the file is still sitting there, unprotected, on a server.',
              cls: 'card-crimson',
            },
          ].map((c) => (
            <div key={c.head} className={`card ${c.cls}`} style={{ height: '100%' }}>
              <span className="eyebrow">{c.head}</span>
              <p className="body" style={{ margin: '0.45rem 0 0', maxWidth: 'none', color: 'var(--ink)' }}>
                {c.body}
              </p>
            </div>
          ))}
        </div>
      </Rise>
      <Rise delay={0.26}>
        <div className="card card-dark">
          <p className="lede" style={{ margin: 0, maxWidth: 'none', color: 'var(--sand)' }}>
            The blocker is not technology. It is that{' '}
            <span className="hi hi-gold">nobody can prove a release is safe</span> — so nobody
            signs off.
          </p>
        </div>
      </Rise>
    </>
  ),
  Notes: () => (
    <>
      <h4>say</h4>
      <p>
        Three people, three sentences. The middle card is the real insight and worth pausing on:{' '}
        <strong>nobody is ever blamed for saying no.</strong> That asymmetry is why the data
        does not move, and it is not a technical problem.
      </p>
      <p>
        Then the dark card: the blocker is the absence of proof, not the absence of tools. That
        sets up everything we build.
      </p>
    </>
  ),
}

/* ── 04 ──────────────────────────────────────────────────────────────────── */

const S4: Slide = {
  id: 's4',
  title: 'Two hospitals, one difference',
  blurb: 'The actual definition of the guarantee, made visible.',
  Body: () => (
    <>
      <Rise>
        <span className="eyebrow eyebrow-gold">the core idea</span>
      </Rise>
      <Rise delay={0.08}>
        <h2 className="title-sm">
          Two files, identical except for one patient.{' '}
          <span className="hi hi-gold">Can you tell which is which?</span>
        </h2>
      </Rise>
      <Rise delay={0.16}>
        <TwoHouses />
      </Rise>
    </>
  ),
  Notes: () => (
    <>
      <h4>say — this is the definition, so go slowly</h4>
      <p>
        "Two hospitals. Identical records, except Hospital A has Priya and Hospital B does not.
        Ask both the same question. If you can tell the answers apart, Priya's presence leaked.
        If you cannot, it did not."
      </p>
      <p>
        Start with the slider at zero. The two clouds sit apart — <strong>"right now, the answer
        tells you Priya is in there."</strong> Then drag right and let them watch the clouds
        slide into each other until the verdict flips to YOU CANNOT TELL.
      </p>
      <p>
        Land it: <strong>"That is the whole guarantee. Not 'we removed the names'. The answer
        looks the same whether or not you were ever in the file."</strong>
      </p>
      <h4>if someone asks the obvious question</h4>
      <p>
        <strong>"Doesn't the noise make the answer wrong?"</strong> — Yes, slightly, and that is
        the trade we are managing. The answer is off by a few, and the population-level finding
        survives. Slide 5 is about how we budget exactly how much wrongness to buy.
      </p>
    </>
  ),
}

/* ── 05 ──────────────────────────────────────────────────────────────────── */

const S5: Slide = {
  id: 's5',
  title: 'Privacy is a battery',
  blurb: 'Every question drains it. At zero, the system refuses.',
  Body: () => (
    <>
      <Rise>
        <span className="eyebrow eyebrow-gold">how we control it</span>
      </Rise>
      <Rise delay={0.08}>
        <h2 className="title-sm">
          Each file gets one battery. <span className="hi hi-gold">Every question drains it.</span>
        </h2>
      </Rise>
      <Rise delay={0.16}>
        <BudgetBattery />
      </Rise>
    </>
  ),
  Notes: () => (
    <>
      <h4>say — press the buttons, do not describe them</h4>
      <p>
        Press them in order and let the bar drop. Then press one more when it is empty and let
        the room read the word <strong>REFUSED</strong>. "Not 'be more careful'. Refused. The
        budget is a promise to the people in that file."
      </p>
      <p>
        Two buttons matter. <strong>"Work out what values a column holds"</strong> — that is a
        question about real people, and most tools do it for free. We charge for it, or you
        declare the columns up front.
      </p>
      <p>
        And <strong>"Build the synthetic table" — FREE.</strong> That is the surprising one, and
        it is a theorem: once data has been made private, anything you calculate from it stays
        private. Nobody expects the expensive-sounding step to be the free one.
      </p>
    </>
  ),
}

/* ── 06 ──────────────────────────────────────────────────────────────────── */

const S6: Slide = {
  id: 's6',
  title: 'Fake data is not automatically safe',
  blurb: 'A generator that memorised one patient, caught live.',
  hotPulse: true,
  Body: () => (
    <>
      <Rise>
        <span className="eyebrow eyebrow-crimson">the trap everyone falls into</span>
      </Rise>
      <Rise delay={0.08}>
        <h2 className="title-sm">
          &ldquo;It&rsquo;s fake, so it&rsquo;s safe.&rdquo;{' '}
          <span className="hi hi-crimson">Press the button.</span>
        </h2>
      </Rise>
      <Rise delay={0.16}>
        <CopyMachine />
      </Rise>
    </>
  ),
  Notes: () => (
    <>
      <h4>say</h4>
      <p>
        Set it up first: "Most teams propose generating fake data and stopping there. Here are
        two fake tables. Both look completely reasonable." Give them a second to read.
      </p>
      <p>
        Then press the button. One row lights crimson.{' '}
        <strong>"That is a real patient. Copied word for word into a file labelled
        synthetic."</strong>
      </p>
      <p>
        Then explain why it is always the same kind of row: the 96-year-old with the rare
        diagnosis. <strong>A model memorises outliers, because for an outlier the pattern IS
        the person.</strong> The people most at risk are the ones a generator is most likely to
        reprint.
      </p>
      <p>
        Close: "Nothing in 'make me a similar table' forbids this. You need a guarantee that
        makes it impossible, not a hope that it will not happen."
      </p>
    </>
  ),
}

/* ── 07 ──────────────────────────────────────────────────────────────────── */

const S7: Slide = {
  id: 's7',
  title: 'What we are building',
  blurb: 'Six stages, two of which cost battery.',
  Body: () => (
    <>
      <Rise>
        <span className="eyebrow eyebrow-jade">the system</span>
      </Rise>
      <Rise delay={0.08}>
        <h2 className="title-sm">
          Your file goes in. <span className="hi hi-gold">Safe data and a receipt come out.</span>
        </h2>
      </Rise>
      <Rise delay={0.16}>
        <Steps
          items={[
            { name: '1 · Check', sub: 'reads column names only, never your data', tag: 'free', tone: 'card-jade' },
            { name: '2 · Learn', sub: 'what values each column holds', tag: 'cost', tone: 'card-gold' },
            { name: '3 · Count + blur', sub: 'noise added to every count', tag: 'cost', tone: 'card-gold' },
            { name: '4 · Build', sub: 'new table from blurred counts', tag: 'free', tone: 'card-jade' },
            { name: '5 · Attack', sub: 'we hunt our own output', tone: 'card-crimson' },
            { name: '6 · Certify', sub: 'sign it and attach the receipt' },
          ]}
        />
      </Rise>
      <Rise delay={0.26}>
        <div className="cols cols-3">
          <div className="card card-jade">
            <span className="eyebrow eyebrow-jade">stage 1 · it says no</span>
            <p className="body" style={{ margin: '0.4rem 0 0', maxWidth: 'none', color: 'var(--ink)' }}>
              Give it a patient-ID column and it refuses, names the column, and tells you the
              fix — <strong>without reading a single value.</strong>
            </p>
          </div>
          <div className="card card-gold">
            <span className="eyebrow eyebrow-gold">stage 3 · where safety is bought</span>
            <p className="body" style={{ margin: '0.4rem 0 0', maxWidth: 'none', color: 'var(--ink)' }}>
              The real table stops here. Everything downstream only ever sees blurred counts —
              which is why stage 4 is free.
            </p>
          </div>
          <div className="card card-crimson">
            <span className="eyebrow eyebrow-crimson">stage 5 · we attack ourselves</span>
            <p className="body" style={{ margin: '0.4rem 0 0', maxWidth: 'none', color: 'var(--ink)' }}>
              We hide known records and hunt for them in our own output, before anyone outside
              gets the chance.
            </p>
          </div>
        </div>
      </Rise>
    </>
  ),
  Notes: () => (
    <>
      <h4>say</h4>
      <p>
        Walk the six boxes in one breath, then spend the time on the three cards. Point at the
        two <strong>COSTS</strong> tags and connect them straight back to the battery they just
        drained on slide 5.
      </p>
      <p>
        The strongest line here is stage 1: <strong>a product whose headline feature is
        refusing to work.</strong> "A check that had to read your data to decide whether your
        data was safe would be the exact bug it exists to prevent."
      </p>
    </>
  ),
}

/* ── 08 ──────────────────────────────────────────────────────────────────── */

const S8: Slide = {
  id: 's8',
  title: 'What actually makes this new',
  blurb: 'Three decisions, and where we sit against existing tools.',
  Body: () => (
    <>
      <Rise>
        <span className="eyebrow eyebrow-gold">novelty</span>
      </Rise>
      <Rise delay={0.08}>
        <h2 className="title-sm">
          Three decisions <span className="hi hi-gold">nobody else makes.</span>
        </h2>
      </Rise>
      <Rise delay={0.16}>
        <div className="cols cols-3">
          {[
            {
              n: '01',
              head: 'Two numbers, one run',
              body: 'The proof and the attack come from the same pipeline and both land on the file you receive. Today they live in different research papers.',
              cls: 'card-gold',
            },
            {
              n: '02',
              head: 'We print the limit of our own attack',
              body: 'An attack finding nothing might mean nothing leaked — or that the attack was too small to see it. We calculate which, and print it beside the result.',
              cls: 'card-dark',
            },
            {
              n: '03',
              head: 'It refuses',
              body: 'Unsafe tables are turned away before a single value is read, with the offending column named and a remedy given.',
              cls: 'card-crimson',
            },
          ].map((c) => (
            <div key={c.n} className={`card ${c.cls}`} style={{ height: '100%' }}>
              <span className="huge" style={{ fontSize: 'clamp(1.5rem,2.4vw,2.1rem)' }}>{c.n}</span>
              <h3 style={{ fontSize: 'clamp(1.1rem,1.6vw,1.35rem)', margin: '0.25rem 0 0.3rem' }}>
                {c.head}
              </h3>
              <p
                className="body"
                style={{ margin: 0, maxWidth: 'none', fontSize: '1rem', color: c.cls === 'card-dark' ? 'var(--sand)' : 'var(--ink)' }}
              >
                {c.body}
              </p>
            </div>
          ))}
        </div>
      </Rise>
      <Rise delay={0.26}>
        <div className="card" style={{ padding: '0.55rem 0.8rem' }}>
          <table className="cm" style={{ marginTop: 0 }}>
            <thead>
              <tr>
                <th>capability</th>
                <th style={{ textAlign: 'center' }}>SDV</th>
                <th style={{ textAlign: 'center' }}>Gretel</th>
                <th style={{ textAlign: 'center' }}>SmartNoise</th>
                <th style={{ textAlign: 'center', color: 'var(--gold-deep)' }}>SynthProof</th>
              </tr>
            </thead>
            <tbody>
              {[
                ['Makes synthetic data', 1, 1, 1, 1],
                ['Formal privacy guarantee', 0, 1, 1, 1],
                ['Attacks its own output', 0, 0, 0, 1],
                ['Ships both numbers to you', 0, 0, 0, 1],
                ['States the limit of its own attack', 0, 0, 0, 1],
                ['Refuses unsafe tables up front', 0, 0, 0, 1],
              ].map(([row, ...cells]) => (
                <tr key={row as string}>
                  <td style={{ fontWeight: 800 }}>{row}</td>
                  {(cells as number[]).map((v, i) => (
                    <td
                      key={i}
                      style={{
                        textAlign: 'center',
                        fontWeight: 900,
                        color: v ? 'var(--jade)' : 'var(--ink-3)',
                        background: i === 3 ? 'var(--gold-wash)' : undefined,
                      }}
                    >
                      {v ? '✓' : '—'}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Rise>
    </>
  ),
  Notes: () => (
    <>
      <h4>say</h4>
      <p>
        Card 02 is the most defensible thing in the project, so give it the time. "If you attack
        a dataset and find nothing, there are two possible reasons: nothing leaked, or your
        attack was too small to see it. Everyone reports the first. We work out which one it
        was, and print it next to the number."
      </p>
      <h4>the table — be scrupulous</h4>
      <p>
        This compares published capabilities, not benchmark results. SDV is a synthesis library
        and does not claim to be a privacy tool; Gretel and SmartNoise <em>do</em> offer formal
        guarantees. <strong>Concede that immediately if pushed.</strong> The bottom four rows
        are what we are claiming, and they are design decisions rather than performance claims.
      </p>
    </>
  ),
}

/* ── 09 ──────────────────────────────────────────────────────────────────── */

const S9: Slide = {
  id: 's9',
  title: 'What you receive',
  blurb: 'A nutrition label for data.',
  Body: () => (
    <>
      <Rise>
        <span className="eyebrow eyebrow-gold">the deliverable</span>
      </Rise>
      <Rise delay={0.08}>
        <h2 className="title-sm">
          Food tells you what is inside. <span className="hi hi-gold">Data should too.</span>
        </h2>
      </Rise>
      <Rise delay={0.16}>
        <NutritionLabel />
      </Rise>
    </>
  ),
  Notes: () => (
    <>
      <h4>say</h4>
      <p>
        Open on the metaphor: "Every packet of food in this building lists its ingredients. No
        dataset anywhere does." Then tap two lines in front of them.
      </p>
      <p>
        <strong>Privacy budget spent</strong> — one number for the whole file, straight back to
        the battery. Then <strong>Limit of that attack</strong>, sitting deliberately under the
        attack result, because a zero nobody can interpret is worse than no number at all.
      </p>
      <p>
        Finish on the last two rows: columns you declared versus columns we had to guess.
        Guessing costs battery, so we count it and we tell you.
      </p>
    </>
  ),
}

/* ── 10 ──────────────────────────────────────────────────────────────────── */

const S10: Slide = {
  id: 's10',
  title: 'One hospital, end to end',
  blurb: 'The whole thing as a story.',
  Body: () => (
    <>
      <Rise>
        <span className="eyebrow eyebrow-jade">use case</span>
      </Rise>
      <Rise delay={0.08}>
        <h2 className="title-sm">
          A hospital shares 50,000 diabetes records{' '}
          <span className="hi hi-jade">with a university lab.</span>
        </h2>
      </Rise>
      <Rise delay={0.16}>
        <Steps
          items={[
            { name: 'Lab asks', sub: 'for a diabetes study', tone: 'card-sand' },
            { name: 'Hospital uploads', sub: 'with declared columns', tone: 'card-sand' },
            { name: 'We refuse one', sub: 'patient ID — named, with a fix', tone: 'card-crimson' },
            { name: 'They drop it', sub: 'and re-upload', tone: 'card-gold' },
            { name: 'Release', sub: 'data + signed receipt', tone: 'card-jade' },
            { name: 'Lab trains', sub: 'no patient exposed', tone: 'card-jade' },
          ]}
        />
      </Rise>
      <Rise delay={0.26}>
        <div className="cols cols-3">
          {[
            { h: 'the hospital gets', b: 'A defensible written answer to "was it safe to share this?" — signed, with a number on it.', c: 'card-gold' },
            { h: 'the lab gets', b: 'Data in weeks instead of a year of review, plus a label saying what it is fit for.', c: 'card-jade' },
            { h: 'the patient gets', b: 'A guarantee that holds whether or not anyone ever bothers to attack the file.', c: 'card-sand' },
          ].map((x) => (
            <div key={x.h} className={`card ${x.c}`} style={{ height: '100%' }}>
              <span className="eyebrow">{x.h}</span>
              <p className="body" style={{ margin: '0.4rem 0 0', maxWidth: 'none', color: 'var(--ink)' }}>
                {x.b}
              </p>
            </div>
          ))}
        </div>
      </Rise>
      <Rise delay={0.34}>
        <p className="small" style={{ margin: 0 }}>
          Same shape elsewhere: banks sharing fraud data with vendors, telecoms releasing
          mobility data for city planning, any government open-data portal. The holder cannot
          prove safety, so nothing moves.
        </p>
      </Rise>
    </>
  ),
  Notes: () => (
    <>
      <h4>say</h4>
      <p>
        Tell it as a story, not a diagram. The box that matters is the crimson one:{' '}
        <strong>we refuse the patient-ID column, name it, and say how to fix it.</strong> Most
        tools would have cheerfully synthesised it and handed back real identifiers — which is
        exactly what slide 6 showed happening.
      </p>
      <p>
        Then the three cards: one release, three different problems solved for three different
        people. If they ask about other domains, the line at the bottom has three.
      </p>
    </>
  ),
}

/* ── 11 ──────────────────────────────────────────────────────────────────── */

const STACK = [
  { name: 'Privacy core', cls: 'card-gold', items: ['Google dp_accounting', 'discrete Gaussian / Laplace', 'Ed25519 signatures'], why: 'We do not write our own privacy maths. It is delegated and cross-checked.' },
  { name: 'Generators', cls: 'card-sand', items: ['private-PGM (AIM)', 'pairwise tree', 'independent marginals', 'moment baseline'], why: 'Four ways to build the table, from a naive baseline to current state of the art.' },
  { name: 'Attack suite', cls: 'card-crimson', items: ['canary audit', 'density-ratio attack', 'exact-match check'], why: 'The half that hunts our own output.' },
  { name: 'Service + app', cls: 'card-jade', items: ['Python 3.11', 'FastAPI', 'SQLite ledger', 'React + TypeScript', 'Docker'], why: 'A CLI for engineers, a web console for everyone else.' },
]

const S11: Slide = {
  id: 's11',
  title: 'What we are building it from',
  blurb: 'We buy the privacy maths. We build the rest.',
  Body: () => (
    <>
      <Rise>
        <span className="eyebrow eyebrow-gold">tech stack</span>
      </Rise>
      <Rise delay={0.08}>
        <h2 className="title-sm">
          We <span className="hi hi-gold">buy</span> the privacy maths. We{' '}
          <span className="hi hi-jade">build</span> everything around it.
        </h2>
      </Rise>
      <Rise delay={0.16}>
        <div style={{ display: 'grid', gap: '6px' }}>
          {STACK.map((l) => (
            <div key={l.name} className={`stack-layer ${l.cls}`}>
              <span style={{ fontSize: '1rem', fontWeight: 900, lineHeight: 1.1 }}>{l.name}</span>
              <div style={{ display: 'grid', gap: '0.25rem' }}>
                <div className="chips">
                  {l.items.map((i) => (
                    <span key={i} className="chip">
                      {i}
                    </span>
                  ))}
                </div>
                <span style={{ fontSize: '0.92rem', fontWeight: 600, color: 'var(--ink-2)', lineHeight: 1.2 }}>
                  {l.why}
                </span>
              </div>
            </div>
          ))}
        </div>
      </Rise>
      <Rise delay={0.26}>
        <div className="card card-dark">
          <p className="lede" style={{ margin: 0, maxWidth: 'none', color: 'var(--sand)' }}>
            The rule we work to:{' '}
            <span className="hi hi-gold">if we cannot cite it, we do not claim it.</span>
          </p>
        </div>
      </Rise>
    </>
  ),
  Notes: () => (
    <>
      <h4>say</h4>
      <p>
        Lead with the top layer and the rule at the bottom. "We do not write our own privacy
        mathematics. Adding up the cost of many operations is the part implementations get
        wrong, so we delegate it to Google's library and check it against a second one."
      </p>
      <p>
        That answers the sharpest question an examiner has — <em>how do I know your numbers are
        right?</em> — with: attack Google's library, not our arithmetic.
      </p>
      <p>
        Row 2, volunteer it: AIM comes from the private-PGM authors. We integrate it, we did not
        invent it. Much stronger said than conceded.
      </p>
    </>
  ),
}

/* ── 12 ──────────────────────────────────────────────────────────────────── */

const S12: Slide = {
  id: 's12',
  title: 'What ships first',
  blurb: 'The MVP, and what we are deliberately not building.',
  Body: () => (
    <>
      <Rise>
        <span className="eyebrow eyebrow-jade">plan</span>
      </Rise>
      <Rise delay={0.08}>
        <h2 className="title-sm">
          The smallest version that is <span className="hi hi-jade">actually useful.</span>
        </h2>
      </Rise>
      <Rise delay={0.16}>
        <div className="cols cols-2">
          <div className="card card-jade">
            <span className="eyebrow eyebrow-jade">the MVP</span>
            <p style={{ fontSize: '1.2rem', fontWeight: 800, margin: '0.35rem 0' }}>
              One table in, one certified table out.
            </p>
            <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'grid', gap: '0.28rem' }}>
              {[
                'Upload a CSV with declared columns',
                'It refuses unsafe columns, by name',
                'Choose how private you want it',
                'Get safe data + a signed receipt',
                'Verify the receipt with one command',
              ].map((x) => (
                <li key={x} style={{ fontSize: '1rem', fontWeight: 600, display: 'flex', gap: '0.45rem' }}>
                  <span className="jade" style={{ fontWeight: 900 }}>
                    ✓
                  </span>
                  {x}
                </li>
              ))}
            </ul>
          </div>
          <div className="card card-sand">
            <span className="eyebrow">deliberately not in v1</span>
            <ul style={{ margin: '0.35rem 0 0', padding: 0, listStyle: 'none', display: 'grid', gap: '0.28rem' }}>
              {[
                'Many tables joined together',
                'Images, text or time series',
                'Budget shared across many users',
                'Deep-learning generators',
              ].map((x) => (
                <li key={x} style={{ fontSize: '1rem', fontWeight: 600, display: 'flex', gap: '0.45rem' }}>
                  <span style={{ color: 'var(--ink-3)', fontWeight: 900 }}>—</span>
                  {x}
                </li>
              ))}
            </ul>
            <p style={{ margin: '0.5rem 0 0', fontSize: '0.96rem', fontWeight: 700 }}>
              Each is a project on its own. Claiming all four is the fastest way to build none.
            </p>
          </div>
        </div>
      </Rise>
      <Rise delay={0.26}>
        <div className="cols cols-2" style={{ gap: '0.6rem' }}>
          {[
            { w: 'phase 1', t: 'Prove the core', i: 'budget accounting · two generators · the refusal gate', c: 'card-gold' },
            { w: 'phase 2', t: 'Make it honest', i: 'self-attack · print the attack limit · signed receipts', c: 'card-crimson' },
            { w: 'phase 3', t: 'Make it usable', i: 'web console · second dataset · reproducible runs', c: 'card-sand' },
            { w: 'phase 4', t: 'Harden it', i: 'stronger attacker · budget across sessions · third dataset', c: 'card-jade' },
          ].map((p) => (
            <div key={p.w} className={`card ${p.c}`} style={{ padding: '0.5rem 0.7rem' }}>
              <span className="eyebrow" style={{ fontSize: 10 }}>
                {p.w}
              </span>
              <div style={{ fontSize: '1.05rem', fontWeight: 800, margin: '0.2rem 0 0.1rem' }}>{p.t}</div>
              <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--ink-2)' }}>{p.i}</div>
            </div>
          ))}
        </div>
      </Rise>
    </>
  ),
  Notes: () => (
    <>
      <h4>say</h4>
      <p>
        Lead with the RIGHT card, not the left. <strong>What you refuse to build is more
        persuasive than what you promise.</strong> "Multi-table, images, shared budgets — each is
        a project on its own."
      </p>
      <p>
        Then the MVP in one sentence and five bullets, no elaboration. Then the phases, one
        breath each. Note the order puts <em>make it honest</em> before <em>make it usable</em>;
        an examiner will notice, and it is a real statement of priorities.
      </p>
      <p>
        This is the natural moment to offer the live demo — five commands, script in{' '}
        <Src>docs/DEMO_SCRIPT.md</Src>.
      </p>
    </>
  ),
}

/* ── 13 ──────────────────────────────────────────────────────────────────── */

const S13: Slide = {
  id: 's13',
  title: 'Team and the ask',
  blurb: 'Who is building it, and what we want from you.',
  tone: 'dark',
  Body: () => (
    <>
      <Rise>
        <span className="eyebrow eyebrow-gold">closing</span>
      </Rise>
      <Rise delay={0.08}>
        <h2 className="title" style={{ color: 'var(--sand)' }}>
          Four of us. <span className="hi hi-gold">One instrument.</span>
        </h2>
      </Rise>
      <Rise delay={0.16}>
        <div className="cols cols-2">
          <div className="card">
            <span className="eyebrow eyebrow-gold">team · MIT-WPU CSE-AIDS · Panel B</span>
            <ul style={{ margin: '0.45rem 0 0', padding: 0, listStyle: 'none', display: 'grid', gap: '0.3rem' }}>
              {['Raj Modi', 'Krishna Renuse', 'Aaditya Kumar Sinha', 'Levinesh G R'].map((n) => (
                <li key={n} style={{ fontSize: '1.15rem', fontWeight: 700 }}>
                  {n}
                </li>
              ))}
            </ul>
          </div>
          <div className="card">
            <span className="eyebrow eyebrow-gold">what we want from you</span>
            <ul style={{ margin: '0.45rem 0 0', padding: 0, listStyle: 'none', display: 'grid', gap: '0.4rem' }}>
              {[
                'A hard look at decision 02 — printing the limit of our own attack. It is the claim we most want tested.',
                'A pointer to a public dataset with a published schema, for the second evaluation.',
                'Guidance on scope: is the refusal gate a paper in its own right?',
              ].map((x) => (
                <li key={x} style={{ fontSize: '0.98rem', fontWeight: 600, lineHeight: 1.3 }}>
                  {x}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </Rise>
      <Rise delay={0.28}>
        <p className="title-sm" style={{ textAlign: 'center', color: 'var(--sand)', margin: 0 }}>
          Data you can share, <span className="hi hi-gold">with the receipt attached.</span>
        </p>
      </Rise>
    </>
  ),
  Notes: () => (
    <>
      <h4>say</h4>
      <p>
        Names fast — add each person's area if you want, but keep it short. The right-hand card
        is the content. <strong>Ask for something specific.</strong> A panel that is asked a real
        question engages; a panel asked "any questions?" judges.
      </p>
      <p>Then the closing line. Stop. Do not add anything after it.</p>
      <h4>the three questions most likely to come</h4>
      <p>
        <strong>"Has anyone done this?"</strong> — The two halves exist separately, in different
        research communities. Shipping both on one release, with the limit of the measurement
        printed beside it, is ours.
      </p>
      <p>
        <strong>"Is this just a wrapper?"</strong> — The generators and the privacy arithmetic
        are existing work, and we say so on the stack slide. The refusal gate, the self-attack,
        the receipt and the limit calculation are the project.
      </p>
      <p>
        <strong>"Can a hospital use it tomorrow?"</strong> — No. Single table, one shared key, no
        budget across sessions. It is an instrument for checking releases, and we would rather
        say that than oversell it.
      </p>
    </>
  ),
}

export const SLIDES: Slide[] = [S1, S2, S3, S4, S5, S6, S7, S8, S9, S10, S11, S12, S13]
