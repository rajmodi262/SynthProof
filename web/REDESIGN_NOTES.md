# SynthProof "Atelier" Prototype Redesign Notes

## Overview
The SynthProof web console has been completely redesigned into the **"Atelier"** precision scientific instrument identity, embodying a **Brass, Ivory & Ink** visual system (`ANTIGRAVITY_PROTOTYPE_BRIEF.md` & `ANTIGRAVITY_PROTOTYPE_DESIGN_SPEC.md`).

All visual indicators, charts, 3D point cloud layers, and ledger entries are strictly wired to **live backend API responses** from `/api/run`, `/api/ledger`, `/api/health`, and the zero-trust verification endpoints. **Zero numbers are fabricated.**

---

## 1. Architectural & Aesthetic Upgrades

### "Brass, Ivory & Ink" Design Tokens
- Ground and Surfaces: Warm ivory `--paper` (`#F4F1EA`) with subtle CSS paper micro-grain texture, recessed wells `--paper-2` (`#EDE8DD`), and raised card surfaces `--card` (`#FBFAF6`). Dark mode equivalents implemented seamlessly under `:root[data-theme="dark"]`.
- Typography:
  - **Instrument Serif** for hero numerals and section titles.
  - **Geist Sans** for UI and body text.
  - **Geist Mono** for hashes, tabular numbers, source paths, and mathematical parameters.
- Elevation & Lines: Machined `1px` hairlines (`--line`) with low warm-shadow elevation levels (`e0`, `e1`, `e2`, `e-inset`) and signature measured dividers with 24px brass ticks.
- Semantic Color Discipline:
  - `--brass`: Single accent reserved for active selections and primary actions.
  - `--verify`: Semantic OK (moss green `#3F6B4E`) for intact chains and in-range certificates.
  - `--seal`: Semantic ALERT (oxide red `#7C2D2A`) for cryptographic cracks, leaks, and canaries.

---

## 2. Component System

### (a) Clickable KPI Row ("Instrument Dials") (`KpiRow.tsx`, `KpiCard.tsx`)
7 live instrument tiles with Instrument Serif numerals and tabular digit formatting:
1. **Privacy spent:** `sheet.total_proved_eps`
2. **Privacy audited:** `sheet.total_audited_eps`
3. **Audit reach:** `audit.ceiling` with in-range indicator
4. **Faithfulness:** `evaluation.correlation_error`
5. **Records:** `sheet.num_rows`
6. **Ledger height:** `/api/ledger` count
7. **Seal:** `/api/ledger` verified (`INTACT` / `BROKEN`)

### (b) Center Stage — 3D "Privacy Chamber" (`PrivacyChamber.tsx`)
- Three.js / React Three Fiber interactive scene with instanced point clouds:
  - **Real records:** Ink points (`0.55` opacity).
  - **Synthetic records:** Warm brass points.
  - **Canary decoys:** Oxide red points (`1.6×` size) with pulsating radar rings and nearest-neighbor affinity lines.
- Raycasting and point hit-testing: Clicking any point opens the `<DetailDrawer>` with its exact DP mechanism.
- Multi-angle camera projection toggles (3D Orbit, 2D PCA Top-Down, Side Cross-Section).
- Safe fallback: Renders a 2D PCA scatter plot using ECharts if WebGL is unavailable or fails inside `ErrorBoundary`.

### (c) Signature DetailDrawer & KaTeX Explainer Engine (`DetailDrawer.tsx`, `explainers.ts`)
- Slide-in instrument tray (440px, framer-motion, accessible dialog).
- Dual-register layout:
  1. Plain-words layman explanation (2–3 sentences).
  2. Mathematical formulation typeset with KaTeX.
  3. Live run parameter table extracted from the active pipeline state.
  4. Exact repository source file pointer in mono.
- Covers all 8 core mechanisms transcribed directly from cited backend code:
  - Privacy spent (`synthproof/accounting/accountant.py`)
  - AIM / synthetic point (`synthproof/generators/aim.py`)
  - Audit reach / ceiling (`synthproof/audit/ceiling.py`)
  - Ledger block (`synthproof/ledger/ledger.py`)
  - Faithfulness (`synthproof/evaluate/utility.py`)
  - Canary decoy point (`synthproof/audit/canary.py`)
  - The seal / verify (`synthproof/ledger/signing.py`)
  - Public release boundary & seed withholding (`docs/design/PUBLIC_RELEASE_BOUNDARY.md`)

### (d) Right Rail Instrumentation (`RightRail.tsx`)
- **ε Pressure Gauge (`GaugeEpsilon.tsx`):** Brass semicircular gauge showing budget spent vs target, streaming live from stage events.
- **Audit Range (`AuditRange.tsx`):** Verifiable MIQE range vs hatched oxide seal zone when claims exceed audit reach.
- **Marginals Fidelity (`Marginals.tsx`):** Real (ink outline) vs synthetic (brass fill) histograms via ECharts.
- **Pipeline Log (`PipelineLog.tsx`):** Streamed execution timeline rendered like an engraved log.

### (e) Ledger Spine & Interactive Tamper Studio (`LedgerChain.tsx`)
- 2.5D horizontal scroll chain of sealed blocks showing hashes, mechanism, and epsilon spent.
- Illustrative charges explicitly flagged with an "ILLUSTRATIVE" ribbon.
- Interactive Tamper Studio: Triggers real `/api/ledger/tamper` attacks (`modify_eps`, `truncate`, `corrupt_hash`, `corrupt_signature`), visibly fracturing the chain at the attacked block and flipping the live Seal status. Reset restores it via `/api/ledger/reset`.
- Clicking any block opens the `<DetailDrawer>` with its SHA-256 and Ed25519 signature proof.

---

## 3. Dependencies Added
- `echarts` (`^5.6.0`) & `echarts-for-react` (`^3.0.3`): For scientific gauges and marginal histograms.
- `katex` (`^0.16.22`) & `@types/katex`: For rigorous formula typesetting inside detail drawers.

---

## 4. How to Run

### Development Mode
```bash
cd web
npm run dev
```

### Production Build
```bash
cd web
npm run build
```
*(Runs `tsc --noEmit` and bundles into `../synthproof/api/console/`)*

### Run Automated Unit Tests
```bash
cd web
npm test
```

### Launch Full Prototype Server
Double-click `START_PROTOTYPE.bat` in the repository root or run:
```bash
python run_prototype.py
```
Browse to `http://127.0.0.1:8000/`.
