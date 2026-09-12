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
| Build health | 9.0 | 58 tests green, 87% coverage, ruff clean, CI with a calibration gate |
| Test quality | 5.5 | Regression tests now assert values, not just shapes; no property tests yet |
| Generators | 2.0 | Independent marginals only; neither is the algorithm it is named after |
| Attack suite | 2.0 | 2 weak baselines of 4 claimed |
| Empirical rigor | 2.0 | Toy data, 1 seed, no confidence intervals |
| Data layer | 6.5 | `Schema` + `from_csv` + CLI `--input`; real datasets still to land |
| Documentation | 1.5 | Thesis is 161 words against an 8,000–15,000 word requirement |
| Frontend integrity | 6.0 | Fabricated verdicts removed; still no live attack surface |
| **Weighted total** | **6.0** | |

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

> **Rewritten 2026-08-23 after a full scan.** The previous version of this section was ten
> days stale and **understated the project in almost every row** — it listed real data, five
> seeds, H1/H2/H3, property tests, `make reproduce`, the differential test and the signature
> as outstanding when all of them had shipped. A gap list that invents gaps is as misleading
> as one that hides them, and this is the file an examiner opens to find weaknesses. Every row
> below was checked against the code on the date above.

### 4.1 Code

| Item | State |
|---|---|
| Data ingestion | ✅ `Schema`, `from_csv`, CLI `--input` |
| Real AIM | ✅ private-PGM (`mbi`) behind `generators/aim.py`; two deviations from the paper stated in its docstring |
| Sensitivity from a public schema | ✅ no unbounded min/max |
| Attack suite | ✅ **all four run on every cell** — `distance_mia`, `domias`, `exact_match_risk`, `attribute_inference`. Wired 2026-08-23; two of them existed and were never called |
| Canary audit | ✅ full one-run Steinke construction is the default; the paired auditor is retained for comparison |
| Signed certificate + third-party verify | ✅ `synthproof keygen` / `run --sign` / `verify` |
| Persistent Ed25519 key | ✅ `ledger/signing.py`. The API service still uses an in-process key and says so in its own response |
| Differential accounting | ✅ every release cross-checked against `autodp`; verdict inside the signed payload |
| Pre-audit power analysis | ✅ `synthproof audit-power` |
| **Budget under-spend** | ⚠️ **Open.** proved/target ≈ 0.92 for `independent`/`pairwise` and 0.77–0.82 for `aim`, so 8–23% of the budget is never spent. Conservative, never unsafe, but it is utility left on the table |
| `moments` is a second independent baseline | ✅ **Named correctly everywhere.** `generators/moments.py` fits per-column moments and samples independently — no covariance, no rank transform. The registry key is `moments` and the class is `GaussianMomentGenerator`; the README called it `copula` until 2026-08-23 and now does not. A real Gaussian copula remains optional future work, not a correction |
| **One adversary** | ⚠️ **Open, and the most consequential.** Both auditors score by nearest-neighbour similarity. MAMA-MIA (Golob et al., SaTML 2025) is algorithm-aware against exactly this mechanism family. Every audited ε is a lower bound on a lower bound |
| **LiRA** | ❌ **Deliberately absent.** ~21h compute for a likely wide-CI null; naming anything cheaper "LiRA" would repeat audit finding F7 |

### 4.2 Science

| Item | State |
|---|---|
| Real data | ✅ UCI Adult (SHA-256 verified) and ACSIncome (CA 2018), 6,000 rows each |
| Seeds and intervals | ✅ 5 seeds per cell, bootstrapped 95% CIs (4,000 resamples) |
| **H1** | ✅ Run on both datasets. Supported on Adult; the structure ordering **does not transfer** to ACS. Diagnosed as clique-selection confounding, and the diagnosis was tested and weakened |
| **H2** | ✅ Run on both. A *bounded* null — BH-FDR, Bonferroni and TOST equivalence applied; detectability stated |
| **H3** | ✅ Run on both. Null, replicated |
| Auditor characterisation | ✅ Detection floor and ceiling both measured, with positive and negative controls |
| **Second-dataset generality** | ⚠️ Two datasets, both US census-derived, single-table, binary target. No healthcare, no time series |

### 4.3 Documentation

| Item | Required | Have | State |
|---|---:|---:|---|
| **Thesis** | 15,700 | **7,906** | ⚠️ **The binding constraint.** 50%, and four chapters are stubs. `make thesis` prints the shortfall per chapter |
| Threat model (ch03) | ~1,500 | 1,270 | ✅ close |
| **Preregistration** | — | 218 | ✅ **Leave it alone. Do NOT expand it.** A preregistration is a time-stamped commitment made *before* the results exist; rewriting it now, with every outcome known, would destroy the one property that gives it value and would be far worse than its being short. 218 words that were written on 2026-08-05 are worth more than 1,200 written today. What belongs in the thesis instead is ch06 §6.8, which already logs all five deviations with their direction of effect |
| Reproducibility guide | ~800 | 1,387 | ✅ `ARTIFACT.md`, USENIX artifact-evaluation format |
| API reference | ~1,000 | ~1,100 | ✅ `docs/API.md`, generated from the live route table by `scripts/build_api_reference.py`. All 9 routes carry handler docstrings |

### 4.4 Infrastructure

| Item | State |
|---|---|
| CI | ✅ ruff, **black**, coverage ≥80% gate, CLI smoke, bandit, pip-audit, gitleaks, console typecheck + build |
| `data/CHECKSUMS.txt` | ✅ present |
| `make reproduce` | ✅ `scripts/reproduce.py` + `results/MANIFEST.json` |
| Property tests | ✅ Hypothesis, `tests/test_accounting_properties.py` |
| Differential test vs `autodp` | ✅ and **promoted from a test to a release gate** |
| Test suite | ✅ 500+ cases, 94% coverage |
| Console tests | ✅ 10 vitest cases over the hand-rolled SSE parser |
| Claim and citation checks | ✅ `make claims` — dead claims and dangling/duplicate citations |
| Console dependency on a CDN | ✅ **Closed 2026-08-23.** The legacy console at `api/static/index.html` loaded Inter and JetBrains Mono from Google Fonts. Replaced with system stacks; a test now fails if any console HTML references an external host |

### 4.5 The short list

Everything genuinely outstanding, in the order it is worth doing:

1. **Thesis prose** — 7,794 words. Nothing else is close in size or risk.
2. **A stronger adversary** — the one open item that could change a published number.
3. ~~Preregistration and API reference~~ — API reference done (generated). **The preregistration must not be expanded**: see §4.3.
4. **A real Gaussian copula** — optional. It would add a genuinely distinct mechanism family; nothing is currently misnamed.
5. **Budget under-spend** — 8–23% of utility, conservative in the safe direction.

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
| 9 | Attack suite: DOMIAS + anonymeter (**"LiRA" is deliberately excluded** — ~21 h of compute for a likely wide-CI null, and naming anything cheaper after it would repeat audit finding F7) | 35–50 | M2 |
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

**Remaining to "excellent": ~170–285 engineer-hours.**

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
| **Today** | **6.0** |
| + M1 (real data, real mechanism, H1) | 7.5 |
| + M2 (attack suite, Steinke audit, H2) | 9.0 |
| + M3 (signed, verifiable, reproducible) | **9.5–10** |

See [`TASKBOARD.md`](TASKBOARD.md) for the trackable breakdown.
