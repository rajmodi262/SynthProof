# SynthProof — Deep Audit & Road to 10/10

> **Audit date:** 2026-08-13 · **Method:** full-file read of every source file, test-suite
> execution, live execution of the pipeline, and empirical verification of every numeric claim.
>
> Findings are reproduced by running the code, not inferred from reading it. Where a number
> appears below, the command that produced it is recoverable from the repository.

---

## 1. Verdict

> ### **6.0 / 10** as a research capstone — up from 3.5 at the first audit
>
> *(updated 2026-08-13 after F5 closed and CSV ingestion landed)*
>
> The two hardest correctness problems are now solved: the accountant delegates to a citable
> reference implementation, and a requested ε is the ε you actually get. What remains is
> largely **volume, not difficulty** — real mechanisms, real data, real attacks, and a real
> thesis.

### Scorecard

| Aspect | Score | Basis |
|---|---:|---|
| Architecture & packaging | 8.0 | Clean module boundaries, ABCs, typed frozen dataclasses |
| Privacy accounting | 8.0 | `dp_accounting` composition; calibration verified to <1e-4 |
| ε-calibration | 8.5 | proved/target = 0.92 across the grid, never overspends |
| Cryptographic ledger | 7.0 | Real Ed25519 + SHA-256, tamper-tested against live SQLite |
| Build health | 9.0 | 40 tests green, 90% coverage, ruff clean, CI with a calibration gate |
| Test quality | 5.5 | Regression tests now assert values, not just shapes; no property tests yet |
| Generators | 2.0 | Independent marginals only; neither is the algorithm it is named after |
| Attack suite | 2.0 | 2 weak baselines of 4 claimed |
| Empirical rigor | 2.0 | Toy data, 1 seed, no confidence intervals |
| Data layer | 6.5 | `Schema` + `from_csv` + CLI `--input`; real datasets still to land |
| Documentation | 1.5 | Thesis is 161 words against an 8,000–15,000 word requirement |
| Frontend integrity | 6.0 | Fabricated verdicts removed; still no live attack surface |
| **Weighted total** | **5.5** | |

**Task board completion: 427 / 950 = 44.9%**

---

## 2. What changed since the first audit

| First audit finding | Status |
|---|---|
| F1 — canary auditor structurally always zero | ✅ **Fixed.** Clopper-Pearson bound, FPR measured from held-out canaries, Fisher exact test, validated against a deliberately leaky release |
| F2 — `target_eps` is not a privacy budget | ✅ **Fixed.** See §3 |
| F3 — silent zero-noise hole at σ<0.3 | ✅ **Fixed**, with a regression test |
| F4 — unsound subsampling amplification | ✅ **Fixed.** Migrated to `dp_accounting`. The old bound under-reported ε by ~2× (0.485 vs 0.956 at q=0.01) |
| F5 — profiler leaked the exact category domain | ✅ **Fixed.** Domain released under a noisy threshold, and sensitivity is now derived from the public schema width rather than asserted as 1.0 |
| F6 — generators are not what they are named | ⚠️ **Honest, not fixed.** Docstrings and the deck now say so; real AIM is M1 |
| F7 — fabricated metrics | ✅ **Fixed** in Python *and*, as of this audit, in the web console |
| F8 — TRTR measured in-sample | ✅ **Fixed.** Shared held-out split; TRTR fell from a bogus 0.971 to ~0.334 (chance, correct for random labels) |
| F9 — experiments violate the preregistration | ❌ **Open.** Toy data, 1 seed |
| F10 — data sheet neither signed nor ledgered | ⚠️ **Partial.** Ledger head is real; signature still absent |
| F11 — README claims features that do not exist | ✅ **Fixed** |

### New findings from this scan

| ID | Finding | Status |
|---|---|---|
| **G1** | Web console hardcoded four `PASSED` attack verdicts with invented figures, including a pass for **attribute reconstruction, which does not exist in the codebase** | ✅ Fixed this session |
| **G2** | The `Anonymeter Risk 0.040` metric card had **no data source** — the data sheet carries no singling-out field | ✅ Fixed this session |
| **G3** | Copula categorical branch **charged ε and applied no noise**, releasing exact category frequencies | ✅ Fixed this session |
| **G4** | **No CSV ingestion anywhere.** No `read_csv`, no upload endpoint, no `--input` flag | ✅ Fixed this session — `Schema`, `from_csv`, `synthproof run --input` |
| **G5** | Thesis is **161 words**; threat model 177; preregistration 218 | ❌ Open |
| **G6** | `Allocator` was defined but never called by the pipeline, structurally blocking H3 | ✅ Fixed — `BudgetPlan` now routes through it |
| **G7** | Frontend loads Google Fonts from a CDN, so the console degrades without internet | ⚠️ Minor |

---

## 3. F2 closed — the headline result

`target_eps` was a knob that influenced the noise scale; the ε that composed was whatever fell
out. It is now an inversion of the composition theorem, with the release budget split across
every stage that reads the data.

| target ε | proved ε (before) | ratio | proved ε (now) | ratio |
|---:|---:|---:|---:|---:|
| 0.5 | 2.53 | 5.06× | **0.458** | 0.92× |
| 1.0 | 5.30 | 5.30× | **0.918** | 0.92× |
| 2.0 | 11.60 | 5.80× | **1.842** | 0.92× |
| 4.0 | 27.20 | 6.80× | **3.698** | 0.92× |
| 8.0 | 70.49 | 8.81× | **7.437** | 0.93× |

Calibration returns the conservative side of the bracket, so a release **never overspends**.
The residual ~8% under-spend is RDP composition being sublinear across the two stages — safe,
but it leaves a little utility unclaimed. Tracked as a refinement, not a defect.

A CI job asserts this across 24 mechanism × step × target configurations. If the claim
regresses, every certificate the project emits becomes false, so it gets its own gate.

---

## 4. What is left, by aspect

### 4.1 Code

| Gap | Consequence | Milestone |
|---|---|---|
| **No data ingestion path** | Cannot run on UCI Adult or anything else. Blocks all of §4.2 | M1 |
| AIM is not AIM; copula has no copula | H1 needs ≥2 genuinely distinct mechanism families | M1 |
| LiRA, DOMIAS, attribute inference missing | 2 of 4 claimed attacks | M2 |
| Canary audit simplified vs Steinke et al. | Bound is indicative, not tight | M2 |
| Unbounded min/max sensitivity in the profiler | The declared `sensitivity=1.0` is still unjustified | M1 |
| Certificate unsigned; no third-party verifier | The project's title is not yet literally true | M3 |
| Ed25519 key never persisted | File-backed ledgers become unverifiable after restart | M3 |
| ~8% budget under-spend | Utility left on the table | M3 |

### 4.2 Science

| Gap | Consequence | Milestone |
|---|---|---|
| Toy data (100 rows, independent columns) | Nothing to preserve; utility measurement is vacuous | M1 |
| 1 seed, no confidence intervals | No result is statistically defensible | M1 |
| **H1 untested** | Primary hypothesis | M1 |
| **H2 not started** — no subgroup code exists | The most publishable result in the project | M2 |
| **H3 blocked** until the allocator drives generators | Third hypothesis | M3 |

### 4.3 Documentation

| Gap | Required | Have | Milestone |
|---|---:|---:|---|
| **Thesis** | 8,000–15,000 words | **161** | Continuous |
| Threat model | ~1,500 | 177 | M1 |
| Preregistration | ~1,200 | 218 | M1 |
| API reference | ~1,000 | 0 | M2 |
| Reproducibility guide | ~800 | 0 | M3 |

### 4.4 Infrastructure

| Gap | Status |
|---|---|
| CI | ✅ Added this session |
| `data/` + `CHECKSUMS.txt` | ❌ M1 |
| `make reproduce` | ❌ M3 |
| Property tests (`hypothesis`) | ❌ M1 |
| Differential test vs `autodp` | ❌ M2 |

---

## 5. Mandatory vs optional

### 🔴 Mandatory — not defensible without these

| # | Item | Hours | Milestone |
|---|---|---:|---|
| 1 | ~~Fix build, wire calibration~~ | ~~5~~ | ✅ done |
| 2 | ~~Remove frontend fabrication~~ | ~~1~~ | ✅ done |
| 3 | ~~CI~~ | ~~2~~ | ✅ done |
| 4a | ~~CSV ingestion + public schema~~ | ~~6~~ | ✅ done |
| 4b | UCI Adult dataset loader + checksums | 4–6 | M1 |
| 5 | One real published mechanism (AIM via `private-pgm`) | 12–20 | M1 |
| 6 | Multi-seed sweep + confidence intervals | 10–15 | M1 |
| 7 | H1 tested and reported | 8–12 | M1 |
| 8 | **Thesis document** | **60–100** | continuous |
| | **Remaining subtotal** | **~96–157 h** | |

### 🟠 Strongly recommended — the gap between "passed" and "excellent"

| # | Item | Hours | Milestone |
|---|---|---:|---|
| 9 | Attack suite: LiRA + DOMIAS + anonymeter | 35–50 | M2 |
| 10 | Full Steinke one-run audit | 15–25 | M2 |
| 11 | Signed certificate + standalone verifier | 8–12 | M3 |
| 12 | **H2 subgroup disparity** | 15–25 | M2 |
| 13 | Property tests + differential test vs `autodp` | 8–12 | M1 |
| | **Subtotal** | **~81–124 h** | |

### 🟢 Stretch

| # | Item | Hours |
|---|---|---:|
| 14 | H3 allocator study | 12–20 |
| 15 | Real Gaussian copula | 8–12 |
| 16 | Frontend wired to live attack results | 15–25 |
| 17 | `make reproduce` artifact | 6–10 |

**Remaining to "excellent": ~180–300 engineer-hours.**

---

## 6. Schedule

At 4 people × ~6 h/week ≈ **24 h/week team capacity**:

| Target | Remaining hours | Calendar |
|---|---:|---|
| Mandatory only | ~126 | **5–6 weeks** |
| + Recommended | ~230 | **9–10 weeks** |
| + Stretch | ~290 | **12 weeks** |

Over a five-month horizon there is roughly 480 hours of capacity — enough for everything,
**provided thesis writing starts now and runs in parallel**. That single 60–100 hour item is
what sinks most capstones, because it cannot be compressed at the end.

### Recommended order

1. **Data layer + UCI Adult.** Everything downstream is blocked on this. Highest leverage.
2. **Real AIM via `private-pgm`.** Gives H1 two genuinely distinct mechanism families.
3. **Multi-seed sweep with CIs.** Turns output into evidence.
4. **H1.** At this point the project is complete and defensible.
5. **Attack suite → Steinke audit → H2.** This is what makes it excellent.
6. **Signing + verifier.** Makes the title literally true.
7. **Thesis, continuously from today.**

---

## 7. Standing rules

Adopted after the first audit found fabricated metrics in four separate modules.

1. **Never write a bound that cannot be cited.** Composition is delegated to `dp_accounting`.
2. **Never report a number that was not computed.** No hardcoded fallbacks, no derived
   stand-ins, no affine functions of another metric presented as independent.
3. **A mechanism that is charged must be applied.** Paying ε and skipping the noise is worse
   than not paying: budget is spent *and* the data leaks deterministically.
4. **Name things what they are.** A nearest-neighbour heuristic is not LiRA.
5. **Illustrative values must be labelled where they are displayed**, not only in a commit
   message or a chat.
6. **A null result is a result.** Reframe honestly rather than manufacturing a signal.

---

## 8. Where each stage lands

| State | Score |
|---|---:|
| First audit (2026-08-06) | 3.2 |
| After Tier 0 integrity work | 4.5 |
| **Today** | **5.5** |
| + M1 (real data, real mechanism, H1) | 7.5 |
| + M2 (attack suite, Steinke audit, H2) | 9.0 |
| + M3 (signed, verifiable, reproducible) | **9.5–10** |

See [`TASKBOARD.md`](TASKBOARD.md) for the trackable breakdown.
