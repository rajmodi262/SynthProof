import type { ComponentType, ReactNode } from 'react'
import { motion, useReducedMotion } from 'framer-motion'

import { Tabs } from './Tabs'
import { BudgetBattery } from './widgets/BudgetBattery'
import { CopyMachine } from './widgets/CopyMachine'
import { FindYourself } from './widgets/FindYourself'
import { NutritionLabel } from './widgets/NutritionLabel'
import { ParticleTitle } from './widgets/ParticleTitle'
import { TwoHouses } from './widgets/TwoHouses'

/**
 * Thirteen slides — same visual language as the sibling deck, rebuilt content.
 *
 * The version this replaces had a real structural fault: the project itself did not appear
 * until slide 7, four concept demos ran back to back before it, and six slides carried under
 * forty words. Three things a review panel always needs were missing outright — a comparison
 * against existing approaches, the engineering challenges, and an evaluation plan.
 *
 * So the payload is redistributed. The project arrives at slide 4. Each demo is now attached
 * to the part of the system it explains rather than front-loaded. The freed slots pay for the
 * three missing slides. Every widget from the previous version survives.
 *
 * This is a proposal deck: nothing here is presented as an experimental result. Every figure
 * is either a published finding (attributed on the slide) or an illustration of the design,
 * and every illustration carries a flag.
 */

export type Slide = {
  id: string
  title: string
  blurb: string
  tone?: 'light' | 'dark'
  /** Turns the heartbeat rail crimson: used on the slides about leaks. */
  hotPulse?: boolean
  Body: ComponentType
  Notes: ComponentType
}

/* ── shared pieces ───────────────────────────────────────────────────────── */

function Rise({ children, delay = 0 }: { children: ReactNode; delay?: number }) {
  const reduce = useReducedMotion()
  return (
    <motion.div
      initial={{ opacity: 0, y: reduce ? 0 : 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: reduce ? 0 : 0.4, delay: reduce ? 0 : delay, ease: [0.22, 0.61, 0.36, 1] }}
    >
      {children}
    </motion.div>
  )
}

function DT({ head, rows }: { head: string[]; rows: ReactNode[][] }) {
  return (
    <div className="scrollx">
      <table className="dt">
        <thead>
          <tr>
            {head.map((h) => (
              <th key={h}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              {r.map((c, j) => (
                <td key={j}>{c}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
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

/* ── 01 · what it is ─────────────────────────────────────────────────────── */

const S1: Slide = {
  id: 's1',
  title: 'What SynthProof is',
  blurb: 'The name, the one-line definition, and what goes in and out.',
  tone: 'dark',
  Body: () => (
    <>
      <ParticleTitle />
      <Rise delay={2.1}>
        <p
          className="lede"
          style={{ margin: '0 auto', textAlign: 'center', maxWidth: '74ch', color: 'var(--sand)' }}
        >
          A system that turns a sensitive table into a{' '}
          <span className="hi hi-gold">safe, shareable synthetic version</span> — and attaches a
          signed certificate saying exactly how private it is.
        </p>
      </Rise>
      <Rise delay={2.4}>
        <div className="cols cols-3">
          <div className="card card-sand">
            <span className="eyebrow">1 · goes in</span>
            <p className="body" style={{ margin: '0.35rem 0 0', maxWidth: 'none' }}>
              One table of real people, plus a short declaration of what its columns contain.
            </p>
          </div>
          <div className="card card-gold">
            <span className="eyebrow eyebrow-gold">2 · we do</span>
            <p className="body" style={{ margin: '0.35rem 0 0', maxWidth: 'none' }}>
              Charge every touch to a <strong>privacy accountant</strong>, add calibrated noise,
              build a new table, then <strong>attack it ourselves</strong>.
            </p>
          </div>
          <div className="card card-jade">
            <span className="eyebrow eyebrow-jade">3 · comes out</span>
            <p className="body" style={{ margin: '0.35rem 0 0', maxWidth: 'none' }}>
              Synthetic data you can share, plus a <strong>Privacy Data Sheet</strong> — signed
              and machine-checkable.
            </p>
          </div>
        </div>
      </Rise>
      <Rise delay={2.7}>
        <p className="small" style={{ textAlign: 'center', margin: 0 }}>
          MIT-WPU · CSE-AIDS Capstone 2026-27 · Panel B · Raj Modi · Krishna Renuse · Aaditya
          Kumar Sinha · Levinesh G R
        </p>
      </Rise>
    </>
  ),
  Notes: () => (
    <>
      <h4>say — the project in thirty seconds</h4>
      <p>
        Let the dots assemble in silence, then: <strong>"Every dot is one person's
        record."</strong> Drag the slider hard left — the name is unreadable. "That is perfect
        privacy, and it is useless." Hard right — "now you can read it, and so can an attacker
        read the people inside."
      </p>
      <p>
        Then the three cards. <strong>Do not move on until the panel could repeat the middle
        one.</strong> Everything else in the deck is detail underneath it.
      </p>
      <p>The sentence to plant: "synthetic data is common; shipping proof with it is not."</p>
    </>
  ),
}

/* ── 02 · the problem ────────────────────────────────────────────────────── */

const S2: Slide = {
  id: 's2',
  title: 'The problem',
  blurb: 'Removing names does not work — and here is the published evidence.',
  hotPulse: true,
  Body: () => (
    <>
      <Rise>
        <div style={{ display: 'flex', gap: '0.8rem', alignItems: 'baseline', flexWrap: 'wrap' }}>
          <span className="eyebrow eyebrow-crimson">the problem</span>
          <h2 className="title-sm">
            Pick four ordinary facts. <span className="hi hi-crimson">We find one person.</span>
          </h2>
        </div>
      </Rise>
      <Rise delay={0.08}>
        <FindYourself />
      </Rise>
      <Rise delay={0.16}>
        <DT
          head={['this is not paranoia — it is documented', 'what happened']}
          rows={[
            [
              'Sweeney, 1997',
              'Re-identified the Governor of Massachusetts inside a "de-identified" hospital release, using a $20 voter roll.',
            ],
            [
              'Sweeney, 2000',
              <>
                <strong>87% of Americans</strong> are unique on ZIP code + date of birth + sex
                alone — three fields nobody calls identifying.
              </>,
            ],
            [
              'Netflix Prize, 2008',
              'Narayanan & Shmatikov de-anonymised users of an "anonymous" ratings dataset by matching public reviews.',
            ],
            [
              'EPFL, 2022',
              'Tested the popular synthetic-data tools by attacking them properly. None beat simple manual blurring.',
            ],
          ]}
        />
      </Rise>
    </>
  ),
  Notes: () => (
    <>
      <h4>say — hand this to the panel</h4>
      <p>
        <strong>Ask a panel member for their PIN code</strong>, then birth month, day, year.
        Read the counter aloud as it falls: one lakh → six thousand → five hundred → eighteen →{' '}
        <strong>one</strong>.
      </p>
      <p>
        Then: <strong>"That file had no names in it. It had a PIN code and a birthday — and it
        just pointed at one person in this room."</strong>
      </p>
      <p>
        Only then the table. Spend your time on row 2 (87% unique) and row 4 — EPFL 2022
        pre-empts the obvious suggestion, "just generate fake data", before anyone offers it.
      </p>
      <h4>sources — all published, none ours</h4>
      <p>
        Sweeney (1997, 2000); Narayanan &amp; Shmatikov (2008); Stadler, Oprisanu &amp; Troncoso,
        USENIX Security 2022. The crowd on screen is a drawing and is flagged as one.
      </p>
    </>
  ),
}

/* ── 03 · why every fix fails ────────────────────────────────────────────── */

const S3: Slide = {
  id: 's3',
  title: 'Why every existing fix fails',
  blurb: 'Four approaches, four specific failure modes, and the gap we build into.',
  Body: () => (
    <>
      <Rise>
        <div style={{ display: 'flex', gap: '0.8rem', alignItems: 'baseline', flexWrap: 'wrap' }}>
          <span className="eyebrow eyebrow-crimson">prior art</span>
          <h2 className="title-sm">
            Four things people try. <span className="hi hi-yellow">Each breaks in a known way.</span>
          </h2>
        </div>
      </Rise>
      <Rise delay={0.08}>
        <Tabs
          tabs={[
            {
              label: 'the four approaches',
              node: (
                <div style={{ display: 'grid', gap: '0.6rem' }}>
                  <DT
                    head={['approach', 'what it does', 'why it fails']}
                    rows={[
                      [
                        'Anonymisation',
                        'Delete names, IDs, addresses; share the rest.',
                        <span className="crimson">
                          The combination of the columns you kept is itself a fingerprint. Broken
                          in 1997; still the default today.
                        </span>,
                      ],
                      [
                        'Aggregation',
                        'Publish only totals and averages.',
                        <span className="crimson">
                          Enough overlapping totals let you subtract your way back to a person —
                          and you cannot train a model on averages.
                        </span>,
                      ],
                      [
                        'Synthetic data',
                        'Learn the statistics, generate a fake table (SDV, CTGAN).',
                        <span className="crimson">
                          Nothing stops the model memorising and reprinting a real person — see
                          the next tab.
                        </span>,
                      ],
                      [
                        'DP tools',
                        'Add calibrated noise under a formal guarantee (SmartNoise, Tumult).',
                        <span className="gold">
                          Genuinely sound — but you get a number nobody verifies, with no attack,
                          no certificate, and no statement of what the number is worth.
                        </span>,
                      ],
                    ]}
                  />
                  <div className="card card-dark">
                    <p className="lede" style={{ margin: 0, maxWidth: 'none', color: 'var(--sand)' }}>
                      Formal privacy <strong>proves</strong> a number nobody checks. Auditing{' '}
                      <strong>measures</strong> a number that guarantees nothing. Two separate
                      research communities.{' '}
                      <span className="hi hi-gold">Nothing ships both to the recipient.</span>
                    </p>
                  </div>
                </div>
              ),
            },
            { label: 'watch approach 3 fail', node: <CopyMachine /> },
          ]}
        />
      </Rise>
    </>
  ),
  Notes: () => (
    <>
      <h4>say</h4>
      <p>
        Walk the four rows. Rows 1–3 are what most people in the room would have proposed. Row 4
        is the serious prior art and <strong>be generous about it</strong> — SmartNoise and
        Tumult are sound tools. Our criticism is narrow: they hand you a number with nothing
        attached.
      </p>
      <p>
        Then the second tab, and press the button. One row lights crimson: a real patient copied
        word for word into a file labelled synthetic. Explain why it is always the same kind of
        row — <strong>a model memorises outliers, because for an outlier the pattern IS the
        person.</strong> The people most at risk are the ones a generator is most likely to
        reprint.
      </p>
      <p>Then the dark box, slowly. That sentence is the reason the project exists.</p>
      <h4>they will ask</h4>
      <p>
        <strong>"So you are adding a report on top of SmartNoise?"</strong> — No. The refusal
        gate, the self-attack, the detection-limit calculation and the signed ledger are new
        components. Slide 6 lists exactly what is ours and what is imported.
      </p>
    </>
  ),
}

/* ── 04 · what we are building ───────────────────────────────────────────── */

const S4: Slide = {
  id: 's4',
  title: 'What we are building',
  blurb: 'Architecture, the six stages, and which of them cost privacy.',
  Body: () => (
    <>
      <Rise>
        <div style={{ display: 'flex', gap: '0.8rem', alignItems: 'baseline', flexWrap: 'wrap' }}>
          <span className="eyebrow eyebrow-cyan" style={{ background: 'var(--gold)', color: 'var(--ink)' }}>
            the system
          </span>
          <h2 className="title-sm">
            Your table goes in. <span className="hi hi-gold">Safe data and a receipt come out.</span>
          </h2>
        </div>
      </Rise>
      <Rise delay={0.08}>
        <Steps
          items={[
            { name: 'Real table', sub: 'CSV + declared schema', tone: 'card-sand' },
            { name: '1 · Gate', sub: 'admit or refuse', tone: 'card-crimson', tag: 'free' },
            { name: '2 · Profile', sub: 'learn column domains', tone: 'card-gold', tag: 'cost' },
            { name: '3 · Measure', sub: 'noisy counts', tone: 'card-gold', tag: 'cost' },
            { name: '4 · Generate', sub: 'build fake table', tone: 'card-jade', tag: 'free' },
            { name: '5 · Audit', sub: 'attack our output', tone: 'card-crimson' },
            { name: '6 · Certify', sub: 'sign + ledger', tone: 'card-gold' },
          ]}
        />
      </Rise>
      <Rise delay={0.16}>
        <Tabs
          tabs={[
            {
              label: 'what each stage does',
              node: (
                <DT
                  head={['stage', 'what happens', 'reads real data?', 'costs ε?', 'output']}
                  rows={[
                    ['1 Gate', 'Checks declared column names and the row count only.', <span className="jade">no — never a cell</span>, <span className="jade">no</span>, 'admit, or a refusal naming the column'],
                    ['2 Profile', 'Works out what values each column can hold.', <span className="crimson">yes</span>, <span className="crimson">yes</span>, 'noisy column domains'],
                    ['3 Measure', 'Counts groups and pairs, adding exact discrete noise.', <span className="crimson">yes</span>, <span className="crimson">yes</span>, 'noisy marginals'],
                    ['4 Generate', 'Fits a model to the noisy counts and samples a table.', <span className="jade">no</span>, <span className="jade">no — post-processing</span>, 'synthetic table'],
                    ['5 Audit', 'Plants known records, runs the pipeline, attacks the output.', 'planted only', <span className="jade">no</span>, 'measured leak + its detection limit'],
                    ['6 Certify', 'Writes and signs the sheet; appends to a hash-chained ledger.', <span className="jade">no</span>, <span className="jade">no</span>, 'signed certificate'],
                  ]}
                />
              ),
            },
            { label: 'the budget, live', node: <BudgetBattery /> },
          ]}
        />
      </Rise>
      <Rise delay={0.24}>
        <div className="cols cols-3">
          <div className="card card-jade">
            <span className="eyebrow eyebrow-jade">the surprise</span>
            <p className="body" style={{ margin: '0.3rem 0 0', maxWidth: 'none', color: 'var(--ink)' }}>
              <strong>Generating is free.</strong> Once data is private, anything computed from
              it stays private — a theorem, not a shortcut.
            </p>
          </div>
          <div className="card card-crimson">
            <span className="eyebrow eyebrow-crimson">the bit others skip</span>
            <p className="body" style={{ margin: '0.3rem 0 0', maxWidth: 'none', color: 'var(--ink)' }}>
              <strong>Stage 2 costs budget.</strong> Learning a column&rsquo;s values is a
              question about real people. Most tools do it free and never say so.
            </p>
          </div>
          <div className="card card-sand">
            <span className="eyebrow">three ways in</span>
            <p className="body" style={{ margin: '0.3rem 0 0', maxWidth: 'none', color: 'var(--ink)' }}>
              A <strong>CLI</strong> for engineers, a <strong>REST API</strong> for pipelines,
              and a <strong>web console</strong> for everyone else.
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
        Walk the seven boxes with your hand, then let the table carry it. The two columns that
        matter are <strong>"reads real data?"</strong> and <strong>"costs ε?"</strong> — read
        those two down the page and the whole design becomes obvious.
      </p>
      <p>
        Second tab if you want it physical: press the buttons and watch the battery drain, then
        press one more at zero and let them read <strong>REFUSED</strong>.
      </p>
      <p>
        Then the three cards. Green is the surprise, red is the differentiator, sand answers
        "how would anyone actually use this".
      </p>
      <h4>they will ask</h4>
      <p>
        <strong>"Why does generation cost nothing?"</strong> — Post-processing invariance: any
        function of an ε-private output is still ε-private, because it never touched the
        original data.
      </p>
      <p>
        <strong>"What does the gate refuse?"</strong> — Identifier-like columns (about one
        distinct value per row), free text, tables under 500 rows, and column pairs whose grid is
        too large to be informative.
      </p>
    </>
  ),
}

/* ── 05 · the guarantee ──────────────────────────────────────────────────── */

const S5: Slide = {
  id: 's5',
  title: 'The guarantee',
  blurb: 'What differential privacy actually promises, and what ε means.',
  Body: () => (
    <>
      <Rise>
        <div style={{ display: 'flex', gap: '0.8rem', alignItems: 'baseline', flexWrap: 'wrap' }}>
          <span className="eyebrow eyebrow-gold">the core idea</span>
          <h2 className="title-sm">
            Two files, identical except one patient.{' '}
            <span className="hi hi-gold">Can you tell which is which?</span>
          </h2>
        </div>
      </Rise>
      <Rise delay={0.08}>
        <TwoHouses />
      </Rise>
      <Rise delay={0.16}>
        <div className="cols cols-2">
          <DT
            head={['ε said three ways', 'what it means']}
            rows={[
              ['A budget', 'One allowance per dataset. Every question spends some. At zero you stop — not ask more carefully, stop.'],
              ['A noise dial', 'Turn it down: safer, less useful. Turn it up: sharper, less safe. No setting gives you both.'],
              ['A cap on you', 'Removing your row changes any output by at most a factor of e^ε. That is why nobody can work backwards to you.'],
            ]}
          />
          <DT
            head={['ε', 'best guess an attacker can make about you']}
            rows={[
              ['0.1', <span className="jade">52 in 100 — barely better than a coin flip</span>],
              ['1.0', <span className="jade">73 in 100 — real but bounded</span>],
              ['4.0', <span className="gold">98 in 100 — almost certain</span>],
              ['8.0', <span className="crimson">100 in 100 — no protection worth the name</span>],
            ]}
          />
        </div>
      </Rise>
    </>
  ),
  Notes: () => (
    <>
      <h4>say — drag it, do not lecture</h4>
      <p>
        "Two hospitals. Identical records, except A has Priya and B does not. Ask both the same
        question." Start at no noise: the clouds sit apart —{' '}
        <strong>"the answer tells you Priya is in there."</strong> Drag right until the badge
        flips. <strong>"Now the answer looks the same whether or not she was ever in the file.
        That is the entire guarantee."</strong>
      </p>
      <p>
        Then the two tables. Use whichever framing the room reacts to. Read the last row of the
        right table aloud: at ε = 8 an attacker gets you right essentially every time — and most
        papers use ε = 8 without ever saying that.
      </p>
      <h4>they will ask</h4>
      <p>
        <strong>"Doesn't the noise make the answer wrong?"</strong> — Slightly, and that is the
        trade. The count is off by a few; the population-level finding survives. The certificate
        on slide 7 declares how much of that trade we spent.
      </p>
      <p>
        <strong>"Who picks ε?"</strong> — The data owner. The certificate records the choice so
        the recipient can judge it.
      </p>
    </>
  ),
}

/* ── 06 · novelty ────────────────────────────────────────────────────────── */

const S6: Slide = {
  id: 's6',
  title: 'What is new — and what is not',
  blurb: 'Three decisions nobody else makes, plus what we imported.',
  Body: () => (
    <>
      <Rise>
        <div style={{ display: 'flex', gap: '0.8rem', alignItems: 'baseline', flexWrap: 'wrap' }}>
          <span className="eyebrow eyebrow-gold">novelty</span>
          <h2 className="title-sm">
            Three decisions <span className="hi hi-gold">nobody else makes.</span>
          </h2>
        </div>
      </Rise>
      <Rise delay={0.08}>
        <div className="cols cols-3">
          {[
            { n: '01', h: 'Both numbers, one run', b: 'The proved bound and the attacked bound come from the same pipeline, on the same release, and both land on the file you receive.', c: 'card-gold' },
            { n: '02', h: 'We print the limit of our own attack', b: 'An attack finding nothing means either nothing leaked, or the attack was too small to see it. We calculate which, and print it beside the result.', c: 'card-dark' },
            { n: '03', h: 'It refuses', b: 'Unsafe tables are turned away before a single value is read, with the offending column named and a remedy given.', c: 'card-crimson' },
          ].map((c) => (
            <div key={c.n} className={`card ${c.c}`} style={{ height: '100%' }}>
              <span className="eyebrow eyebrow-gold">novelty {c.n}</span>
              <h3 style={{ fontSize: '1.5rem', margin: '0.3rem 0 0.25rem' }}>{c.h}</h3>
              <p
                className="body"
                style={{ margin: 0, maxWidth: 'none', fontSize: '1.02rem', color: c.c === 'card-dark' ? 'var(--sand)' : 'var(--ink)' }}
              >
                {c.b}
              </p>
            </div>
          ))}
        </div>
      </Rise>
      <Rise delay={0.16}>
        <div className="scrollx">
          <table className="dt">
            <thead>
              <tr>
                <th>capability</th>
                <th style={{ textAlign: 'center' }}>SDV</th>
                <th style={{ textAlign: 'center' }}>Gretel</th>
                <th style={{ textAlign: 'center' }}>SmartNoise</th>
                <th style={{ textAlign: 'center' }}>Tumult</th>
                <th style={{ textAlign: 'center' }}>SynthProof</th>
              </tr>
            </thead>
            <tbody>
              {[
                ['Generates synthetic tables', 1, 1, 1, 1, 1],
                ['Formal privacy guarantee', 0, 1, 1, 1, 1],
                ['Attacks its own output', 0, 0, 0, 0, 1],
                ['Ships both numbers to the recipient', 0, 0, 0, 0, 1],
                ['States the limit of its own attack', 0, 0, 0, 0, 1],
                ['Refuses unsafe tables up front', 0, 0, 0, 0, 1],
                ['Signed, checkable certificate', 0, 0, 0, 0, 1],
              ].map(([label, ...cells]) => (
                <tr key={label as string}>
                  <td>{label}</td>
                  {(cells as number[]).map((v, i) => (
                    <td key={i} className={`c ${v ? 'yes' : 'no'} ${i === 4 ? 'us' : ''}`}>
                      {v ? '✓' : '—'}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Rise>
      <Rise delay={0.24}>
        <div className="card card-sand">
          <span className="eyebrow">what we did NOT invent — say this before being asked</span>
          <p className="body" style={{ margin: '0.3rem 0 0', maxWidth: 'none', color: 'var(--ink)' }}>
            The privacy arithmetic is Google&rsquo;s <Src>dp_accounting</Src>. The strongest
            generator is <Src>AIM</Src> from the private-PGM authors. The one-run audit is
            Steinke, Nasr &amp; Jagielski (2023), and the fact that an attack has a detection
            limit is known in that literature.{' '}
            <strong>Ours is the integration, the refusal gate, the certificate, and the decision
            to report the limit beside every number.</strong>
          </p>
        </div>
      </Rise>
    </>
  ),
  Notes: () => (
    <>
      <h4>say</h4>
      <p>
        Card 02 is the most defensible thing in the project — give it the most time. "If your
        attack finds nothing there are two possible reasons: nothing leaked, or your attack was
        too weak to see it. Everyone reports the first. We work out which, and print it."
      </p>
      <p>
        Card 03 lands because it is counter-intuitive: <strong>a product whose headline feature
        is refusing to work.</strong>
      </p>
      <h4>the table — be scrupulous</h4>
      <p>
        These are published capabilities, not benchmark results. SDV is a synthesis library and
        does not claim to be a privacy tool; Gretel, SmartNoise and Tumult all offer genuine
        formal guarantees. <strong>Concede that immediately if pushed</strong> — our claim is the
        bottom four rows only, and they are design decisions rather than performance claims.
      </p>
      <h4>the last card is not optional</h4>
      <p>
        Read it out. Volunteering what you imported is far stronger than being caught on it, and
        it makes the three claims above more credible rather than less.
      </p>
    </>
  ),
}

/* ── 07 · the certificate ────────────────────────────────────────────────── */

const S7: Slide = {
  id: 's7',
  title: 'What you actually receive',
  blurb: 'The Privacy Data Sheet, field by field, and who reads it.',
  Body: () => (
    <>
      <Rise>
        <div style={{ display: 'flex', gap: '0.8rem', alignItems: 'baseline', flexWrap: 'wrap' }}>
          <span className="eyebrow eyebrow-gold">the deliverable</span>
          <h2 className="title-sm">
            Food tells you what is inside. <span className="hi hi-gold">Data should too.</span>
          </h2>
        </div>
      </Rise>
      <Rise delay={0.08}>
        <NutritionLabel />
      </Rise>
      <Rise delay={0.16}>
        <DT
          head={['who reads it', 'the question they are answering', 'the field they look at']}
          rows={[
            ['Data owner', 'Is it defensible for me to release this at all?', 'privacy budget spent · columns we had to guess'],
            ['Researcher', 'Is this data fit for the study I want to run?', 'records released · what the attack found'],
            ['Auditor, later', 'Is this the file that was actually produced?', 'the signature and the ledger entry'],
          ]}
        />
      </Rise>
    </>
  ),
  Notes: () => (
    <>
      <h4>say</h4>
      <p>
        Open on the metaphor: <strong>"Every packet of food in this building lists its
        ingredients. No dataset anywhere does."</strong>
      </p>
      <p>
        Tap exactly two lines. <strong>Privacy budget spent</strong> — one number for the whole
        file. Then <strong>limit of that attack</strong>, and explain why it sits directly under
        the attack result: a zero nobody can interpret is worse than no number at all.
      </p>
      <p>
        Then the table underneath — it answers the question a panel always asks about a
        certificate, which is <em>who is this for?</em> Three different readers, three different
        fields, one file.
      </p>
    </>
  ),
}

/* ── 08 · applications ───────────────────────────────────────────────────── */

const S8: Slide = {
  id: 's8',
  title: 'Where this gets used',
  blurb: 'Four sectors with the same shape, and one worked end-to-end.',
  Body: () => (
    <>
      <Rise>
        <div style={{ display: 'flex', gap: '0.8rem', alignItems: 'baseline', flexWrap: 'wrap' }}>
          <span className="eyebrow eyebrow-jade">applications</span>
          <h2 className="title-sm">
            Same shape everywhere:{' '}
            <span className="hi hi-jade">the holder cannot prove safety, so nothing moves.</span>
          </h2>
        </div>
      </Rise>
      <Rise delay={0.08}>
        <Tabs
          tabs={[
            {
              label: 'four sectors',
              node: (
                <DT
                  head={['sector', 'who holds the data', 'who needs it', 'what we unblock']}
                  rows={[
                    ['Healthcare', 'Hospital with 50,000 diabetes records', 'University lab building a risk model', 'A signed, defensible answer to "was it safe to share this?"'],
                    ['Banking', 'Bank with labelled fraud transactions', 'A vendor training a detection model', 'Share the patterns without exposing any customer account'],
                    ['Telecom', 'Operator with mobility traces', 'City planners modelling transport', 'Population movement without individual journeys'],
                    ['Government', 'Census or scheme-enrolment records', 'Open-data portal, researchers, NGOs', 'Publish usable microdata with the privacy cost printed on it'],
                  ]}
                />
              ),
            },
            {
              label: 'one hospital, end to end',
              node: (
                <div style={{ display: 'grid', gap: '0.6rem' }}>
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
                  <div className="cols cols-3">
                    {[
                      { h: 'the hospital gets', b: 'A written, signed answer to "was it safe?" — with a number on it.', c: 'card-gold' },
                      { h: 'the lab gets', b: 'Data in weeks instead of a year of review, plus a label saying what it is fit for.', c: 'card-jade' },
                      { h: 'the patient gets', b: 'A guarantee that holds whether or not anyone ever attacks the file.', c: 'card-sand' },
                    ].map((x) => (
                      <div key={x.h} className={`card ${x.c}`}>
                        <span className="eyebrow">{x.h}</span>
                        <p className="body" style={{ margin: '0.3rem 0 0', maxWidth: 'none', color: 'var(--ink)' }}>
                          {x.b}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              ),
            },
          ]}
        />
      </Rise>
    </>
  ),
  Notes: () => (
    <>
      <h4>say</h4>
      <p>
        Read the headline, then <strong>pick one row and tell it as a story</strong> — do not
        read all four. Healthcare is strongest because the refusal step is vivid.
      </p>
      <p>
        Then switch to the second tab and walk the six boxes. The crimson one is the moment:{' '}
        <strong>we refuse the patient-ID column, name it, and say how to fix it.</strong> Most
        tools would have cheerfully synthesised it and handed back real identifiers — which is
        exactly what slide 3 showed happening.
      </p>
      <p>Close on the three cards: one release, three different problems solved.</p>
    </>
  ),
}

/* ── 09 · tech stack ─────────────────────────────────────────────────────── */

const STACK = [
  {
    name: 'Privacy core',
    cls: 'card-gold',
    items: ['Google dp_accounting', 'discrete Gaussian / Laplace', 'Ed25519 signatures'],
    why: 'Bought, not built, and cross-checked against a second implementation. Composition is where DP code goes wrong, and the error is silent.',
  },
  {
    name: 'Generators',
    cls: 'card-sand',
    items: ['private-PGM (AIM)', 'pairwise tree', 'independent marginals', 'moment baseline'],
    why: 'Four options from a deliberately naive baseline up to current state of the art, so the comparison is honest.',
  },
  {
    name: 'Attack suite',
    cls: 'card-crimson',
    items: ['one-run canary audit', 'density-ratio attack', 'exact-match check'],
    why: 'The half that hunts our own output before anyone outside gets the chance.',
  },
  {
    name: 'Product',
    cls: 'card-jade',
    items: ['Python 3.11', 'FastAPI', 'SQLite ledger', 'React + TypeScript', 'Docker'],
    why: 'A CLI for engineers, an API for pipelines, a console for everyone else.',
  },
]

const S9: Slide = {
  id: 's9',
  title: 'What we build it from',
  blurb: 'Four layers, and why each choice was made.',
  Body: () => (
    <>
      <Rise>
        <div style={{ display: 'flex', gap: '0.8rem', alignItems: 'baseline', flexWrap: 'wrap' }}>
          <span className="eyebrow eyebrow-gold">tech stack</span>
          <h2 className="title-sm">
            We <span className="hi hi-gold">buy</span> the privacy maths. We{' '}
            <span className="hi hi-jade">build</span> everything around it.
          </h2>
        </div>
      </Rise>
      <Rise delay={0.08}>
        <div style={{ display: 'grid', gap: '0.5rem' }}>
          {STACK.map((l) => (
            <div key={l.name} className={`stack-layer ${l.cls}`}>
              <span style={{ fontSize: '1.02rem', fontWeight: 900, lineHeight: 1.1 }}>{l.name}</span>
              <div style={{ display: 'grid', gap: '0.22rem' }}>
                <div className="chips">
                  {l.items.map((i) => (
                    <span key={i} className="chip">
                      {i}
                    </span>
                  ))}
                </div>
                <span style={{ fontSize: '0.92rem', fontWeight: 600, color: 'var(--ink-2)', lineHeight: 1.24 }}>
                  {l.why}
                </span>
              </div>
            </div>
          ))}
        </div>
      </Rise>
      <Rise delay={0.16}>
        <div className="cols cols-2">
          <div className="card card-dark">
            <p className="lede" style={{ margin: 0, maxWidth: 'none', color: 'var(--sand)' }}>
              The rule we work to:{' '}
              <span className="hi hi-gold">if we cannot cite it, we do not claim it.</span>
            </p>
          </div>
          <DT
            head={['choice', 'why']}
            rows={[
              ['Python 3.11', 'The privacy libraries live there, and the workload is counting, not language speed.'],
              ['SQLite for the ledger', 'Append-only, single writer. A heavier database would be infrastructure with no experiment behind it.'],
            ]}
          />
        </div>
      </Rise>
    </>
  ),
  Notes: () => (
    <>
      <h4>say</h4>
      <p>
        Lead with the top layer and the rule. "We do not write our own privacy mathematics.
        Adding up the cost of many operations is the part implementations get wrong, so we
        delegate it and check it against a second library."
      </p>
      <p>
        That answers the sharpest question a reviewer has — <em>how do I know your numbers are
        right?</em> — with: attack Google&rsquo;s library, not our arithmetic.
      </p>
      <p>
        Row 2, volunteer it: AIM comes from the private-PGM authors. We integrate it, we did not
        invent it.
      </p>
    </>
  ),
}

/* ── 10 · the hard part ──────────────────────────────────────────────────── */

const S10: Slide = {
  id: 's10',
  title: 'The hard part',
  blurb: 'Five problems that make this more than plumbing.',
  hotPulse: true,
  Body: () => (
    <>
      <Rise>
        <div style={{ display: 'flex', gap: '0.8rem', alignItems: 'baseline', flexWrap: 'wrap' }}>
          <span className="eyebrow eyebrow-crimson">engineering</span>
          <h2 className="title-sm">
            Five problems that make this{' '}
            <span className="hi hi-crimson">more than plumbing.</span>
          </h2>
        </div>
      </Rise>
      <Rise delay={0.08}>
        <DT
          head={['challenge', 'why it is hard', 'our approach']}
          rows={[
            [
              'Charging for schema discovery',
              'Learning a column’s range is a query against real people, but every tool treats it as free setup.',
              'Charge it to the accountant, or require a declared public schema — and record which was used on the certificate.',
            ],
            [
              'Composition arithmetic',
              'Adding up the cost of many operations is where DP implementations go wrong, and the error is silent.',
              <>
                Delegate to <Src>dp_accounting</Src> and differentially test against a second
                independent implementation.
              </>,
            ],
            [
              'Exact noise sampling',
              'Sampling continuous noise and rounding to integers reopens known floating-point attacks.',
              'Discrete Gaussian and discrete Laplace samplers, verified against the exact distribution.',
            ],
            [
              'Knowing what “no leak found” means',
              'An attack that finds nothing is usually written up as a clean result. It may simply have been too small to detect anything.',
              'Compute the detection limit for the attack we ran, and print it beside the result.',
            ],
            [
              'Making the certificate trustworthy',
              'A hash chain catches edits in the middle — but a chain with its tail cut off is still internally consistent.',
              'An Ed25519-signed head that commits to the chain length, so truncation is caught too.',
            ],
          ]}
        />
      </Rise>
      <Rise delay={0.16}>
        <div className="card card-dark">
          <p className="lede" style={{ margin: 0, maxWidth: 'none', color: 'var(--sand)' }}>
            Every one of these is a place a privacy tool can be{' '}
            <span className="hi hi-crimson">quietly wrong</span> — and a quietly wrong privacy
            tool is worse than no tool at all.
          </p>
        </div>
      </Rise>
    </>
  ),
  Notes: () => (
    <>
      <h4>say — this is the engineering credibility slide</h4>
      <p>
        Do not read all five. <strong>Pick two.</strong> Row 1 is the differentiator: everyone
        else treats schema discovery as free setup; we treat it as a query about real people.
        Row 4 is the intellectual one: an attack that finds nothing only means something if you
        also know what it could have detected.
      </p>
      <p>
        Then the dark box. That is the sentence to leave hanging before the evaluation slide:
        the failure mode of this whole field is being <em>quietly</em> wrong.
      </p>
      <h4>if they push on row 3</h4>
      <p>
        Floating-point attacks on naive DP implementations are a real published class. Sampling
        discretely from the start avoids them, which is why we do not sample a float and round.
      </p>
    </>
  ),
}

/* ── 11 · evaluation plan ────────────────────────────────────────────────── */

const S11: Slide = {
  id: 's11',
  title: 'How we will know it works',
  blurb: 'Datasets, metrics, success criteria — and what would prove us wrong.',
  Body: () => (
    <>
      <Rise>
        <div style={{ display: 'flex', gap: '0.8rem', alignItems: 'baseline', flexWrap: 'wrap' }}>
          <span className="eyebrow eyebrow-jade">evaluation</span>
          <h2 className="title-sm">
            How we will know it works —{' '}
            <span className="hi hi-jade">and what would prove us wrong.</span>
          </h2>
        </div>
      </Rise>
      <Rise delay={0.08}>
        <div className="cols cols-2">
          <DT
            head={['what we measure', 'how']}
            rows={[
              ['Fidelity', 'How far the relationships between columns drift from the real data.'],
              ['Utility', 'Train a classifier on the synthetic data, test it on real data. Compare against training on real data.'],
              ['Privacy — proved', 'The ε the accountant charges, calibrated so we never overspend what was requested.'],
              ['Privacy — attacked', 'What our own attack recovers, reported next to the limit of what it could have found.'],
            ]}
          />
          <div style={{ display: 'grid', gap: '0.5rem' }}>
            <div className="card card-gold">
              <span className="eyebrow eyebrow-gold">datasets</span>
              <ul className="pts" style={{ marginTop: '0.3rem' }}>
                <li>
                  <strong>UCI Adult</strong> — the standard benchmark, so results are comparable
                  to published work.
                </li>
                <li>
                  <strong>ACS PUMS (folktables)</strong> — a second, larger, real-world source.
                  A single-dataset conclusion is not a conclusion.
                </li>
              </ul>
            </div>
            <div className="card card-sand">
              <span className="eyebrow">method</span>
              <ul className="pts" style={{ marginTop: '0.3rem' }}>
                <li>Hypotheses written into version control <strong>before</strong> any result exists.</li>
                <li>Multiple random seeds; every number carries an uncertainty range.</li>
                <li>Every result regenerates from a committed manifest at a fixed seed.</li>
              </ul>
            </div>
          </div>
        </div>
      </Rise>
      <Rise delay={0.16}>
        <div className="cols cols-2">
          <div className="card card-jade">
            <span className="eyebrow eyebrow-jade">success looks like</span>
            <p className="body" style={{ margin: '0.3rem 0 0', maxWidth: 'none', color: 'var(--ink)' }}>
              A release whose certificate a third party can verify, whose utility is close
              enough to the real data to train a usable model, and whose numbers <strong>a
              stranger can reproduce from our repository.</strong>
            </p>
          </div>
          <div className="card card-crimson">
            <span className="eyebrow eyebrow-crimson">what would prove us wrong</span>
            <p className="body" style={{ margin: '0.3rem 0 0', maxWidth: 'none', color: 'var(--ink)' }}>
              A stronger attacker recovering more than our stated bound; the accountant
              disagreeing with an independent implementation; or the fidelity ordering{' '}
              <strong>failing to hold on the second dataset.</strong>
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
        This is the slide that separates a project from a demo. Four things measured, two
        datasets, and — the part reviewers care about — <strong>a stated falsification
        condition.</strong>
      </p>
      <p>
        Land the last card deliberately: "we have written down, in advance, the results that
        would mean we were wrong." Very few student projects can say that, and saying it is
        worth more than any positive result you could show.
      </p>
      <p>
        On datasets, volunteer the reasoning: <strong>a single-dataset conclusion is not a
        conclusion</strong>, which is why the second one is a deliverable and not a stretch goal.
      </p>
      <h4>they will ask</h4>
      <p>
        <strong>"Why those two datasets?"</strong> — Adult is the standard benchmark so our
        numbers are comparable to published work; ACS is larger and closer to real
        administrative data. Different shapes, so a result that only holds on one is visible as
        such.
      </p>
    </>
  ),
}

/* ── 12 · MVP + roadmap ──────────────────────────────────────────────────── */

const S12: Slide = {
  id: 's12',
  title: 'What ships first',
  blurb: 'The MVP, what is deliberately excluded, and the four phases.',
  Body: () => (
    <>
      <Rise>
        <div style={{ display: 'flex', gap: '0.8rem', alignItems: 'baseline', flexWrap: 'wrap' }}>
          <span className="eyebrow eyebrow-jade">plan</span>
          <h2 className="title-sm">
            The smallest version that is <span className="hi hi-jade">actually useful.</span>
          </h2>
        </div>
      </Rise>
      <Rise delay={0.08}>
        <div className="cols cols-2">
          <div className="card card-jade">
            <span className="eyebrow eyebrow-jade">MVP — in scope</span>
            <ul className="pts pts-yes" style={{ marginTop: '0.3rem' }}>
              <li>Upload one CSV with a declared schema</li>
              <li>Gate refuses unsafe columns, by name, with a remedy</li>
              <li>Choose the privacy setting</li>
              <li>Get synthetic data + a signed Privacy Data Sheet</li>
              <li>Verify the sheet with one command</li>
              <li>CLI, REST API and web console</li>
            </ul>
          </div>
          <div className="card card-sand">
            <span className="eyebrow">deliberately NOT in v1</span>
            <ul className="pts pts-no" style={{ marginTop: '0.3rem' }}>
              <li>Several tables joined together</li>
              <li>Images, free text or time series</li>
              <li>One budget shared across many users and sessions</li>
              <li>Deep-learning generators (DP-SGD)</li>
            </ul>
            <p className="small" style={{ marginTop: '0.4rem' }}>
              Each is a project on its own. Claiming all four is the fastest way to build none.
            </p>
          </div>
        </div>
      </Rise>
      <Rise delay={0.16}>
        <div className="cols cols-4" style={{ gridTemplateColumns: 'repeat(4, minmax(0,1fr))' }}>
          {[
            { w: 'Phase 1', t: 'Prove the core', i: 'Budget accounting · two generators · the refusal gate', c: 'card-gold' },
            { w: 'Phase 2', t: 'Make it honest', i: 'Self-attack suite · print the detection limit · signed certificates', c: 'card-crimson' },
            { w: 'Phase 3', t: 'Make it usable', i: 'Web console · second dataset · reproducible runs', c: 'card-sand' },
            { w: 'Phase 4', t: 'Harden it', i: 'Stronger attacker · budget across sessions · third dataset', c: 'card-jade' },
          ].map((p) => (
            <div key={p.w} className={`card ${p.c}`} style={{ padding: '0.5rem 0.65rem' }}>
              <span className="eyebrow" style={{ fontSize: 10 }}>
                {p.w}
              </span>
              <div style={{ fontSize: '1.02rem', fontWeight: 800, margin: '0.2rem 0 0.1rem' }}>
                {p.t}
              </div>
              <div style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--ink-2)', lineHeight: 1.24 }}>
                {p.i}
              </div>
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
        Lead with the RIGHT card. <strong>What you refuse to build is more persuasive than what
        you promise.</strong> Then the MVP in one sentence — one table in, one certified table
        out — and the five bullets without elaboration.
      </p>
      <p>
        Phases left to right, one breath each. Note the order puts <em>make it honest</em>{' '}
        before <em>make it usable</em>; that is a real statement of priorities and a reviewer
        will notice it.
      </p>
      <p>
        This is the natural moment to offer the live demo — five commands, script in{' '}
        <Src>docs/DEMO_SCRIPT.md</Src>.
      </p>
    </>
  ),
}

/* ── 13 · team, risks, ask ───────────────────────────────────────────────── */

const S13: Slide = {
  id: 's13',
  title: 'Team, risks and the ask',
  blurb: 'Who is building it, what could go wrong, and what we want from you.',
  tone: 'dark',
  Body: () => (
    <>
      <Rise>
        <div style={{ display: 'flex', gap: '0.8rem', alignItems: 'baseline', flexWrap: 'wrap' }}>
          <span className="eyebrow eyebrow-gold">closing</span>
          <h2 className="title-sm" style={{ color: 'var(--sand)' }}>
            Four of us. <span className="hi hi-gold">One instrument.</span>
          </h2>
        </div>
      </Rise>
      <Rise delay={0.08}>
        <div className="cols cols-3">
          <div className="card">
            <span className="eyebrow eyebrow-gold">team · MIT-WPU CSE-AIDS · Panel B</span>
            <ul className="pts" style={{ marginTop: '0.35rem' }}>
              {['Raj Modi', 'Krishna Renuse', 'Aaditya Kumar Sinha', 'Levinesh G R'].map((n) => (
                <li key={n}>
                  <strong>{n}</strong>
                </li>
              ))}
            </ul>
          </div>
          <div className="card card-crimson">
            <span className="eyebrow eyebrow-crimson">risks we are carrying</span>
            <ul className="pts" style={{ marginTop: '0.35rem' }}>
              <li>
                <strong>Single dataset early.</strong> Any conclusion is provisional until the
                second lands — so it is a deliverable, not a stretch goal.
              </li>
              <li>
                <strong>One attacker.</strong> A stronger one could move every number. We report
                the detection limit so nothing is over-read.
              </li>
              <li>
                <strong>Not deployment-ready.</strong> Single table, one shared key, no
                cross-session budget.
              </li>
            </ul>
          </div>
          <div className="card card-jade">
            <span className="eyebrow eyebrow-jade">what we want from you</span>
            <ul className="pts" style={{ marginTop: '0.35rem' }}>
              <li>
                <strong>Attack novelty 02</strong> — printing the limit of our own attack is the
                claim we most want stress-tested.
              </li>
              <li>
                <strong>A second public dataset</strong> with a published schema.
              </li>
              <li>
                <strong>Scope guidance:</strong> is the refusal gate a contribution on its own?
              </li>
            </ul>
          </div>
        </div>
      </Rise>
      <Rise delay={0.18}>
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
        Names fast. Then the <strong>middle card</strong>, and do not soften it — volunteering
        your own risks is the most credible thing you can do at the end of a review, and it
        removes the panel&rsquo;s best questions before they ask them.
      </p>
      <p>
        Then the ask. Be specific: a panel that is asked a real question engages; a panel asked
        "any questions?" judges. Then the closing line, and stop.
      </p>
      <h4>the three questions most likely to come</h4>
      <p>
        <strong>"Has anyone done this?"</strong> — The two halves exist separately in different
        research communities. Shipping both on one release, with the limit of the measurement
        printed beside it, is ours.
      </p>
      <p>
        <strong>"Is this just a wrapper?"</strong> — The generators and the privacy arithmetic
        are existing work, and slide 6 says so. The gate, the self-attack, the certificate and
        the limit calculation are the project.
      </p>
      <p>
        <strong>"Can a hospital use it tomorrow?"</strong> — No, and the risk card says why. It
        is an instrument for checking releases, not a production pipeline.
      </p>
    </>
  ),
}

export const SLIDES: Slide[] = [S1, S2, S3, S4, S5, S6, S7, S8, S9, S10, S11, S12, S13]
