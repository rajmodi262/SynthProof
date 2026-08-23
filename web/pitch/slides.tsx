import type { ComponentType } from 'react'

import { Line, Stagger } from './Bits'
import { Flow, Gap } from './Flow'
import { Beat, Statement } from './Layouts'
import { Tabs } from './Tabs'
import { AttackTerminal } from './widgets/AttackTerminal'
import { NutritionLabel } from './widgets/NutritionLabel'
import { ParticleTitle } from './widgets/ParticleTitle'
import { PipelineSim } from './widgets/PipelineSim'
import { Reidentify } from './widgets/Reidentify'

/**
 * Twelve slides, framed as a PROPOSAL.
 *
 *   1  SYNTHPROOF     the name, made of data, with the trade-off as a slider
 *   2  the problem    deleting names does not work, and here is a person to prove it
 *   3  why fixes fail three approaches, three reasons they do not hold
 *   4  the idea       one sentence, and the two numbers every release will carry
 *   5  how it works   six stages
 *   6  watch it run   the simulation
 *   7  what is new    three claims, and where we sit against existing tools
 *   8  the output     the privacy nutrition label
 *   9  use case       one hospital, end to end, plus an attacker who fails
 *  10  tech stack     what we are building it out of
 *  11  MVP + roadmap  what ships first, and in what order
 *  12  team + ask     who we are and what we want
 *
 * This deck describes what the system will do and how it is designed. It deliberately shows
 * no experimental results. Everything on screen that carries a number is therefore either a
 * published figure from the literature (attributed) or an illustration of the design — and
 * every illustration carries a yellow flag saying so. Nothing here is dressed up as a
 * measurement of ours.
 */

export type Slide = {
  id: string
  title: string
  blurb: string
  tone?: 'light' | 'dark' | 'alarm'
  Body: ComponentType
  Notes: ComponentType
}

/* ── 01 · the name ───────────────────────────────────────────────────────── */

const S1: Slide = {
  id: 's1',
  title: 'SynthProof',
  blurb: 'The name, built out of data. Drag the slider to see the whole problem.',
  tone: 'dark',
  Body: () => (
    <>
      <ParticleTitle />
      <Beat delay={2.2}>
        <div style={{ display: 'grid', gap: '0.5rem', justifyItems: 'center', textAlign: 'center' }}>
          <p className="lede" style={{ margin: 0, maxWidth: '54ch' }}>
            Synthetic data that ships with{' '}
            <span className="hi hi-violet">a receipt for its own privacy.</span>
          </p>
          <p className="small" style={{ margin: 0 }}>
            MIT-WPU · CSE-AIDS Capstone 2026-27 · Panel B
          </p>
        </div>
      </Beat>
    </>
  ),
  Notes: () => (
    <>
      <h4>say — let the slide do the work first</h4>
      <p>
        Open on the assembly. The dots fly together and spell the name on their own: say
        nothing for those two seconds. Then: <strong>"Every dot is one person's record."</strong>
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
        tells you where. That is the problem we are solving."</strong> Leave it somewhere in the
        middle and move on.
      </p>
      <h4>why this is slide 1</h4>
      <p>
        The panel has now understood the core trade-off without hearing a definition, and they
        understood it by trying to read your project name. Everything after this is detail.
      </p>
    </>
  ),
}

/* ── 02 · the problem ────────────────────────────────────────────────────── */

const S2: Slide = {
  id: 's2',
  title: 'Deleting names does not work',
  blurb: 'A 1997 story, and 2,600 anonymous people becoming one.',
  Body: () => (
    <Stagger>
      <Line>
        <span className="eyebrow eyebrow-coral">the problem</span>
      </Line>
      <Line>
        <h2 className="title">
          A hospital has data that could save lives.{' '}
          <span className="hi hi-yellow">It cannot share it.</span>
        </h2>
      </Line>
      <Line>
        <Flow
          steps={[
            { title: 'Real records', sub: '50,000 patients', tone: 'cyan' },
            { title: 'Delete names', sub: 'the standard fix' },
            { title: 'Share it', sub: 'for research' },
            { title: 'Buy a voter list', sub: 'costs $20', tone: 'yellow' },
            { title: 'Match 3 columns', sub: 'ZIP + birthday + sex', tone: 'yellow' },
            { title: 'Person identified', sub: 'name and illness', tone: 'red' },
          ]}
        />
      </Line>
      <Line>
        <Reidentify />
      </Line>
    </Stagger>
  ),
  Notes: () => (
    <>
      <h4>say</h4>
      <p>
        Walk the arrows with your hand. The point of the flow is that{' '}
        <em>every single step is reasonable</em> — nobody was careless — and a named person
        still falls out of the end.
      </p>
      <p>
        Then drive the dots. Click "add one more column" three times: 2,600 → 208 → 7 → 1. When
        one is left, say it: "Nobody removed ZIP, birthday or sex, because none of them is a
        name. Together they are a fingerprint."
      </p>
      <p>
        The story, only after the animation: in 1997 Latanya Sweeney bought the Cambridge voter
        roll for twenty dollars, matched it against a hospital release the state had called
        de-identified, and mailed the Governor of Massachusetts his own medical records.
      </p>
      <h4>sources — published, not ours</h4>
      <p>
        Sweeney (1997); Sweeney (2000): roughly 87% of Americans are unique on ZIP + birthday +
        sex. The yellow flag on screen says so. Do not let anyone think we measured it.
      </p>
    </>
  ),
}

/* ── 03 · why the fixes fail ─────────────────────────────────────────────── */

const S3: Slide = {
  id: 's3',
  title: 'Three fixes people try. None of them hold.',
  blurb: 'Anonymise, aggregate, fake it — and why each one breaks.',
  Body: () => (
    <Stagger>
      <Line>
        <span className="eyebrow eyebrow-coral">why this is still open</span>
      </Line>
      <Line>
        <h2 className="title-sm">
          People have tried three things.{' '}
          <span className="hi hi-yellow">None of them survive contact with an attacker.</span>
        </h2>
      </Line>
      <Line>
        <div className="cols cols-3">
          {[
            {
              n: '1',
              head: 'Delete the names',
              body: 'The combination of the columns you kept is itself a fingerprint.',
              why: 'Broken in 1997. Still the default today.',
              cls: 'card-red',
            },
            {
              n: '2',
              head: 'Only share totals',
              body: 'Ask enough overlapping questions and the individual answers fall out.',
              why: 'Useless for research anyway — you cannot train a model on averages.',
              cls: 'card-red',
            },
            {
              n: '3',
              head: 'Generate fake data',
              body: 'Nothing stops a model from memorising and reprinting a real person.',
              why: 'Tested properly in 2022: none beat simply blurring the data by hand.',
              cls: 'card-yellow',
            },
          ].map((c) => (
            <div key={c.n} className={`card ${c.cls}`} style={{ height: '100%' }}>
              <span className="eyebrow" style={{ background: 'var(--ink)' }}>
                attempt {c.n}
              </span>
              <h3 style={{ fontSize: 'clamp(1.25rem,1.9vw,1.6rem)', margin: '0.4rem 0 0.35rem' }}>
                {c.head}
              </h3>
              <p className="body" style={{ margin: 0, maxWidth: 'none', color: 'var(--ink)' }}>
                {c.body}
              </p>
              <p style={{ margin: '0.5rem 0 0', fontSize: '0.98rem', fontWeight: 800, color: 'var(--red)' }}>
                {c.why}
              </p>
            </div>
          ))}
        </div>
      </Line>
      <Line>
        <div className="card card-cyan">
          <p className="lede" style={{ margin: 0, maxWidth: 'none' }}>
            All three answer <em>"is it anonymous?"</em> — a yes/no question with no honest
            answer. We are asking a different one:{' '}
            <span className="hi hi-violet">how much leaks, and how would you know?</span>
          </p>
        </div>
      </Line>
    </Stagger>
  ),
  Notes: () => (
    <>
      <h4>say</h4>
      <p>
        Three cards, one sentence each — do not over-explain. The third is the one that
        surprises people, because "just generate fake data" is what most teams propose. Stadler,
        Oprisanu &amp; Troncoso, USENIX Security 2022, tested the popular tools by attacking
        them and none beat simple blurring.
      </p>
      <p>
        Then the blue card, slowly. <strong>"Is it anonymous" is a yes/no question with no
        honest answer.</strong> We replace it with a measurement. That reframing is the project.
      </p>
    </>
  ),
}

/* ── 04 · the idea ───────────────────────────────────────────────────────── */

const S4: Slide = {
  id: 's4',
  title: 'The idea',
  blurb: 'Two numbers on every release, and the gap between them.',
  tone: 'dark',
  Body: () => (
    <>
      <Statement
        sub={
          <>
            One from mathematics, one from an attack. Nobody currently ships either one to the
            person receiving the data — let alone both.
          </>
        }
      >
        Every dataset we release will carry{' '}
        <span className="hi hi-violet">two numbers</span> and a signature.
      </Statement>

      <Beat delay={0.9}>
        <Gap
          middle="today these live in different papers"
          left={
            <div className="card card-violet" style={{ height: '100%' }}>
              <span className="eyebrow eyebrow-violet">number 1 · proved</span>
              <h3 style={{ fontSize: 'clamp(1.3rem,1.9vw,1.7rem)', margin: '0.4rem 0' }}>
                "The most that could leak."
              </h3>
              <p className="body" style={{ margin: 0, maxWidth: 'none', color: 'var(--ink)' }}>
                Calculated before anything runs. Holds against every possible attacker,
                including ones nobody has invented yet.
              </p>
            </div>
          }
          right={
            <div className="card card-coral" style={{ height: '100%' }}>
              <span className="eyebrow eyebrow-coral">number 2 · attacked</span>
              <h3 style={{ fontSize: 'clamp(1.3rem,1.9vw,1.7rem)', margin: '0.4rem 0' }}>
                "The least that did leak."
              </h3>
              <p className="body" style={{ margin: 0, maxWidth: 'none', color: 'var(--ink)' }}>
                Measured by attacking our own output on purpose, before anyone else gets the
                chance.
              </p>
            </div>
          }
        />
      </Beat>
    </>
  ),
  Notes: () => (
    <>
      <h4>say</h4>
      <p>
        "Every file we hand over will carry two numbers." Left: the most that could ever leak,
        proved with maths before anything runs. Right: the least that actually did leak,
        measured by attacking ourselves.
      </p>
      <p>
        Then the gap in the middle: <strong>"Today these two numbers live in different
        research papers, produced by different people, and neither reaches the person actually
        receiving the data."</strong> We put both on the file.
      </p>
      <h4>they will ask</h4>
      <p>
        <strong>"If the maths already proves it, why attack it?"</strong> — Because the proof is
        about the algorithm on paper, and the attack is about the code on the machine. Attacks
        have caught real bugs in real privacy libraries. It is a test for broken code.
      </p>
    </>
  ),
}

/* ── 05 · how it works ───────────────────────────────────────────────────── */

const S5: Slide = {
  id: 's5',
  title: 'How it will work',
  blurb: 'Six stages. Two cost privacy, one is free, and that surprises people.',
  Body: () => (
    <Stagger>
      <Line>
        <span className="eyebrow eyebrow-cyan">the design</span>
      </Line>
      <Line>
        <h2 className="title-sm">
          Six stages. <span className="hi hi-yellow">Two of them cost privacy.</span>
        </h2>
      </Line>
      <Line>
        <Flow
          steps={[
            { title: '1. Check', sub: 'is this table safe to try?', tone: 'cyan', tag: { text: 'free', kind: 'free' } },
            { title: '2. Learn columns', sub: 'what values exist?', tone: 'yellow', tag: { text: 'costs', kind: 'cost' } },
            { title: '3. Count + blur', sub: 'add measured noise', tone: 'yellow', tag: { text: 'costs', kind: 'cost' } },
            { title: '4. Build table', sub: 'from blurred counts only', tone: 'green', tag: { text: 'free', kind: 'free' } },
            { title: '5. Attack it', sub: 'we hunt our own output', tone: 'coral' },
            { title: '6. Certify', sub: 'sign and publish', tone: 'violet' },
          ]}
        />
      </Line>
      <Line>
        <div className="cols cols-3">
          <div className="card card-yellow">
            <span className="eyebrow" style={{ background: 'var(--ink)' }}>
              the bit others skip
            </span>
            <p className="body" style={{ margin: '0.4rem 0 0', maxWidth: 'none', color: 'var(--ink)' }}>
              Working out what values a column can hold is a <em>question about real people</em>.
              Most tools do it for free. We charge for it, or you declare it up front.
            </p>
          </div>
          <div className="card card-green">
            <span className="eyebrow" style={{ background: 'var(--ink)' }}>
              the surprise
            </span>
            <p className="body" style={{ margin: '0.4rem 0 0', maxWidth: 'none', color: 'var(--ink)' }}>
              Building the fake table costs <strong>nothing</strong>. Once data is private,
              anything you calculate from it stays private. That is a theorem, not a shortcut.
            </p>
          </div>
          <div className="card card-red">
            <span className="eyebrow" style={{ background: 'var(--ink)' }}>
              the refusal
            </span>
            <p className="body" style={{ margin: '0.4rem 0 0', maxWidth: 'none', color: 'var(--ink)' }}>
              Stage 1 reads only column names and a row count — <em>never the data</em>. A check
              that reads your data to decide if your data is safe is the bug it exists to stop.
            </p>
          </div>
        </div>
      </Line>
    </Stagger>
  ),
  Notes: () => (
    <>
      <h4>say</h4>
      <p>
        Walk the six boxes fast; the three cards below are where you slow down. Point at the
        yellow tags — <strong>stages 2 and 3 cost privacy budget</strong> — then at stage 4 in
        green and give the surprise: building the fake table is free, because once data is
        private anything computed from it stays private.
      </p>
      <p>
        The middle card is your differentiator against every off-the-shelf tool. Say it plainly:
        "finding out what a column can contain means looking at real people's values. Most tools
        charge nothing for that. We think that is a leak."
      </p>
    </>
  ),
}

/* ── 06 · watch it run ───────────────────────────────────────────────────── */

const S6: Slide = {
  id: 's6',
  title: 'Watch it run',
  blurb: 'The whole system in fifteen seconds. Press play.',
  Body: () => (
    <>
      <span className="eyebrow eyebrow-cyan">simulation</span>
      <h2 className="title-sm">
        Press play. <span className="hi hi-cyan">The whole thing, in fifteen seconds.</span>
      </h2>
      <PipelineSim />
    </>
  ),
  Notes: () => (
    <>
      <h4>say</h4>
      <p>
        Press play and <strong>stop talking</strong>. Let it run once end to end without
        narration — the room will follow the dots on their own.
      </p>
      <p>Then step back through the two moments that matter, by clicking the pills:</p>
      <p>
        <strong>Safety gate</strong> — "watch some rows disappear. Those are columns we refuse
        outright, before reading a single value."
      </p>
      <p>
        <strong>Add noise</strong> — "this is the only place privacy is actually bought.
        Everything after this point never sees a real value again."
      </p>
      <p>
        If they ask whether this is real output: no, and say so — it is a drawing of the design,
        which is what the flag on screen says. The working demo is slide 11.
      </p>
    </>
  ),
}

/* ── 07 · what is new ────────────────────────────────────────────────────── */

const VS = [
  { row: 'Makes synthetic data', sdv: true, gretel: true, sn: true, us: true },
  { row: 'Formal privacy guarantee', sdv: false, gretel: true, sn: true, us: true },
  { row: 'Attacks its own output', sdv: false, gretel: false, sn: false, us: true },
  { row: 'Ships both numbers to you', sdv: false, gretel: false, sn: false, us: true },
  { row: 'States the limit of its own attack', sdv: false, gretel: false, sn: false, us: true },
  { row: 'Refuses unsafe tables up front', sdv: false, gretel: false, sn: false, us: true },
  { row: 'Signed, checkable certificate', sdv: false, gretel: false, sn: false, us: true },
]

const S7: Slide = {
  id: 's7',
  title: 'What is actually new',
  blurb: 'Three design decisions nobody else makes.',
  Body: () => (
    <>
      <span className="eyebrow eyebrow-violet">novelty</span>
      <h2 className="title-sm">
        Three decisions <span className="hi hi-violet">nobody else makes.</span>
      </h2>
      <div className="cols cols-3">
        {[
          {
            n: '01',
            head: 'Both numbers, one run',
            body: 'The proof and the attack come from the same pipeline, on the same release, and both land on the file you receive.',
            cls: 'card-violet',
          },
          {
            n: '02',
            head: 'We print the limit of our own measurement',
            body: 'An attack that finds nothing might mean nothing leaked — or that the attack was too small to see it. We calculate which, and print it beside the result.',
            cls: 'card-yellow',
          },
          {
            n: '03',
            head: 'It says no',
            body: 'Give it a table with an ID column and it refuses, names the column, and tells you the fix — without reading a single value.',
            cls: 'card-coral',
          },
        ].map((c) => (
          <div key={c.n} className={`card ${c.cls}`} style={{ height: '100%' }}>
            <span className="hero-num" style={{ fontSize: 'clamp(1.6rem,2.4vw,2.1rem)' }}>
              {c.n}
            </span>
            <h3 style={{ fontSize: 'clamp(1.15rem,1.7vw,1.42rem)', margin: '0.3rem 0 0.35rem' }}>
              {c.head}
            </h3>
            <p className="body" style={{ margin: 0, maxWidth: 'none', color: 'var(--ink)', fontSize: '1.02rem' }}>
              {c.body}
            </p>
          </div>
        ))}
      </div>
      <div className="scroll-x">
        <table className="data vs">
          <colgroup>
            <col />
            <col />
            <col />
            <col />
            <col className="us" />
          </colgroup>
          <thead>
            <tr>
              <th>capability</th>
              <th>SDV</th>
              <th>Gretel</th>
              <th>SmartNoise</th>
              <th>SynthProof</th>
            </tr>
          </thead>
          <tbody>
            {VS.map((r) => (
              <tr key={r.row}>
                <td>{r.row}</td>
                {[r.sdv, r.gretel, r.sn, r.us].map((v, i) => (
                  <td key={i} className={v ? 'yes' : 'no'}>
                    {v ? '✓' : '—'}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  ),
  Notes: () => (
    <>
      <h4>say</h4>
      <p>
        Card 02 is the one to spend time on, and it is the most defensible thing in the project.
        "If you attack a dataset and find nothing, there are two possible reasons: nothing
        leaked, or your attack was too small to see it. Everyone reports the first. We calculate
        which one it was, and print it next to the number."
      </p>
      <p>
        Card 03 lands with examiners because it is counter-intuitive: <strong>a product whose
        feature is refusing to work.</strong> "It reads your column names and your row count. It
        never reads your data. A check that had to read your data to decide whether your data
        was safe would be the exact bug it exists to prevent."
      </p>
      <h4>the table — be careful and be fair</h4>
      <p>
        This compares published capabilities of general-purpose tools, not benchmark results.
        SDV is a synthesis library, not a privacy tool, and it does not claim otherwise. Gretel
        and SmartNoise do offer formal guarantees. If pushed, concede that immediately — the
        bottom four rows are the ones we are claiming, and they are design decisions, not
        performance claims.
      </p>
    </>
  ),
}

/* ── 08 · the output ─────────────────────────────────────────────────────── */

const S8: Slide = {
  id: 's8',
  title: 'What you actually receive',
  blurb: 'A privacy nutrition label attached to every release.',
  Body: () => (
    <>
      <span className="eyebrow eyebrow-violet">the deliverable</span>
      <h2 className="title-sm">
        Food tells you what is in it. <span className="hi hi-violet">Data should too.</span>
      </h2>
      <NutritionLabel />
    </>
  ),
  Notes: () => (
    <>
      <h4>say</h4>
      <p>
        Open with the metaphor and let it do all the work: "Every packet of food in this
        building lists its ingredients. No dataset anywhere does. That is what we are shipping."
      </p>
      <p>
        Then tap two lines in front of them. <strong>"Privacy budget spent"</strong> — one
        number for the whole file. Then <strong>"Limit of that attack"</strong> — and explain
        why it sits directly under the attack result: a zero nobody can interpret is worse than
        no number at all.
      </p>
      <p>
        Finish on the last two rows: columns you declared versus columns we had to guess.
        "Guessing costs privacy, so we count it and we tell you."
      </p>
      <h4>they will ask</h4>
      <p>
        <strong>"Who reads this?"</strong> — Three people: the data owner deciding whether to
        release, the researcher deciding whether the data is fit for their study, and an auditor
        checking the claim later. The signature is for the third one.
      </p>
    </>
  ),
}

/* ── 09 · use case ───────────────────────────────────────────────────────── */

const S9: Slide = {
  id: 's9',
  title: 'One hospital, end to end',
  blurb: 'A concrete scenario, and an attacker who fails.',
  Body: () => (
    <>
      <span className="eyebrow eyebrow-green">use case</span>
      <h2 className="title-sm">
        A hospital wants to share 50,000 diabetes records{' '}
        <span className="hi hi-green">with a university lab.</span>
      </h2>
      <Tabs
        tabs={[
          {
            label: '① what happens',
            node: (
              <div style={{ display: 'grid', gap: '0.7rem' }}>
                <Flow
                  steps={[
                    { title: 'Lab requests data', sub: 'diabetes study', tone: 'cyan' },
                    { title: 'Hospital uploads', sub: 'with a declared schema', tone: 'cyan' },
                    { title: 'We refuse one column', sub: 'patient ID — named, with a fix', tone: 'red' },
                    { title: 'Hospital drops it', sub: 're-uploads', tone: 'yellow' },
                    { title: 'Release + label', sub: 'signed certificate', tone: 'violet' },
                    { title: 'Lab trains a model', sub: 'no patient ever exposed', tone: 'green' },
                  ]}
                />
                <div className="cols cols-3">
                  <div className="card card-cyan">
                    <span className="eyebrow" style={{ background: 'var(--ink)' }}>
                      the hospital gets
                    </span>
                    <p className="body" style={{ margin: '0.35rem 0 0', maxWidth: 'none', color: 'var(--ink)' }}>
                      A defensible answer to "was it safe to share this?" — in writing, signed,
                      with a number.
                    </p>
                  </div>
                  <div className="card card-green">
                    <span className="eyebrow" style={{ background: 'var(--ink)' }}>
                      the lab gets
                    </span>
                    <p className="body" style={{ margin: '0.35rem 0 0', maxWidth: 'none', color: 'var(--ink)' }}>
                      Data in weeks instead of a year of ethics review, and a label telling them
                      what it is fit for.
                    </p>
                  </div>
                  <div className="card card-violet">
                    <span className="eyebrow" style={{ background: 'var(--ink)' }}>
                      the patient gets
                    </span>
                    <p className="body" style={{ margin: '0.35rem 0 0', maxWidth: 'none', color: 'var(--ink)' }}>
                      A guarantee that holds whether or not anyone ever bothers to attack the
                      file.
                    </p>
                  </div>
                </div>
              </div>
            ),
          },
          { label: '② now let an attacker try', node: <AttackTerminal /> },
        ]}
      />
    </>
  ),
  Notes: () => (
    <>
      <h4>say</h4>
      <p>
        Tab 1: walk the six boxes as a story, not a diagram. The box that matters is the red
        one — <strong>we refuse the patient ID column, name it, and say how to fix it.</strong>{' '}
        Most tools would have happily synthesised it and handed back real identifiers.
      </p>
      <p>
        Then the three cards: the same release solves a different problem for three different
        people. Panels remember that framing.
      </p>
      <p>
        Tab 2: press run and <strong>say nothing while it types.</strong> The first attack
        succeeds against the "anonymised" file. The same attack against ours returns zero
        matches, then 51% confidence — a coin flip. Only then speak: "same attacker, same
        target, same three columns."
      </p>
      <p>
        Be straight if asked: the transcript is a worked example of the designed behaviour, and
        the flag on screen says so.
      </p>
      <h4>other domains, if they ask</h4>
      <p>
        Banks sharing fraud data with vendors; telecoms releasing mobility data for city
        planning; any government open-data portal. Same shape: the holder cannot prove safety,
        so nothing moves.
      </p>
    </>
  ),
}

/* ── 10 · tech stack ─────────────────────────────────────────────────────── */

const STACK: Array<{ name: string; cls: string; items: string[]; why: string }> = [
  {
    name: 'Privacy core',
    cls: 'card-violet',
    items: ["Google dp_accounting", 'discrete Gaussian / Laplace', 'Ed25519 signatures'],
    why: 'We do not write our own privacy maths. Composition is delegated to a maintained library.',
  },
  {
    name: 'Generators',
    cls: 'card-cyan',
    items: ['private-PGM (AIM)', 'pairwise tree', 'independent marginals', 'moment baseline'],
    why: 'Four ways to build the table, from a deliberately naive baseline up to current state of the art.',
  },
  {
    name: 'Attack suite',
    cls: 'card-coral',
    items: ['one-run canary audit', 'density-ratio attack', 'exact-match check'],
    why: 'The half that hunts our own output.',
  },
  {
    name: 'Service + app',
    cls: 'card-green',
    items: ['Python 3.11', 'FastAPI', 'SQLite ledger', 'React + TypeScript', 'Vite', 'Docker'],
    why: 'A CLI for engineers, a web console for everyone else.',
  },
]

const S10: Slide = {
  id: 's10',
  title: 'What we are building it out of',
  blurb: 'Four layers. We buy the privacy maths, we build the rest.',
  Body: () => (
    <>
      <span className="eyebrow eyebrow-cyan">tech stack</span>
      <h2 className="title-sm">
        We <span className="hi hi-violet">buy</span> the privacy maths. We{' '}
        <span className="hi hi-cyan">build</span> everything around it.
      </h2>
      <div className="stack">
        {STACK.map((l) => (
          <div key={l.name} className={`stack-layer ${l.cls}`}>
            <span className="stack-name">{l.name}</span>
            <div style={{ display: 'grid', gap: '0.3rem' }}>
              <div className="stack-items">
                {l.items.map((i) => (
                  <span key={i} className="chip">
                    {i}
                  </span>
                ))}
              </div>
              <span style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--ink-2)', lineHeight: 1.25 }}>
                {l.why}
              </span>
            </div>
          </div>
        ))}
      </div>
      <div className="card card-yellow">
        <p className="lede" style={{ margin: 0, maxWidth: 'none' }}>
          The rule we work to:{' '}
          <span className="hi hi-yellow">if we cannot cite it, we do not claim it.</span> The
          privacy arithmetic is Google's, and it is checked against a second independent
          implementation.
        </p>
      </div>
    </>
  ),
  Notes: () => (
    <>
      <h4>say</h4>
      <p>
        Lead with the top layer and the rule at the bottom. "We do not write our own privacy
        mathematics. Composition — adding up the cost of many operations — is the part
        implementations get wrong, so we delegate it to Google's library and check it against a
        second one."
      </p>
      <p>
        That answers the sharpest question an examiner has: <em>how do I know your numbers are
        right?</em> Answer: attack Google's library, not our arithmetic.
      </p>
      <p>
        Row 2, be straight: AIM comes from the private-PGM authors. We integrate it; we did not
        invent it. Volunteering that is much stronger than being caught on it.
      </p>
      <h4>they will ask</h4>
      <p>
        <strong>"Why Python and not something faster?"</strong> — The privacy libraries live
        there, and the workload is dominated by counting, not by language speed.
      </p>
      <p>
        <strong>"Why SQLite?"</strong> — The spend ledger is append-only and single-writer. A
        heavier database would be infrastructure with no experiment behind it.
      </p>
    </>
  ),
}

/* ── 11 · MVP + roadmap ──────────────────────────────────────────────────── */

const S11: Slide = {
  id: 's11',
  title: 'What ships first',
  blurb: 'The MVP, then three phases.',
  Body: () => (
    <>
      <span className="eyebrow eyebrow-green">plan</span>
      <h2 className="title-sm">
        The smallest version that is <span className="hi hi-green">actually useful</span> — then
        three steps out.
      </h2>
      <div className="cols cols-2">
        <div className="card card-green">
          <span className="eyebrow" style={{ background: 'var(--ink)' }}>
            the MVP
          </span>
          <p style={{ fontSize: '1.2rem', fontWeight: 800, margin: '0.4rem 0 0.4rem' }}>
            One table in, one certified table out.
          </p>
          <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'grid', gap: '0.32rem' }}>
            {[
              'Upload a CSV with a declared schema',
              'Safety gate refuses unsafe columns, by name',
              'Choose how private you want it',
              'Get synthetic data + a signed label',
              'Verify the label with one command',
            ].map((i) => (
              <li key={i} style={{ fontSize: '1rem', fontWeight: 600, display: 'flex', gap: '0.5rem' }}>
                <span className="green" style={{ fontWeight: 900 }}>
                  ✓
                </span>
                {i}
              </li>
            ))}
          </ul>
        </div>
        <div className="card card-cyan">
          <span className="eyebrow" style={{ background: 'var(--ink)' }}>
            deliberately not in v1
          </span>
          <ul style={{ margin: '0.4rem 0 0', padding: 0, listStyle: 'none', display: 'grid', gap: '0.32rem' }}>
            {[
              'Many tables joined together',
              'Images, text, or time series',
              'Budget shared across many users',
              'Deep-learning generators',
            ].map((i) => (
              <li key={i} style={{ fontSize: '1rem', fontWeight: 600, display: 'flex', gap: '0.5rem' }}>
                <span style={{ color: 'var(--ink-3)', fontWeight: 900 }}>—</span>
                {i}
              </li>
            ))}
          </ul>
          <p style={{ margin: '0.55rem 0 0', fontSize: '0.98rem', fontWeight: 700 }}>
            Each is a real project on its own. Claiming them would be the fastest way to build
            none of them.
          </p>
        </div>
      </div>
      <div className="road">
        {[
          { when: 'phase 1', title: 'Prove the core', items: ['Budget accounting', 'Two generators', 'Safety gate'], cls: 'card-violet' },
          { when: 'phase 2', title: 'Make it honest', items: ['Self-attack suite', 'Print the attack limit', 'Signed labels'], cls: 'card-coral' },
          { when: 'phase 3', title: 'Make it usable', items: ['Web console', 'Second dataset', 'Reproducible runs'], cls: 'card-cyan' },
          { when: 'phase 4', title: 'Harden it', items: ['Stronger attacker', 'Budget across sessions', 'Third dataset'], cls: 'card-green' },
        ].map((s) => (
          <div key={s.when} className={`road-step ${s.cls}`}>
            <span className="road-when">{s.when}</span>
            <span className="road-title">{s.title}</span>
            <ul className="road-items">
              {s.items.map((i) => (
                <li key={i}>{i}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </>
  ),
  Notes: () => (
    <>
      <h4>say</h4>
      <p>
        Lead with the right-hand card, not the left. <strong>What you are refusing to build is
        more persuasive than what you are promising.</strong> "Multi-table, images, shared
        budgets — each is a project on its own. Claiming all of them is the fastest way to build
        none of them."
      </p>
      <p>
        Then the MVP as one sentence: one table in, one certified table out. Five bullets, do
        not elaborate.
      </p>
      <p>
        Phases left to right, one breath each. Note the ordering deliberately puts{' '}
        <em>"make it honest"</em> before <em>"make it usable"</em> — that is a statement about
        priorities and an examiner will notice it.
      </p>
      <p>
        If they want to see it working, this is the moment to switch to the live demo — five
        commands, script in <span className="mono">docs/DEMO_SCRIPT.md</span>.
      </p>
    </>
  ),
}

/* ── 12 · team + ask ─────────────────────────────────────────────────────── */

const S12: Slide = {
  id: 's12',
  title: 'Team and the ask',
  blurb: 'Who is building it, and what we want from you.',
  Body: () => (
    <Stagger>
      <Line>
        <span className="eyebrow">closing</span>
      </Line>
      <Line>
        <h2 className="title-sm">
          Four of us, <span className="hi hi-violet">one instrument.</span>
        </h2>
      </Line>
      <Line>
        <div className="cols cols-2">
          <div className="card">
            <span className="eyebrow" style={{ background: 'var(--ink)' }}>
              team · MIT-WPU CSE-AIDS · Panel B
            </span>
            <ul style={{ margin: '0.5rem 0 0', padding: 0, listStyle: 'none', display: 'grid', gap: '0.34rem' }}>
              {['Raj Modi', 'Krishna Renuse', 'Aaditya Kumar Sinha', 'Levinesh G R'].map((n) => (
                <li key={n} style={{ fontSize: '1.1rem', fontWeight: 700 }}>
                  {n}
                </li>
              ))}
            </ul>
          </div>
          <div className="card card-green">
            <span className="eyebrow" style={{ background: 'var(--ink)' }}>
              what we are asking for
            </span>
            <ul style={{ margin: '0.5rem 0 0', padding: 0, listStyle: 'none', display: 'grid', gap: '0.42rem' }}>
              {[
                'A hard look at decision 02 — printing the limit of our own attack. It is the claim we most want tested.',
                'A pointer to a public dataset with a published schema, for the second evaluation.',
                'Guidance on scope: is the safety gate a paper in its own right?',
              ].map((i) => (
                <li key={i} style={{ fontSize: '1rem', fontWeight: 600, lineHeight: 1.3 }}>
                  {i}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </Line>
      <Line>
        <div className="card card-cyan" style={{ textAlign: 'center' }}>
          <p className="title-sm" style={{ margin: 0 }}>
            Data you can share, <span className="hi hi-violet">with the receipt attached.</span>
          </p>
        </div>
      </Line>
    </Stagger>
  ),
  Notes: () => (
    <>
      <h4>say</h4>
      <p>
        Names quickly — add each person's area out loud if you want, but keep it to a few
        seconds. The right-hand card is the real content.
      </p>
      <p>
        Ask for something specific. A panel that is asked a real question engages; a panel that
        is asked "any questions?" judges. Decision 02 is the right thing to put in front of
        them, because it is genuinely arguable.
      </p>
      <p>Then the closing line, and stop. Do not add anything after it.</p>
      <h4>the three questions most likely to come</h4>
      <p>
        <strong>"Has anyone done this?"</strong> — The two halves exist separately, in different
        research communities. Shipping both on one release, with the limit of the measurement
        printed next to it, is ours.
      </p>
      <p>
        <strong>"Is this just a wrapper?"</strong> — The generators and the privacy arithmetic
        are existing work and we say so. The safety gate, the self-attack, the certificate and
        the limit calculation are the project.
      </p>
      <p>
        <strong>"Can a hospital use it tomorrow?"</strong> — No. Single table, one shared key,
        no budget across sessions. It is an instrument for checking releases, and we would
        rather say that than oversell it.
      </p>
    </>
  ),
}

export const SLIDES: Slide[] = [S1, S2, S3, S4, S5, S6, S7, S8, S9, S10, S11, S12]
