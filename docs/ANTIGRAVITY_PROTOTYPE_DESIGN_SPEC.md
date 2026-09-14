# SynthProof "Atelier" — pixel-level design & engineering specification

**Companion to `ANTIGRAVITY_PROTOTYPE_BRIEF.md`. The brief says WHAT and WHY; this says the EXACT
geometry, tokens, states, motion, and engineering contracts. Every square pixel is specified here.
Where a value is given, use that value. Where you must deviate, deviate by the scale, never by a
random number.**

> Non-negotiables from the brief still bind: `web/` only, real API data only, no fabricated numbers,
> build stays `tsc --noEmit && vite build` → `../synthproof/api/console`, honesty over polish.

---

## PART A — FOUNDATIONS (the design system)

### A1. Base unit & spacing scale
Base unit **4px**. Everything snaps to it. Tailwind's default 4px scale is kept; use these named
steps and nothing between them:

`space-0 0 · space-1 4 · space-2 8 · space-3 12 · space-4 16 · space-5 20 · space-6 24 · space-8 32
· space-10 40 · space-12 48 · space-16 64 · space-20 80 · space-24 96`

- Card interior padding: **24px** (`space-6`) desktop, **16px** (`space-4`) below 1280px.
- Gap between KPI cards: **16px**. Gap between major zones (vertical): **32px** desktop, **24px** ≤1280.
- Page side gutter: **32px** ≥1440, **24px** 1024–1439, **16px** <1024. Set once on the outer wrapper.

### A2. Layout grid
- App max content width **1600px**, centred. Above 1600, the page stays 1600 and the ivory ground
  extends full-bleed behind it.
- **12-column** grid, 16px gutters, inside the gutters. Zone spans:
  - KPI row: 12 cols, cards auto-fit at `minmax(200px, 1fr)`, 6 across ≥1440, 4 across 1180–1439,
    2 across 768–1179, 1 col <768 (demo target is ≥1024, but do not break narrower).
  - Main body: **8-col centre stage** (3D chamber) + **4-col right rail** (charts/readouts) ≥1280.
    Below 1280 they stack: chamber full-width (min-height 480px), rail below.
  - Ledger spine: full 12-col band under the main body.
- Vertical rhythm: header 64px, then 32px, KPI row, 32px, main body, 32px, ledger band, 32px, footer.

### A3. Radii
`r-sm 4 · r-md 8 · r-lg 12 · r-xl 16 · r-pill 999`.
- Cards & panels: **12px**. Buttons & inputs: **8px**. Pills/tags: **999px**. The 3D canvas frame &
  drawer: **16px**. Never mix radii on one element's corners.

### A4. Hairlines & borders
- Standard hairline **1px** `--line`. Structural/engineering rules **1px** `--line` at 60% opacity,
  used like a drafting drawing (thin, confident).
- A "measured" divider (used once per major section header): 1px `--line` with a 24px `--brass`
  segment at its left end (an engraved tick). This is the only decorative rule; everywhere else the
  rule is plain.
- Focus ring: **2px** solid `--brass` **offset 2px** (`outline: 2px solid var(--brass); outline-offset:
  2px`). Visible on every interactive element on keyboard focus. Never remove outlines without a
  replacement of equal clarity.

### A5. Elevation (warm, low, engraved — not floaty material shadows)
Four levels; shadows are warm-black, low-spread, paired with a 1px top inner highlight on raised
surfaces to read "machined."
- `e0` flat: no shadow, 1px `--line` border. (KPI cards at rest, list rows.)
- `e1` raised: `0 1px 2px rgba(40,30,15,.06), 0 6px 16px -10px rgba(40,30,15,.20)`. (Cards on hover,
  chart panels.)
- `e2` floating: `0 2px 4px rgba(40,30,15,.10), 0 18px 40px -18px rgba(40,30,15,.34)`. (DetailDrawer,
  modals.)
- `e-inset` (the 3D stage well & gauges): `inset 0 1px 3px rgba(40,30,15,.14), inset 0 0 0 1px
  var(--line)`. In dark theme swap the rgba base to `rgba(0,0,0,.5)`.
Brass elements add a 1px inner top highlight: `inset 0 1px 0 rgba(255,244,222,.5)`.

### A6. Color tokens — exact values & usage law
Define once at `:root`; redefine the dark set under both `@media (prefers-color-scheme: dark)` guarded
`:root:not([data-theme="light"])` AND `:root[data-theme="dark"]`. (Same pattern the current app uses.)

| token | light | dark | usage law |
|---|---|---|---|
| `--paper` | `#F4F1EA` | `#17140F` | body ground only |
| `--paper-2`| `#EDE8DD` | `#1E1A13` | recessed wells behind the stage/gauges |
| `--card` | `#FBFAF6` | `#221D16` | any raised surface |
| `--ink` | `#1A1712` | `#F3EEE4` | headings, KPI numerals, primary text |
| `--muted` | `#6B6053` | `#A9A08F` | labels, secondary text (AA on card: verify ≥4.5:1) |
| `--faint` | `#9A8F7E` | `#7A7060` | captions, source paths, disabled |
| `--line` | `#DED6C7` | `#3A3227` | hairlines, borders |
| `--brass` | `#8A5A2B` | `#C08A4E` | THE accent: primary button, active tab, 1 highlight per view |
| `--brass-deep`| `#5E3A18`| `#8A5A2B` | pressed brass, brass text on ivory |
| `--seal` | `#7C2D2A` | `#C4635C` | ALERT ONLY: tamper break, leak, canary, error |
| `--seal-bg`| `#F3E4E1` | `#2A1714` | alert surface tint |
| `--verify` | `#3F6B4E` | `#7FB08C` | OK ONLY: chain intact, verified, "in range" |
| `--verify-bg`|`#E4EFE6`| `#12241A` | ok surface tint |

**Laws:** (1) `--brass` appears at most a few times per screen and never as a large fill — it is a
line, an underline, a small button, a single glowing point. (2) `--seal`/`--verify` are *semantic* and
carry meaning; they are never used for decoration and never as the brand accent. (3) No pure `#fff` /
`#000`. (4) Every text/background pair verified ≥ 4.5:1 (body) / ≥ 3:1 (large ≥24px). (5) A color used
on a surface comes from the same token set as that surface — never a literal.

### A7. Typography — exact scale
Fonts (installed): **Instrument Serif** (display), **Geist Sans** (UI/body), **Geist Mono** (data).
Fallbacks declared: `"Instrument Serif", Georgia, serif` / `"Geist Sans", system-ui, sans-serif` /
`"Geist Mono", ui-monospace, monospace`.

| role | family | size / line-height | weight | tracking | notes |
|---|---|---|---|---|---|
| Display XL (hero KPI number) | Instrument Serif | 56 / 56 | 400 | -0.02em | `tabular-nums`; ≤44 on <1280 |
| Display L (section title) | Instrument Serif | 32 / 36 | 400 | -0.01em | `text-wrap: balance` |
| Display M (drawer title) | Instrument Serif | 24 / 30 | 400 | -0.01em | |
| Title (card value fallback) | Geist Sans | 20 / 28 | 600 | 0 | |
| Body | Geist Sans | 15 / 24 | 400 | 0 | measure ≤ 68ch in drawers |
| Body-strong | Geist Sans | 15 / 24 | 600 | 0 | |
| Label (KPI caption) | Geist Sans | 13 / 18 | 500 | 0 | `--muted` |
| Eyebrow / tag | Geist Mono | 11 / 16 | 500 | 0.14em | UPPERCASE, `--faint`/`--brass` |
| Data / hash / ε | Geist Mono | 13 / 20 | 500 | 0 | `tabular-nums`; hashes 12/18 |
| Caption / source path | Geist Mono | 12 / 18 | 400 | 0 | `--faint` |

Numerals that update use `font-variant-numeric: tabular-nums` so they don't jitter during count-up.

### A8. Iconography
Line icons, **1.5px stroke**, **20×20** on a 24px box (or 16×16 for inline). Rounded caps/joins. Draw
as inline SVG (no icon-font, no runtime fetch). Match `currentColor`. Keep the set tiny: play/run,
stop, shield/seal, chain-link, cube/records, gauge, chart, info, close, orbit, download, chevron.

### A9. Motion system
Durations: `fast 120ms · base 200ms · slow 320ms · stage 480ms`. Easings:
`standard cubic-bezier(.2,0,0,1) · decel cubic-bezier(0,0,0,1) · accel cubic-bezier(.4,0,1,1) ·
spring (framer) {type:"spring", stiffness:260, damping:30}`.
- Hover on interactive: `fast`, `standard`, translateY(-1px) + shadow e0→e1.
- KPI count-up: only when a real value arrives; `slow`, `decel`, from previous value (or 0 on first).
- Drawer enter: x from +24px + opacity 0→1, `slow`, `decel`; exit `base`, `accel`.
- Stage/pipeline reveal: children stagger 40ms, each `stage`, `decel`.
- Tamper crack: `base`, `standard`, a 2px x-jitter (±2px, 3 cycles) then the break settles.
- **`prefers-reduced-motion: reduce`** → all of the above become opacity-only ≤120ms; count-up jumps;
  no jitter, no orbit auto-rotate.

---

## PART B — THE SCREEN, REGION BY REGION

Coordinates are content-box, desktop ≥1440 unless noted. "H" = height, "P" = padding.

### B1. Global frame
- Body: `--paper`, faint paper grain (CSS `background-image` via a tiny repeating radial-gradient of
  `rgba(120,90,40,.015)`, 3px tile — NOT an image request). Min-height 100vh, but content sizes to
  its content (no forced 100vh hero).
- Outer wrapper: max-width 1600, side gutter per A1, `padding-block: 0` (zones own their spacing).

### B2. Header (sticky, H 64px)
- Sticky top, `--paper` at 82% + `backdrop-filter: blur(12px)`, bottom hairline `--line`.
- Left: product lockup. A 20px brass seal glyph + "SynthProof" in Geist Sans 16/600 `--ink` + a Geist
  Mono 11px `--faint` version tag pulled from the API/health if present. Under it, on ≥1280, a 12px
  `--muted` tagline: "synthetic data that ships with its proof."
- Centre: nothing (keep it calm) OR the dataset name once a run starts, Geist Mono 13 `--muted`.
- Right: control cluster in one row, 12px gaps — Dataset select, ε control, Mechanism select, then the
  **Run release** primary button, then icon buttons (Verifier, Guided tour, theme toggle). Controls:
  H 36px, radius 8, 1px `--line`, `--card` fill, 12px horizontal P, Geist Sans 14. Primary button: H
  36px, brass fill, ivory text, radius 8, `e0`→`e1` on hover, brass-deep on active; label "Run
  release" + play icon; disabled = `--faint` fill, no shadow, `cursor:not-allowed`.

### B3. KPI card (the instrument dials)
The most-designed element. Grid auto-fit per A2. Each card:
- Box: `--card`, 1px `--line`, radius 12, `e0`. P 24 (16 ≤1280). Min-H **132px**. Full card is a
  `<button>`; entire surface is the click target (cursor pointer).
- Internal vertical stack, gap 8:
  1. **Eyebrow row** (H 16): Geist Mono 11/500/UPPERCASE `--faint` label key (e.g. "PRIVACY · ε") on
     the left; a 16px info glyph `--faint` on the right that brightens to `--brass` on card hover — the
     "there's more inside" affordance.
  2. **Number** (Display XL, `--ink`, tabular-nums). Before data: render an em-dash `—` at the same
     size, `--faint`. With data: count-up on arrival. A unit/suffix (e.g. the ε symbol, "rows") sits
     inline in Geist Mono 15 `--muted`, baseline-aligned.
  3. **Layman label** (Label 13/500 `--muted`, max 2 lines, `text-wrap: balance`) — the one-sentence
     plain meaning from the brief's KPI table.
  4. **Micro-state chip** (optional, only when meaningful): a pill (H 20, P 8, Geist Mono 11) — e.g.
     the Seal card shows `INTACT` in `--verify`/`--verify-bg` or `BROKEN` in `--seal`/`--seal-bg`; the
     Audit-reach card shows `AUDIT COULD SEE THIS` vs `BELOW RESOLUTION` from `audit_is_informative`.
- **States:** rest `e0`; hover `e1` + translateY(-1px) + info glyph → brass; focus-visible brass ring
  (A4); active translateY(0), `e0`. The card that is currently open in the drawer gets a persistent 2px
  brass left-border inset (so the viewer knows which dial they're inspecting).
- **Never** show a number the API didn't send. Empty = `—` + label, calm.

Card-to-explainer mapping and source fields: exactly the brief's §4.2 + §5 tables.

### B4. Centre stage — the 3D Privacy Chamber
- Frame: a recessed "well" — `--paper-2` background, radius 16, `e-inset`, 1px `--line`. Inner canvas
  fills it with 1px inset. Min-H **480px** (8-col), grows to available height, cap 640px.
- Top-left overlay HUD (absolute, 16px inset): stage name (Geist Mono 12 `--muted`) + a 2px brass
  progress hairline that fills 0→100% across the well's top as `stage` events stream.
- Bottom-left legend (absolute, 16px inset, `--card` at 70% + blur, radius 8, P 8/12): three rows,
  each a 8px swatch + Geist Mono 11 label — "Real record" (ink), "Synthetic" (brass), "Canary decoy"
  (seal). Legend items are toggles (reuse the existing layer toggles) but styled to this spec.
- **Scene** (three.js / R3F, upgrade `RecordCloud.tsx`):
  - Camera: perspective, fov 42, initial position framing the cloud with ~12% margin. OrbitControls:
    damping on, auto-rotate at 0.3 rad/s **only** when idle >4s and reduced-motion off; user drag
    stops it. No zoom past the well bounds.
  - Points: instanced, from the `done` frame `cloud` layers. Real = `--ink` at 0.55 opacity, size
    small; Synthetic = `--brass`, size small; Canary = `--seal`, size 1.6×, additive glow (a soft
    sprite halo, radius ~2.2× point). Depth-sorted; no z-fighting.
  - **Dissolve choreography** on a completed run: real points fade 1→0.35 while synthetic points scale
    0→1 and drift to their positions over `stage`×2 with per-point 0–200ms stagger; canaries pulse
    (opacity 0.6↔1, 1.6s) continuously but gently. Reduced-motion: no drift, just crossfade.
  - Lighting: one warm key light (brass-tinted) + soft ambient; subtle so points read as ink/brass, not
    rainbow. A faint ground reflection or grid is optional and must stay under `--line` intensity.
  - **Hit-testing:** raycast on pointer; hovered point scales 1.3× and shows a 1-line tooltip (its
    layer) in a `--card` chip; click opens the DetailDrawer for that point type (real vs synthetic vs
    canary → the AIM/DP-math / canary explainer). Keep 60fps target; cap point count (subsample the
    cloud to ≤ ~6k drawn instances, note it in a HUD caption if subsampled — honesty).
  - All of this lives behind the existing `ErrorBoundary`; on WebGL failure it renders a static 2D
    scatter (ECharts) with the same legend, never a blank box.

### B5. Right rail (4-col) — readouts & charts
Stacked panels, 16px gaps, each `--card`/1px `--line`/radius 12/`e0`, P 20, title row = Display M-ish
(Instrument Serif 20) + a right-aligned info glyph (opens the panel's explainer).
1. **ε pressure gauge** (BudgetMeter): a brass semicircular gauge (ECharts gauge OR hand-SVG) 0→target
   ε, needle at `eps_spent` streamed from stages; the arc fills brass, the remaining is `--line`; the
   centre reads the ε value (Geist Mono 20). Under it a 12px `--muted` line "budget spent / target."
2. **Audit range** (BoundsGauge): a horizontal bar showing proved ε (brass tick) vs audit ceiling
   (`--faint` bracket) — if proved > ceiling, the region beyond the ceiling is hatched `--seal` and the
   caption reads "audit could NOT have certified this" (from `audit_is_informative`). This is the
   project's honesty centrepiece — design it to be unmissable but not alarmist.
3. **Faithfulness** (Marginals): small real-vs-synthetic overlaid histograms (ECharts), real = ink
   outline, synthetic = brass fill at 40%. One per top numeric column, max 3, each ≤ 96px tall.

### B6. Ledger band (full 12-col)
- Section header: "The ledger" (Display L) + measured divider (A4) + right-aligned live seal chip
  (`verified` → INTACT/BROKEN).
- **Spine:** horizontal row of blocks, 12px gaps, horizontal scroll (`overflow-x:auto`) with the well
  treatment (`--paper-2`, `e-inset`) as the track. Each block:
  - Card 160×96, `--card`, radius 8, 1px `--line`. Inside: run id (Geist Mono 11 `--faint`, truncated),
    mechanism (Geist Sans 13/600), ε (Geist Mono 13 brass), and the truncated `hash` (Geist Mono 11
    `--faint`, 12 chars + …). Illustrative entries (`run_id` starts `illustrative-`) get a `--faint`
    "ILLUSTRATIVE" ribbon and are visibly lighter — never styled as a verified release.
  - Between blocks: a 12px brass link glyph (chain). When the chain is broken at block k, links after k
    turn `--seal` and gain a 2px gap "snap", and blocks after k get a `--seal` left-border.
  - Click a block → DetailDrawer with the hash-chain + Ed25519 math (brief §5), showing THIS block's
    real `prev_hash`, `hash`, `signature` prefix.
- **Tamper studio** (AttackDossier): a compact control strip above/beside the spine — four buttons
  (`modify_eps`, `truncate`, `corrupt_hash`, `corrupt_signature`) styled as `--seal`-outline buttons +
  a `--verify`-outline **Reset**. Firing one calls the real endpoint, then re-fetches `/api/ledger`;
  the crack animation and the seal chip flip are driven by the live `verified` field, never faked. A
  one-line result caption reports what broke, from the response.

### B7. Footer (H auto, top hairline, P-block 20)
Left: "SynthProof — B.Tech capstone · runs locally · every number computed." Right (Geist Mono 12
`--faint`): `docs/design/PUBLIC_RELEASE_BOUNDARY.md`. No fake logos, no invented affiliations.

### B8. The DetailDrawer (the signature interaction — specify to the pixel)
- Container: right-anchored, width **440px** (min(440px, 92vw)), full height minus header (top:64,
  bottom:0), `--card`, left 1px `--line`, `e2`, radius 16 on the top-left & bottom-left corners only.
  Backdrop: `rgba(26,23,18,.32)` + blur(2px), click-to-close.
- Enter/exit per A9. Focus-trapped; Esc closes; on open, focus moves to the close button; on close,
  focus returns to the element that opened it. `role="dialog"`, `aria-modal`, `aria-labelledby`.
- Internal layout, top→bottom, P 24, gap 20, scrollable body:
  1. **Header row:** eyebrow (Geist Mono 11 UPPERCASE `--brass`, the subject key) + close icon (top
     right, 32px hit box). Below: drawer title (Display M `--ink`).
  2. **In plain words:** a `--verify`-free plain block — Body 15/24 `--ink`, 2–3 sentences, ≤ 68ch.
     Left 3px `--brass` rule, 16px left P. This is the layman register.
  3. **The mechanism:** a `--paper-2` well (radius 8, P 16). Contains:
     - The formula, typeset with **KaTeX** (display mode), sized 18px, horizontal-scroll if wide.
     - A **parameters table**: 2 columns (name | value), Geist Mono 13, tabular-nums, the values pulled
       from THIS run's live fields (e.g. b, per-round ε, num_canaries, ceiling). Missing value → `—`,
       never invented.
  4. **Source:** footer row — a 16px file glyph + the exact repo path (Geist Mono 12 `--faint`), e.g.
     `synthproof/generators/aim.py`. This is the "verify me" affordance; it is mandatory on every
     drawer.
- One explainer per subject, from a typed registry (`explainers.ts`, schema in Part C). The drawer is
  pure presentation; it renders whatever explainer + live params it's handed.

---

## PART C — ENGINEERING SPEC

### C1. File layout (inside `web/src/`)
```
theme/tokens.css          // all CSS custom properties, light + dark (A6)
theme/tailwind additions  // extend colors/spacing/radii/shadow in tailwind.config
lib/api.ts                // KEEP — the contract; reuse verbatim
types.ts                  // KEEP — extend additively only
components/
  Shell.tsx               // header + layout scaffold
  KpiCard.tsx             // B3, one component, driven by props
  KpiRow.tsx
  PrivacyChamber.tsx      // B4 (rename/upgrade RecordCloud)
  RightRail.tsx  GaugeEpsilon.tsx  AuditRange.tsx  Marginals.tsx
  LedgerBand.tsx  LedgerBlock.tsx  TamperStudio.tsx
  DetailDrawer.tsx        // B8 — pure presentation
  charts/EChart.tsx       // themed echarts wrapper (light/dark aware)
  ErrorBoundary.tsx       // KEEP, wrap every 3D/chart surface
explainers/explainers.ts  // C4 registry
motion.ts                 // durations/easings as exported constants (A9)
```

### C2. Theme implementation
- All tokens as CSS custom properties in `theme/tokens.css`, declared on bare `:root`, redefined under
  `@media (prefers-color-scheme: dark):root:not([data-theme="light"])` and `:root[data-theme="dark"]`.
- Extend `tailwind.config` `theme.extend` with `colors` referencing `var(--...)`, the A1 spacing names,
  A3 radii, A5 boxShadow. Components use Tailwind classes bound to tokens — never hex literals in JSX.
- `body` sets `background: var(--paper)` explicitly (never transparent). Theme toggle stamps
  `data-theme` on `<html>`; persist choice in `localStorage` (wrapped in try/catch).

### C3. Data flow (all live; no mocks in the shipped path)
- On mount: `GET /api/datasets`, `/api/mechanisms`, `/api/ledger`, `/api/health`. Populate controls +
  ledger + version tag. Empty/`—` states until data lands.
- Run: `POST /api/run` SSE. Reducer over events: `start` → set run context; each `stage` → advance the
  progress hairline, ε gauge (`eps_spent`), pipeline log; `done` → hydrate every KPI, the chamber
  (`cloud`), the rail charts, append the ledger entry; `error` → surface in the log + a `--seal` toast,
  never swallow. Keep the existing `runRelease`/SSE code in `lib/api.ts`; only restyle consumers.
- **Single source of truth:** a typed `RunState` holds the last `done` payload; every KPI/chart/drawer
  reads from it. No component computes a displayed metric itself except trivial formatting.

### C4. Explainer registry schema (`explainers.ts`)
```ts
type Explainer = {
  key: string                       // 'epsilon' | 'aim' | 'ceiling' | 'ledger' | ...
  eyebrow: string                   // UPPERCASE subject key
  title: string
  plain: string                     // 2–3 sentences, layman
  katex: string                     // the formula, KaTeX string (display)
  params: (s: RunState) => { label: string; value: string }[]  // LIVE values, '—' if absent
  source: string                    // exact repo path shown in the footer
}
```
One entry per brief §5 row. `params` pulls only from `RunState`/ledger — if a field is absent it
returns `—`. The `katex` and `plain` text and `source` path must be faithful to the cited file; do not
introduce a claim the source doesn't make.

### C5. Charts (echarts)
- One `EChart.tsx` wrapper reading the current theme tokens and injecting them into every chart's
  `textStyle`, axis, split-line, tooltip. Colors: series brass / ink, semantic seal/verify only for
  meaning. `tabular-nums` equivalent via `fontFeatureSettings`. Tooltips: `--card` bg, 1px `--line`,
  Geist Mono 12. No default echarts blue/green palette anywhere.
- Re-theme on light/dark change (subscribe to the theme and re-init or `setOption` with new colors).

### C6. Performance budget
- Three.js is already code-split (vite manualChunks); keep it lazy — the chamber loads in a
  `React.lazy` boundary so the shell + KPIs paint first. Target first meaningful paint < 1.5s local.
- 3D: ≤ ~6k drawn instances, instanced meshes, frustum-culled; 60fps on an integrated GPU laptop; drop
  to the 2D fallback if `gl` context is lost.
- Total added JS from echarts+katex kept reasonable; katex CSS inlined via the package import, no CDN.

### C7. Accessibility (mandatory, not optional)
- Every interactive element: keyboard reachable, visible A4 focus ring, correct role/label. KPI cards
  are `<button>`s with `aria-haspopup="dialog"`. Drawer is a proper modal dialog (C/B8). Charts have a
  text `aria-label` summarizing the datum. Icon-only buttons have `aria-label`. Color is never the only
  signal — the seal state also shows the word INTACT/BROKEN; the audit-range also says it in words.
- Contrast verified per A6. Respect `prefers-reduced-motion` per A9 everywhere.

### C8. Definition of done (in addition to the brief's §8)
1. `npm run build` clean (tsc + vite) → `../synthproof/api/console`; `npm run test` green.
2. `START_PROTOTYPE.bat` serves the redesign at `:8000`; a real Adult/ε=1 run drives every pixel of
   the KPI row, chamber, rail, and ledger from the `done`/`ledger` payloads.
3. Every KPI card, ≥1 ledger block, ≥1 chamber point, and each rail panel opens a DetailDrawer whose
   formula (KaTeX) and Source path match the cited file and whose params are live.
4. Tamper: each attack visibly cracks the spine and flips the seal via the live `verified` field; Reset
   restores it.
5. Light + dark both pass contrast; reduced-motion honored; ≥1024px flawless, no horizontal body
   scroll at any width; the well/spine scroll internally.
6. Honesty grep: no displayed numeric literal in `web/src/**` that isn't an axis tick, a source-cited
   constant in a drawer, or explicitly labelled illustrative.
7. `web/REDESIGN_NOTES.md`: what changed, new deps, how to run, and anything not yet wired to real data
   (named honestly, never faked).

### C9. Build order (keep it runnable at every step — there is a demo tomorrow)
tokens+shell+KpiRow wired to a real run + DetailDrawer(explainers) → build/run → rail charts → build/run
→ ledger band + tamper → build/run → PrivacyChamber (lazy, behind ErrorBoundary) → build/run → modals
restyle → DoD sweep. Never leave the tree un-buildable between zones.
```
