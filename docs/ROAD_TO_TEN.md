# Road to Ten — execution tracker

Live status of the 19-day plan that takes this project from the 2026-09-12 deep scan (7.4/10)
to every gate green. **This file is the source of truth for what is done and what is not.**

Baseline commit: `eac2e54` · branch `audit-fixes-and-acs` · scan date 2026-09-12

> **Rule for this file:** a task moves to DONE only when its acceptance criterion has been
> *executed* and passed, and the command output is recorded. "I wrote the code" is not done.
> This is the same rule the claims checker enforces on prose, applied to the plan itself.

---

## Status summary

| Phase | Tasks | Done | Remaining |
|---|---:|---:|---:|
| P0 — Green the gates | 3 | **3** | 0 ✅ |
| P1 — Every artifact works | 6 | **6** | 0 ✅ |
| P2 — Honesty ledger to zero | 6 | **6** | 0 ✅ |
| P3 — Harden the engineering | 6 | **5** | 1 |
| P4 — Close the science gaps | 4 | 0 | 4 |
| P5 — Consolidate and release | 5 | 0 | 5 |
| P6 — Viva readiness | 3 | 0 | 3 |
| **Total** | **33** | **21** | **12** |

## Gate status

| Gate | Command | Status |
|---|---|---|
| lint | `make lint` | ✅ ruff 0, black 0 |
| reproduce | `python -m scripts.reproduce` | ✅ exit 0 |
| claims (thesis) | `python scripts/check_thesis_claims.py` | ✅ clean |
| claims (repo-wide) | `python scripts/check_thesis_claims.py --all` | ✅ **0 across 75 files** (was 73) — now the CI step |
| tests | `make test` | ✅ **782 pass, 1 skip, 92%** (8m04s) · `make test-fast` 762 in **1m32s** |
| types | `mypy` | ✅ **0 errors**, now a blocking CI step (was 79, ungated) |
| console types | `npx tsc --noEmit` | ✅ clean |
| console tests | `npm test` | ✅ **28 pass, 3 files** (was 10/1) |
| e2e | `cd web && npm run test:e2e` | ✅ **10 specs** — 9 gate every push (17s), the browser-driven synthesis is `@slow` and runs weekly |
| **CI pipeline** | `gh run list` | ✅ **FULLY GREEN** on 3.11/3.12/3.13 — first green run since ≥2026-08-26 |
| SAST | `bandit -c pyproject.toml -r synthproof/ scripts/ -ll` | ✅ 0 medium+ |
| deps (py) | `pip-audit --skip-editable` | ✅ clean in declared closure |
| deps (npm prod) | `npm audit --omit=dev` | ✅ 0 vulnerabilities |
| capsule | open `demo_capsules/*.html` | ✅ verifies; tamper → red; no-crypto → amber |

---

## P0 — Green the gates · ~3 h

| # | Task | Status | Evidence |
|---|---|---|---|
| 0.1 | Clear 74 ruff errors | ✅ **DONE** | `68d8186` · ruff 0, black 0. 33 auto-fixed, 10 real lines wrapped, 4 dead bindings removed, 27 template E501s per-file-ignored (verified all inside the f-string, lines 103–494) |
| 0.2 | Regenerate the reproducibility manifest | ✅ **DONE** | `1e9105b` · exit 0. Diff read first: 2 path strings, 0 numeric changes. Full `--update` re-run reproduced every hash across **Linux 3.11.15 → Windows 3.11.4** |
| 0.3 | Put both honesty gates into CI | ✅ **DONE** | `04fb41a` · claims + citations + reproduce are CI steps; black now blocking; stale "94%" coverage comment corrected to 92% |

**Gate 0:** ✅ **HELD** (2026-09-12, local). Verified explicitly, one command each:
`ruff 0 · black 0 · claims 0 · citations 0 · reproduce 0 · CLI demo smoke 0`.
Still to confirm on a real push — the branch has not been pushed.

## P1 — Make every shipped artifact work · ~6 h

| # | Task | Status | Evidence |
|---|---|---|---|
| 1.1 | Restore the missing `try {`, regenerate both capsules | ✅ **DONE** | `d66bad1` · `node --check` passes on both; badge resolves to a real verdict |
| 1.2 | Kill the green-tick verification bypass | ✅ **DONE** | `d66bad1` · browser-verified 4 states: genuine→green, ε 1.0→0.001→**red**, Ed25519-unsupported→amber, no-WebCrypto→amber. `grep -c 'Proof Format Verified'` = 0 |
| 1.3 | Single-source the verifier | ✅ **DONE** | `aaab786` · logic moved to `synthproof/capsule/verifier.js`; vitest reads the *same bytes off disk* (8 cases, 10→18 total); Python test pins verbatim inlining; CI parses the emitted `<script>` with node's vm and greps for the retired bypass |
| 1.4 | Fix demo presets; keep the refusal as a feature | ✅ **DONE** | `1f9498b` · all 5 presets run against the real pipeline: 4 COMPLETE, 1 REFUSES by design. Relabelled “🛑 Refusal demo (400 rows)”, amber at both render sites, hover says so |
| 1.5 | Repoint the three PDF builders | ✅ **DONE** | `a84c3aa` · all three build into the deliverables folder, no stray root PDFs. **Also found: `make defence` had been refusing to build since before `eac2e54`** — hand-typed manifest commit had gone stale; now injected at build time |
| 1.6 | Bind `make serve` to 127.0.0.1 | ✅ **DONE** | `a84c3aa` · Dockerfile keeps `0.0.0.0`, where the container is the boundary |

**Gate 1:** ⚠️ **MECHANICALLY VERIFIED, human cold-start still pending.** Every path the three
launchers resolve exists and the targets work: `run_prototype.py` prerequisites pass, both
capsules parse and verify in a browser, the pitch deck resolves through the
`02_Presentations_and_Pitches/..` fallback and has a pre-built copy behind it. What has *not*
happened is the part that matters — someone who is not the author double-clicking all three on
a machine that has never run this, saying nothing. That is still owed.

## P2 — Take the honesty ledger to zero · ~8 h

| # | Task | Status | Evidence |
|---|---|---|---|
| 2.1 | Cite MIQE 2.0 for the LoD transfer — 26 files | ✅ **DONE** | `73694d9` · 26→0. `docs/MEASUREMENT_CONVENTIONS.md` states it once; each affected doc carries an attribution |
| 2.2 | Purge the canary percentage that does not replicate | ✅ **DONE** | `73694d9` · 20→0. Docs carried a SUPERSEDED marker *and then printed the number anyway*. **Also fixed the rule**, which flagged an unrelated literature statistic — 10 regression tests pin it both ways |
| 2.3 | Stop calling the ledger `append-only` | ✅ **DONE** | `d933708` · 9→0, plus both `ledger.py` docstrings — the phrase sat untouched in the module the prose described, because the checker reads only Markdown |
| 2.4 | Un-star the retracted confound in `results/RESULTS.md` | ✅ **DONE** | `d933708` · now a replication with a selection-deleted control arm, citing the three prior papers |
| 2.5 | Close the checker's blind spot + regression tests | ✅ **DONE** | `d933708` · widened for bare assertions, pinned with the literal evading text. Also guarded 3 sources of *unfixable* false positives (questions, quoted dead claims, citation rows). Checker suite 31→55 tests |
| 2.6 | Promote the claims gate to repo-wide in CI | ✅ **DONE** | `258509a` · CI runs `--all`; 0 of 75 files violate. 5 counter-tests guard against the checker having gone blind |

**Gate 2:** ✅ **HELD.** `check_thesis_claims.py --all` exits 0 over 75 documents, and the
widened rules carry regression tests in both directions — including one that feeds the checker
a document of seven dead claims and asserts all seven are still caught.

## P3 — Harden the engineering · ~14 h

| # | Task | Status | Evidence |
|---|---|---|---|
| 3.1 | Turn on type checking | ✅ **DONE** | `6b88bee` · **79 → 0**, blocking in CI. Found a `width` property that would compute a sensitivity from a missing bound, unguarded Optionals on the audit path, and a generator contract that disagrees with its only control caller. 6 suppressions, all error-coded pandas-stubs limits |
| 3.2 | Coverage 92% → 95%, gate at 94% | ⚠️ **PARTIAL** | `allocator.py` 79%→**100%**, `api/main.py` 79%→**85%**. 24 new tests incl. all four ledger-attack branches. CI measures **92.27%** on 789 tests. Gate stays at 90 until 94 is actually met |
| 3.3 | Test the console | ✅ **DONE** | `280dde3` · 10 component tests for LedgerChain, VerifierModal, ErrorBoundary. Console suite **10 → 28**. Coverage gate still to add |
| 3.4 | Playwright end-to-end | ✅ **DONE** | `248a4b5` · 10 specs against the real FastAPI service + built bundle + real synthesis. **Found a live defect**: the audit-ceiling marker was hidden whenever the ceiling exceeded the axis scale — i.e. exactly when it matters. Also caught its own first version being vacuous (passed in 2.5s without running anything) |
| 3.5 | Split `api/main.py` | ✅ **DONE** | `9d3e7af` · 1,225 lines → 7 modules, largest 356. Behaviour verified by 776 tests + mypy + all 10 e2e specs |
| 3.6 | Fast lane under 5 min | ✅ **DONE** | `280dde3` · `make test-fast` = 762 tests in **1m32s** (target was 5 min). Four ACS files marked `slow`; CI still runs everything |

**Gate 3:** ⚠️ **MOSTLY HELD.** ruff, black, mypy, pytest, vitest, Playwright, bandit, pip-audit,
gitleaks, claims (`--all`) and reproduce all run in CI, and **all pass on 3.11/3.12/3.13**.
Two parts of the original wording are NOT met and are not being quietly dropped:
coverage is **92%**, not ≥94% (P3.2 remains partial), and the console has no coverage
threshold yet. The gate stays at 90 rather than being raised to a number the suite does not
reach.

## P4 — Close the science gaps · 7–10 days

| # | Task | Status | Evidence |
|---|---|---|---|
| 4.1 | A stronger adversary (MAMA-MIA, Golob et al. SaTML 2025) | ⬜ TODO | |
| 4.2 | A third dataset, from outside the census | ⬜ TODO | |
| 4.3 | Recover the 8–23% unspent budget | ⬜ TODO | |
| 4.4 | A Gaussian copula — OPTIONAL, cut first | ⬜ TODO | |

**Gate 4:** every published number survives `make reproduce-all`; manifest updated with the diff read first.

## P5 — Consolidate and release · ~7 h

| # | Task | Status | Evidence |
|---|---|---|---|
| 5.1 | Kill or generate the three stale planning documents | ⬜ TODO | |
| 5.2 | Rewrite the outer README; fix B.Tech vs Master's | ⬜ TODO | |
| 5.3 | One `INDEX.md`, one `archive/`; prune the pitch decks | ⬜ TODO | |
| 5.4 | Merge to `master`; tag `v1.0.0` | ⬜ TODO | |
| 5.5 | Mint a Zenodo DOI; verify `docker-compose up` on a clean machine | ⬜ TODO | |

**Gate 5:** a stranger clones `master`, follows the README, reaches a working demo without asking a question.

## P6 — Viva readiness · ~5 h

| # | Task | Status | Evidence |
|---|---|---|---|
| 6.1 | One rehearsed offline path, with a fallback | ⬜ TODO | |
| 6.2 | `CONTRIBUTIONS.md` matching what the git history shows | ⬜ TODO | |
| 6.3 | Rehearse the three questions you would least like | ⬜ TODO | |

**Gate 6:** nothing in the room is being seen for the first time.

---

## Capped aspects — not fixable by effort, documented instead

- **Novelty positioning.** Capped by the literature, not by effort. Ganev, Annamalai,
  De Cristofaro and Kulynych are ~2 years ahead and killed eight claims. The target is the
  strongest execution of the three survivors, positioned as integration. See
  `research/08_novelty_verdict.md`.
- **Contribution record.** 107 of 107 commits belong to one author; four are credited.
  Addressed by 6.2, not scored away.

## Log

| Date | Change |
|---|---|
| 2026-09-12 | Tracker created from the deep scan. 33 tasks, 0 done. |
| 2026-09-12 | **P0 complete.** `68d8186` lint · `04fb41a` CI gates · `1e9105b` manifest. Gate 0 holds locally. |
| 2026-09-12 | **P1.1 + P1.2 complete.** `d66bad1`. Capsule verifier rewritten to three outcomes; forged capsules now rejected. |
| 2026-09-13 | 🟢 **CI green again with e2e included** — 7 jobs, console job 2m07s. |
| 2026-09-13 | **The toy table is the SLOWEST path**, not the fastest: independent columns mean the attack suite finds nothing and works hardest doing it. A UI run against it was still going after 9 minutes; the 600-row HR preset finishes in ~4s. Recorded because it is counter-intuitive and cost three debugging rounds. |
| 2026-09-13 | **P3.4 + P3.5 complete.** e2e suite added (and it immediately found a hidden ceiling marker); API module split 1,225 → 7 files, none over 400 lines. |
| 2026-09-13 | **Two lessons from the split, both the same failure in different clothes — a name that LOOKS like the thing but is a copy of it:** a router binding `GLOBAL_LEDGER` by name kept using the pre-reload ledger, so a tamper was applied to one chain and verified against another; and a test patching `main.DEMO_MODE` after the guard moved to `state` silently did nothing, asserting 403 against a service that was never locked down. |
| 2026-09-12 | 🟢 **CI IS FULLY GREEN** — all 7 jobs, Python 3.11/3.12/3.13, 789 passed, 92.27%. First green run since at least 2026-08-26. |
| 2026-09-12 | **Pushed to `origin/audit-fixes-and-acs`.** Note: `on: push` watches only master/main, so this branch had never triggered CI — every run since August was a scheduled one on stale master. |
| 2026-09-12 | **Five CI failures found and fixed, four of them pre-existing:** (1) `jax` imported but undeclared — `pip install -e ".[dev]"` produced an environment that could not import the experiment module; (2) `statsmodels` likewise, so `test_equivalence.py` never collected; (3) bandit B608 on the adversarial SQL tests, a scan no local target ran; (4) gitleaks flagging the capsules' **public** key + signature; (5) mine: a mypy `python_version` pin that made 3.12/3.13 reject numpy's own stubs. |
| 2026-09-12 | **CI had never run real AIM.** `mbi` installs from git, was never in the dependency set, so every AIM test SKIPPED silently — taking ~4 points of coverage with it. The headline mechanism, the H1 result and the ablation's control arm all ran on a path CI did not touch. Now installed. |
| 2026-09-12 | **P3.1, P3.3, P3.6 complete.** mypy 79→0 and gated · console tests 10→28 · fast lane 8m04s→1m32s. `6b88bee`, `280dde3`. |
| 2026-09-12 | **Deferred from P3.1:** `BaseGenerator.fit` declares `profile`/`accountant` required, but the detection-floor controls pass None deliberately. Widening the base alone gives 14 incompatible overrides; the real fix is a per-generator decision on whether None means "control, proceed" or "error, raise". Design decision, not a typing chore. |
| 2026-09-12 | **P2 COMPLETE (6/6).** Dead claims **73 → 0** across 75 documents; CI gate promoted to `--all`. `258509a`. Four of the last ten were false positives fixed in the RULES, not the prose. |
| 2026-09-12 | **P2.1–P2.5 complete.** Repo-wide dead claims **73 → 10**. `73694d9` LoD + canary · `d933708` append-only + confound + blind spot. |
| 2026-09-12 | Full suite after P0+P1: **740 passed, 1 skipped, 91%**, 10m03s (was 738/92%/36m42s). Coverage dipped 1pt on new capsule code — P3.2 raises it. |
| 2026-09-12 | **P1 complete (6/6).** `a84c3aa` PDF paths + serve · `1f9498b` presets · `aaab786` shared verifier. |
| 2026-09-12 | Found in passing: `make defence` had been REFUSING TO BUILD since before `eac2e54` — the shipped Defence-Pack PDF could not be regenerated from its own sources. Its gate wanted a hand-typed manifest commit that had gone stale. Now injected at build time. |
| 2026-09-12 | Found in passing: `/api/ledger/tamper` claimed the ledger "guarantees non-repudiation", contradicting `ledger/signing.py`. Corrected in `68d8186`. The claims checker reads only Markdown, which is why it survived in Python — noted for P2.5. |
