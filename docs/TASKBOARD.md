# SynthProof — Task Board & Tracker

**Target: 10/10 in every aspect.** Companion to [`AUDIT_AND_ROADMAP.md`](AUDIT_AND_ROADMAP.md).

Update the dashboard whenever a task closes. Every task carries an owner, an hour estimate,
and — critically — a **Definition of Done that is checkable by someone else**. "Looks fine" is
not a DoD.

Legend: `[ ]` open · `[~]` in progress · `[x]` done · `[!]` blocked
Priority: 🔴 mandatory · 🟠 recommended · 🟢 stretch

---

## Dashboard

| Milestone | Scope | Done | Hours left | Status |
|---|---|---|---:|---|
| **M0** Foundations | A budget you can trust | 12 / 12 | 0 | ✅ **complete** |
| **M1** Real synthesis | Published mechanisms, real data, H1 | 12 / 14 | 8–12 | ✅ **H1 answered** |
| **M2** Audit engine | Real attacks, Steinke audit, H2 | 7 / 12 | 34–50 | 🔨 in progress |
| **M3** Ship the proof | Signed, verifiable, reproducible | 6 / 10 | 18–30 | 🔨 in progress |
| **DOC** Thesis & docs | Continuous | 3 / 9 | 70–95 | 🔴 **the critical path** |

**Health right now:** 201 tests green · 86% coverage · ruff + bandit clean · CI with calibration
AND auditor gates · H1 supported on structure and utility · H2 reported as not supported ·
data sheet signed and third-party verifiable

> **The one number that matters for submission:** the thesis is ~5,700 of 15,700 words.
> Everything else on this board is now ahead of it. See [`thesis/DATA_PACK.md`](thesis/DATA_PACK.md)
> — every figure, table and number each chapter needs is already generated and traced to a seed.

---

## M0 — Foundations ✅ COMPLETE

| # | Task | Pri | Owner | Hrs | Status |
|---|---|:--:|---|--:|:--:|
| M0.1 | Initialise git, push to GitHub | 🔴 | — | 1 | [x] |
| M0.2 | Delete every fabricated metric in Python | 🔴 | — | 4 | [x] |
| M0.3 | Remove the σ<0.3 zero-noise hole | 🔴 | — | 1 | [x] |
| M0.4 | Honest README + RESULTS status headers | 🔴 | — | 2 | [x] |
| M0.5 | LICENSE, drop 6 unused deps, fix `requires-python` | 🔴 | — | 1 | [x] |
| M0.6 | Migrate accountant to `dp_accounting` | 🔴 | — | 6 | [x] |
| M0.7 | Implement `calibrate_noise_scale` | 🔴 | — | 5 | [x] |
| M0.8 | `BudgetPlan` — split one budget across stages | 🔴 | — | 3 | [x] |
| M0.9 | Wire calibration into both generators | 🔴 | — | 4 | [x] |
| M0.10 | DP category-domain release in the profiler | 🔴 | — | 3 | [x] |
| M0.11 | Remove fabricated verdicts from the web console | 🔴 | — | 2 | [x] |
| M0.12 | CI: pytest + ruff + coverage + calibration guard | 🔴 | — | 2 | [x] |

**Evidence:** proved/target ratio moved from 5.06–8.81× to a consistent 0.92×, never
overspending. CI asserts this across 24 configurations.

---

## M1 — Real synthesis · 96–157 h

> **M1.1 is done — the critical path is open.** The system now ingests arbitrary CSVs with a
> declared public schema, so M1.2/M1.3 (real datasets) can proceed. Verified end to end on an
> 800-row correlated CSV: requested ε=2.0 → proved ε=1.836.

| # | Task | Pri | Owner | Hrs | Status | Definition of Done |
|---|---|:--:|---|--:|:--:|---|
| M1.1 | `TabularDataset.from_csv()` + schema spec | 🔴 | — | 4 | [x] | Loads an arbitrary CSV with declared column types; unit-tested on a fixture |
| M1.2 | `data/` loader + `CHECKSUMS.txt` | 🔴 | — | 3 | [x] | `make data` fetches UCI Adult and verifies SHA-256 |
| M1.3 | UCI Adult end to end | 🔴 | — | 3 | [x] | Full sweep completes on 48,842 rows × 14 cols |
| M1.4 | ACS PUMS via `folktables` | 🟠 | | 4 | [!] | Second real dataset, ≥50k rows, with subgroup labels for H2 |
| M1.5 | CLI `--input` flag | 🔴 | — | 2 | [x] | `synthproof run --input my.csv --eps 2.0` works |
| M1.6 | API upload endpoint | 🟠 | — | 4 | [x] | `POST /api/upload` accepts a CSV; console can drive it |
| M1.7 | Caller-declared public bounds (closes F5) | 🔴 | — | 5 | [x] | Sensitivity is derived from declared clip range, not asserted as 1.0 |
| M1.8 | Real AIM via `private-pgm` | 🔴 | — | 10–14 | [x] | Uses published AIM; preserves ≥1 measured 2-way marginal the baseline destroys |
| M1.9 | Real Gaussian copula | 🟢 | | 10 | [ ] | DP covariance + rank transform; measurably preserves correlation |
| M1.10 | Rename baseline → `IndependentMarginalGenerator` | 🔴 | — | 1 | [x] | No class claims an algorithm it does not implement |
| M1.11 | Multi-seed sweep runner (5 seeds) | 🔴 | — | 8 | [x] | Emits per-cell mean ± 95% CI |
| M1.12 | Bootstrapped frontier + plots | 🔴 | — | 6 | [x] | Privacy–utility frontier with CI bands, saved as a figure |
| M1.13 | **H1 tested and reported** | 🔴 | — | 10 | [x] | ε_audited/ε_proved compared across ≥2 real mechanism families with CIs; result reported either way |
| M1.14 | Property tests with `hypothesis` | 🟠 | — | 8 | [x] | Composition monotonicity; budget never exceeded; σ→0 ⇒ ε→∞ |

---

## M2 — Audit engine · 81–124 h

| # | Task | Pri | Owner | Hrs | Status | Definition of Done |
|---|---|:--:|---|--:|:--:|---|
| M2.1 | Full Steinke one-run audit | 🟠 | — | 20 | [x] | Randomised inclusion vector; ε from confusion counts via Clopper-Pearson |
| M2.2 | Auditor validation harness | 🟠 | — | 5 | [x] | Re-introduce the σ<0.3 bug; auditor must catch it. Becomes a CI test |
| M2.3 | LiRA with shadow models | 🟠 | | 20 | [ ] | ≥64 shadow models, per-example Gaussian fit, calibrated LR test |
| M2.4 | DOMIAS density-ratio MIA | 🟠 | — | 12 | [x] | Reproduces published behaviour on a known-leaky mechanism |
| M2.5 | `anonymeter` integration | 🟠 | | 6 | [ ] | Real singling-out, linkability, inference — three separate simulations |
| M2.6 | Attribute inference attack | 🟠 | | 8 | [ ] | Predicts a held-out sensitive column; reports lift over a marginal baseline |
| M2.7 | Report AUC + TPR@0.1%FPR everywhere | 🔴 | — | 3 | [x] | No attack reports accuracy at a median threshold |
| M2.8 | **H2 subgroup disparity** | 🟠 | — | 20 | [x] | Done on UCI Adult (not ACS) by race and sex. **Not supported**; the audit ceiling is the binding constraint |
| M2.9 | Differential test vs `autodp` | 🟠 | — | 6 | [x] | ε agrees with two independent implementations to 1e-6, in CI |
| M2.10 | Wasserstein-1 marginal distance | 🟢 | | 4 | [ ] | Replaces the current first-moment-only proxy |
| M2.11 | Fairness metrics (real) | 🟠 | | 8 | [ ] | Per-subgroup TSTR F1 and equalised-odds gap |
| M2.12 | Coverage gate → 90% | 🟠 | | 4 | [~] | CI fails below 90% |

---

## M3 — Ship the proof · 41–67 h

| # | Task | Pri | Owner | Hrs | Status | Definition of Done |
|---|---|:--:|---|--:|:--:|---|
| M3.1 | Persist the Ed25519 keypair | 🟠 | — | 3 | [x] | Key survives restart; file-backed ledgers verify |
| M3.2 | Sign the Privacy Data Sheet | 🟠 | — | 4 | [x] | Signature over canonical bytes of the whole sheet |
| M3.3 | `synthproof verify` command | 🟠 | — | 5 | [x] | A third party verifies with only the sheet and a public key |
| M3.4 | Anchor ledger head in each certificate | 🟠 | — | 2 | [x] | Certificate commits to the chain head at issue time |
| M3.5 | Ledger-driven allocator wired to generators | 🟢 | | 8 | [ ] | Per-column weights actually change noise allocation |
| M3.6 | **H3 tested** | 🟢 | | 10 | [ ] | Weighted vs uniform at equal total ε, with CIs |
| M3.7 | Close the ~8% budget under-spend | 🟢 | | 4 | [ ] | proved/target ≥ 0.98 while never exceeding 1.0 |
| M3.8 | `make reproduce` | 🟠 | — | 8 | [x] | Regenerates every published number from scratch; emits a manifest hash |
| M3.9 | Frontend wired to live attack results | 🟢 | — | 12 | [x] | Console shows measured attack output, no static values |
| M3.10 | Self-host fonts in the console | 🟢 | | 1 | [ ] | Console renders correctly with no internet |

---

## DOC — Thesis & documentation · 63–105 h · **START NOW**

> This is the item most likely to sink the project. It cannot be compressed at the end.
> Chapters 2 and 3 can be written **today** — they do not depend on any code.

| # | Chapter / doc | Words | Owner | Hrs | Status | Depends on |
|---|---|--:|---|--:|:--:|---|
| D.1 | Ch.1 Introduction & motivation | 1,200 | | 6 | [ ] | — |
| D.2 | Ch.2 Literature review | 2,500 | — | 20 | [~] | draft 1,888/2,500 words; needs ~600 more + BibTeX |
| D.3 | Ch.3 Threat model & problem formulation | 1,500 | | 8 | [ ] | **nothing — start today** |
| D.4 | Ch.4 System design & architecture | 2,000 | | 12 | [ ] | M0 ✅ — writable now |
| D.5 | Ch.5 Implementation | 1,500 | | 8 | [ ] | M1 |
| D.6 | Ch.6 Experimental methodology | 1,200 | | 6 | [ ] | M1.11 |
| D.7 | Ch.7 Results & analysis | 2,500 | | 16 | [ ] | M1.13, M2.8 |
| D.8 | Ch.8 Discussion, limitations, future work | 1,500 | | 8 | [ ] | M2 |
| D.9 | API reference + reproducibility guide | 1,800 | | 10 | [ ] | M3.8 |
| | **Total** | **15,700** | | **94** | | |

**Writable today with zero code dependency: D.2, D.3, D.4 — 4,000 words, ~40 h.**
That is 43% of the thesis, available now. Start there.

See [`thesis/`](thesis/) for the chapter scaffolds with per-section outlines.

---

## Weekly ritual

1. Update every `[ ]` → `[~]` → `[x]` touched this week.
2. Re-run `pytest` and paste the count into the dashboard.
3. **Re-check the deck's status slide** — [`deck/README.md`](deck/README.md) explains why a
   stale status slide is the single most dangerous artefact in this repo.
4. Any new fabrication, unciteable bound, or charged-but-unapplied mechanism is a **stop-work
   defect**. Fix before continuing. See the standing rules in the audit.

---

## Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| ~~`private-pgm` dependency problems~~ | — | — | ✅ **Resolved.** Works on Python 3.11; env verified end to end. See [PYTHON311_UPGRADE.md](PYTHON311_UPGRADE.md) |
| Thesis left to the end | **High** | **Critical** | D.2/D.3/D.4 start this week, before any M1 code |
| Audit detects nothing at realistic n | Medium | Medium | Scale canaries; report the detection floor; M2.2 validates the instrument |
| LiRA compute exceeds available hardware | Medium | Medium | Reduce shadow models to 32 and report the sensitivity of the result |
| Utility collapses at small ε | Medium | Low | That is itself the finding — a frontier showing where utility ends |
| Scope overrun | Medium | High | M1 alone is a complete project. M2 makes it good. M3 makes it excellent |
