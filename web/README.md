# SynthProof Console

The live console for the SynthProof pipeline: React + Vite + Tailwind + Framer Motion +
react-three-fiber, talking to the FastAPI service over server-sent events.

## Running it

Two processes. Backend first:

```bash
uvicorn synthproof.api.main:app --reload --port 8000
```

Then the console:

```bash
cd web
npm install
npm run dev
```

Open <http://localhost:5173>. Vite proxies `/api` to port 8000, so the browser stays on one
origin and nothing depends on the server's CORS policy.

To serve the console from the API process instead of a dev server:

```bash
cd web && npm run build      # emits into ../synthproof/api/static
```

`uvicorn synthproof.api.main:app` then serves the built console at `/`.

## What is on screen

| Panel | Source |
|---|---|
| Record space (3D) | Real, synthetic and canary rows projected through one transform fitted on the real table (`api/projection.py`) |
| Privacy loss, both sides | `ε_proved` from the RDP accountant, `ε_audited` from the canary auditor |
| Budget drawdown | The accountant's running total, updated as each stage charges |
| Pipeline | SSE stage events from `run_cell`'s `on_stage` callback |
| Attack dossier | Measured audit and MIA results; unimplemented attacks are named, not hidden |
| Ledger | The append-only chain, with a tamper button that breaks it live |
| Marginal fidelity | Real vs synthetic histograms on shared bin edges |
| Accountant charges | Every `PrivacySpend` recorded during the run |

## The rule this console follows

**Nothing on screen is a literal.** Every number is returned by the pipeline. Where a
capability does not exist — LiRA, DOMIAS, attribute inference, a signed data sheet — the
interface says so rather than rendering a pass.

That rule exists because an earlier version of this console displayed four hardcoded
`PASSED` attack verdicts with invented figures, one of them for an attack that was never
written. A demo that overstates is worse than no demo.

## The canary connectors

The lines in the 3D view run from each planted canary to its nearest synthetic record, which
is exactly the quantity `CanaryAuditor._similarity_scores` computes. Short, hot lines mean
that individual is recoverable from the release; long, cold lines mean they dissolved into
the population. It is the audit score, drawn.

## Known gaps

- The ledger is in-memory, so it resets when the API restarts. Set `SYNTHPROOF_LEDGER_DB`
  to a file path to persist it — though signatures still will not verify across restarts
  until the Ed25519 key is persisted too.
- Uploaded CSVs are held in memory for the session and never written to disk. That is
  deliberate; this service receives sensitive data by definition.
- A CSV uploaded without a declared schema has its bounds inferred **from the data**, which
  leaks. The console warns about this; do not use that path for a real release.
