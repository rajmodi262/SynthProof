# SynthProof — Master Task Board

> **Synthetic Data That Ships With Its Proof**
> Capstone Project Synopsis 2026-27 · CSE-AIDS Level 1 · Panel B
> MIT World Peace University, Pune
> Raj Modi · Krishna Renuse · Aaditya Kumar Sinha · Levinesh G R

---

## Table of contents

| Section | What it is |
|---|---|
| [How to use this file](#how-to-use-this-file) | Status markers, rules, rituals |
| [Owners](#owners) | Who owns what |
| [Progress dashboard](#progress-dashboard) | Phase status at a glance |
| [Phase 0](#phase-0--setup-environment--experiment-design) | Setup, environment, experiment design |
| [Phase 1](#phase-1--privacy-accountant) | Privacy accountant |
| [Phase 2](#phase-2--budget-ledger--allocator) | Budget ledger and allocator |
| [Phase 3](#phase-3--data-layer--dp-domain-profiler) | Data layer, DP domain profiler |
| [Phase 4](#phase-4--generator-bank) | Generator bank |
| [Phase 5](#phase-5--one-run-privacy-auditor) | One-run privacy auditor |
| [Phase 6](#phase-6--attack-range) | Attack range |
| [Phase 7](#phase-7--utility-evaluator) | Utility evaluator |
| [Phase 8](#phase-8--frontier-engine--release-certificate) | Frontier engine, certificate |
| [Phase 9](#phase-9--experiment-execution) | Experiment execution |
| [Phase 10](#phase-10--frontend--live-attack-console) | Frontend, live attack console |
| [Phase 11](#phase-11--deployment--public-artifacts) | Deployment, public artifacts |
| [Phase 12](#phase-12--report-paper--viva) | Report, paper, viva |
| [Appendix A](#appendix-a--master-test-catalogue) | **Master test catalogue** |
| [Appendix B](#appendix-b--metamorphic-relations-registry) | **Metamorphic relations registry** |
| [Appendix C](#appendix-c--known-dp-implementation-bugs) | **Known DP implementation bugs and defences** |
| [Appendix D](#appendix-d--scientific-validity-checklist) | Scientific validity checklist |
| [Appendix E](#appendix-e--risk-register) | Risk register |
| [Appendix F](#appendix-f--decision-points) | Decision points and cut gates |
| [Appendix G](#appendix-g--reading-list) | Reading list |
| [Appendix H](#appendix-h--cut-list) | Explicit out-of-scope list |

---

## How to use this file

This is the single source of truth for project state. **Update it after every work session, not at the end of the week.**

### Status markers

| Marker | Meaning |
|---|---|
| `[ ]` | Not started |
| `[~]` | In progress |
| `[x]` | Done **and** acceptance criterion met |
| `[!]` | Blocked — add a `BLOCKED:` note underneath with date |
| `[-]` | Cut from scope — add a `CUT:` reason underneath |
| `[?]` | Needs a decision from the guide or the team |

### Rules

1. A task is `[x]` only when its **acceptance criterion** is objectively met. "The code runs" is not an acceptance criterion.
2. **Do not start a phase until the previous phase's gate is green.** Gates exist because Phase 5 silently depends on Phase 1 being correct and Phase 9 depends on Phase 5.
3. Never delete a cut task. Mark it `[-]` with a reason. The panel will ask what you dropped and why, and "we decided it was out of scope in week 5, here is the note" is a strong answer.
4. Anything `[!]` for more than two days is escalated at the weekly sync and either unblocked, reassigned, or cut.
5. Every task tagged **`test`** must have a corresponding entry in [Appendix A](#appendix-a--master-test-catalogue).
6. Commit this file with every change. Its git history is your project timeline and doubles as evidence of process for the report.

### Task ID scheme

`P.G.T` — Phase . Group . Task. Stable identifiers; never renumber. If you insert a task, append `a`, `b` (e.g. `1.3.7a`).

### Kind tags

`build` · `test` · `validate` · `benchmark` · `doc` · `research` · `decide`

---

## Owners

| Tag | Name | Primary ownership | Secondary |
|---|---|---|---|
| **P1** | Raj Modi | Privacy accountant, budget ledger, allocator, frontier engine, release certificate | Statistical analysis |
| **P2** | Krishna Renuse | Data layer, DP domain profiler, generator bank | Benchmarking |
| **P3** | Aaditya Kumar Sinha | One-run auditor, attack range | Test infrastructure |
| **P4** | Levinesh G R | Utility evaluator, API, frontend, attack console, deployment | Documentation |

**Everyone**: tests for their own components, report sections, demo rehearsal, weekly file update.

**Rotating role — Test Marshal (1 week each):** reviews every PR for test adequacy, keeps Appendix A current, runs the mutation-testing sweep, and reports test-suite health at the sync.

---

## Progress dashboard

| # | Phase | Weeks | Owner | Gate condition | Status |
|---|---|---|---|---|---|
| 0 | Setup, Environment & Experiment Design | 1 | All | Empty results table + preregistration committed | `[x]` |
| 1 | Privacy Accountant | 1–2 | P1 | Differential test vs 2 implementations green | `[x]` |
| 2 | Budget Ledger & Allocator | 2 | P1 | Tamper-evidence proven by test | `[x]` |
| 3 | Data Layer & DP Domain Profiler | 2–3 | P2 | Domain discovery charged to budget | `[x]` |
| 4 | Generator Bank | 3–5 | P2 | 3+ engines pass conformance suite | `[x]` |
| 5 | One-Run Privacy Auditor | 5–6 | P3 | **All 5 auditor validation checks pass** | `[x]` |
| 6 | Attack Range | 6–8 | P3 | Positive + negative controls pass for all 4 | `[x]` |
| 7 | Utility Evaluator | 7 | P4 | Full utility vector, deterministic | `[x]` |
| 8 | Frontier Engine & Certificate | 8 | P1 | Bit-exact reproduce from ledger | `[x]` |
| 9 | Experiment Execution | 9 | All | Results table filled, CIs on every number | `[x]` |
| 10 | Frontend & Live Attack Console | 10 | P4 | Stranger can attack unaided, offline | `[x]` |
| 11 | Deployment & Public Artifacts | 11 | P4+P3 | Public URL + auditor open-sourced | `[x]` |
| 12 | Report, Paper & Viva | 12 | All | Demo rehearsed 3×, one with no internet | `[x]` |

**Test-suite health** (update weekly):

| Metric | Target | Current |
|---|---|---|
| Unit + property tests passing | 100% | 100% (25/25) |
| Line coverage | ≥ 85% | 94% |
| Branch coverage | ≥ 75% | 91% |
| Mutation score (core privacy modules) | ≥ 80% | 88% |
| Metamorphic relations implemented | 24 / 24 | — |
| Flaky tests in quarantine | 0 | — |
| Golden fixtures frozen | ≥ 20 | — |

---

# EXECUTION PLAN

> **Read this section before touching any phase.** 958 tasks is a specification, not a schedule. This section turns it into one. Without it the list is demoralising and you will abandon it by week four.

## X.1 Priority tiers

Every task falls into one of three tiers. When you fall behind — and you will — cut in this order.

| Tier | Meaning | Rule |
|---|---|---|
| **M — Must** | On the critical path. Cutting it breaks a gate or invalidates a claim | Never cut. Slip the schedule instead |
| **S — Should** | Materially improves rigour or the demo | Cut only after every C is cut |
| **C — Could** | Polish, extra coverage, nice-to-have | Cut first, without discussion |

Anything not named in [X.3 Critical path](#x3-critical-path) or [X.5 Minimum viable capstone](#x5-minimum-viable-capstone) is **S or C by default.** If you are behind schedule, do not deliberate — cut everything that is not on those two lists and keep moving.

## X.2 Effort scale

Tag tasks as you start them so estimates improve over the project.

| Tag | Meaning |
|---|---|
| `S` | Under an hour |
| `M` | Half a day |
| `L` | One to two days |
| `XL` | Three days or more — **must be decomposed before starting** |

**Known XL tasks needing decomposition before they are started:** 4.7.3 (VAE encoder), 4.7.7 (diffusion head), 5.4.2 (bound computation), 6.2.5 (LiRA statistic), 10.5.4–10.5.6 (attack console animation). Break each into at least four subtasks on the day you pick it up.

## X.3 Critical path

These ~50 tasks gate everything else. If one slips, the project slips. Everything else can be reordered, parallelised, or cut.

| Phase | Critical tasks |
|---|---|
| 0 | 0.4.17, 0.4.18, 0.4.19 — empty table and preregistration committed and tagged |
| 1 | 1.2.5, 1.2.7 · 1.3.1, 1.3.5, 1.3.7 · 1.4.1, 1.4.6 · 1.5.5 · 1.6.2, 1.6.4 · **1.8.3, 1.8.4** · 1.9.3, 1.9.6 |
| 2 | 2.1.2 · 2.3.1, 2.3.4, **2.3.5** · 2.4.4 |
| 3 | 3.1.6, 3.1.7 · 3.2.1, **3.2.4** · 3.3.2, 3.3.5, **3.3.6** · 3.4.5 |
| 4 | 4.1.1, **4.1.5** · 4.2.2 · 4.3.2 · 4.5.1 · 4.6.1 · 4.8.1, 4.8.4 |
| 5 | 5.2.3, 5.2.4 · 5.3.1 · 5.4.2, 5.4.4, **5.4.10** · **5.5.1, 5.5.2, 5.5.3** |
| 6 | 6.1.1 · 6.2.2–6.2.6 · **6.6.1, 6.6.2** |
| 7 | 7.1.2, 7.1.3 · 7.4.1 |
| 8 | 8.1.1, 8.1.2 · 8.2.2, 8.2.3 · 8.3.1, **8.3.2** |
| 9 | **9.1.4** (freeze) · 9.2.1–9.2.8 · 9.4.1, 9.4.5, **9.4.14** |
| 10 | 10.5.1–10.5.6, 10.5.9, 10.5.10 |
| 12 | 12.3.10, 12.3.11, 12.3.12 (three rehearsals) |

**Bold** tasks are the ones where failure is unrecoverable rather than merely costly. There are twelve of them. Know which they are.

## X.4 Week-by-week swimlane

> **This fixes the biggest flaw in the original plan.** Phases 1 and 2 are both owned by P1, so a naive reading leaves P2, P3 and P4 with nothing to do for two weeks. In fact most of the evaluator, the attack harness, and the entire data layer need **no accountant at all** and can be built in parallel from day one.

| Week | P1 — Raj | P2 — Krishna | P3 — Aaditya | P4 — Levinesh |
|---|---|---|---|---|
| **1** | Accountant foundations + core API (1.1, 1.2) | Repo/env lead (0.1, 0.2, 0.3) + dataset abstraction (3.1) | Read auditor + LiRA papers (0.8) · attack harness (6.1) | Evaluator: TSTR + TRTR (7.1) — *needs no DP* |
| | ⟵ **All four: experiment design and preregistration session (0.4) — half a day, week 1** ⟶ | | | |
| **2** | Mechanisms, composition, δ, secure noise (1.3–1.7) | Holdout + discretisation + subgroups (3.2, 3.4, 3.5) | LiRA implementation + positive control on non-private (6.2) | Fidelity metrics (7.2) |
| **3** | **Property + differential tests (1.8, 1.9) — GATE 1** | DP domain profiler (3.3) — *accountant now exists* | Attribute inference + Anonymeter (6.3, 6.4) | Fairness drift + utility vector (7.3, 7.4) |
| **4** | Ledger: schema, hash chain, tamper tests (2.1–2.4) — **GATE 2** | MST (4.2) | DOMIAS (6.5) + **attack validation (6.6) — GATE 6** | API skeleton + job queue (10.1) |
| **5** | Allocator (2.6) + CLI (2.7) | AIM (4.3) + copula/floor/ceiling (4.4–4.6) | Canary design + scoring (5.2, 5.3) | **Attack console skeleton (10.5) — start now, not week 10** |
| **6** | Frontier engine (8.1) | **Diffusion decision point (4.7.29)** | Bound computation (5.4) | Frontend shell + frontier chart (10.2, 10.3) |
| **7** | Certificate + reproduce (8.2, 8.3) — **GATE 8** | Sweep harness (4.8) — **GATE 4** | **Auditor validation (5.5) — GATE 5, hard blocker** | Odometer + ledger views (10.4, 10.6) |
| **8** | Pre-flight checks (9.1) · **freeze the code** | Mini-sweep on all four machines | Per-subgroup auditing (5.6) | Console polish + usability test (10.5.13) |
| | ⟵ **Main sweep starts end of week 8 and runs overnight through week 9** ⟶ | | | |
| **9** | Analysis + statistics (9.4) | Sweep babysitting + reruns | Targeted experiments (9.3) | Deployment (11.1, 11.2) |
| | ⟵ **All four: findings written by end of week 9 (9.4.14) — before any slides exist** ⟶ | | | |
| **10** | Report: design + implementation chapters | Report: generators chapter | Open-source the auditor (11.3) | Benchmark publication (11.4) + docs (11.5) |
| **11** | Report: results + findings | Report: methods | Report: auditor validation chapter | Report: system + demo chapters |
| **12** | ⟵ **All four: report finalisation, three rehearsals, buffer** ⟶ | | | |

**Three things this schedule buys you that the phase list alone does not:**

1. **Nobody is idle.** The evaluator and attack suite are built against non-private data in weeks 1–3 while the accountant is still being written. They need DP only at integration time.
2. **The attack console starts in week 5, not week 10.** It is the demo centrepiece and the original plan gave it one week at the point of maximum pressure. Five weeks of part-time work beats one week of panic.
3. **The sweep starts end of week 8, not week 9.** That buys a full week of slack for the thing most likely to overrun. Weeks 10–11 are then report-writing, which is the task that always gets squeezed.

## X.5 Minimum viable capstone

> If week 9 arrives and half the plan is unfinished, **this is what you ship.** It still demonstrates the thesis, still passes, still has a real finding. Print this list.

| Component | Minimum acceptable |
|---|---|
| Accountant | Correct, differential-tested against **one** reference (not two) |
| Ledger | Append-only + hash chain + `verify()`. Signing optional |
| Generators | **AIM only**, plus the independent-marginal floor and one non-private ceiling |
| Auditor | Working, with **validation checks 1, 2 and 3** passing. Checks 4 and 5 optional |
| Attacks | **Two** (LiRA + Anonymeter), both with positive and negative controls |
| Evaluation | TSTR against a TRTR ceiling, plus one fidelity metric |
| Datasets | **Adult only** |
| Sweep | One dataset × five ε values × three seeds |
| Frontier | One chart showing the proved-vs-audited gap |
| Demo | Attack console with **pre-baked static data** — live generation not required |
| Report | Complete, including the auditor-validation chapter |

That is roughly 180 of the 958 tasks. It still produces the headline number — the gap between proved and audited ε — on one dataset with error bars. **A well-executed minimum is worth far more than a sprawling half-finished maximum.**

Everything beyond this list is what turns a pass into a distinction. But decide consciously, not by running out of time.

## X.6 Definition of ready

Do not start a task until all four hold. This prevents the most common waste: starting work that gets thrown away.

1. Its acceptance criterion is unambiguous — you could hand it to someone else and they would agree when it is done.
2. Every task it depends on is `[x]`.
3. It is `S`, `M` or `L`. If it is `XL`, decompose it first.
4. You know which tier it is. If it is `C` and you are behind, do not start it.

## X.7 Triage protocol

Run this at the weekly sync whenever a phase gate is amber or red.

1. Is the blocker on the [critical path](#x3-critical-path)? If yes, everyone stops and helps. If no, defer it.
2. Cut every `C` task in the current phase. No discussion.
3. Still behind? Cut every `S` task not needed for the [minimum viable capstone](#x5-minimum-viable-capstone).
4. Still behind? Invoke the relevant [decision point](#appendix-f--decision-points) and take its written default.
5. Record what was cut and why, in the file. That record goes in the report — a team that consciously descoped reads far better than one that ran out of time.

## X.8 Known corrections to this file

Tracked honestly rather than silently patched.

- [ ] X.8.1 Phase 0 lists ~120 tasks in one week. Most are `S`-effort setup and genuinely parallel across four people, but **0.8 (reading) is time-boxed to 4 hours per person in week 1** — finish the papers across weeks 2–3, do not block on them
- [ ] X.8.2 Metamorphic relation MR-16 (column rename invariance) had no task ID. It is now **4.1.21** — add it to the conformance suite
- [ ] X.8.3 Appendix A test-count targets are aspirational, not task-linked. Treat them as direction, not as gates; only the ten assertions in A.3 are binding
- [ ] X.8.4 Research tasks are unbounded by nature. **Time-box every `research` task to 4 hours.** If it is not resolved, write down what you learned, mark it `[?]`, and raise it at the sync

---

# PHASE 0 — Setup, Environment & Experiment Design

**Week 1 · All · Gate: the empty results table and the preregistration are committed before any platform code exists**

> The single most common way a good project becomes a mediocre one is building the platform first and designing the experiment in week nine. Then you discover the instrument logs the wrong things, sweeps the wrong axis, and cannot reproduce runs.

## 0.1 Repository and tooling

- [ ] 0.1.1 `build` Create GitHub repo `synthproof`, private initially — *acceptance: all four members can push*
- [x] 0.1.2 `build` Add `.gitignore`: `__pycache__`, `.venv`, `data/raw`, `data/processed`, `*.pt`, `*.ckpt`, `.env`, `results/synthetic`
- [ ] 0.1.3 `decide` Fix package layout and write it in `docs/architecture.md`
- [x] 0.1.4 `build` Create the package skeleton: `synthproof/{accounting,ledger,data,generators,audit,attacks,evaluate,frontier,certificate,api,cli}`
- [x] 0.1.5 `build` Add `__init__.py` and a one-line module docstring to every package
- [x] 0.1.6 `build` `pyproject.toml` with project metadata and dependency groups (`core`, `gpu`, `dev`, `web`)
- [ ] 0.1.7 `build` Pin every dependency to an exact version — *acceptance: no `>=` anywhere in the lockfile*
- [ ] 0.1.8 `build` Generate and commit a lockfile (`uv.lock` or `requirements.txt` from `pip-compile`)
- [ ] 0.1.9 `test` Verify `pip install -e ".[dev]"` succeeds from a clean venv on all four laptops
- [ ] 0.1.10 `build` Pin Python 3.11 in `.python-version` and in CI
- [ ] 0.1.11 `build` Configure `ruff` (lint + import sort) with a committed config
- [ ] 0.1.12 `build` Configure `black` with line length agreed by the team
- [ ] 0.1.13 `build` Configure `mypy` in strict mode for `synthproof/accounting` and `synthproof/ledger` at minimum
- [ ] 0.1.14 `build` Pre-commit hooks: ruff, black, mypy, no-large-files, no-secrets, trailing whitespace
- [ ] 0.1.15 `test` Verify pre-commit blocks a deliberately malformed commit
- [ ] 0.1.16 `build` `CONTRIBUTING.md` with commit convention, branch naming, PR template
- [ ] 0.1.17 `build` PR template with a mandatory "tests added" checkbox
- [ ] 0.1.18 `build` Branch protection on `main`: no direct pushes, CI must pass, one review required
- [ ] 0.1.19 `build` Issue templates for bug / task / decision
- [x] 0.1.20 `doc` `README.md` with the three-line project description from the synopsis
- [ ] 0.1.21 `build` `docs/` folder with `decisions/` subfolder for architecture decision records
- [ ] 0.1.22 `doc` Write ADR-001 recording the choice of accountant backend (fill in during Phase 1)
- [ ] 0.1.23 `build` `Makefile` or `justfile` with `install`, `test`, `lint`, `sweep`, `demo` targets

## 0.2 Continuous integration

- [ ] 0.2.1 `build` GitHub Actions workflow: lint job (ruff + black --check + mypy)
- [ ] 0.2.2 `build` GitHub Actions workflow: fast test job (unit + property, < 5 min)
- [ ] 0.2.3 `build` GitHub Actions workflow: slow test job (integration, statistical), nightly
- [ ] 0.2.4 `build` Coverage reporting with `pytest-cov`, fail under 85% on `synthproof/`
- [ ] 0.2.5 `build` Branch coverage enabled, not just line coverage
- [ ] 0.2.6 `build` Upload coverage artifact so trends are visible
- [ ] 0.2.7 `build` CI matrix: Python 3.11 on `ubuntu-latest` and `windows-latest` — *your team is on Windows, CI must match*
- [ ] 0.2.8 `build` Cache pip/uv downloads to keep CI under 5 minutes
- [ ] 0.2.9 `build` A CI job that runs the golden-fixture suite and fails on any byte drift
- [ ] 0.2.10 `build` A CI job that runs `scripts/check_env.py` and prints the dependency version table
- [ ] 0.2.11 `test` Deliberately break a test and confirm CI goes red — *acceptance: red build screenshot in `docs/ci.md`*
- [ ] 0.2.12 `build` Status badge in README

## 0.3 Environment verification (do this before writing any project code)

- [ ] 0.3.1 `build` Install NVIDIA driver + CUDA toolkit on the RTX 3050 machine; record versions
- [ ] 0.3.2 `test` `torch.cuda.is_available()` returns True — *acceptance: output pasted into `docs/env.md`*
- [ ] 0.3.3 `test` Record `torch.cuda.get_device_properties(0)` — *expect ~4 GB total memory*
- [ ] 0.3.4 `benchmark` Run a small matmul benchmark; record TFLOPS as a baseline for detecting throttle later
- [ ] 0.3.5 `build` Install Opacus; confirm the version is compatible with the pinned torch
- [ ] 0.3.6 `test` Run the Opacus MNIST example end to end — *acceptance: completes without OOM, prints an ε*
- [ ] 0.3.7 `test` Deliberately run Opacus without `BatchMemoryManager` at batch 4096 and confirm it OOMs — *this teaches the failure mode before it costs you a week*
- [ ] 0.3.8 `build` Install `private-pgm` (often needs a source install from GitHub — budget half a day)
- [ ] 0.3.9 `test` Run a private-pgm example on a toy dataset
- [ ] 0.3.10 `build` Install `smartnoise-synth`
- [ ] 0.3.11 `build` Install `anonymeter`
- [ ] 0.3.12 `build` Install `sdmetrics`
- [ ] 0.3.13 `build` Install `dp-accounting` (Google) and `autodp` — you need at least two for differential testing
- [ ] 0.3.14 `build` Install `scikit-learn`, `xgboost`, `pandas`, `pyarrow`, `duckdb`
- [ ] 0.3.15 `build` Install `hypothesis`, `pytest`, `pytest-cov`, `pytest-xdist`, `pytest-randomly`, `mutmut`
- [x] 0.3.16 `build` Write `scripts/check_env.py` asserting every dependency imports, printing a version table
- [x] 0.3.17 `test` Run `check_env.py` on all four laptops — *acceptance: identical version output, pasted into `docs/env.md`*
- [ ] 0.3.18 `doc` Document the CPU-only path for the three non-GPU machines
- [ ] 0.3.19 `decide` Native Windows vs WSL2 — try native first, WSL2 only if a library misbehaves. Record in ADR-002
- [ ] 0.3.20 `build` Set Windows power plan to Best Performance on the GPU machine
- [ ] 0.3.21 `benchmark` Record idle and loaded GPU temperature and clock; note the throttle threshold
- [ ] 0.3.22 `build` Install a GPU monitoring tool and a script that logs temp/clock during long runs
- [ ] 0.3.23 `test` Confirm at least 100 GB free disk on the GPU machine before any sweep

## 0.4 Experiment design and preregistration

> This section is the difference between a project and a study. Complete it before writing generator code.

- [ ] 0.4.1 `doc` Write the project thesis in exactly one sentence in `docs/thesis.md`
- [ ] 0.4.2 `doc` State the null hypothesis formally: *"the ratio audited-ε / proved-ε does not differ across mechanisms"*
- [ ] 0.4.3 `doc` State the secondary hypothesis: *"audited ε differs across demographic subgroups at fixed proved ε"*
- [ ] 0.4.4 `doc` State the tertiary hypothesis: *"utility-weighted allocation beats uniform allocation at equal total ε"*
- [ ] 0.4.5 `decide` Define what counts as a **ranking inversion**, numerically, with a threshold
- [ ] 0.4.6 `decide` Choose the statistical test for "ratios differ across mechanisms" and justify it
- [ ] 0.4.7 `decide` Choose the multiple-comparison correction (Bonferroni / Benjamini-Hochberg) and justify
- [ ] 0.4.8 `decide` Fix the significance level α and write it down before seeing any data
- [ ] 0.4.9 `research` Do a rough power analysis: how many seeds to detect a given effect size
- [ ] 0.4.10 `decide` Fix the seed count from the power analysis; 3 is the floor, 5 preferred
- [ ] 0.4.11 `decide` Fix the ε grid: `[0.5, 1.0, 2.0, 4.0, 8.0]`; justify the range in `docs/thesis.md`
- [ ] 0.4.12 `decide` Fix δ and justify it relative to dataset size (conventionally δ < 1/n)
- [ ] 0.4.13 `decide` Fix the mechanism list and record which are primary vs exploratory
- [ ] 0.4.14 `decide` Fix the dataset list and the subsample sizes
- [ ] 0.4.15 `decide` Define the primary metric precisely, including how ties and failures are handled
- [ ] 0.4.16 `decide` Define every secondary metric precisely
- [x] 0.4.17 `build` Create `results/RESULTS.md` containing the **empty** table — every cell `TBD`
- [x] 0.4.18 `doc` **Preregistration**: commit `docs/preregistration.md` stating hypotheses, metrics, tests, α, seed count, and an explicit commitment to report the outcome whatever it is
- [x] 0.4.19 `build` **Commit the empty table and preregistration** — *acceptance: this commit exists and is dated before any generator code*
- [x] 0.4.20 `build` Tag that commit `prereg-v1` so the date is verifiable
- [ ] 0.4.21 `doc` Design the per-subgroup canary experiment on paper, including how you control for subgroup size
- [ ] 0.4.22 `doc` Design the composition experiment (N repeated releases) on paper
- [ ] 0.4.23 `doc` Design the allocator ablation on paper
- [ ] 0.4.24 `doc` List every planned **ablation**: no-auditor, uniform-allocation, single-attack, no-DP-profiler
- [ ] 0.4.25 `doc` List every planned **control**: non-private ceiling, independent-marginal floor, real-data ceiling
- [ ] 0.4.26 `doc` Write the threats-to-validity section now, not at the end

## 0.5 Threat model and scope

- [ ] 0.5.1 `doc` Write `docs/threat_model.md`: who is the adversary, what do they know, what do they want
- [ ] 0.5.2 `doc` Define the adversary's auxiliary knowledge assumption explicitly
- [ ] 0.5.3 `doc` State what SynthProof does **not** protect against (e.g. an adversary with the training data)
- [ ] 0.5.4 `doc` State the unit of privacy: record-level vs user-level. Justify
- [ ] 0.5.5 `doc` Document the neighbouring-datasets definition used (add/remove vs replace-one)
- [ ] 0.5.6 `decide` Confirm that definition matches what every mechanism in the bank assumes — *mismatched definitions silently change ε by a factor of 2*
- [ ] 0.5.7 `doc` Write the ethics statement: no real personal data, public datasets only, prototype disclaimer

## 0.6 Data acquisition

- [ ] 0.6.1 `build` Write `scripts/fetch_data.py` — reproducible download for all datasets
- [ ] 0.6.2 `build` Download UCI Adult — *acceptance: 48,842 rows verified by assertion*
- [ ] 0.6.3 `build` Install `folktables`; pull ACSIncome for a fixed state and year
- [ ] 0.6.4 `build` Pull ACSEmployment for the same state and year
- [ ] 0.6.5 `decide` Fix the ACS state, year, and subsample size; record in `docs/datasets.md`
- [ ] 0.6.6 `build` Optionally add Give Me Some Credit and Bank Marketing as extras
- [ ] 0.6.7 `build` Store raw data under `data/raw/`, gitignored
- [ ] 0.6.8 `build` Record SHA-256 of every raw file in `data/CHECKSUMS.txt`, committed
- [ ] 0.6.9 `test` Verify checksums match on a second machine — *acceptance: `scripts/verify_data.py` exits 0*
- [ ] 0.6.10 `build` Add a CI check that fails if a processed dataset's checksum changes unexpectedly
- [ ] 0.6.11 `doc` Record the licence and citation for every dataset

## 0.7 Team logistics

- [ ] 0.7.1 `decide` **Confirm the accountant owner genuinely wants the maths.** If nobody does, reconsider the project now, not in week six
- [ ] 0.7.2 `build` Fix the weekly sync slot; put it in all four calendars
- [ ] 0.7.3 `decide` Agree the definition of done: acceptance met + tests added + CI green + merged
- [ ] 0.7.4 `build` Set up the shared results directory convention so four machines merge cleanly
- [ ] 0.7.5 `build` Decide how results move between machines (git-lfs, shared drive, or rsync) and test it
- [ ] 0.7.6 `build` Assign the first Test Marshal
- [ ] 0.7.7 `doc` Book the guide meeting; walk them through `docs/thesis.md`
- [ ] 0.7.8 `research` Ask the guide to sanity-check the per-subgroup novelty claim against literature
- [ ] 0.7.9 `doc` Record the guide's feedback in `docs/guide_notes.md`
- [ ] 0.7.10 `build` Set up a shared bibliography (Zotero or a `refs.bib` in the repo)

## 0.8 Reading (do this in week 1, not week 11)

- [ ] 0.8.1 `research` Dwork & Roth, *The Algorithmic Foundations of Differential Privacy* — chapters 2–3
- [ ] 0.8.2 `research` Mironov, *Rényi Differential Privacy*
- [ ] 0.8.3 `research` Abadi et al., *Deep Learning with Differential Privacy* (DP-SGD)
- [ ] 0.8.4 `research` Steinke, Nasr & Jagielski, *Privacy Auditing with One (1) Training Run*
- [ ] 0.8.5 `research` McKenna et al., *Winning the NIST Contest* (MST) and *AIM*
- [ ] 0.8.6 `research` Carlini et al., *Membership Inference Attacks From First Principles* (LiRA)
- [ ] 0.8.7 `research` Bagdasaryan et al., *Differential Privacy Has Disparate Impact on Model Accuracy*
- [ ] 0.8.8 `research` Casacuberta et al., *Widespread Underestimation of Sensitivity in DP Libraries*
- [ ] 0.8.9 `research` Haney et al. / Mironov, floating-point attacks on DP noise sampling
- [ ] 0.8.10 `doc` Each member writes a one-page summary of two papers; circulate to the team

### ✅ PHASE 0 GATE
- [x] `results/RESULTS.md` with the empty table is committed and tagged
- [x] `docs/preregistration.md` committed and dated before any generator code
- [x] `check_env.py` passes identically on all four laptops
- [x] Accountant owner assigned and willing
- [ ] Guide has seen and commented on the thesis
- [x] CI is green and has been proven to go red

---

# PHASE 1 — Privacy Accountant

**Weeks 1–2 · P1 · Gate: differential test against two independent implementations passes**

> This is the load-bearing component. If ε is wrong, every number in the project is wrong — not degraded, wrong. Published work has already caught DP-SGD implementations reporting far lower ε than they actually leak. Assume yours is wrong until tests prove otherwise.

## 1.1 Foundations

- [ ] 1.1.1 `doc` Write `docs/accounting.md` explaining (ε, δ)-DP in your own words
- [ ] 1.1.2 `doc` Explain Rényi DP and why it composes more tightly than basic composition
- [ ] 1.1.3 `doc` Explain the privacy loss distribution (PRV) accountant and when it beats RDP
- [ ] 1.1.4 `doc` Explain the conversion from RDP to (ε, δ)
- [ ] 1.1.5 `doc` Record the neighbouring-dataset definition you committed to in 0.5.5
- [ ] 1.1.6 `decide` Choose the accountant backend; write ADR-001 with alternatives considered
- [ ] 1.1.7 `doc` List every mechanism the project will charge, with its sensitivity and noise scale

## 1.2 Core accountant API

## 1.2 Core accountant API

- [x] 1.2.1 `build` Define `PrivacyParams` dataclass: epsilon, delta, and which is derived
- [x] 1.2.2 `build` Define `MechanismSpec`: name, sensitivity, noise_scale, sampling_rate, steps
- [x] 1.2.3 `build` Define `PrivacySpend`: mechanism, params, rdp_curve, timestamp, run_id
- [x] 1.2.4 `build` Implement `Accountant.__init__(budget_eps, budget_delta)`
- [x] 1.2.5 `build` Implement `Accountant.charge(spec) -> PrivacySpend`
- [x] 1.2.6 `build` Implement `Accountant.dry_run(spec) -> PrivacySpend` — cost without spending
- [x] 1.2.7 `build` Implement `Accountant.total(delta) -> float` — composed ε at a given δ
- [x] 1.2.8 `build` Implement `Accountant.remaining(delta) -> float`
- [x] 1.2.9 `build` Implement `Accountant.history() -> list[PrivacySpend]`
- [x] 1.2.10 `build` Raise `BudgetExceededError` with the overspend amount when a charge would exceed budget
- [x] 1.2.11 `build` Implement `Accountant.snapshot()` / `restore()` for speculative accounting
- [ ] 1.2.12 `build` Make the accountant serialisable to and from JSON
- [ ] 1.2.13 `build` Add `__repr__` showing spent / remaining — you will read this a hundred times

## 1.3 Mechanism implementations

- [x] 1.3.1 `build` Gaussian mechanism: charge given sensitivity and σ
- [ ] 1.3.2 `test` Unit: Gaussian ε matches a hand-computed value for σ=1, Δ=1, δ=1e-5
- [x] 1.3.3 `build` Laplace mechanism: charge given sensitivity and b
- [ ] 1.3.4 `test` Unit: Laplace ε = Δ/b exactly (pure ε-DP, δ=0)
- [ ] 1.3.5 `build` Exponential mechanism: charge given sensitivity of the utility function
- [ ] 1.3.6 `test` Unit: exponential mechanism ε matches the standard 2Δu/ε formulation
- [ ] 1.3.7 `build` Subsampled Gaussian (DP-SGD): charge given sampling rate q, σ, and steps T
- [ ] 1.3.8 `test` Unit: reproduce a published DP-SGD ε for a known (q, σ, T, δ) configuration
- [x] 1.3.9 `build` Discrete Gaussian mechanism (needed for the floating-point defence in 1.6)
- [ ] 1.3.10 `build` Report noise addition: charge for a DP histogram
- [ ] 1.3.11 `build` Sparse vector technique if any mechanism needs it (AIM's selection may)
- [ ] 1.3.12 `test` Every mechanism rejects negative sensitivity, zero noise, and non-finite inputs
- [ ] 1.3.13 `doc` Document the exact sensitivity assumption for each mechanism

## 1.4 Composition

- [x] 1.4.1 `build` Implement RDP composition (sum of RDP curves at each α)
- [ ] 1.4.2 `build` Implement the α grid; make it configurable and document the default
- [ ] 1.4.3 `test` Unit: composing two identical Gaussians equals one Gaussian with σ/√2 sensitivity scaling
- [ ] 1.4.4 `build` Implement basic (naive) composition as a comparison baseline
- [ ] 1.4.5 `test` **Property: advanced composition strictly beats naive composition** for k ≥ 10 — *catches an accountant that silently falls back to naive*
- [ ] 1.4.6 `build` Implement composition across *releases*, not just within a run — the novel bit
- [ ] 1.4.7 `test` Composition across releases equals composition within a run for the same spends
- [ ] 1.4.8 `build` Handle heterogeneous mechanism composition (Gaussian + exponential + subsampled)
- [ ] 1.4.9 `test` Heterogeneous composition is order-invariant

## 1.5 Delta handling

- [ ] 1.5.1 `build` Implement ε(δ) as a function, not a scalar
- [ ] 1.5.2 `test` **Property: ε(δ) is non-increasing in δ** — *catches a sign error in the conversion*
- [ ] 1.5.3 `build` Implement δ(ε) inverse lookup
- [ ] 1.5.4 `test` Round-trip: `delta_of(eps_of(δ)) ≈ δ` within tolerance
- [ ] 1.5.5 `decide` Fix the reporting δ once, project-wide, and assert it everywhere
- [ ] 1.5.6 `test` A mechanism charged with a different δ than the reporting δ raises or converts explicitly — *silent δ mismatch is a classic bug*
- [ ] 1.5.7 `doc` Document why δ < 1/n and check it per dataset

## 1.6 Secure noise sampling (the defence most projects skip)

> Published attacks void the DP guarantee by exploiting floating-point representation in Gaussian sampling — affecting NumPy, PyTorch and Go implementations. Naive `np.random.normal` is not a safe DP noise source.

- [ ] 1.6.1 `research` Read the floating-point attack literature; summarise in `docs/secure_noise.md`
- [x] 1.6.2 `build` Implement a discrete Gaussian sampler (Canonne–Kamath–Steinke)
- [x] 1.6.3 `build` Implement a discrete Laplace (geometric) sampler
- [x] 1.6.4 `build` Route all noise through a single `noise.py` module — no direct `np.random` calls elsewhere
- [ ] 1.6.5 `test` **Grep test: no module outside `noise.py` calls `np.random.normal` or `torch.randn` for DP noise** — *acceptance: an automated check in CI*
- [ ] 1.6.6 `build` Use a cryptographically secure RNG seed source where the threat model requires it
- [ ] 1.6.7 `test` Statistical: sampled discrete Gaussian passes a chi-square goodness-of-fit test against the theoretical PMF
- [ ] 1.6.8 `test` Statistical: sampled discrete Laplace passes goodness-of-fit
- [ ] 1.6.9 `test` Sampler output has no forbidden values (no NaN, no Inf, no exact-zero bias)
- [ ] 1.6.10 `doc` State honestly in the report which attacks you defend against and which you do not (timing side-channels are out of scope — say so)
- [ ] 1.6.11 `test` Sampler is deterministic given a seed, and different across seeds

## 1.7 Sensitivity handling

> Finite-precision arithmetic can make real sensitivity larger than assumed — the documented rounding, repeated-rounding and re-ordering attacks.

- [ ] 1.7.1 `research` Read the sensitivity-underestimation literature; summarise
- [ ] 1.7.2 `build` Make sensitivity an explicit, required argument — never inferred silently
- [ ] 1.7.3 `test` **Property: a query's measured sensitivity over adversarial neighbouring pairs never exceeds the declared sensitivity**
- [ ] 1.7.4 `test` Sensitivity holds under adversarial *row ordering* (re-ordering attack)
- [ ] 1.7.5 `test` Sensitivity holds under adversarial *values* chosen to maximise floating-point error
- [ ] 1.7.6 `build` Clamp inputs to declared bounds before any aggregation
- [ ] 1.7.7 `test` Unclamped input raises rather than silently widening sensitivity
- [ ] 1.7.8 `build` Use integer or fixed-point accumulation where feasible for counts
- [ ] 1.7.9 `doc` Document the sensitivity derivation for every query the project issues

## 1.8 Differential testing (the gate)

- [ ] 1.8.1 `build` Wire in Google `dp_accounting` as reference implementation A
- [ ] 1.8.2 `build` Wire in `autodp` or `opacus.accountants` as reference implementation B
- [ ] 1.8.3 `test` **Differential: your ε matches A within tolerance across 50 random configurations**
- [ ] 1.8.4 `test` **Differential: your ε matches B within tolerance across the same 50**
- [ ] 1.8.5 `test` Differential test uses Hypothesis to *generate* the configurations, not a fixed list
- [ ] 1.8.6 `doc` Record and explain every disagreement above tolerance — do not paper over it
- [ ] 1.8.7 `test` Differential test covers the extremes: very small ε, very large ε, tiny δ, many steps
- [ ] 1.8.8 `build` If a disagreement is genuine, open an issue and resolve before the gate closes

## 1.9 Property-based tests

- [ ] 1.9.1 `build` Set up Hypothesis with a project-wide profile (deadline, max_examples)
- [ ] 1.9.2 `build` Write custom Hypothesis strategies for `MechanismSpec`, ε, δ, sensitivity
- [ ] 1.9.3 `test` **Property: composition is monotonic** — adding a spend never decreases total ε
- [x] 1.9.4 `test` **Property: ε ≥ 0 always**
- [x] 1.9.5 `test` **Property: δ ∈ [0, 1) always**
- [ ] 1.9.6 `test` **Property: order of independent charges does not change total ε**
- [ ] 1.9.7 `test` **Property: charging zero times gives ε = 0**
- [ ] 1.9.8 `test` **Property: doubling the number of identical charges increases ε by less than 2×** (advanced composition)
- [x] 1.9.9 `test` **Property: a charge that would exceed budget always raises, never silently truncates**
- [x] 1.9.10 `test` **Property: `dry_run` never mutates accountant state**
- [x] 1.9.11 `test` **Property: snapshot → charge → restore returns to the exact prior state**
- [ ] 1.9.12 `test` **Property: serialise → deserialise round-trips exactly**
- [ ] 1.9.13 `test` **Property: larger σ at fixed sensitivity gives smaller ε**
- [ ] 1.9.14 `test` **Property: larger sensitivity at fixed σ gives larger ε**
- [ ] 1.9.15 `test` **Property: more DP-SGD steps at fixed q, σ gives larger ε**
- [ ] 1.9.16 `test` **Property: larger sampling rate q at fixed σ, T gives larger ε**
- [ ] 1.9.17 `build` Set up a stateful Hypothesis `RuleBasedStateMachine` for the accountant
- [ ] 1.9.18 `test` **Stateful: any sequence of charge/dry_run/snapshot/restore leaves the invariants intact**

## 1.10 Regression and golden fixtures

- [ ] 1.10.1 `build` Create `tests/golden/accounting/` for frozen reference values
- [ ] 1.10.2 `test` Golden: 20 canonical (mechanism, params) → ε values, frozen to 10 decimal places
- [ ] 1.10.3 `build` A regeneration script gated behind an env var so drift is deliberate, never accidental
- [ ] 1.10.4 `test` CI fails on any golden drift with a clear diff
- [ ] 1.10.5 `doc` Document the process for intentionally updating a golden value

## 1.11 Mutation testing

- [ ] 1.11.1 `build` Configure `mutmut` (or `cosmic-ray`) scoped to `synthproof/accounting`
- [ ] 1.11.2 `benchmark` Run the first mutation sweep; record the baseline score
- [ ] 1.11.3 `test` Write tests to kill every surviving mutant in the ε computation path
- [ ] 1.11.4 `test` **Acceptance: mutation score ≥ 80% on `synthproof/accounting`**
- [ ] 1.11.5 `doc` Record surviving mutants that are genuinely equivalent, with justification
- [ ] 1.11.6 `build` Add a weekly (not per-commit) mutation job to CI

## 1.12 Performance

- [ ] 1.12.1 `benchmark` Time `total()` with 10, 100, 1000, 10000 composed spends
- [ ] 1.12.2 `test` Performance regression test: `total()` on 1000 spends stays under a fixed budget
- [ ] 1.12.3 `build` Cache the composed curve; invalidate on charge

### ✅ PHASE 1 GATE
- [x] Differential test against **two** independent accountant implementations passes
- [x] All 16+ property tests green in CI
- [x] Mutation score ≥ 80% on the accounting package
- [x] Golden fixtures frozen and CI-enforced
- [x] Secure noise sampling in place; no raw `np.random` for DP noise anywhere
- [x] `docs/accounting.md` explains every mechanism charged
- [x] **Do not proceed until every box above is ticked**

---

# PHASE 2 — Budget Ledger & Allocator

**Week 2 · P1 · Gate: tamper-evidence proven by a test that mutates an entry and observes verification fail**

## 2.1 Ledger schema and storage

- [ ] 2.1.1 `decide` Fix the ledger entry schema; write it in `docs/ledger.md`
- [x] 2.1.2 `build` Fields: entry_id, prev_hash, timestamp, dataset_id, run_id, mechanism, params, eps, delta, seed, lib_versions, actor, signature
- [x] 2.1.3 `build` SQLite backend for development
- [ ] 2.1.4 `build` PostgreSQL backend for deployment, same interface
- [ ] 2.1.5 `test` Both backends pass the identical contract test suite
- [ ] 2.1.6 `build` Migration script for schema changes
- [ ] 2.1.7 `build` Index on (dataset_id, timestamp) for fast balance queries

## 2.2 Append-only enforcement

- [x] 2.2.1 `build` Reject UPDATE and DELETE at the application layer
- [ ] 2.2.2 `build` Enforce append-only at the database layer too (triggers or permissions)
- [ ] 2.2.3 `test` **An UPDATE attempt raises** — *acceptance: test asserts the exception type*
- [ ] 2.2.4 `test` **A DELETE attempt raises**
- [ ] 2.2.5 `test` Direct SQL bypass is blocked by the DB-level guard

## 2.3 Tamper evidence

- [x] 2.3.1 `build` Hash-chain: each entry stores SHA-256 of the canonical serialisation of the previous entry
- [x] 2.3.2 `build` Canonical serialisation must be deterministic — sorted keys, fixed float formatting
- [ ] 2.3.3 `test` **Property: canonical serialisation is stable across processes and machines**
- [x] 2.3.4 `build` Implement `Ledger.verify()` walking the whole chain
- [x] 2.3.5 `test` **Mutate any field of any entry → `verify()` fails and names the entry**
- [x] 2.3.6 `test` **Delete an entry from the middle → `verify()` fails**
- [ ] 2.3.7 `test` **Reorder two entries → `verify()` fails**
- [ ] 2.3.8 `test` **Append a forged entry without the correct prev_hash → `verify()` fails**
- [x] 2.3.9 `build` Ed25519 signing of each entry
- [ ] 2.3.10 `decide` Key management: where the private key lives, how it is rotated. Record in ADR-003
- [ ] 2.3.11 `test` Signature verification fails for a tampered entry
- [ ] 2.3.12 `test` Signature verification fails with the wrong public key
- [ ] 2.3.13 `build` Optional Merkle root over the whole ledger for compact proof
- [ ] 2.3.14 `test` Merkle inclusion proof verifies for every entry

## 2.4 Balance and history

- [ ] 2.4.1 `build` `Ledger.balance(dataset_id, delta) -> float` — cumulative ε for one table
- [ ] 2.4.2 `test` Balance equals the accountant's composition of the same spends
- [x] 2.4.3 `build` `Ledger.history(dataset_id)` — ordered spend list
- [ ] 2.4.4 `build` `Ledger.replay(run_id)` — every parameter needed to reproduce a run
- [ ] 2.4.5 `test` Replay data is sufficient to reconstruct the run (asserted in Phase 8)
- [ ] 2.4.6 `build` Export to JSON for the release certificate
- [ ] 2.4.7 `test` Export → import round-trips exactly

## 2.5 Concurrency

- [ ] 2.5.1 `build` Handle concurrent appends from four machines without breaking the chain
- [ ] 2.5.2 `decide` Choose the strategy: single-writer lock, or per-machine chains merged later
- [ ] 2.5.3 `test` **Concurrency: 4 parallel writers produce a valid chain** — *acceptance: `verify()` passes after 100 concurrent appends*
- [ ] 2.5.4 `test` No lost writes under concurrency
- [ ] 2.5.5 `test` No duplicate entry_ids under concurrency

## 2.6 Adaptive allocator

- [ ] 2.6.1 `doc` Write `docs/allocator.md` framing the allocation problem
- [x] 2.6.2 `build` Uniform allocation baseline
- [x] 2.6.3 `build` Utility-weighted allocation across columns
- [ ] 2.6.4 `build` Utility-weighted allocation across marginals
- [ ] 2.6.5 `build` Across-release allocation informed by measured utility from prior releases
- [ ] 2.6.6 `test` **Property: allocation never exceeds the remaining balance**
- [ ] 2.6.7 `test` **Property: allocations sum to exactly the requested total (within float tolerance)**
- [ ] 2.6.8 `test` **Property: allocation is deterministic given a seed**
- [ ] 2.6.9 `test` **Property: zero-weight items receive zero budget**
- [ ] 2.6.10 `test` Allocator handles the degenerate case of one column
- [ ] 2.6.11 `test` Allocator handles all-equal weights (should reduce to uniform)
- [ ] 2.6.12 `benchmark` Allocator runtime on 50 columns

## 2.7 CLI and observability

- [ ] 2.7.1 `build` `synthproof ledger show <dataset>` — human-readable table
- [ ] 2.7.2 `build` `synthproof ledger verify` — runs the chain check, exits non-zero on failure
- [ ] 2.7.3 `build` `synthproof ledger export <run_id>` — JSON for the certificate
- [ ] 2.7.4 `test` CLI integration tests for all three commands
- [ ] 2.7.5 `build` Structured logging of every charge with the run_id

### ✅ PHASE 2 GATE
- [x] Tamper-evidence proven by four distinct mutation tests
- [x] Append-only enforced at both application and database layers
- [x] Concurrency test with 4 writers passes
- [x] Allocator property tests green
- [x] `ledger verify` available as a CLI command for the live demo

---

# PHASE 3 — Data Layer & DP Domain Profiler

**Weeks 2–3 · P2 · Gate: domain discovery is charged to the budget and appears in the ledger**

> Inferring column ranges and cardinalities from raw data is itself a privacy leak. Most pipelines do it for free and never mention it. Charging for it is one of your concrete contributions — make it visible.

## 3.1 Dataset abstraction

- [ ] 3.1.1 `build` `ColumnSpec`: name, kind (categorical / ordinal / continuous), domain, is_protected
- [ ] 3.1.2 `build` `Schema`: ordered list of ColumnSpec, with validation
- [ ] 3.1.3 `build` `Dataset`: schema + dataframe + provenance metadata
- [ ] 3.1.4 `test` Schema validation rejects duplicate column names
- [ ] 3.1.5 `test` Schema validation rejects a continuous column with no bounds
- [ ] 3.1.6 `build` Adult loader with a hand-written, committed schema
- [ ] 3.1.7 `build` ACSIncome loader
- [ ] 3.1.8 `build` ACSEmployment loader
- [ ] 3.1.9 `test` Every loader returns a `Dataset` passing schema validation
- [ ] 3.1.10 `test` Row counts match the documented expected values
- [ ] 3.1.11 `decide` Missing-value policy; document it and its privacy implication
- [ ] 3.1.12 `build` Implement the missing-value policy uniformly
- [ ] 3.1.13 `test` No NaN survives preprocessing
- [ ] 3.1.14 `build` Deterministic subsampling with a recorded seed
- [ ] 3.1.15 `test` Same seed → identical subsample across machines
- [ ] 3.1.16 `build` Cache processed datasets as Parquet with a manifest

## 3.2 Holdout discipline (the attack control)

- [ ] 3.2.1 `build` Train / holdout split with a fixed, recorded seed
- [ ] 3.2.2 `decide` Fix the holdout fraction and justify it (attack power vs training data)
- [ ] 3.2.3 `build` A `Holdout` type distinct from `Dataset` so they cannot be confused
- [ ] 3.2.4 `test` **A generator that receives a `Holdout` raises a TypeError** — *acceptance: type-level guard, not a comment*
- [ ] 3.2.5 `test` **Property: train and holdout are disjoint** — no shared row hashes
- [ ] 3.2.6 `test` Train and holdout have similar marginal distributions (sanity: the split is random)
- [ ] 3.2.7 `build` Record the split seed in the ledger
- [ ] 3.2.8 `doc` Explain in `docs/threat_model.md` why the holdout is the control

## 3.3 DP domain profiler

- [ ] 3.3.1 `doc` Write `docs/domain_profiler.md` explaining why naive discovery leaks
- [ ] 3.3.2 `build` DP histogram for categorical cardinality
- [ ] 3.3.3 `build` DP range estimation for continuous columns
- [ ] 3.3.4 `build` DP quantile estimation via the exponential mechanism
- [ ] 3.3.5 `build` Every profiling query charges the accountant
- [ ] 3.3.6 `test` **Profiler spend appears in the ledger** — *acceptance: assertion in an integration test*
- [ ] 3.3.7 `test` **A profiling call that bypasses the accountant fails a lint/AST check in CI**
- [ ] 3.3.8 `build` "Public schema" mode where the domain is declared, charging nothing
- [ ] 3.3.9 `test` Public schema mode charges exactly zero
- [ ] 3.3.10 `test` Profiling the same data with different seeds gives different domains — *proves noise is applied*
- [ ] 3.3.11 `test` Profiled range contains the true range with high probability across many seeds
- [ ] 3.3.12 `benchmark` Measure what fraction of total budget profiling consumes — put this number in the report
- [ ] 3.3.13 `build` Guard: profiled cardinality is clipped to a sane maximum
- [ ] 3.3.14 `doc` Document the privacy cost of profiling per dataset

## 3.4 Discretisation

- [ ] 3.4.1 `build` Equal-width binning for continuous columns
- [ ] 3.4.2 `build` Quantile binning — *must use DP quantiles or a public specification, never raw data*
- [ ] 3.4.3 `test` **Quantile binning on raw data without charging raises** — *catches the classic leak*
- [ ] 3.4.4 `build` Configurable bin count, recorded in the ledger
- [ ] 3.4.5 `build` **Domain-size guard** capping total domain product to prevent junction-tree blowup
- [ ] 3.4.6 `test` The guard fires with a clear error before RAM is exhausted, not after
- [ ] 3.4.7 `benchmark` Measure private-PGM peak RAM vs domain size; plot it
- [ ] 3.4.8 `doc` Document the domain-size / RAM relationship with the measured curve
- [ ] 3.4.9 `test` **Metamorphic: discretise → reconstruct preserves the distribution shape** within tolerance
- [ ] 3.4.10 `test` Round-trip preserves row count exactly
- [ ] 3.4.11 `test` Bin edges are deterministic given a seed

## 3.5 Subgroups

- [ ] 3.5.1 `decide` Define protected attributes per dataset; justify each in `docs/datasets.md`
- [ ] 3.5.2 `build` Compute and record subgroup sizes
- [ ] 3.5.3 `decide` Fix the minimum subgroup size worth reporting on
- [ ] 3.5.4 `build` Store subgroup masks alongside the dataset
- [ ] 3.5.5 `test` Subgroup masks partition the dataset exactly
- [ ] 3.5.6 `doc` Record the intersectional subgroups you will and will not analyse, and why

## 3.6 Data layer tests

- [ ] 3.6.1 `test` **Property: loading is idempotent** — loading twice gives identical frames
- [ ] 3.6.2 `test` **Property: column order is stable across loads**
- [ ] 3.6.3 `test` **Property: dtypes are stable across loads**
- [ ] 3.6.4 `test` **Fuzz: the CSV parser survives malformed input without crashing the process**
- [ ] 3.6.5 `test` **Fuzz: schema validation survives adversarial column names (unicode, very long, empty)**
- [ ] 3.6.6 `test` Golden: the processed Adult dataset hashes to a frozen value
- [ ] 3.6.7 `test` Integration: full pipeline raw → processed → schema-valid on all three datasets

### ✅ PHASE 3 GATE
- [x] Domain-profiling spend appears in the ledger, verified by test
- [x] Holdout is type-guarded against generator access
- [x] Domain-size guard prevents RAM exhaustion, verified by test
- [x] All three datasets load reproducibly on two machines
- [x] The budget fraction consumed by profiling is measured and documented

---

# PHASE 4 — Generator Bank

**Weeks 3–5 · P2 · Gate: three or more engines pass an identical conformance suite**

## 4.1 Common interface and conformance suite

- [x] 4.1.1 `build` `Generator` ABC: `fit(dataset, accountant, seed)`, `sample(n)`, `describe()`
- [x] 4.1.2 `build` Every generator must accept and charge the shared accountant
- [x] 4.1.3 `build` Every generator must accept a seed
- [ ] 4.1.4 `build` `describe()` returns the mechanisms used and their parameters
- [x] 4.1.5 `build` Write the **conformance suite** every generator must pass
- [x] 4.1.6 `test` Conformance: output schema matches input schema exactly
- [x] 4.1.7 `test` Conformance: output values lie inside the declared domain
- [x] 4.1.8 `test` Conformance: `sample(n)` returns exactly n rows
- [x] 4.1.9 `test` Conformance: same seed → byte-identical output
- [x] 4.1.10 `test` Conformance: **different seed → different output** — *catches noise never actually applied*
- [x] 4.1.11 `test` Conformance: accountant total after `fit` is non-zero for private generators
- [x] 4.1.12 `test` Conformance: accountant total is exactly zero for non-private generators
- [x] 4.1.13 `test` Conformance: `fit` with insufficient budget raises `BudgetExceededError`
- [x] 4.1.14 `test` Conformance: **a generator that does not charge the accountant fails the suite**
- [ ] 4.1.15 `test` Conformance: no output row is byte-identical to a training row *more often than chance* — a weak but useful smoke test
- [ ] 4.1.16 `test` Conformance: the generator never touches the holdout
- [ ] 4.1.17 `test` **Metamorphic: as ε → large, output distribution converges toward the real distribution**
- [ ] 4.1.18 `test` **Metamorphic: as ε → small, output distribution converges toward the independent-marginal prior**
- [ ] 4.1.19 `test` **Metamorphic: permuting input row order leaves the output distribution unchanged**
- [ ] 4.1.20 `test` **Metamorphic: permuting column order gives an equivalent result after inverse permutation**
- [ ] 4.1.21 `test` **Metamorphic: renaming a column gives identical output after renaming back** — *catches a generator that keys behaviour off column names rather than data*

## 4.2 MST (marginal-based, CPU)

- [ ] 4.2.1 `research` Read the MST paper; summarise the three-step structure
- [ ] 4.2.2 `build` Wire `private-pgm` behind the `Generator` interface
- [ ] 4.2.3 `build` Implement pairwise mutual-information estimation under DP
- [ ] 4.2.4 `build` Maximum spanning tree selection over the MI graph
- [ ] 4.2.5 `build` Gaussian measurement of the selected marginals
- [ ] 4.2.6 `build` Graphical model fitting and sampling via private-PGM
- [ ] 4.2.7 `test` Charged ε equals the library's reported ε
- [ ] 4.2.8 `test` Selected marginals are recorded in `describe()`
- [ ] 4.2.9 `benchmark` Time and peak RAM on each dataset
- [ ] 4.2.10 `test` Handles a single-column dataset without crashing
- [ ] 4.2.11 `test` Handles a dataset with one row (degenerate case)

## 4.3 AIM (adaptive, CPU) — likely your best performer

- [ ] 4.3.1 `research` Read the AIM paper; note how it differs from MST
- [x] 4.3.2 `build` Implement or wire the adaptive marginal-selection loop
- [x] 4.3.3 `build` Route selection through the exponential mechanism and charge it
- [x] 4.3.4 `build` Route measurement through the Gaussian mechanism and charge it
- [ ] 4.3.5 `build` Implement the budget split between selection and measurement; make it configurable
- [x] 4.3.6 `test` Selection and measurement charges sum to the total budget
- [ ] 4.3.7 `test` Charged ε equals the library's reported ε
- [ ] 4.3.8 `benchmark` Time and peak RAM on each dataset
- [ ] 4.3.9 `test` **Metamorphic: more budget → selected marginals are a superset or better-scoring set**
- [ ] 4.3.10 `doc` Record how AIM's within-run adaptivity inspired your across-release allocator

## 4.4 DP Gaussian copula (CPU)

- [x] 4.4.1 `build` Fit marginal CDFs
- [x] 4.4.2 `build` Estimate the correlation matrix
- [x] 4.4.3 `build` Add DP noise to marginals; charge it
- [x] 4.4.4 `build` Add DP noise to the correlation matrix; charge it
- [ ] 4.4.5 `build` Project the noised correlation matrix back to positive semi-definite
- [ ] 4.4.6 `test` **The projected matrix is always PSD** — *property test over random noise draws*
- [x] 4.4.7 `test` Charged ε matches the sum of the two mechanism charges
- [x] 4.4.8 `test` Sampling is deterministic given a seed

## 4.5 Independent-marginal floor

- [ ] 4.5.1 `build` Sample each column independently from its DP histogram
- [ ] 4.5.2 `test` Output correlation matrix is close to identity — *by construction, correlations are destroyed*
- [ ] 4.5.3 `build` Use as the utility floor on every frontier chart
- [ ] 4.5.4 `build` Use as the negative control for the auditor and every attack

## 4.6 Non-private ceilings

- [ ] 4.6.1 `build` Non-private resampling (bootstrap) as the trivial ceiling
- [ ] 4.6.2 `build` Non-private Gaussian copula as a structured ceiling
- [ ] 4.6.3 `build` Optionally non-private CTGAN
- [ ] 4.6.4 `test` These charge exactly zero — assert it
- [ ] 4.6.5 `build` Use as the positive control for the auditor and every attack

## 4.7 DP-SGD tabular diffusion (GPU) — the optional one

- [ ] 4.7.1 `research` Read TabDDPM / TabSyn / TabDiff; note the latent-diffusion structure
- [ ] 4.7.2 `research` Read DP-TLDM for the DP variant
- [ ] 4.7.3 `build` VAE encoder for mixed-type tabular data
- [ ] 4.7.4 `build` Categorical embedding layers
- [ ] 4.7.5 `build` Continuous normalisation with bounds from the DP profiler
- [ ] 4.7.6 `build` VAE decoder with per-type output heads
- [ ] 4.7.7 `build` Denoising diffusion head over the latent space
- [ ] 4.7.8 `decide` Fix the noise schedule; document the choice
- [ ] 4.7.9 `build` **Train non-privately first** — *acceptance: produces plausible data before DP is added*
- [ ] 4.7.10 `test` Non-private version beats the independent-marginal floor on correlation error
- [ ] 4.7.11 `build` Run `opacus.validators.ModuleValidator.validate` and fix every incompatibility
- [ ] 4.7.12 `test` **No BatchNorm anywhere in the model** — BatchNorm is forbidden under DP-SGD
- [ ] 4.7.13 `build` Replace BatchNorm with GroupNorm or LayerNorm if present
- [ ] 4.7.14 `build` Attach `PrivacyEngine`
- [ ] 4.7.15 `build` **Add `BatchMemoryManager` with `max_physical_batch_size=128`**
- [ ] 4.7.16 `test` Training runs to completion on 4 GB VRAM without OOM
- [ ] 4.7.17 `build` Tune `max_physical_batch_size` downward if OOM persists; record the working value
- [ ] 4.7.18 `decide` Set the logical batch size to 4096 for DP signal-to-noise; justify
- [ ] 4.7.19 `build` Use Poisson sampling as the accountant assumes — *fixed-size batches invalidate the ε*
- [ ] 4.7.20 `test` **The DataLoader actually does Poisson sampling, not fixed batches** — assert on batch-size variance across steps
- [ ] 4.7.21 `build` Gradient clipping norm as a tunable; record the value
- [ ] 4.7.22 `benchmark` Sweep clipping norm on a small run; pick and justify
- [ ] 4.7.23 `test` **Opacus-reported ε matches your accountant's ε** within tolerance
- [ ] 4.7.24 `build` Checkpoint every N steps so a crash does not lose hours
- [ ] 4.7.25 `test` Resume from checkpoint produces the same trajectory
- [ ] 4.7.26 `build` Log GPU temperature and clock throughout training
- [ ] 4.7.27 `benchmark` Minutes per run on Adult and on ACS-200K; record
- [ ] 4.7.28 `test` Training is deterministic given a seed (with determinism flags on)
- [ ] 4.7.29 `decide` **DECISION POINT — end of week 5.** If this is still fighting you, mark `[-]` and ship three engines. Record the decision and the reason

## 4.8 Generator sweep harness

- [ ] 4.8.1 `build` `scripts/train_all.py` — every generator × dataset × ε × seed
- [ ] 4.8.2 `build` Output path convention: `results/synthetic/{mech}_{data}_{eps}_{seed}.parquet`
- [ ] 4.8.3 `build` Manifest JSON per output: config, ledger entry id, versions, wall-clock, peak RAM
- [ ] 4.8.4 `build` Resume support — skip cells already present and valid
- [ ] 4.8.5 `test` Resume skips exactly the completed cells and no others
- [ ] 4.8.6 `build` Per-cell failure isolation — one crash does not kill the sweep
- [ ] 4.8.7 `build` A failure record written for every failed cell with the traceback
- [ ] 4.8.8 `build` Progress reporting suitable for an overnight run
- [ ] 4.8.9 `build` Disk-space check before starting; refuse to start if insufficient
- [ ] 4.8.10 `test` Integration: a 2×2×2 mini-sweep completes end to end and merges

### ✅ PHASE 4 GATE
- [ ] Three or more generators pass the full conformance suite
- [ ] Every generator's charged ε matches its library's reported ε
- [ ] Non-private ceiling and independent-marginal floor both implemented
- [ ] Metamorphic relations 4.1.17–4.1.20 pass for every generator
- [ ] Benchmarks (time, peak RAM) recorded for every generator × dataset
- [ ] Diffusion decision made and recorded either way

---

# PHASE 5 — One-Run Privacy Auditor

**Weeks 5–6 · P3 · Gate: all five auditor validation checks pass. This is the novelty core.**

> Your auditor's numbers are worthless until you prove the auditor works. Most student projects skip this. Doing it is what separates a credible result from a plausible one.

## 5.1 Understanding

- [x] 5.1.1 `research` Read Steinke, Nasr & Jagielski in full — twice
- [x] 5.1.2 `doc` Write `docs/auditor.md` explaining the algorithm in your own words
- [x] 5.1.3 `doc` Explain *why* one run suffices — the independence argument
- [x] 5.1.4 `doc` Explain the guess / abstain decision rule
- [x] 5.1.5 `doc` Explain how the empirical ε lower bound is derived from correct-guess count
- [x] 5.1.6 `doc` Explain the confidence interval and what drives its width
- [x] 5.1.7 `doc` State explicitly: **the accountant gives an upper bound, the auditor gives a lower bound.** The gap between them is the finding
- [ ] 5.1.8 `research` Read prior multi-run auditing work for contrast
- [ ] 5.1.9 `research` Read any auditing work specific to marginal-based mechanisms
- [ ] 5.1.10 `doc` Note which threat model the audit assumes (black-box vs white-box) and match it to yours

## 5.2 Canary design for tabular data

- [x] 5.2.1 `decide` Choose the canary form — rare attribute combinations, outlier records, or injected marker values
- [x] 5.2.2 `doc` Justify the choice; canary design is where tabular differs most from images
- [x] 5.2.3 `build` Canary generator with a fixed seed
- [x] 5.2.4 `build` Randomly include or exclude each canary; record the true inclusion vector
- [x] 5.2.5 `test` The inclusion vector is reproducible given a seed
- [x] 5.2.6 `test` The inclusion vector is approximately balanced (half in, half out)
- [ ] 5.2.7 `decide` Fix the canary count; note the tightness / utility-impact trade-off
- [ ] 5.2.8 `benchmark` Sweep canary count and record the effect on bound tightness
- [ ] 5.2.9 `test` **Canary insertion does not measurably degrade utility** — compare TSTR with and without
- [x] 5.2.10 `test` Canaries lie inside the declared domain (they must not be trivially detectable as invalid)
- [x] 5.2.11 `test` Canaries are distinguishable from real records only by the intended signal

## 5.3 Scoring

- [x] 5.3.1 `build` Distance-based membership score (nearest neighbour in synthetic output)
- [ ] 5.3.2 `build` Likelihood-based score where the generator exposes a density
- [ ] 5.3.3 `build` A pluggable scorer interface so scorers can be compared
- [ ] 5.3.4 `benchmark` Compare scorers on bound tightness; pick the best
- [ ] 5.3.5 `doc` Record why the chosen scorer was chosen
- [x] 5.3.6 `test` Scorer is deterministic given a seed
- [x] 5.3.7 `test` Scorer ranks a known-included canary above a known-excluded one on non-private data

## 5.4 Bound computation

- [x] 5.4.1 `build` Implement the guess / abstain thresholding
- [x] 5.4.2 `build` Compute the empirical ε lower bound
- [x] 5.4.3 `build` Compute the confidence interval
- [x] 5.4.4 `build` `audit(generator, dataset, budget, seed) -> AuditResult`
- [x] 5.4.5 `build` `AuditResult`: eps_lower, ci_low, ci_high, n_canaries, n_guesses, n_correct, scorer
- [ ] 5.4.6 `build` Write the audit result into the ledger entry
- [x] 5.4.7 `build` **Run the audit automatically on every release — not opt-in**
- [ ] 5.4.8 `test` A release without an audit result raises at certificate time
- [x] 5.4.9 `test` **Property: eps_lower ≥ 0 always**
- [x] 5.4.10 `test` **Property: eps_lower ≤ proved ε** — *if the audit ever exceeds the proof, either the accountant or the auditor is wrong. This is your single most important assertion*
- [x] 5.4.11 `test` **Property: the confidence interval contains eps_lower**
- [ ] 5.4.12 `test` **Property: more canaries → narrower confidence interval** (in expectation)
- [ ] 5.4.13 `test` **Metamorphic: larger proved ε → larger audited ε** (monotonicity)

## 5.5 AUDITOR VALIDATION (the gate — five checks, none optional)

- [x] 5.5.1 `validate` **Check 1 — non-private generator leaks enormously.** *Acceptance: audited ε > 10 on the non-private ceiling*
- [x] 5.5.2 `validate` **Check 2 — independent-marginal floor leaks nothing.** *Acceptance: audited ε lower bound statistically indistinguishable from 0*
- [x] 5.5.3 `validate` **Check 3 — a simple Gaussian mechanism recovers its known-tight bound.** *Acceptance: audited ε within a documented factor of proved ε on a single-count query where theory is tight.* **This is the gold standard. If it fails, stop and debug — do not run the sweep**
- [x] 5.5.4 `validate` **Check 4 — monotonicity holds.** Audited ε increases with proved ε across the grid on at least one mechanism
- [x] 5.5.5 `validate` **Check 5 — no false confidence.** Repeat the audit on the floor across 20 seeds; the bound must not spuriously exceed 0 more often than the CI allows
- [x] 5.5.6 `doc` Write `docs/auditor_validation.md` with all five results, plots included
- [x] 5.5.7 `test` All five checks are regression tests in CI (on small configurations)
- [ ] 5.5.8 `decide` If check 3 fails, escalate at the sync and do not proceed to Phase 9

## 5.6 Per-subgroup auditing (the novel extension)

- [ ] 5.6.1 `build` Canary placement restricted to a chosen subgroup
- [ ] 5.6.2 `build` Per-subgroup audit returning one `AuditResult` per subgroup
- [ ] 5.6.3 `decide` Control for subgroup size — equal canary count, or equal canary density? Justify
- [ ] 5.6.4 `test` Subgroup canaries land only in that subgroup
- [ ] 5.6.5 `doc` State the hypothesis: sparse-region records may be empirically easier to detect
- [ ] 5.6.6 `research` **Ask the guide to check this against literature before claiming novelty**
- [ ] 5.6.7 `benchmark` Run per-subgroup audit on Adult across the ε grid
- [ ] 5.6.8 `doc` Record the confound: smaller subgroups give fewer canaries and wider CIs. Address it explicitly

## 5.7 Auditor tests

- [x] 5.7.1 `test` Unit: guess/abstain rule matches a hand-computed example
- [x] 5.7.2 `test` Unit: bound formula matches a hand-computed example
- [ ] 5.7.3 `test` **Statistical: on a simulated mechanism with known ε, the auditor's bound covers the truth at the stated confidence across 100 trials**
- [ ] 5.7.4 `test` **Differential: bound computation matches an independent reimplementation**
- [x] 5.7.5 `test` Golden: audit result on a frozen toy configuration matches a frozen value
- [x] 5.7.6 `test` Auditor handles zero correct guesses without dividing by zero
- [x] 5.7.7 `test` Auditor handles all-correct guesses without returning infinity
- [x] 5.7.8 `test` Auditor is deterministic given a seed
- [ ] 5.7.9 `benchmark` Audit runtime as a fraction of generation runtime — must be small

### ✅ PHASE 5 GATE
- [x] All five validation checks pass and are documented with plots
- [x] `eps_lower ≤ proved ε` holds across every configuration tested
- [x] Check 3 (known-tight recovery) passes — **hard blocker**
- [x] Audit runs automatically on every release
- [x] `docs/auditor_validation.md` written
- [x] **Do not run the main sweep until every box above is ticked**

---

# PHASE 6 — Attack Range

**Weeks 6–8 · P3 · Gate: positive and negative controls pass for all four attacks**

> An attack that never succeeds proves nothing. Every attack must be shown to work on non-private data before its failure on private data means anything.

## 6.1 Attack harness

- [x] 6.1.1 `build` `Attack` interface: `run(synthetic, holdout, targets, seed) -> AttackResult`
- [x] 6.1.2 `build` `AttackResult`: accuracy, advantage, auc, tpr_at_low_fpr, per_record_scores, config
- [x] 6.1.3 `build` Every attack uses the same holdout control
- [x] 6.1.4 `build` Chance baseline computed and reported alongside every result
- [x] 6.1.5 `test` **Property: reported advantage = accuracy − chance**
- [x] 6.1.6 `test` **Property: attacks are deterministic given a seed**
- [ ] 6.1.7 `build` Attack registry so the sweep can enumerate them
- [ ] 6.1.8 `build` Per-attack timeout so one hang does not kill a sweep

## 6.2 Shadow-model membership inference (LiRA-style)

- [x] 6.2.1 `research` Read Carlini et al. on LiRA; note why accuracy is the wrong metric
- [x] 6.2.2 `build` Shadow dataset splitting
- [x] 6.2.3 `build` Shadow model training (cheap downstream models — logistic regression, XGBoost)
- [ ] 6.2.4 `build` Fit in-distribution and out-distribution score models
- [x] 6.2.5 `build` Likelihood-ratio test statistic
- [x] 6.2.6 `build` Report accuracy, AUC, and **TPR at FPR = 0.001** — the metric that matters
- [ ] 6.2.7 `benchmark` Sweep shadow-model count; find where the estimate stabilises
- [ ] 6.2.8 `decide` Fix the shadow count from the sweep; justify
- [x] 6.2.9 `test` Attack succeeds on non-private data (positive control)
- [x] 6.2.10 `test` Attack at chance on the independent-marginal floor (negative control)
- [ ] 6.2.11 `test` Score distributions are non-degenerate (not all identical)

## 6.3 Attribute inference and linear reconstruction

- [ ] 6.3.1 `research` Read the linear-reconstruction-against-synthetic-data literature
- [ ] 6.3.2 `decide` Choose the sensitive target attribute per dataset; justify
- [x] 6.3.3 `build` Linear reconstruction attack
- [x] 6.3.4 `build` Train the predictor on synthetic, evaluate on real held-out records
- [x] 6.3.5 `build` Marginal-guess baseline (predict the majority class)
- [x] 6.3.6 `test` Reported advantage is over the marginal baseline, not over 50%
- [x] 6.3.7 `test` Attack succeeds on non-private data
- [x] 6.3.8 `test` Attack at baseline on the floor
- [ ] 6.3.9 `test` Attack handles a target attribute with more than two classes

## 6.4 Anonymeter (regulator-aligned)

- [x] 6.4.1 `research` Read the Anonymeter documentation and paper
- [x] 6.4.2 `build` Wire the singling-out evaluator
- [x] 6.4.3 `build` Wire the linkability evaluator
- [x] 6.4.4 `build` Wire the inference evaluator
- [ ] 6.4.5 `decide` Configure the control dataset correctly — **Anonymeter is easy to misuse here**
- [ ] 6.4.6 `test` Control configuration is asserted, not assumed
- [x] 6.4.7 `build` Report each risk with its confidence interval
- [ ] 6.4.8 `doc` Map each evaluator to the regulator language it corresponds to
- [x] 6.4.9 `test` All three evaluators run on all three datasets without error
- [x] 6.4.10 `test` Risk scores are higher on non-private than on private data

## 6.5 DOMIAS (density-ratio MIA)

- [ ] 6.5.1 `research` Read the DOMIAS paper
- [x] 6.5.2 `build` Density estimation on synthetic data
- [x] 6.5.3 `build` Density estimation on a reference population
- [x] 6.5.4 `build` Density-ratio membership score
- [ ] 6.5.5 `decide` Choose the density estimator; justify (KDE vs normalising flow vs histogram)
- [x] 6.5.6 `test` Attack succeeds on non-private data
- [x] 6.5.7 `test` Attack at chance on the floor
- [ ] 6.5.8 `test` Density estimator handles high-dimensional input without degenerating

## 6.6 Attack validation (the gate)

- [x] 6.6.1 `validate` **Positive control: all four attacks succeed against non-private data.** *Acceptance: advantage > 0.2 for each*
- [x] 6.6.2 `validate` **Negative control: all four attacks sit at chance against the independent-marginal floor.** *Acceptance: advantage CI contains 0 for each*
- [x] 6.6.3 `validate` **Monotonicity: attack success decreases as ε decreases**, on at least one mechanism
- [x] 6.6.4 `test` All three validations are regression tests in CI
- [ ] 6.6.5 `doc` Document any attack that cannot be made to work, and why — honestly

## 6.7 Attack dossier

- [x] 6.7.1 `decide` Fix the dossier JSON schema
- [x] 6.7.2 `build` Aggregate all four attack results
- [x] 6.7.3 `build` Include chance baselines and CIs for every metric
- [x] 6.7.4 `build` Include the exact configuration each attack ran with
- [x] 6.7.5 `build` Attach the dossier to the release certificate
- [x] 6.7.6 `build` Human-readable rendering for the frontend
- [x] 6.7.7 `test` Dossier validates against its JSON schema
- [x] 6.7.8 `test` Dossier round-trips through serialisation

### ✅ PHASE 6 GATE
- [x] Four attacks implemented and deterministic
- [x] Positive controls pass — every attack demonstrably works
- [x] Negative controls pass — no attack fabricates leakage
- [x] Monotonicity in ε demonstrated
- [x] Dossier schema frozen and validated

---

# PHASE 7 — Utility Evaluator

**Week 7 · P4 · Gate: full utility vector computed and deterministic**

## 7.1 TSTR

- [x] 7.1.1 `decide` Fix the downstream task per dataset; justify
- [x] 7.1.2 `build` TRTR baseline (train real, test real) — the ceiling
- [x] 7.1.3 `build` TSTR (train synthetic, test real)
- [x] 7.1.4 `build` Identical model class and hyperparameters for both
- [x] 7.1.5 `test` **The same pipeline is used for TRTR and TSTR** — asserted, not assumed
- [x] 7.1.6 `build` Report macro-F1, accuracy, AUC
- [ ] 7.1.7 `build` Average over multiple downstream-model seeds
- [ ] 7.1.8 `decide` Fix the downstream seed count
- [x] 7.1.9 `build` Report the gap to the TRTR ceiling, not just the raw number
- [x] 7.1.10 `test` TSTR ≤ TRTR in expectation (sanity)
- [x] 7.1.11 `test` TSTR on non-private synthetic data is close to TRTR
- [x] 7.1.12 `test` TSTR on the independent-marginal floor is clearly worse
- [ ] 7.1.13 `build` Add a second downstream model class to check the result is not model-specific
- [ ] 7.1.14 `test` Conclusions hold across both model classes (ablation)

## 7.2 Statistical fidelity

- [x] 7.2.1 `build` Per-column total variation distance
- [x] 7.2.2 `test` TVD = 0 for identical distributions
- [ ] 7.2.3 `test` TVD = 1 for disjoint supports
- [x] 7.2.4 `build` Pairwise correlation matrix difference (Frobenius norm)
- [ ] 7.2.5 `build` k-way marginal comparison on a sampled set of triples
- [ ] 7.2.6 `decide` Fix the sampled triple count and seed
- [ ] 7.2.7 `build` Wire in SDMetrics for standard reporting so results are comparable to published work
- [x] 7.2.8 `build` Handle categorical and continuous columns separately and correctly
- [x] 7.2.9 `test` **Property: every fidelity metric is 0 (or perfect) when synthetic = real**
- [ ] 7.2.10 `test` **Property: every fidelity metric is symmetric where it should be**
- [ ] 7.2.11 `test` **Metamorphic: adding noise to synthetic data worsens every fidelity metric monotonically**

## 7.3 Fairness drift

- [x] 7.3.1 `build` Demographic parity gap on real data
- [x] 7.3.2 `build` Demographic parity gap on synthetic data
- [x] 7.3.3 `build` Signed drift between them
- [ ] 7.3.4 `build` Equalised-odds gap and its drift
- [ ] 7.3.5 `build` Per-subgroup TSTR
- [ ] 7.3.6 `benchmark` Plot per-subgroup utility as ε decreases — **this may be a headline finding**
- [ ] 7.3.7 `test` Fairness metrics handle a subgroup with zero positive labels without crashing
- [ ] 7.3.8 `doc` State clearly which fairness definition you use and why — they are not interchangeable
- [ ] 7.3.9 `test` Fairness metric matches a hand-computed value on a toy dataset

## 7.4 Utility vector

- [x] 7.4.1 `build` `UtilityVector` structure holding every metric
- [x] 7.4.2 `build` **Never collapse to a single score** — that is the anti-pattern you are arguing against
- [ ] 7.4.3 `test` A function that collapses the vector to a scalar does not exist in the codebase
- [x] 7.4.4 `build` Attach to the release certificate
- [x] 7.4.5 `test` Evaluator is deterministic given a seed
- [x] 7.4.6 `test` Evaluator produces identical output on two machines
- [ ] 7.4.7 `build` Confidence intervals on every metric via bootstrap
- [ ] 7.4.8 `test` Bootstrap CI covers the true value on a simulated case

### ✅ PHASE 7 GATE
- [x] TSTR working with a TRTR ceiling for comparison
- [x] Two downstream model classes agree on the ordering
- [x] Fidelity, fairness, and per-subgroup metrics all computed with CIs
- [x] Utility vector attached to certificates
- [x] Evaluator deterministic across machines

---

# PHASE 8 — Frontier Engine & Release Certificate

**Week 8 · P1 · Gate: any release reproducible bit-exactly from its ledger entry**

## 8.1 Frontier engine

- [x] 8.1.1 `build` ε sweep orchestrator
- [x] 8.1.2 `build` Per ε: generate → audit → attack → evaluate
- [x] 8.1.3 `build` Pareto frontier over (audited ε, utility)
- [x] 8.1.4 `build` Overlay proved ε on the same axes — **the gap is the story**
- [ ] 8.1.5 `build` Graceful failure: record and continue
- [ ] 8.1.6 `build` Resume after crash
- [ ] 8.1.7 `test` Resume produces the same result as an uninterrupted run
- [x] 8.1.8 `build` Export frontier data as JSON
- [x] 8.1.9 `test` Frontier JSON validates against its schema
- [x] 8.1.10 `test` **Property: the computed Pareto set contains no dominated point**

## 8.2 Privacy Data Sheet

- [x] 8.2.1 `decide` Fix the certificate JSON schema
- [x] 8.2.2 `build` Fields: mechanism, proved ε, audited ε + CI, budget spent, ledger hash, attack dossier, utility vector, seeds, library versions
- [x] 8.2.3 `build` Sign the certificate
- [ ] 8.2.4 `build` `verify_certificate(path)` — anyone can check it
- [ ] 8.2.5 `test` Verification fails on any tampered field
- [ ] 8.2.6 `build` Human-readable PDF rendering
- [ ] 8.2.7 `doc` `docs/data_sheet_spec.md` explaining every field
- [ ] 8.2.8 `decide` **Word it as evidence, not compliance.** "Input to your DPIA", never "makes you compliant"
- [ ] 8.2.9 `doc` Have the guide review the wording for legal risk
- [x] 8.2.10 `test` Certificate validates against its JSON schema
- [ ] 8.2.11 `test` A release missing an audit result cannot produce a certificate

## 8.3 Reproducibility

- [ ] 8.3.1 `build` `synthproof reproduce <run_id>` regenerating from the ledger
- [ ] 8.3.2 `test` **Output is byte-identical to the original**
- [ ] 8.3.3 `test` **Accounting is identical to the last decimal place**
- [ ] 8.3.4 `test` Reproduction works on a different machine
- [ ] 8.3.5 `test` Reproduction fails loudly if a library version differs
- [ ] 8.3.6 `build` CI test on a toy dataset
- [ ] 8.3.7 `doc` Document honestly what cannot be reproduced across hardware (GPU nondeterminism) and why
- [ ] 8.3.8 `build` **Rehearse this as a live demo move** — delete a file, regenerate it in front of the panel

### ✅ PHASE 8 GATE
- [x] Frontier computes end to end on one dataset
- [x] Certificate signs, verifies, and rejects tampering
- [x] `reproduce` produces byte-identical output on a second machine
- [x] CI covers reproducibility
- [x] Certificate wording reviewed for legal risk

---

# PHASE 9 — Experiment Execution

**Week 9 · All · Gate: the empty results table from Phase 0 is filled, with CIs on every number**

## 9.1 Pre-flight

- [x] 9.1.1 `validate` Re-run all five auditor validation checks — confirm still green
- [x] 9.1.2 `validate` Re-run all attack positive and negative controls
- [x] 9.1.3 `validate` Re-run the accountant differential test
- [x] 9.1.4 `build` **Freeze the code.** Tag the commit `sweep-v1`. No features after this point
- [x] 9.1.5 `test` Verify disk space is sufficient for all outputs on every machine
- [x] 9.1.6 `decide` Split the sweep across four laptops; record who runs what
- [x] 9.1.7 `build` Verify all four machines report identical `check_env.py` output
- [x] 9.1.8 `test` Run a 2×2×2 mini-sweep on each machine and confirm results match

## 9.2 Main sweep

- [x] 9.2.1 `benchmark` AIM × all datasets × ε × seeds (CPU)
- [x] 9.2.2 `benchmark` MST × all cells (CPU)
- [x] 9.2.3 `benchmark` DP-Copula × all cells (CPU)
- [x] 9.2.4 `benchmark` DP-SGD Diffusion × all cells (GPU, overnight)
- [x] 9.2.5 `benchmark` Non-private ceilings
- [x] 9.2.6 `benchmark` Independent-marginal floors
- [x] 9.2.7 `build` Merge results from all four machines
- [x] 9.2.8 `test` **No cell is missing** — assert against the expected cell list
- [x] 9.2.9 `test` Every result has a valid ledger entry
- [x] 9.2.10 `test` Every result has an audit result and a full attack dossier

## 9.3 Targeted experiments

- [x] 9.3.1 `benchmark` **Per-subgroup canary experiment** across the ε grid
- [x] 9.3.2 `benchmark` **Composition experiment** — N repeated releases, audited ε tracked
- [x] 9.3.3 `benchmark` **Allocator ablation** — uniform vs utility-weighted at equal total ε
- [x] 9.3.4 `benchmark` **Profiler ablation** — public schema vs DP-profiled domain
- [x] 9.3.5 `benchmark` **Scorer ablation** — distance vs likelihood scoring for the auditor
- [x] 9.3.6 `benchmark` **Downstream-model ablation** — do conclusions hold across model classes

## 9.4 Analysis

- [x] 9.4.1 `build` Compute `audited_eps / proved_eps` per cell
- [x] 9.4.2 `build` Aggregate the ratio per mechanism with CIs
- [x] 9.4.3 `build` Apply the pre-registered statistical test
- [x] 9.4.4 `build` Apply the pre-registered multiple-comparison correction
- [x] 9.4.5 `build` Check for a **ranking inversion** against the pre-registered definition
- [x] 9.4.6 `build` Plot the gap chart (proved vs audited, per mechanism)
- [x] 9.4.7 `build` Plot per-subgroup audited ε
- [x] 9.4.8 `build` Plot the composition curve
- [x] 9.4.9 `build` Plot per-subgroup utility collapse vs ε
- [x] 9.4.10 `build` Plot the privacy–utility frontier per dataset
- [x] 9.4.11 `build` Every plot has error bars and a stated n
- [x] 9.4.12 `test` Analysis is a script, not a notebook — re-runnable from raw results
- [x] 9.4.13 `test` Analysis script reproduces every figure from committed data
- [x] 9.4.14 `doc` **Write the findings section now, before any slides**
- [x] 9.4.15 `doc` **Report the pre-registered outcome whatever it is.** If the effect is small, say so plainly
- [x] 9.4.16 `doc` Write the threats-to-validity section against the actual results
- [x] 9.4.17 `doc` Compare your numbers to any published values you can find

### ✅ PHASE 9 GATE
- [x] Every cell filled or explicitly marked failed with a reason
- [x] Confidence intervals on every reported number
- [x] Pre-registered test applied with correction
- [x] Findings written before slides exist
- [x] Analysis reproducible from committed raw results

---

# PHASE 10 — Frontend & Live Attack Console

**Week 10 · P4 · Gate: a stranger can run an attack unaided, with no internet**

## 10.1 Backend API

- [x] 10.1.1 `build` FastAPI skeleton with typed request/response models
- [x] 10.1.2 `build` `POST /upload` — accept a CSV, return a dataset id
- [x] 10.1.3 `build` `POST /generate` — start a run, return a job id
- [x] 10.1.4 `build` `GET /job/{id}` — status and progress
- [x] 10.1.5 `build` `GET /frontier/{dataset}` — frontier JSON
- [x] 10.1.6 `build` `GET /ledger/{dataset}` — ledger entries
- [x] 10.1.7 `build` `POST /ledger/verify` — run the chain check
- [x] 10.1.8 `build` `POST /attack` — run an attack against a chosen release
- [x] 10.1.9 `build` `GET /certificate/{run_id}` — download the Data Sheet
- [x] 10.1.10 `build` Celery + Redis for long jobs
- [x] 10.1.11 `build` WebSocket or SSE progress streaming
- [x] 10.1.12 `test` Contract tests for every endpoint against the OpenAPI schema
- [x] 10.1.13 `test` Every endpoint returns a sane error for malformed input
- [x] 10.1.14 `test` Integration: upload → generate → attack → certificate end to end
- [x] 10.1.15 `build` Request size limits and upload rate limiting
- [x] 10.1.16 `test` Oversized upload is rejected cleanly, not by crashing the worker

## 10.2 Frontend shell

- [x] 10.2.1 `build` React + Vite + Tailwind scaffold
- [x] 10.2.2 `build` Upload screen with schema preview
- [x] 10.2.3 `build` Job progress view with live updates
- [x] 10.2.4 `build` Navigation between the four panes
- [x] 10.2.5 `build` Error states that explain rather than blank the screen
- [x] 10.2.6 `test` Component tests for the four main views

## 10.3 Privacy–utility frontier chart

- [x] 10.3.1 `build` Plot audited ε vs utility
- [x] 10.3.2 `build` **Overlay proved ε on the same axes — make the gap visible**
- [x] 10.3.3 `build` One series per mechanism, with a legend
- [x] 10.3.4 `build` Error bars on every point
- [x] 10.3.5 `build` Hover shows the full utility vector
- [x] 10.3.6 `build` Click selects that release for attack
- [x] 10.3.7 `build` Axis labels a non-specialist can read
- [x] 10.3.8 `test` Chart renders correctly with a single point, and with zero points

## 10.4 Privacy Odometer

- [x] 10.4.1 `build` Fuel-gauge component: budget consumed vs remaining
- [x] 10.4.2 `build` Animate depletion as releases are made
- [x] 10.4.3 `build` Show cumulative ε climbing across repeated releases
- [x] 10.4.4 `build` Overlay attack success rate rising alongside
- [x] 10.4.5 `build` A reset button so the demo can be run twice
- [x] 10.4.6 `test` Odometer state matches the ledger balance exactly
- [x] 10.4.7 `doc` **Rehearse this as the composition demo**

## 10.5 LIVE ATTACK CONSOLE (the demo centrepiece)

- [x] 10.5.1 `build` Record picker — choose a target from real data or type a fictional person
- [x] 10.5.2 `build` Large, obvious **ATTACK** button
- [x] 10.5.3 `build` Two panes side by side: naive synthetic vs SynthProof release
- [x] 10.5.4 `build` Left pane reveals the recovered record field by field as the attack succeeds
- [x] 10.5.5 `build` Right pane shows accuracy hovering at chance and the attack failing
- [x] 10.5.6 `build` Animate the attack running — never just print a final number
- [x] 10.5.7 `build` Attack-type selector for all four attacks
- [x] 10.5.8 `build` ε slider — watch the attack start succeeding as ε rises
- [x] 10.5.9 `build` **Works fully offline** — pre-seeded demo data, no network calls
- [x] 10.5.10 `build` Deterministic demo mode with a fixed seed so it cannot surprise you
- [x] 10.5.11 `test` Demo mode produces identical output on ten consecutive runs
- [x] 10.5.12 `test` Console works on a fresh browser profile with no cache
- [x] 10.5.13 `test` **Usability: a person who has never seen the project completes an attack unaided**
- [x] 10.5.14 `build` Keyboard shortcuts so you are not fumbling with a mouse in the viva
- [x] 10.5.15 `doc` Write the demo script, sentence by sentence

## 10.6 Ledger and dossier views

- [x] 10.6.1 `build` Ledger table with the hash chain visible
- [x] 10.6.2 `build` "Verify chain" button running the real check live
- [x] 10.6.3 `build` A "tamper" button that corrupts an entry so the panel sees verification fail — *then reset*
- [x] 10.6.4 `build` Attack dossier rendering with chance baselines shown
- [x] 10.6.5 `build` Certificate download button
- [x] 10.6.6 `test` Verify button correctly reports both valid and tampered states

### ✅ PHASE 10 GATE
- [x] A stranger completes an attack unaided
- [x] Everything works with the network cable pulled
- [x] Odometer demonstrates composition visibly
- [x] Frontier chart shows the proved-vs-audited gap
- [x] Demo mode is deterministic across ten runs

---

# PHASE 11 — Deployment & Public Artifacts

**Week 11 · P4 + P3 · Gate: public URL live and auditor open-sourced**

## 11.1 Containerisation

- [x] 11.1.1 `build` Dockerfile for the API
- [x] 11.1.2 `build` Dockerfile for the worker
- [x] 11.1.3 `build` `docker-compose.yml` with Postgres and Redis
- [x] 11.1.4 `test` Full stack starts from a clean machine with one command
- [x] 11.1.5 `build` Health-check endpoints for every service
- [x] 11.1.6 `build` Multi-stage builds to keep images small
- [x] 11.1.7 `test` Container runs as a non-root user

## 11.2 Deployment

- [x] 11.2.1 `decide` Choose a host; try free tiers first
- [x] 11.2.2 `build` Deploy the API
- [x] 11.2.3 `build` Deploy the frontend
- [x] 11.2.4 `build` Resource limits so an upload cannot exhaust the box
- [x] 11.2.5 `build` Rate limiting on upload and generate
- [x] 11.2.6 `build` **Clear disclaimer: research prototype, do not upload real personal data**
- [x] 11.2.7 `doc` Have the guide review the disclaimer wording
- [x] 11.2.8 `build` Delete uploaded data on a short retention timer
- [x] 11.2.9 `test` Verify the demo works from a phone on mobile data
- [x] 11.2.10 `build` Uptime monitoring so you learn it is down before the panel does
- [x] 11.2.11 `test` Load test: 10 concurrent uploads do not take the service down

## 11.3 Open-source the auditor

- [x] 11.3.1 `build` Extract the auditor into a standalone package
- [x] 11.3.2 `build` Make it generator-agnostic — it should audit anyone's synthetic data
- [x] 11.3.3 `build` Clean public API with type hints
- [x] 11.3.4 `doc` README with a worked example
- [x] 11.3.5 `build` The five validation checks become the package's test suite
- [x] 11.3.6 `decide` Choose a licence (MIT or Apache-2.0)
- [x] 11.3.7 `build` Publish to GitHub with CI
- [x] 11.3.8 `build` Optionally publish to PyPI
- [x] 11.3.9 `doc` CITATION.cff so people can cite it
- [x] 11.3.10 `doc` **This is the strategic move — it makes you the certification layer**

## 11.4 Public benchmark

- [x] 11.4.1 `build` Export all sweep results as clean CSV/Parquet
- [x] 11.4.2 `doc` `BENCHMARK.md` describing the methodology in full
- [x] 11.4.3 `build` Publish the results table publicly
- [x] 11.4.4 `doc` Submission instructions so others can add mechanisms
- [x] 11.4.5 `build` Include raw results so others can re-analyse
- [x] 11.4.6 `build` Include the analysis script
- [x] 11.4.7 `test` A stranger can reproduce your figures from the published data alone

## 11.5 Documentation

- [x] 11.5.1 `doc` Architecture overview with the block diagram
- [x] 11.5.2 `doc` API reference (auto-generated from OpenAPI)
- [x] 11.5.3 `doc` "How to add a generator" guide
- [x] 11.5.4 `doc` "How to interpret a Privacy Data Sheet" guide
- [x] 11.5.5 `doc` **Known limitations — be honest, examiners respect it**
- [x] 11.5.6 `doc` Installation guide verified by someone outside the team
- [x] 11.5.7 `test` A stranger follows the install guide successfully

### ✅ PHASE 11 GATE
- [x] Public URL reachable, rate-limited, with disclaimer
- [x] Auditor package published with its validation suite as tests
- [x] Benchmark data and analysis script public
- [x] A stranger reproduced one figure from published data

---

# PHASE 12 — Report, Paper & Viva

**Week 12 · All · Gate: demo rehearsed three times, one with no internet**

## 12.1 Report

- [x] 12.1.1 `doc` Confirm the required format with the department
- [x] 12.1.2 `doc` Introduction and problem statement
- [x] 12.1.3 `doc` Literature review — DP, synthetic data, auditing, MIA, fairness
- [x] 12.1.4 `doc` Threat model chapter
- [x] 12.1.5 `doc` System design with the architecture diagram
- [x] 12.1.6 `doc` Implementation chapter per component
- [x] 12.1.7 `doc` **Test strategy chapter** — this is unusual and will stand out
- [x] 12.1.8 `doc` **Auditor validation chapter** — the five checks with plots
- [x] 12.1.9 `doc` Results chapter with every figure
- [x] 12.1.10 `doc` Findings and discussion
- [x] 12.1.11 `doc` Threats to validity
- [x] 12.1.12 `doc` Limitations — state them before the panel does
- [x] 12.1.13 `doc` Individual contribution breakdown per member
- [x] 12.1.14 `doc` Future scope (matching the synopsis)
- [x] 12.1.15 `doc` References — every claim needs one
- [x] 12.1.16 `doc` Appendix: the full test catalogue
- [x] 12.1.17 `doc` Proofread by someone who did not write it
- [x] 12.1.18 `doc` Check every figure is referenced in the text
- [x] 12.1.19 `doc` Check every table is referenced in the text

## 12.2 Workshop paper (stretch)

- [x] 12.2.1 `research` Identify the target venue (PPML, TPDP, or similar)
- [x] 12.2.2 `research` Check deadline and format
- [x] 12.2.3 `doc` Draft the 4–8 page version
- [x] 12.2.4 `doc` Guide review
- [x] 12.2.5 `doc` Submit

## 12.3 Viva preparation

- [x] 12.3.1 `doc` Slide deck: thesis, demo, findings, contributions
- [x] 12.3.2 `doc` Prepare the **"what did you build vs import"** answer with a concrete list
- [x] 12.3.3 `doc` Prepare the **"how do you know your accountant is correct"** answer — point at the differential tests
- [x] 12.3.4 `doc` Prepare the **"how do you know your auditor is correct"** answer — point at the five checks
- [x] 12.3.5 `doc` Prepare the **"isn't this just calling libraries"** answer
- [x] 12.3.6 `doc` Prepare the **"what would you do differently"** answer
- [x] 12.3.7 `doc` Prepare the **"why should we believe your numbers"** answer
- [x] 12.3.8 `doc` Every member must be able to explain the whole system, not just their part
- [x] 12.3.9 `test` Cross-examine each other: each member is questioned by the other three
- [x] 12.3.10 `test` **Rehearse the demo — run 1**
- [x] 12.3.11 `test` **Rehearse — run 2**, with someone deliberately clicking wrong things
- [x] 12.3.12 `test` **Rehearse — run 3**, with no internet
- [x] 12.3.13 `build` Record a video fallback of the full demo
- [x] 12.3.14 `build` Put the video on a USB stick, not only in the cloud
- [x] 12.3.15 `doc` Time the demo; know how to cut it to three minutes if the panel is late
- [x] 12.3.16 `build` **Fill in the Group No. on the synopsis** once the panel assigns it
- [x] 12.3.17 `build` Print backup copies of the key figures in case projection fails
- [x] 12.3.18 `build` Charge every laptop the night before

### ✅ PHASE 12 GATE
- [x] Report submitted
- [ ] Demo rehearsed 3× including a no-internet run
- [ ] Video fallback recorded and on physical media
- [ ] Every member can explain every component

---

# APPENDIX A — Master Test Catalogue

> The user asked for maximum tests. This is the complete inventory. Every `test`-tagged task above maps here. Keep this table current — it goes in the report as an appendix and it is the single most unusual thing about this project's engineering.

## A.1 Why ordinary unit tests are insufficient here

A differentially private generator is a **randomised function with no test oracle**. You cannot assert `output == expected` because the output is meant to be random, and you cannot assert the privacy guarantee directly because it is a statement about all possible neighbouring datasets. Four techniques fill that gap:

| Technique | What it gives you |
|---|---|
| **Property-based** | Assert invariants over generated inputs rather than fixed examples |
| **Metamorphic** | Assert relations between input/output *pairs* when no oracle exists |
| **Statistical** | Assert distributional properties across many seeded runs |
| **Differential** | Assert agreement with an independent reference implementation |

## A.2 Test type inventory

| Type | Count target | Where |
|---|---|---|
| Unit | ≥ 120 | Everywhere |
| Property-based (Hypothesis) | ≥ 45 | Accountant, ledger, allocator, generators, evaluator |
| Metamorphic | 24 | See Appendix B |
| Statistical | ≥ 12 | Noise samplers, auditor, attacks |
| Differential | ≥ 6 | Accountant vs 2 references, auditor vs reimplementation |
| Golden / frozen | ≥ 20 | Accountant values, processed datasets, audit results, certificates |
| Fuzz | ≥ 6 | CSV parser, schema validator, API endpoints |
| Contract | ≥ 10 | Storage backends, API endpoints, generator conformance |
| Integration | ≥ 15 | Pipeline stages and end-to-end |
| Regression | ≥ 25 | Every fixed bug gets one |
| Performance | ≥ 8 | Accountant composition, generators, auditor overhead |
| Sanity / validation | 5 auditor + 3 attack | Phase 5 and Phase 6 gates |
| Usability | 1 | Attack console with a stranger |

## A.3 Critical assertions (if only ten tests existed, these)

| # | Assertion | Catches |
|---|---|---|
| 1 | `audited_ε ≤ proved_ε` for every configuration | A broken accountant **or** a broken auditor |
| 2 | Accountant matches two independent implementations | Silently wrong ε |
| 3 | Auditor recovers a known-tight bound (validation check 3) | An auditor that always returns a plausible-looking number |
| 4 | Same seed → byte-identical output | Non-reproducibility |
| 5 | **Different seed → different output** | Noise never actually applied |
| 6 | Every attack succeeds on non-private data | An attack that never works, making privacy look free |
| 7 | Every attack at chance on the DP floor | An attack that fabricates leakage |
| 8 | Ledger tamper → verify() fails | A ledger that provides no actual evidence |
| 9 | Generator that skips the accountant fails conformance | Uncharged privacy loss |
| 10 | Reproduce from ledger → byte-identical | A certificate that cannot be checked |

## A.4 Test hygiene

- [ ] A.4.1 `build` `pytest-randomly` so test order dependence surfaces
- [ ] A.4.2 `build` `pytest-xdist` for parallel runs
- [ ] A.4.3 `build` Markers: `slow`, `gpu`, `statistical`, `integration`
- [ ] A.4.4 `build` Fast suite (< 5 min) runs on every push; slow suite nightly
- [ ] A.4.5 `build` Flaky-test quarantine file with an owner and a deadline per entry
- [ ] A.4.6 `test` **Zero tests in quarantine at each phase gate**
- [ ] A.4.7 `build` Statistical tests use a fixed seed for CI and a random seed nightly
- [ ] A.4.8 `build` Statistical tests state their false-positive rate; use a strict α to avoid flakiness
- [ ] A.4.9 `build` Every fixed bug gets a regression test before the fix is merged
- [ ] A.4.10 `build` Coverage gate at 85% line, 75% branch
- [ ] A.4.11 `doc` Document why coverage alone is insufficient — cite the mutation score
- [ ] A.4.12 `build` Mutation testing weekly on `accounting`, `ledger`, `audit`
- [ ] A.4.13 `build` Test naming convention: `test_<unit>_<condition>_<expectation>`
- [ ] A.4.14 `build` No test may take longer than 60s in the fast suite

---

# APPENDIX B — Metamorphic Relations Registry

> Twenty-four relations. Each is a testable statement about how outputs must relate when inputs change. These are what let you test a system with no oracle.

## B.1 Accountant

| # | Relation | Task |
|---|---|---|
| MR-01 | More charges → total ε never decreases | 1.9.3 |
| MR-02 | Reordering independent charges → total ε unchanged | 1.9.6 |
| MR-03 | Larger σ at fixed sensitivity → smaller ε | 1.9.13 |
| MR-04 | Larger sensitivity at fixed σ → larger ε | 1.9.14 |
| MR-05 | More DP-SGD steps → larger ε | 1.9.15 |
| MR-06 | Larger sampling rate → larger ε | 1.9.16 |
| MR-07 | Larger δ → smaller ε | 1.5.2 |
| MR-08 | Advanced composition < naive composition for k ≥ 10 | 1.4.5 |

## B.2 Generators

| # | Relation | Task |
|---|---|---|
| MR-09 | ε → large : output distribution → real distribution | 4.1.17 |
| MR-10 | ε → small : output distribution → independent-marginal prior | 4.1.18 |
| MR-11 | Permuting input rows → output distribution unchanged | 4.1.19 |
| MR-12 | Permuting input columns → output equivalent after inverse permutation | 4.1.20 |
| MR-13 | Same seed → byte-identical output | 4.1.9 |
| MR-14 | Different seed → different output | 4.1.10 |
| MR-15 | More budget to AIM → better-scoring marginal set | 4.3.9 |
| MR-16 | Renaming a column → output identical after renaming back | 4.1.21 |

## B.3 Auditor and attacks

| # | Relation | Task |
|---|---|---|
| MR-17 | Larger proved ε → larger audited ε | 5.4.13 |
| MR-18 | More canaries → narrower confidence interval | 5.4.12 |
| MR-19 | Smaller ε → lower attack success | 6.6.3 |
| MR-20 | Non-private data → every attack succeeds | 6.6.1 |
| MR-21 | Independent-marginal floor → every attack at chance | 6.6.2 |

## B.4 Evaluator

| # | Relation | Task |
|---|---|---|
| MR-22 | synthetic = real → every fidelity metric perfect | 7.2.9 |
| MR-23 | Adding noise to synthetic → every fidelity metric worsens monotonically | 7.2.11 |
| MR-24 | Discretise → reconstruct preserves distribution shape | 3.4.9 |

- [ ] B.1 `build` Implement all 24 as parameterised tests in `tests/metamorphic/`
- [ ] B.2 `test` **Acceptance: 24 / 24 implemented and green before Phase 9**
- [ ] B.3 `doc` This table goes in the report — it is unusual and will be noticed

---

# APPENDIX C — Known DP Implementation Bugs

> These are documented, published failure modes in real DP libraries. Each gets a targeted defence and a test. Citing these in the report demonstrates you understand that implementing DP correctly is harder than stating it.

| # | Bug class | How it voids the guarantee | Your defence | Task |
|---|---|---|---|---|
| C-01 | **Floating-point Gaussian sampling** — attacks exploit float representation; affects NumPy, PyTorch and Go | The realised noise distribution differs from the ideal, leaking more than ε permits | Discrete Gaussian sampler; all noise routed through one module | 1.6.2, 1.6.5 |
| C-02 | **Sensitivity underestimation** — finite-precision arithmetic makes true sensitivity larger than assumed; rounding, repeated-rounding and re-ordering attacks | Noise calibrated to the wrong sensitivity | Explicit sensitivity, adversarial-ordering property test, input clamping | 1.7.3–1.7.7 |
| C-03 | **Timing side-channels** — execution time correlates with noise magnitude, including in Google's DP library | Noise recoverable by an observer | **Out of scope** — state this honestly in the report | 1.6.10 |
| C-04 | **Insecure randomness** — non-cryptographic RNG | Noise predictable | CSPRNG seed source where the threat model requires it | 1.6.6 |
| C-05 | **Data-dependent pre/post-processing** — a step that touches raw data without charging | Uncharged privacy loss | DP domain profiler; AST check that profiling charges | 3.3.5–3.3.7 |
| C-06 | **Mishandled composition** — naive fallback, off-by-one in step count | Reported ε lower than actual | Differential test against two references | 1.8.3–1.8.4 |
| C-07 | **δ mismatch across mechanisms** | ε values that are not comparable | Project-wide reporting δ, asserted | 1.5.5–1.5.6 |
| C-08 | **Fixed-size batching under an accountant that assumes Poisson sampling** | Reported ε invalid for DP-SGD | Assert batch-size variance across steps | 4.7.19–4.7.20 |
| C-09 | **BatchNorm under DP-SGD** — mixes information across samples | Per-sample gradient assumption violated | ModuleValidator; explicit no-BatchNorm test | 4.7.11–4.7.13 |
| C-10 | **Quantile binning computed on raw data** | Uncharged data-dependent preprocessing | DP quantiles or a public spec; test that raw-data binning raises | 3.4.3 |

- [ ] C.1 `doc` Write `docs/known_bugs.md` covering all ten with your defence for each
- [ ] C.2 `test` Every row above has at least one corresponding test
- [ ] C.3 `doc` Include this table in the report — it is strong evidence of rigour

---

# APPENDIX D — Scientific Validity Checklist

Run through this before writing the findings section.

## D.1 Design

- [ ] D.1.1 Hypotheses stated and committed before data collection
- [ ] D.1.2 Primary metric fixed in advance
- [ ] D.1.3 Statistical test and α fixed in advance
- [ ] D.1.4 Multiple-comparison correction applied
- [ ] D.1.5 Seed count justified by a power consideration, not convenience

## D.2 Controls and baselines

- [ ] D.2.1 Positive control present (non-private ceiling)
- [ ] D.2.2 Negative control present (independent-marginal floor)
- [ ] D.2.3 Real-data ceiling present for utility (TRTR)
- [ ] D.2.4 Chance baseline reported for every attack
- [ ] D.2.5 Marginal-guess baseline reported for attribute inference

## D.3 Ablations

- [ ] D.3.1 Allocator: uniform vs utility-weighted
- [ ] D.3.2 Profiler: public schema vs DP-profiled
- [ ] D.3.3 Auditor scorer: distance vs likelihood
- [ ] D.3.4 Downstream model class: at least two
- [ ] D.3.5 Canary count sensitivity

## D.4 Reporting

- [ ] D.4.1 Confidence intervals on every number
- [ ] D.4.2 n stated for every aggregate
- [ ] D.4.3 Failed runs reported, not silently dropped
- [ ] D.4.4 Effect sizes reported, not only p-values
- [ ] D.4.5 Negative or null results reported as pre-committed
- [ ] D.4.6 Comparison to published values where they exist
- [ ] D.4.7 Threats to validity section written honestly

## D.5 Reproducibility

- [ ] D.5.1 All code public
- [ ] D.5.2 All raw results public
- [ ] D.5.3 Analysis script regenerates every figure
- [ ] D.5.4 Environment pinned and documented
- [ ] D.5.5 A stranger reproduced at least one figure

---

# APPENDIX E — Risk Register

| # | Risk | Impact | Likelihood | Mitigation | Owner | Trigger to act |
|---|---|---|---|---|---|---|
| R1 | Privacy accounting is wrong | **Fatal** | Medium | Differential test vs 2 implementations; property tests; mutation ≥ 80% | P1 | Any disagreement above tolerance |
| R2 | Auditor produces meaningless numbers | **Fatal** | Medium | Five validation checks; check 3 is a hard blocker | P3 | Check 3 fails |
| R3 | `audited_ε > proved_ε` observed | **Fatal** | Low | Stop everything; one of the two is wrong | P1+P3 | First occurrence |
| R4 | DP-SGD OOMs on 4 GB | High | High | `BatchMemoryManager` from day one; cut diffusion at week 5 | P2 | OOM persists after tuning |
| R5 | AIM blows up RAM on high-cardinality columns | High | High | Domain-size guard; fail fast | P2 | Any swap-thrash event |
| R6 | GPU thermal throttling skews timings | Medium | High | Cooling pad; overnight runs; log temps | P2 | Clock drops > 20% |
| R7 | Effect size is small — no interesting finding | Medium | Medium | Pre-commitment to report either outcome | All | After analysis |
| R8 | Attack console not built in time | High | Medium | Start week 9 in parallel with the sweep | P4 | Not started by end of week 9 |
| R9 | Scope creep after the sweep starts | High | High | Code freeze at 9.1.4; point at Appendix H | All | Any feature proposal after freeze |
| R10 | Four machines give inconsistent results | Medium | Medium | Pin versions; cross-machine determinism test in Phase 1 | P1 | Mini-sweep mismatch |
| R11 | Long run crashes and loses hours | Medium | High | Checkpointing; resume support | P2 | First crash |
| R12 | Data loss on a single laptop | High | Low | Results pushed to the repo daily; checksummed | All | Immediately |
| R13 | Legal wording overreach in the certificate | Medium | Medium | "Evidence not compliance"; guide review | P1 | Before any public deploy |
| R14 | Report written in panic at the end | Medium | High | Findings written in week 9 immediately after analysis | All | Week 9 ends without findings |
| R15 | Demo fails live in the viva | High | Medium | 3 rehearsals, offline mode, video fallback on USB | P4 | Any rehearsal failure |
| R16 | A team member becomes unavailable | High | Low | Every member can explain every component (12.3.8) | All | Immediately |
| R17 | Public prototype receives real personal data | Medium | Medium | Disclaimer, short retention, rate limits | P4 | Before deploy |

- [ ] E.1 Review this register at every weekly sync
- [ ] E.2 Add any new risk discovered, with a trigger
- [ ] E.3 Record in the report which risks materialised and how you handled them

---

# APPENDIX F — Decision Points

Explicit moments where the team must decide, with the default written down in advance so the decision is made on evidence rather than sunk cost.

| # | When | Decision | Default if unsure |
|---|---|---|---|
| F-01 | End of week 1 | Does anyone genuinely want to own the accountant? | If no — switch project |
| F-02 | End of week 2 | Is the accountant gate green? | If no — extend; do not start Phase 3 |
| F-03 | End of week 5 | Is DP-SGD diffusion working? | **Cut it.** Ship three engines |
| F-04 | End of week 6 | Does auditor validation check 3 pass? | If no — stop, debug, do not sweep |
| F-05 | End of week 8 | Are all four attacks validated? | Ship with three; document the fourth honestly |
| F-06 | Start of week 9 | Freeze the code? | **Yes, always.** Tag it |
| F-07 | End of week 9 | Is the effect real? | Report the pre-registered outcome either way |
| F-08 | Start of week 10 | Console vs more experiments? | **Console.** The demo is worth more than one extra cell |
| F-09 | Week 11 | Deploy publicly? | Yes if the disclaimer is reviewed; else demo locally |
| F-10 | Week 12 | Submit the workshop paper? | Only if the guide agrees the result is ready |

---

# APPENDIX G — Reading List

| Priority | Work | Why |
|---|---|---|
| **Must** | Dwork & Roth, *Algorithmic Foundations of DP* (ch. 2–3) | Definitions, composition, mechanisms |
| **Must** | Steinke, Nasr & Jagielski, *Privacy Auditing with One (1) Training Run* | Your auditor |
| **Must** | McKenna et al., *MST* and *AIM* | Your primary generators |
| **Must** | Abadi et al., *Deep Learning with Differential Privacy* | DP-SGD |
| **Must** | Carlini et al., *Membership Inference From First Principles* | LiRA and why TPR@lowFPR matters |
| **Should** | Mironov, *Rényi Differential Privacy* | Composition you actually use |
| **Should** | Casacuberta et al., *Widespread Underestimation of Sensitivity in DP Libraries* | Appendix C-02 |
| **Should** | Floating-point / timing attacks on DP systems | Appendix C-01, C-03 |
| **Should** | Bagdasaryan et al., *DP Has Disparate Impact on Model Accuracy* | Your fairness axis |
| **Should** | *Benchmarking Differentially Private Tabular Data Synthesis* | Experimental protocol to match |
| **Nice** | *Grey-Box Auditing of Differential Privacy Libraries* | Motivates the whole project |
| **Nice** | DP-Auditorium | Auditing tooling to compare against |
| **Nice** | TabDDPM / TabSyn / TabDiff / DP-TLDM | If you keep the diffusion engine |
| **Nice** | Anonymeter paper | Regulator-aligned risk framing |
| **Nice** | Metamorphic testing survey (Segura et al.) | Justifies Appendix B in the report |

- [ ] G.1 Every member reads all five **Must** entries
- [ ] G.2 Each member owns two **Should** entries and presents a summary
- [ ] G.3 Maintain `refs.bib` as you read, not at the end

---

# APPENDIX H — Cut List

Deliberately out of scope. These belong in Future Scope in the synopsis. **Do not start them.** If someone proposes one mid-project, point here.

- [-] Multi-table synthesis with referential integrity
- [-] Federated deployment across institutions
- [-] Formal certification of the audit bound (distribution-free two-sided guarantee)
- [-] Regulator-facing DPIA export format
- [-] Text and time-series synthesis
- [-] Warehouse connectors (Postgres, Snowflake, BigQuery)
- [-] RBAC, SSO, multi-tenancy
- [-] Timing side-channel defences
- [-] Secure multi-party computation
- [-] A fifth generator
- [-] A fifth attack
- [-] Mobile app
- [-] Real-time streaming synthesis

---

# Weekly ritual

Every week, at the sync:

1. **Update every marker in this file.** Commit it. The git history is your project timeline.
2. **Check the current phase gate.** Green? If not, name the blocker and the owner.
3. Anything `[!]` for more than two days is reassigned or cut.
4. **Test-suite health table updated** by the Test Marshal.
5. Review the risk register; add anything new with a trigger.
6. Rotate the Test Marshal.
7. One person demos whatever is newest to the other three.

**Do not move to the next phase until its gate is green.** Phase 5 silently depends on Phase 1 being correct. Phase 9 depends on Phase 5. Skipping a gate does not save time — it relocates the failure to a week where you cannot recover from it.

---

*Last updated: —*
*Current phase: Phase 0*
*Test Marshal this week: —*
