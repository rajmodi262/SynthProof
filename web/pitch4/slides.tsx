import type { ComponentType, ReactNode } from 'react'

import { EpsilonDial } from './widgets/EpsilonDial'
import { Wordmark } from './widgets/Wordmark'

/**
 * Nine slides for a capstone review panel.
 *
 * The previous decks failed the same way twice: they were designed before they were written,
 * and a panel left unable to say what the project actually was. This one is organised around
 * the eight questions a reviewer has to be able to answer afterwards —
 *
 *   what is it · why does it matter · why doesn't the existing stuff work · how does it work ·
 *   what is the guarantee · what is new · what ships and where is it used · what was hard ·
 *   what happens next
 *
 * — with one diagram or table per slide carrying the information, and the styling in service
 * of reading it.
 *
 * This is a proposal deck. Nothing on screen is presented as an experimental result: every
 * figure is either a published finding (attributed on the slide or in the notes) or an
 * illustration of the design, flagged as such.
 */

export type Slide = {
  id: string
  title: string
  centre?: boolean
  Body: ComponentType
  Notes: ComponentType
}

/* ── shared building blocks ──────────────────────────────────────────────── */

function Head({ n, title, lead }: { n: number; title: string; lead?: ReactNode }) {
  return (
    <>
      <div className="shead">
        <span className="snum">{String(n).padStart(2, '0')}</span>
        <h2 className="stitle">{title}</h2>
      </div>
      {lead && <p className="slead">{lead}</p>}
    </>
  )
}

function Arch({
  nodes,
}: {
  nodes: Array<{ name: string; sub?: string; tone?: string; tag?: 'cost' | 'free' }>
}) {
  return (
    <div className="arch">
      {nodes.map((x, i) => (
        <div key={x.name} style={{ display: 'contents' }}>
          {i > 0 && <div className="arrow" aria-hidden="true" />}
          <div className={`node ${x.tone ?? ''}`}>
            <span className="nname">{x.name}</span>
            {x.sub && <span className="nsub">{x.sub}</span>}
            {x.tag && (
              <span className={`ntag ntag-${x.tag}`}>{x.tag === 'cost' ? 'costs ε' : 'free'}</span>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

function Table({ head, rows }: { head: string[]; rows: ReactNode[][] }) {
  return (
    <div className="scrollx">
      <table className="dtable">
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

/* ── 01 · what it is ─────────────────────────────────────────────────────── */

const S1: Slide = {
  id: 's1',
  title: 'What SynthProof is',
  centre: true,
  Body: () => (
    <>
      <Wordmark />
      <p
        className="slead"
        style={{ textAlign: 'center', margin: '0 auto', color: 'var(--ink)', maxWidth: '78ch' }}
      >
        A system that turns a sensitive table into a{' '}
        <span className="mark">safe, shareable synthetic version</span> — and attaches a signed
        certificate stating <span className="mark">exactly how private it is</span>.
      </p>

      <div className="cols c3" style={{ maxWidth: 1080, margin: '0 auto', width: '100%' }}>
        <div className="p">
          <span className="plabel plabel-ink">1 · what goes in</span>
          <p className="ptext">
            One table of real people — patients, customers, citizens — plus a short declaration
            of what its columns contain.
          </p>
        </div>
        <div className="p p-gold">
          <span className="plabel">2 · what we do</span>
          <p className="ptext">
            Measure the data through a <strong>privacy accountant</strong>, add mathematically
            calibrated noise, generate a new table, then <strong>attack it ourselves</strong>.
          </p>
        </div>
        <div className="p p-jade">
          <span className="plabel plabel-jade">3 · what comes out</span>
          <p className="ptext">
            A synthetic table you can share, plus a{' '}
            <strong>Privacy Data Sheet</strong> — a signed, machine-checkable record of the
            guarantee.
          </p>
        </div>
      </div>

      <p className="note" style={{ textAlign: 'center' }}>
        B.Tech CSE-AIDS Capstone 2026-27 · MIT-WPU, Panel B · Raj Modi · Krishna Renuse ·
        Aaditya Kumar Sinha · Levinesh G R
      </p>
    </>
  ),
  Notes: () => (
    <>
      <h4>say — this is the whole project in 30 seconds</h4>
      <p>
        "SynthProof takes a table of real people and produces a fake table that is safe to
        share — and, crucially, a certificate that says how safe, in a number anyone can check."
      </p>
      <p>
        Then the three boxes, one sentence each. <strong>Do not move on until the panel can
        repeat the middle box.</strong> Everything else in the deck is detail underneath it.
      </p>
      <p>
        The phrase to plant: <strong>"synthetic data is common; shipping proof with it is
        not."</strong>
      </p>
    </>
  ),
}

/* ── 02 · the problem ────────────────────────────────────────────────────── */

const S2: Slide = {
  id: 's2',
  title: 'The problem: the data that would help cannot move',
  Body: () => (
    <>
      <Head
        n={2}
        title="The problem: the data that would help cannot move"
        lead="Hospitals, banks and governments hold data that would answer real research questions. Almost none of it is ever shared — and the usual fix does not actually work."
      />

      <div className="cols c2">
        <div className="p p-crimson">
          <span className="plabel plabel-crimson">why sharing is blocked</span>
          <ul className="pts pts-tight">
            <li>
              <strong>No way to prove safety.</strong> A data owner cannot show a regulator that
              a release is safe, so the safest answer is always no.
            </li>
            <li>
              <strong>Nobody is blamed for refusing.</strong> The incentives are one-directional.
            </li>
            <li>
              <strong>Re-identification is real</strong>, not theoretical — see the evidence
              opposite.
            </li>
          </ul>
        </div>

        <div className="p">
          <span className="plabel">the evidence this is not paranoia</span>
          <Table
            head={['case', 'what happened']}
            rows={[
              [
                'Sweeney, 1997',
                'Re-identified the Governor of Massachusetts in a "de-identified" hospital release, using a $20 voter roll.',
              ],
              [
                'Sweeney, 2000',
                <>
                  <strong>87% of Americans</strong> are unique on ZIP + date of birth + sex
                  alone.
                </>,
              ],
              [
                'Netflix Prize, 2008',
                'Narayanan & Shmatikov de-anonymised users of a "anonymous" ratings dataset by matching public reviews.',
              ],
              [
                'EPFL, 2022',
                'Tested popular synthetic-data tools by attacking them. None beat simple manual blurring.',
              ],
            ]}
          />
        </div>
      </div>

      <div className="p">
        <span className="plabel plabel-ink">what the deadlock costs</span>
        <p className="ptext">
          Research stalls for a year in ethics review, then gets refused. Models get trained on
          smaller foreign datasets instead. And the patient gets{' '}
          <strong>neither the research nor the privacy</strong> — the original file is still
          sitting unprotected on a server.
        </p>
      </div>
    </>
  ),
  Notes: () => (
    <>
      <h4>say</h4>
      <p>
        Left box is the mechanism, right box is the proof. The line that lands hardest:{' '}
        <strong>"nobody is ever blamed for saying no."</strong> That is why this is not a
        technology problem — it is a proof problem.
      </p>
      <p>
        On the table, spend your time on Sweeney 2000: 87% unique on three fields nobody thinks
        of as identifying. Then EPFL 2022, because it pre-empts the obvious suggestion — "just
        generate fake data" — before anyone offers it.
      </p>
      <h4>sources — all published, none ours</h4>
      <p>
        Sweeney (1997, 2000); Narayanan &amp; Shmatikov (2008); Stadler, Oprisanu &amp;
        Troncoso, USENIX Security 2022. Say so plainly if asked.
      </p>
    </>
  ),
}

/* ── 03 · why existing approaches fail ───────────────────────────────────── */

const S3: Slide = {
  id: 's3',
  title: 'Why the existing approaches fail',
  Body: () => (
    <>
      <Head
        n={3}
        title="Why the existing approaches fail"
        lead="Four things people try today. Each one breaks in a specific, known way — and the last one is the gap we are building into."
      />

      <Table
        head={['approach', 'what it does', 'why it fails']}
        rows={[
          [
            'Anonymisation',
            'Delete names, IDs and addresses; share the rest.',
            <span className="crimson">
              The combination of the columns you kept is itself a fingerprint. Broken in 1997,
              still the default today.
            </span>,
          ],
          [
            'Aggregation',
            'Publish only totals and averages, never rows.',
            <span className="crimson">
              Enough overlapping totals let you subtract your way back to an individual. Also
              useless for training a model.
            </span>,
          ],
          [
            'Synthetic data',
            'Learn the statistics, generate a fake table (SDV, CTGAN).',
            <span className="crimson">
              Nothing stops the model memorising and reprinting a real person — usually the rare
              one who is easiest to identify.
            </span>,
          ],
          [
            'DP tools',
            'Add calibrated noise under a formal guarantee (SmartNoise, Tumult).',
            <span className="gold">
              Genuinely sound — but they hand you a number nobody verifies, with no attack, no
              certificate and no statement of what the number is worth.
            </span>,
          ],
        ]}
      />

      <div className="p p-gold">
        <span className="plabel">the gap</span>
        <p className="ptext" style={{ fontSize: '1.5rem' }}>
          Formal privacy <strong>proves</strong> a number that nobody checks. Privacy auditing{' '}
          <strong>measures</strong> a number that guarantees nothing. They are two separate
          research communities.{' '}
          <span className="mark">Nothing ships both to the person receiving the data.</span>
        </p>
      </div>
    </>
  ),
  Notes: () => (
    <>
      <h4>say</h4>
      <p>
        Walk the four rows. Rows 1–3 are what most people in the room would have proposed; row 4
        is the serious prior art, and <strong>be generous about it</strong> — SmartNoise and
        Tumult are real, sound tools. Our criticism is narrow and specific: they give you a
        number with nothing attached to it.
      </p>
      <p>
        Then the gold box, slowly. "One field proves a number nobody verifies. The other
        measures a number that promises nothing. Nobody joins them." That sentence is the
        project's reason to exist and it sets up slide 6.
      </p>
      <h4>they will ask</h4>
      <p>
        <strong>"So you are just adding a report on top of SmartNoise?"</strong> — No. The
        refusal gate, the self-attack, the detection-limit calculation and the signed ledger are
        new components, not a wrapper. Slide 6 lists exactly what is ours and what is not.
      </p>
    </>
  ),
}

/* ── 04 · architecture + pipeline ────────────────────────────────────────── */

const S4: Slide = {
  id: 's4',
  title: 'How it works: architecture and pipeline',
  Body: () => (
    <>
      <Head
        n={4}
        title="How it works: architecture and pipeline"
        lead="Seven stages. Only two of them cost privacy budget — and the one everybody assumes is expensive is free."
      />

      <Arch
        nodes={[
          { name: 'Sensitive table', sub: 'CSV + declared schema', tone: 'node-io' },
          { name: '1 Gate', sub: 'admit or refuse', tone: 'node-crimson', tag: 'free' },
          { name: '2 Profile', sub: 'learn column domains', tone: 'node-gold', tag: 'cost' },
          { name: '3 Measure', sub: 'noisy counts', tone: 'node-gold', tag: 'cost' },
          { name: '4 Generate', sub: 'build fake table', tone: 'node-jade', tag: 'free' },
          { name: '5 Audit', sub: 'attack our output', tone: 'node-crimson' },
          { name: '6 Certify', sub: 'sign + ledger', tone: 'node-gold' },
          { name: 'Release', sub: 'data + certificate', tone: 'node-io' },
        ]}
      />

      <Table
        head={['stage', 'what happens', 'reads real data?', 'costs ε?', 'output']}
        rows={[
          [
            '1 Gate',
            'Checks the declared column names and the row count only.',
            <span className="jade">no — never a cell</span>,
            <span className="jade">no</span>,
            'admit, or a refusal naming the column',
          ],
          [
            '2 Profile',
            'Works out what values each column can hold.',
            <span className="crimson">yes</span>,
            <span className="crimson">yes</span>,
            'noisy column domains',
          ],
          [
            '3 Measure',
            'Counts groups and pairs of groups, adding exact discrete noise to each count.',
            <span className="crimson">yes</span>,
            <span className="crimson">yes</span>,
            'noisy marginals',
          ],
          [
            '4 Generate',
            'Fits a model to the noisy counts and samples a new table.',
            <span className="jade">no</span>,
            <span className="jade">no — post-processing</span>,
            'synthetic table',
          ],
          [
            '5 Audit',
            'Plants known records, runs the pipeline, attacks the output.',
            'planted only',
            <span className="jade">no</span>,
            'measured leakage + its detection limit',
          ],
          [
            '6 Certify',
            'Writes and signs the Privacy Data Sheet; appends to a hash-chained ledger.',
            <span className="jade">no</span>,
            <span className="jade">no</span>,
            'signed certificate',
          ],
        ]}
      />

      <div className="cols c2">
        <div className="p p-jade">
          <span className="plabel plabel-jade">the surprise</span>
          <p className="ptext">
            <strong>Generating the table is free.</strong> Once data has been made private,
            anything computed from it stays private — that is a theorem (post-processing
            invariance), not a shortcut. The real table stops at stage 3.
          </p>
        </div>
        <div className="p p-crimson">
          <span className="plabel plabel-crimson">the bit others skip</span>
          <p className="ptext">
            <strong>Stage 2 costs budget.</strong> Finding out what values a column holds is a
            question about real people. Most tools do it for free and never tell you. We charge
            it, or you declare the schema up front.
          </p>
        </div>
      </div>
    </>
  ),
  Notes: () => (
    <>
      <h4>say</h4>
      <p>
        Walk the diagram left to right with your hand, then let the table do the work. The two
        columns that matter are <strong>"reads real data?"</strong> and{' '}
        <strong>"costs ε?"</strong> — read those two down the page and the whole design becomes
        obvious.
      </p>
      <p>
        Then the two boxes. The green one is the surprise: generation is free. The red one is
        the differentiator: stage 2 is a real cost that most tools pretend is free.
      </p>
      <h4>they will ask</h4>
      <p>
        <strong>"Why does generation cost nothing?"</strong> — Post-processing invariance: any
        function of an ε-private output is still ε-private, because that function never touched
        the original data. It is one of the properties that makes DP usable at all.
      </p>
      <p>
        <strong>"What exactly does the gate refuse?"</strong> — Identifier-like columns (roughly
        one distinct value per row), free text, tables under 500 rows, and column pairs whose
        grid is too large to be informative.
      </p>
    </>
  ),
}

/* ── 05 · the guarantee ──────────────────────────────────────────────────── */

const S5: Slide = {
  id: 's5',
  title: 'The guarantee, in plain terms',
  Body: () => (
    <>
      <Head
        n={5}
        title="The guarantee, in plain terms"
        lead="Differential privacy does not hide data. It caps how much any one person can change the answer — and ε is the size of that cap. Drag the slider."
      />
      <EpsilonDial />
    </>
  ),
  Notes: () => (
    <>
      <h4>say — drag it, do not lecture</h4>
      <p>
        "Two files. Identical, except File A contains Priya and File B does not. Ask both the
        same question — how many patients here have diabetes?"
      </p>
      <p>
        Start at high ε (right). The two clouds sit apart:{' '}
        <strong>"the answer tells you whether Priya is in the file."</strong> Now drag left and
        watch them slide into each other until the badge flips.{' '}
        <strong>"Now the answer looks the same whether or not she was ever there. That is the
        entire guarantee."</strong>
      </p>
      <p>
        Then the table on the right: the same setting said three ways — a budget, a noise dial,
        and a cap on your influence. Use whichever one the room reacts to. The last row is the
        one to read aloud: at ε = 1 an attacker who knows everything else gets you right 73
        times in 100; a coin flip is 50.
      </p>
      <h4>they will ask</h4>
      <p>
        <strong>"Doesn't the noise make the answer wrong?"</strong> — Slightly, and that is the
        trade we are managing. The count is off by a few; the population-level finding survives.
        Slide 4 stage 3 is where that trade is bought, and the certificate on slide 7 is where
        we declare how much of it we spent.
      </p>
      <p>
        <strong>"Who picks ε?"</strong> — The data owner, and the certificate records the choice
        so the recipient can judge it.
      </p>
    </>
  ),
}

/* ── 06 · novelty ────────────────────────────────────────────────────────── */

const S6: Slide = {
  id: 's6',
  title: 'What is new — and what is not',
  Body: () => (
    <>
      <Head
        n={6}
        title="What is new — and what is not"
        lead="Three design decisions that no existing tool makes, plus an explicit list of the parts we did not invent."
      />

      <div className="cols c3">
        {[
          {
            n: '01',
            h: 'Both numbers, one run',
            b: 'The proved bound and the attacked bound come from the same pipeline, on the same release, and both land on the file you receive.',
          },
          {
            n: '02',
            h: 'We print the limit of our own attack',
            b: 'If an attack finds nothing, that means either nothing leaked or the attack was too small to see it. We calculate which, and print it beside the result.',
          },
          {
            n: '03',
            h: 'It refuses',
            b: 'Unsafe tables are turned away before a single value is read, with the offending column named and a remedy given.',
          },
        ].map((c) => (
          <div key={c.n} className="p p-gold">
            <span className="plabel">novelty {c.n}</span>
            <h3 style={{ fontSize: '1.5rem', margin: '0 0 0.28rem' }}>{c.h}</h3>
            <p className="ptext">{c.b}</p>
          </div>
        ))}
      </div>

      <div className="scrollx">
        <table className="dtable">
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
                  <td
                    key={i}
                    className={`c ${v ? 'yes' : 'no'} ${i === 4 ? 'us' : ''}`}
                  >
                    {v ? '✓' : '—'}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="p">
        <span className="plabel plabel-ink">what we did NOT invent — say this before you are asked</span>
        <p className="ptext">
          The privacy arithmetic is Google&rsquo;s <span className="mono">dp_accounting</span>.
          The strongest generator is <span className="mono">AIM</span> from the private-PGM
          authors. The one-run audit construction is Steinke, Nasr &amp; Jagielski (2023). The
          fact that an attack has a detection limit is known in that literature.{' '}
          <strong>Ours is the integration, the refusal gate, the certificate, and the decision
          to report the limit next to every number.</strong>
        </p>
      </div>
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
        formal guarantees. <strong>Concede that immediately if pushed</strong> — our claim is
        the bottom four rows only, and they are design decisions rather than performance claims.
      </p>
      <h4>the last box is not optional</h4>
      <p>
        Read it out loud. Volunteering what you imported is far stronger than being caught on
        it, and it makes the three novelty claims more credible rather than less.
      </p>
    </>
  ),
}

/* ── 07 · MVP + applications ─────────────────────────────────────────────── */

const S7: Slide = {
  id: 's7',
  title: 'What ships, and where it is used',
  Body: () => (
    <>
      <Head
        n={7}
        title="What ships, and where it is used"
        lead="One table in, one certified table out — five commands, running offline. Then the four settings this unblocks."
      />

      <div className="cols c21">
        <div className="p p-jade">
          <span className="plabel plabel-jade">MVP — in scope</span>
          <ul className="pts pts-tight pts-yes">
            <li>Upload one CSV with a declared schema</li>
            <li>Gate refuses unsafe columns, by name, with a remedy</li>
            <li>Choose the privacy setting (ε)</li>
            <li>Get synthetic data + a signed Privacy Data Sheet</li>
            <li>Verify the sheet with one command</li>
            <li>CLI, REST API and a web console</li>
          </ul>
          <p className="note" style={{ marginTop: 6 }}>
            <span className="mono gold">
              keygen → run → sign → verify → (edit a value) → verify fails
            </span>
          </p>
        </div>

        <div className="p">
          <span className="plabel plabel-ink">deliberately NOT in v1</span>
          <ul className="pts pts-tight pts-no">
            <li>Several tables joined together</li>
            <li>Images, free text or time series</li>
            <li>One budget shared across many users and sessions</li>
            <li>Deep-learning generators (DP-SGD)</li>
          </ul>
          <p className="note" style={{ marginTop: 6 }}>
            Each is a project on its own. Claiming all four is the fastest way to build none of
            them.
          </p>
        </div>
      </div>

      <Table
        head={['sector', 'who holds the data', 'who needs it', 'what SynthProof unblocks']}
        rows={[
          [
            'Healthcare',
            'Hospital with 50,000 diabetes records',
            'University lab building a risk model',
            'A defensible, signed answer to "was it safe to share this?"',
          ],
          [
            'Banking',
            'Bank with labelled fraud transactions',
            'A vendor training a detection model',
            'Share patterns without exposing any customer account',
          ],
          [
            'Telecom',
            'Operator with mobility traces',
            'City planners modelling transport',
            'Population movement without individual journeys',
          ],
          [
            'Government',
            'Census or scheme-enrolment records',
            'Open-data portal, researchers, NGOs',
            'Publish usable microdata with the privacy cost stated on it',
          ],
        ]}
      />
    </>
  ),
  Notes: () => (
    <>
      <h4>say</h4>
      <p>
        Lead with the RIGHT column, not the left. <strong>What you refuse to build is more
        persuasive than what you promise.</strong> Then the MVP as one sentence — one table in,
        one certified table out — and read the five commands off the mono line.
      </p>
      <p>
        On the applications table, pick <em>one</em> row and tell it as a story; do not read all
        four. Healthcare is the strongest because the refusal step is vivid: the hospital
        uploads, we reject the patient-ID column by name, they drop it, and the release goes
        out with a certificate.
      </p>
      <p>
        The common shape across all four rows, worth stating: <strong>the holder cannot prove
        safety, so nothing moves.</strong>
      </p>
      <h4>if there is time — offer the live demo here</h4>
      <p>
        Five commands, about eight minutes. Script in <span className="mono">docs/DEMO_SCRIPT.md</span>.
      </p>
    </>
  ),
}

/* ── 08 · the hard part + stack ──────────────────────────────────────────── */

const S8: Slide = {
  id: 's8',
  title: 'The hard part, and what we build it from',
  Body: () => (
    <>
      <Head
        n={8}
        title="The hard part, and what we build it from"
        lead="Five problems that make this more than plumbing — and the stack choices that answer them."
      />

      <Table
        head={['challenge', 'why it is hard', 'our approach']}
        rows={[
          [
            'Charging for schema discovery',
            'Working out a column’s range is a query against real people, but every tool treats it as setup and charges nothing.',
            'Charge it to the accountant, or require a declared public schema. Record which was used on the certificate.',
          ],
          [
            'Composition arithmetic',
            'Adding up the cost of many operations is where DP implementations get it wrong, and the error is silent.',
            <>
              Delegate to Google&rsquo;s <span className="mono">dp_accounting</span> and
              differentially test against a second independent implementation.
            </>,
          ],
          [
            'Exact noise sampling',
            'Sampling continuous noise then rounding to integers reopens known floating-point attacks.',
            'Discrete Gaussian and discrete Laplace samplers, verified against the exact distribution.',
          ],
          [
            'Knowing what "no leak found" means',
            'An attack that finds nothing is usually reported as a clean result. It may just be too small to detect anything.',
            'Compute the detection limit for the attack we ran and print it beside the result.',
          ],
          [
            'Making the certificate trustworthy',
            'A hash chain catches edits in the middle, but a chain with its tail cut off is still internally consistent.',
            'Ed25519-signed head committing to the chain length, so truncation is caught too.',
          ],
        ]}
      />

      <div className="cols c4">
        {[
          {
            l: 'Privacy core',
            v: 'dp_accounting · discrete Gaussian/Laplace · Ed25519',
            why: 'Bought, not built. Cross-checked.',
          },
          {
            l: 'Generators',
            v: 'private-PGM (AIM) · pairwise tree · independent marginals',
            why: 'A naive baseline up to current state of the art.',
          },
          {
            l: 'Audit',
            v: 'canary audit · density-ratio attack · exact-match check',
            why: 'The half that attacks our own output.',
          },
          {
            l: 'Product',
            v: 'Python 3.11 · FastAPI · SQLite · React + TypeScript · Docker',
            why: 'CLI for engineers, console for everyone else.',
          },
        ].map((x) => (
          <div key={x.l} className="p">
            <span className="plabel">{x.l}</span>
            <p className="ptext" style={{ fontSize: '1.02rem' }}>
              {x.v}
            </p>
            <p className="note" style={{ marginTop: 3 }}>
              {x.why}
            </p>
          </div>
        ))}
      </div>
    </>
  ),
  Notes: () => (
    <>
      <h4>say — this is the engineering credibility slide</h4>
      <p>
        Do not read all five rows. Pick two. <strong>Row 1</strong> is the differentiator:
        everyone else treats schema discovery as free setup; we treat it as a query about real
        people. <strong>Row 4</strong> is the intellectual one: an attack that finds nothing is
        usually reported as a clean result, and that is only meaningful if you also know what
        the attack could have detected.
      </p>
      <p>
        Then the stack, and lead with the rule: <strong>we do not write our own privacy
        mathematics.</strong> That answers the sharpest question a reviewer has — how do I know
        your numbers are right? — with: attack Google&rsquo;s library, not our arithmetic.
      </p>
      <h4>they will ask</h4>
      <p>
        <strong>"Why Python?"</strong> — The privacy libraries live there, and the workload is
        counting, not language speed.
      </p>
      <p>
        <strong>"Why SQLite for the ledger?"</strong> — Append-only, single-writer. A heavier
        database would be infrastructure with no experiment behind it.
      </p>
    </>
  ),
}

/* ── 09 · roadmap + ask ──────────────────────────────────────────────────── */

const S9: Slide = {
  id: 's9',
  title: 'Plan, risks and the ask',
  Body: () => (
    <>
      <Head
        n={9}
        title="Plan, risks and the ask"
        lead="Four phases, the honest risks, and the three things we want from this panel."
      />

      <div className="cols c4">
        {[
          { w: 'Phase 1', t: 'Prove the core', i: 'Budget accounting · two generators · the refusal gate', c: 'p-gold' },
          { w: 'Phase 2', t: 'Make it honest', i: 'Self-attack suite · print the detection limit · signed certificates', c: 'p-crimson' },
          { w: 'Phase 3', t: 'Make it usable', i: 'Web console · second dataset · reproducible runs', c: 'p' },
          { w: 'Phase 4', t: 'Harden it', i: 'Stronger attacker · budget across sessions · third dataset', c: 'p-jade' },
        ].map((p) => (
          <div key={p.w} className={`p ${p.c}`}>
            <span className="plabel">{p.w}</span>
            <div style={{ fontSize: '1.05rem', fontWeight: 800, marginBottom: 3 }}>{p.t}</div>
            <p className="note">{p.i}</p>
          </div>
        ))}
      </div>

      <div className="cols c2">
        <div className="p p-crimson">
          <span className="plabel plabel-crimson">risks we are carrying</span>
          <ul className="pts pts-tight">
            <li>
              <strong>Single dataset early on.</strong> Any conclusion is provisional until the
              second one lands. Mitigation: a second dataset is a Phase 3 deliverable, not an
              optional extra.
            </li>
            <li>
              <strong>One attacker.</strong> A stronger, mechanism-aware attacker could change
              every measured number. Mitigation: report the detection limit alongside, so the
              result cannot be over-read.
            </li>
            <li>
              <strong>Not deployment-ready.</strong> Single table, one shared key, no
              cross-session budget. We would rather state this than oversell it.
            </li>
          </ul>
        </div>

        <div className="p p-jade">
          <span className="plabel plabel-jade">what we are asking this panel for</span>
          <ul className="pts pts-tight">
            <li>
              <strong>Attack novelty 02.</strong> Printing the limit of our own attack is the
              claim we most want stress-tested before it goes in the thesis.
            </li>
            <li>
              <strong>A second public dataset</strong> with a published schema, so the
              evaluation is not single-dataset.
            </li>
            <li>
              <strong>Scope guidance:</strong> is the refusal gate substantial enough to stand
              as a contribution on its own?
            </li>
          </ul>
        </div>
      </div>

      <p className="slead" style={{ textAlign: 'center', color: 'var(--ink)' }}>
        <span className="mark">Data you can share, with the receipt attached.</span>
      </p>
    </>
  ),
  Notes: () => (
    <>
      <h4>say</h4>
      <p>
        Phases left to right, one breath each. Note that <em>make it honest</em> comes before{' '}
        <em>make it usable</em> — that ordering is deliberate and a reviewer will notice it.
      </p>
      <p>
        Then the red box, and do not soften it. Volunteering your own risks is the single most
        credible thing you can do at the end of a review, and it removes the panel&rsquo;s best
        questions before they ask them.
      </p>
      <p>
        Then the ask. Be specific — a panel that is asked a real question engages; a panel asked
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
        are existing work and slide 6 says so. The gate, the self-attack, the certificate and
        the limit calculation are the project.
      </p>
      <p>
        <strong>"Can a hospital use it tomorrow?"</strong> — No, and the risk box says why. It
        is an instrument for checking releases, not a production pipeline.
      </p>
    </>
  ),
}

export const SLIDES: Slide[] = [S1, S2, S3, S4, S5, S6, S7, S8, S9]
