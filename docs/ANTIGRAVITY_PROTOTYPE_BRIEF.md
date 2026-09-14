# Antigravity build brief — SynthProof "Atelier" prototype (world-class 3D redesign)

**For: Antigravity / Gemini 3.8 high. This is a BUILD brief — you write code.**
**Goal: a drastically redesigned, world-class, 3D, layman-legible front end for the EXISTING
SynthProof prototype — that is 100% WORKING against the real backend, not a mockup.**

**Decisions locked by the owner (2026-09-14):** (1) **YES — build the full 3D "Privacy Chamber"** as
the centrepiece (upgrade the existing three.js cloud). (2) **Full redesign** — all four zones + the
DetailDrawer + tamper studio + ECharts rail.

**Sequencing safety rule (there is a demo tomorrow): keep a runnable prototype at every commit.**
Build in this order, and do not start a zone until the previous one builds and runs against live
data: (a) theme + shell + KPI row wired to a **real `/api/run`** + the DetailDrawer with real math;
(b) ECharts rail; (c) ledger spine + tamper studio; (d) the full 3D chamber last, behind the existing
`ErrorBoundary`, so a 3D problem can never take down a working page. After each zone, run
`npm run build` and a real run. If time runs short, the earlier zones must already be a complete,
honest, working demo on their own.

---

## 0. The five hard guardrails (read these twice; violating any one fails the task)

1. **The backend is fixed. Do not touch it.** The FastAPI app in `synthproof/api/` and everything
   under `synthproof/` (Python) is the graded engineering and is under active change by another
   agent. You may read it to understand the contract. You may **not** edit any `.py` file, any test,
   or anything in `results/`, `research/`, or `docs/design/`. Your work is **entirely inside
   `web/`** (the React console) plus, if truly needed, static assets.
2. **100% working means: it runs from `START_PROTOTYPE.bat` with real data.** The definition of done
   (section 8) is that `npm run build` succeeds, the bundle lands in `../synthproof/api/console`,
   the batch file launches, and every screen is driven by live calls to the real API. A beautiful
   page that does not build, or that shows canned numbers, is a FAIL.
3. **NO FABRICATED NUMBERS. This is the project's first law.** This repository had a fabrication
   incident (a banner once showed invented audited-epsilon values and a dataset that did not exist —
   see the docstring in `run_prototype.py`). Every number, label, hash, and verdict on screen MUST
   come from a field in a real API response. If a value is not in the API, you do not display it —
   you do not invent a plausible one. When you show the *math* behind something (section 5), it must
   be transcribed from the cited source file, not paraphrased into new claims.
4. **Keep the API contract and the build pipeline exactly as they are.** Same endpoints, same
   request/response shapes, same `X-API-Key` header, same SSE streaming for `/api/run`, same vite
   `outDir: '../synthproof/api/console'`. If you add a dependency (echarts, katex), it must be a
   normal `npm install` that `npm run build` bundles — no CDN script tags, no external runtime fetch.
5. **Honesty over polish, always.** SynthProof's whole thesis is "don't trust, verify." The UI must
   never overstate. Where the audit could not certify the epsilon, the UI says so. Where a number is
   an illustration, it is labelled. A gorgeous UI that quietly overclaims is worse than an ugly
   honest one. When in doubt, show the caveat.

---

## 1. What SynthProof is, in one breath (write the UI so a layman gets this in 20 seconds)

SynthProof takes a sensitive table (say, hospital or census records), makes a **fake but
statistically faithful** copy using **differential privacy** (mathematically bounded leakage), and
ships that copy with a **signed, machine-checkable proof** of exactly how private it is — including
an honest statement of what the proof could *not* verify. Think: *"synthetic data that arrives with
its own tamper-evident privacy certificate."*

Three ideas a non-expert must leave understanding:
- **Epsilon (ε)** = a privacy dial. Lower ε = more noise = more privacy, less faithful. It is a
  *budget* that gets spent.
- **The ledger** = a tamper-evident chain (like a receipt book where every page seals the last), so
  nobody can quietly rewrite what privacy was promised.
- **The audit ceiling** = intellectual honesty: the certificate states the *most* its own audit
  could ever have detected, so "we detected no leak" can't masquerade as "there is no leak."

The redesign's job: make those three land **instantly and beautifully**, with the hard math one
click away for the examiner who wants it.

---

## 2. The look — "Brass, Ivory & Ink" (a precision scientific instrument)

The user's palette is **brown / white / black**. Execute it as a *machined brass, ivory paper, and
ink* identity — a beautifully engineered instrument, not a fintech dashboard. This reads as
"rigorous and crafted," which is the whole brand.

**Palette (define as CSS custom properties / Tailwind theme tokens; light default + dark variant):**

| Token | Light | Dark | Role |
|---|---|---|---|
| `--paper` | `#F4F1EA` | `#17140F` | page ground (warm ivory / roasted dark) |
| `--card` | `#FBFAF6` | `#221D16` | raised surfaces |
| `--ink` | `#1A1712` | `#F3EEE4` | primary text (warm near-black) |
| `--muted` | `#6B6053` | `#A9A08F` | secondary text |
| `--line` | `#DED6C7` | `#3A322708` | hairlines |
| `--brass` | `#8A5A2B` | `#C08A4E` | **the one accent** — walnut/brass; use sparingly |
| `--brass-deep`| `#5E3A18` | `#8A5A2B` | pressed/active brass |
| `--seal` | `#7C2D2A` | `#C4635C` | semantic ALERT / tamper / leak (oxide red) |
| `--verify`| `#3F6B4E` | `#7FB08C` | semantic OK / verified / sealed (moss green) |

Rules: **brass is the accent and appears rarely** — one brass element per view carries the eye.
Semantic red/green are *separate* from brass and only mean alert/ok. Never a rainbow. Pure white and
pure black are banned; everything is warm-biased.

**Typography** (fonts already installed in `web/`: `@fontsource/instrument-serif`,
`@fontsource/geist-sans`, `@fontsource/geist-mono`):
- **Display** — Instrument Serif, large, for hero numbers and section titles. It gives the "engraved
  instrument dial" feel. Use with tight leading and generous size.
- **Body/UI** — Geist Sans.
- **Data/hashes/ε/code** — Geist Mono, with `font-variant-numeric: tabular-nums` everywhere digits
  align.
You may add ONE more display weight only if it earns its place; prefer using what's installed.

**Texture & motion**: subtle. A faint paper grain (CSS, not an image request), hairline rules like an
engineering drawing, engraved/embossed shadows on brass elements. Motion via framer-motion:
orchestrated entrance of KPI cards, a smooth number count-up **only when a real value arrives**, the
detail drawer sliding in like a drawn instrument tray. Respect `prefers-reduced-motion`. No
gratuitous parallax.

**Design exploration with Stitch (optional, encouraged):** you may use Google Stitch to generate
layout/visual directions for the shell, the KPI row, and the detail drawer, then implement the chosen
direction faithfully in React + Tailwind. Stitch is for *exploration*; the shipped code is
hand-built React that meets this brief. Do not ship Stitch's raw export.

---

## 3. Tech stack — keep the spine, add two libraries

**Keep:** React 18 + TypeScript + Vite + Tailwind (all configured), `three` + `@react-three/fiber`
+ `@react-three/drei` (already installed — the 3D point cloud already exists in
`web/src/components/RecordCloud.tsx`; upgrade it, don't rip it out), `framer-motion` (installed).

**Add (via `npm install`, bundled by vite — never a CDN tag):**
- **`echarts`** + **`echarts-for-react`** — for the KPI trend, the ε-vs-utility frontier curve, the
  budget breakdown, and the detection-floor chart. The user explicitly wants ECharts. Theme every
  chart with the Brass/Ivory/Ink tokens; charts must read in both light and dark.
- **`katex`** (+ its CSS) — to typeset the real math inside the detail drawers (section 5). Do NOT
  hand-render equations as images.

Do not swap frameworks. Do not introduce Next.js, a different bundler, or a CSS-in-JS runtime. The
build MUST remain `tsc --noEmit && vite build` → `../synthproof/api/console`.

---

## 4. Information architecture — the "Atelier"

One page, four zones, a persistent detail drawer. Everything a viewer needs is visible at rest
(no value hidden behind scroll before it loads).

### 4.1 Header / mission strip
Product mark ("SynthProof — synthetic data that ships with its proof"), a one-line layman tagline,
dataset + ε + mechanism controls (reuse `Controls.tsx` logic; restyle), a big **Run release** button,
theme toggle, and secondary actions (Verifier, Guided tour) already wired in `App.tsx`.

### 4.2 KPI card row (the "instrument dials") — 6–7 cards, each CLICKABLE
Big-number tiles, Instrument Serif numerals, one-line layman label under each. **Every card opens the
detail drawer (section 5) on click.** Sourced fields, from the `/api/run` `done` frame and `/api/ledger`:

| Card | Big number (source field) | Layman label |
|---|---|---|
| Privacy spent | `sheet.total_proved_eps` | "How much privacy budget this release used (ε)" |
| Privacy audited | `sheet.total_audited_eps` + ceiling from `audit.ceiling` | "What an attacker-simulation could actually detect" |
| Audit reach | `audit.ceiling` (+ `audit_is_informative`) | "The most this audit could ever have caught" |
| Faithfulness | `evaluation.correlation_error` / `tstr_f1` | "How well the fake data preserves real patterns" |
| Records | `sheet.num_rows` (+ `release_rows_source`) | "Rows in the released synthetic table" |
| Ledger height | `/api/ledger` `count`, `verified` | "Sealed entries in the tamper-evident chain" |
| Seal | `/api/ledger` `verified` (green/red) | "Is the chain intact right now?" |

Before a run, cards show a calm empty/"—" state with the layman label still legible (no fake
numbers). During a run, they animate from the streamed `stage` events.

### 4.3 The centre stage — the 3D "Privacy Chamber" (upgrade `RecordCloud.tsx`)
A three.js / R3F scene showing the **real projected records** the API returns in the `done` frame's
`cloud` object (real vs synthetic point layers, canaries flagged). Orbitable. The story it tells:
real records (ink) dissolve into a synthetic cloud (brass) as noise is applied; planted **canaries**
glow (seal red) — these are the decoys the audit uses. **Clicking a point** opens the detail drawer
explaining what that point is and the DP math that produced it. Keep it performant (instanced meshes,
as the current component does); degrade gracefully via the existing `ErrorBoundary`.

### 4.4 The ledger spine + tamper studio (upgrade `LedgerChain.tsx` + `AttackDossier.tsx`)
A 2.5D/3D chain of sealed blocks from `/api/ledger` `entries` (each shows truncated `hash`,
`prev_hash`, `mechanism_name`, `eps_spent`). The **Tamper studio** calls the real
`/api/ledger/tamper` endpoint (`attack_type` ∈ `modify_eps | truncate | corrupt_hash |
corrupt_signature`); the chain visibly **cracks** at the broken link and the Seal card flips red,
driven by the live `verified` field — not a hardcoded animation. A **Reset** calls
`/api/ledger/reset`. **Clicking a block** opens the drawer with the hash-chain + Ed25519 math.

### 4.5 The charts rail (ECharts)
- **Budget meter** → a brass "pressure gauge" or filling vessel for ε spent vs target (drive from the
  streamed `stage` `eps_spent`).
- **Frontier curve** → ε (x) vs faithfulness/correlation-error (y), proved vs audited — an ECharts
  line/area. Use the `FrontierStudio.tsx` data path if present; otherwise plot the single run's point
  and label it clearly as one point, not a fabricated curve.
- **Pipeline log** → keep `PipelineLog.tsx`'s streamed stages, restyled as an engraved timeline.

---

## 5. THE SIGNATURE INTERACTION — "layman on the surface, rigor one click deep"

This is the feature the user cares about most: **clicking any card, any 3D point, any ledger node, or
any chart element opens a small panel (a slide-in "instrument tray" drawer) that reveals the pure
engineering / math behind it.** Two registers in every drawer:

1. **In plain words** (2–3 sentences a non-technical examiner understands).
2. **The actual mechanism** — the real formula (KaTeX), the real parameter values from this run, and a
   one-line **Source:** pointer to the file it comes from. Transcribe from the source; do not invent.

Build a single reusable `<DetailDrawer>` fed by a typed registry of "explainers," one per clickable
subject. Here is the real content and its source — **read the source file and quote it faithfully**:

| Click target | Plain words | The math to typeset (KaTeX) | Source to transcribe from |
|---|---|---|---|
| **Privacy spent (ε)** | "ε bounds how much any one person changes the output. We compose many noisy steps and report the total." | (ε,δ)-DP definition; RDP composition; `Lap`/Gaussian calibration | `synthproof/accounting/accountant.py`, `calibration.py` |
| **AIM / a synthetic point** | "AIM privately picks which column-pairs matter, then fits a model to noisy counts of them." | selection = `argmax(score + DiscreteLaplace(b))`; exponential-mechanism `softmax(0.5·ε/Δ·q)`; total from noisy measurements (not the exact row count) | `synthproof/generators/aim.py`, `research/11_selection_accounting.md` |
| **Audit reach / ceiling** | "The most leakage this test could POSSIBLY have caught, given how many decoys we planted. Honesty guardrail." | one-run ceiling (Steinke Thm 2.1 corollary), `max_provable_epsilon` | `synthproof/audit/ceiling.py`, `audit/steinke.py` |
| **Ledger block** | "Each entry seals the previous one's fingerprint, so any edit breaks every seal after it. Then we sign the tip." | SHA-256 chain `hᵢ = H(entryᵢ ‖ hᵢ₋₁)`; Ed25519 signature over the head | `synthproof/ledger/ledger.py`, `ledger/signing.py` |
| **Faithfulness** | "Train a model on the fake data, test on real (TSTR). Compare to real-on-real. Also measure how much correlations shifted." | TSTR/TRTR F1; mean abs correlation error | `synthproof/evaluate/utility.py`, `frontier/experiment.py` |
| **Canary point** | "We plant extreme decoy records, then see if an attacker can tell they were in the training data. That's the leakage test." | membership audit; detection floor / limit-of-detection | `synthproof/audit/canary.py`, `audit/detection_floor.py` |
| **The seal / verify** | "Anyone can re-hash the chain and check the signature without trusting our server." | verify: re-hash all entries, check tip signature | `synthproof/ledger/ledger.py::verify`, `signing.py::verify_datasheet` |
| **The boundary / seed (bonus, high-value)** | "The certificate must not itself leak. Publishing the random seed would let an attacker replay the release and read off who was in the data — we found and fixed this." | release = deterministic `f(table, seed)`; measured 15/15 vs 0/15 | `docs/design/PUBLIC_RELEASE_BOUNDARY.md`, `synthproof/audit/boundary.py` |

Drawer UX: slides in from the right (framer-motion), ~420px, dismissible (Esc, backdrop, close). It
does **not** cover the element that opened it. Keyboard accessible, focus-trapped, `prefers-reduced-
motion` honored. Each drawer footer shows the **Source:** path in mono so an examiner can verify.

---

## 6. The exact API contract (consume this; do not change it)

Base: same origin (the FastAPI app serves the console). Auth: send header `X-API-Key` with
`import.meta.env.VITE_SYNTHPROOF_API_KEY` (empty in demo mode → auth is a no-op; keep sending it).
`web/src/lib/api.ts` already implements all of this — reuse it, restyle the components.

- `GET /api/health` → liveness.
- `GET /api/datasets` → `{ datasets: [{ id, label, rows|null, kind, note }] }`.
- `GET /api/mechanisms` → available generators (+ `available` flag; the UI already disables unavailable ones).
- `POST /api/run` → **Server-Sent Events**, `Accept: text/event-stream`. Events:
  - `start` → `{ dataset, mechanism, mechanism_label, target_eps, delta, seed(null), target_col, correlation_cols }`
  - `stage` → `{ stage, eps_spent, eps_remaining, ... }` (many, one per pipeline step — drive progress + budget meter from these)
  - `done` → `{ measurements, sheet, sample_records, cloud, histograms, evaluation, audit, ledger_entry }`
    where `sheet` has `total_proved_eps, total_audited_eps, audit_ceiling, num_rows, release_rows_source,
    evaluation{tstr_f1,trtr_f1,mia_auc,correlation_error}, evaluation_privacy, ledger_hash, ...` and
    `audit` has `{ ceiling, audited_eps, informative, ... }`.
  - `error` → `{ message, type?, trace? }` — surface it in the pipeline log, never swallow it.
  Request body: `{ dataset, mechanism, target_eps, delta, seed?, num_canaries, rows }`. `seed` may be
  omitted → the server draws a secret one (this is the D5 privacy fix; the UI should say the seed is
  "kept secret" and never display a seed value from a real release).
- `GET /api/ledger` → `{ verified, head, count, total_eps_spent, entries:[{ entry_id, prev_hash, hash,
  timestamp, dataset_id, run_id, mechanism_name, eps_spent, delta, seed, signature(32 char) }] }`.
- `POST /api/ledger/tamper` → `{ attack_type }`, returns the post-attack state; re-fetch `/api/ledger`
  to show the break. `POST /api/ledger/reset` restores it. (Demo-mode only — already gated server-side.)
- `POST /api/capsule/export`, `/api/capsule/verify`, `/api/certificate/verify`, `/api/croissant/export`
  → the Verifier flows; `VerifierModal.tsx` already wires them. Restyle, keep behavior.

The three illustrative ledger entries at start have run ids beginning `illustrative-` and carry **no**
audit result — label them clearly as illustrative charges, never as verified releases.

---

## 7. Component-by-component plan (you rewrite the presentation, keep the data wiring)

Everything is in `web/src/`. Reuse each component's data/props/hooks; replace the visual layer.
- `App.tsx` → new Atelier layout, theme tokens, KPI row, drawer host, scene composition.
- `RecordCloud.tsx` → upgraded Privacy Chamber (instanced points, canary glow, click→drawer).
- `LedgerChain.tsx` + `AttackDossier.tsx` → sealed-block spine + tamper studio with live cracking.
- `Readouts.tsx` (`BoundsGauge`, `BudgetMeter`, `Metric`) → brass instrument gauges (ECharts).
- `FrontierStudio.tsx` → ECharts frontier curve (proved vs audited).
- `Marginals.tsx` → ECharts real-vs-synthetic histograms.
- `PipelineLog.tsx` → engraved streamed timeline.
- `Controls.tsx` → restyled dataset/ε/mechanism controls (keep the seed-is-secret behavior).
- `VerifierModal.tsx`, `GuidedTourModal.tsx` → restyle; keep flows.
- **New:** `DetailDrawer.tsx` + `explainers.ts` (the section-5 registry with KaTeX + Source paths).
- Keep `ErrorBoundary.tsx` around every 3D surface.

Keep `web/src/lib/api.ts` and `types.ts` as the single source of the contract. Extend types additively
if a field you need already exists in the response; never invent a field.

---

## 8. Definition of done (all must hold — verify before declaring finished)

1. `cd web && npm install && npm run build` completes with **no TypeScript errors** (the build runs
   `tsc --noEmit` first) and writes to `../synthproof/api/console`.
2. `web` unit tests still pass: `npm run test` (vitest). Update tests you break; do not delete
   coverage. Keep the existing Playwright e2e green where feasible.
3. Double-clicking `START_PROTOTYPE.bat` (or `python run_prototype.py`) serves the console at
   `http://127.0.0.1:8000/` and the redesigned UI loads.
4. A real run (Adult, ε=1, AIM or pairwise) streams stages, fills every KPI from the `done` frame,
   renders the 3D chamber from `cloud`, and appends a ledger entry — **all from live API data.**
5. Tamper studio: firing each `attack_type` visibly breaks the chain and flips the Seal to red via the
   live `verified` field; Reset restores it.
6. Every KPI card, ≥1 ledger block, ≥1 3D point, and ≥1 chart element opens a `DetailDrawer` whose
   math is transcribed from the cited source and whose parameter values come from the live run.
7. Light and dark themes both legible; responsive down to a laptop (≥1024px is the target; the page
   must not break below that even if 3D simplifies).
8. **Grep test for honesty:** no numeric literal appears as a displayed metric anywhere in
   `web/src/**` except values that are (a) axis ticks/scales, (b) explicitly labelled "illustrative,"
   or (c) constants transcribed from a cited source in a drawer. If you cannot trace a shown number to
   an API field or a cited file, remove it.

Deliver: the updated `web/` source, a short `web/REDESIGN_NOTES.md` (what changed, any new deps, how
to run), and a note of anything you could not wire to real data (so it can be finished — do not paper
over it with fakes).

---

## 9. First moves (suggested order)

1. Read `web/src/App.tsx`, `lib/api.ts`, `types.ts`, `components/RecordCloud.tsx`, `LedgerChain.tsx`,
   `Readouts.tsx`, and `run_prototype.py`. Run `START_PROTOTYPE.bat` once to see the current thing.
2. Install `echarts echarts-for-react katex`. Set up the Brass/Ivory/Ink Tailwind theme + fonts.
3. Build the shell + KPI row + `DetailDrawer` + `explainers.ts` (transcribe the math from the sources
   in section 5). Wire the KPI cards to a real run first — prove the data path end to end.
4. Upgrade the 3D chamber, then the ledger spine + tamper studio, then the ECharts rail.
5. Restyle the modals, run the DoD checklist, write `REDESIGN_NOTES.md`.

Make it beautiful. Make it honest. Make it **run**.
