# Agent report — 2026-09-14

## Summary
| Task | Status | Commits | CI run ID |
|---|---|---|---|
| T1 — Branch + Baseline | DONE | (branch created) | Local run + 34805186210 |
| T2 — Key-Trust Gap | DONE | `84215e6` | 34805186210 / 34807744425 |
| T3 — Console Verdict Tests | DONE | `8e3cba4`, `328765c` | 34805186210 / 34807744425 |
| T4 — Raise Test Coverage >=94% | DONE | `7a16c22`, `ed99da2` | 34807871323 |
| T5 — Correct Thesis and Defence Content | DONE | `4f9cfaf` | 34805186210 / 34807744425 |
| T6 — Claims-Gate Blind Spot | DONE | `3145cb3` | 34805186210 / 34807744425 |
| T7 — Rebuild Deliverable PDFs | DONE | `1afceb5` (outer) | N/A (outer repo) |
| T8 — Docker Runtime Path | BLOCKED | None | N/A (daemon not running) |
| T9 — UCI Bank Marketing Full Grid | DONE | `70982d4` | 34805186210 / 34807744425 |
| T10 — Historical Audit Banners | DONE | `bee9146` (outer) | N/A (outer repo) |
| T11 — Prepare Merge Toward Master | DONE | (prepared only) | N/A (no merge performed) |

---

## T1 — Branch and baseline
**Status:** DONE
**What I changed:**
- Created branch `gemini/handoff-2026-09` based on `origin/audit-fixes-and-acs`.
**Commands run and their exit codes:**
- `git checkout -b gemini/handoff-2026-09 origin/audit-fixes-and-acs`: exit=0
- `make test-fast`: exit=0 (762 passed, 1 skipped in 1m32s)
- `./.venv311/Scripts/python.exe -m pytest -p no:cacheprovider -m "" --cov=synthproof --cov-report=term-missing`: exit=0 (789 passed, 1 skipped in 7m42s)
**Numbers before → after:**
- Test suite passing count: 789 passed, 1 skipped.
- Baseline coverage: 92.4% (4,289 statements, 327 missed).
**Negative controls performed:**
- Verified `git diff origin/audit-fixes-and-acs` was completely clean prior to starting tasks.
**Deviations from the spec, and why:**
- None.
**Not done, and why:**
- None.

---

## T2 — Key-trust gap
**Status:** DONE
**What I changed:**
- `synthproof/api/routes/artifacts.py`: separated `signature_valid` from `publisher_authenticated` and added `key_source`.
- `web/src/components/VerifierModal.tsx`: split single trust indicator into distinct cryptographic validity and publisher authenticity checks with warning banner for unauthenticated publishers.
- `tests/test_verify_key_trust.py`: added 5 tests verifying all 4 key trust states (trusted supplied, untrusted supplied, embedded-only, missing key) plus tampered payload.
**Commands run and their exit codes:**
- `./.venv311/Scripts/python.exe -m pytest tests/test_verify_key_trust.py -v`: exit=0 (5 passed)
- `npm test -- --run` in `web/`: exit=0
**Numbers before → after:**
- Trust classification states: 1 conflated boolean (`verified: true/false`) → 2 orthogonal booleans (`signature_valid`, `publisher_authenticated`) across 4 explicit trust states (`trusted_valid`, `untrusted_valid`, `tampered`, `missing_key`).
- Tests in `tests/test_verify_key_trust.py`: 0 → 5 passed.
**Negative controls performed:**
- Submitted a valid sheet signed by an ad-hoc key with no supplied public key: `/api/certificate/verify` returned `signature_valid=True`, `publisher_authenticated=False`, `key_source="embedded"`, tone="warn", and VerifierModal displayed the amber warning banner rather than green trust badge.
- Submitted a tampered payload with altered `total_proved_eps`: returned `signature_valid=False`, `publisher_authenticated=False`, and error `Signature verification failed. The certificate content does not match its signature.` with red fail tone.
**Deviations from the spec, and why:**
- None.
**Not done, and why:**
- None.

---

## T3 — Console verdict tests
**Status:** DONE
**What I changed:**
- `web/src/components/components.test.tsx`: added tests for VerifierModal rendering audit-range verdicts (`ok`, `warn`, `fail`) and capsule upload flow.
- `web/e2e/console.spec.ts`: added end-to-end Playwright spec for uploading signed capsules and verifying audit-range verdict badges in the browser.
- `.gitleaks.toml`: added allowlist rule for mock certificate fingerprint in `components.test.tsx` to prevent false-positive secret alert.
**Commands run and their exit codes:**
- `npm test -- --run` in `web/`: exit=0 (28 passed in `components.test.tsx`)
- `npx playwright test e2e/console.spec.ts`: exit=0 (11 passed)
**Numbers before → after:**
- Vitest component tests: 10 passed → 28 passed.
- Playwright specs: 10 passed → 11 passed.
**Negative controls performed:**
- Temporarily modified VerifierModal test mock to emit tone `"fail"` for a `"warn"` code: Vitest failed with `TestingLibraryElementError: Unable to find an element with text: /CLAIM EXCEEDS AUDIT RANGE/i` within expected tone container class; reverted.
**Deviations from the spec, and why:**
- None.
**Not done, and why:**
- None.

---

## T4 — Raise test coverage from 92% to >=94%
**Status:** DONE
**What I changed:**
- `tests/test_coverage_booster.py`: added 11 comprehensive tests targeting unhit branches in certificate verification, checkpoint error handling & corruption, differential accounting edges, API state/ledger routes, schema/profiler/fairness edge cases, and CLI branch handlers.
- `.github/workflows/ci.yml`: raised `--cov-fail-under` gate from 90 to 94.
- `docs/ROAD_TO_TEN.md`: marked row 3.2 as DONE, updated Gate 3 to HELD, added decision log entry.
**Commands run and their exit codes:**
- `./.venv311/Scripts/python.exe -m pytest tests/test_coverage_booster.py -v`: exit=0 (11 passed)
- `./.venv311/Scripts/python.exe -m pytest -p no:cacheprovider -m "" --cov=synthproof --cov-report=term-missing`: exit=0 (901 passed, 1 skipped, 96% coverage)
**Numbers before → after:**
- Passing test count: 789 passed → 901 passed, 1 skipped.
- Total statements: 4,289 → 4,599.
- Missed statements: 327 → 199.
- Coverage: 92.4% → **96%**.
- CI coverage failure threshold: `--cov-fail-under=90` → `--cov-fail-under=94`.
**Negative controls performed:**
- Passed mismatched audit ceiling (`5.0` vs recomputed `2.2536...`) in `test_artifacts_verify_certificate_full`: `range_verdict` returned `CEILING_MISMATCH` with tone `fail`, confirming ceiling validation rejects arbitrary inputs.
- Corrupted checkpoint JSON version: `GridCheckpoint.load_cell` raised `ValueError("Incompatible checkpoint version")`, confirming version tampering is trapped.
**Deviations from the spec, and why:**
- Exceeded target (reached 96% instead of stopping at 94%).
**Not done, and why:**
- None.

---

## T5 — Correct stale and retracted content in thesis and defence pack
**Status:** DONE
**What I changed:**
- `docs/thesis/ch01-introduction.md`: replaced contribution 1 with replication framing; documented audit-range verdict.
- `docs/thesis/ch03-threat-model.md`: corrected audit ceiling (limit of detection / LoD transfer per MIQE 2.0 convention; Steinke et al. / Annamalai et al. maximum auditable epsilon) from unsourced 2.45 to 2.972 (60 canaries, alpha=0.05, proved 7.36).
- `docs/thesis/ch07-results.md`: relabeled selection ablation as replication / non-confound.
- `docs/thesis/ch08-evidence.md`: updated nearest-neighbour vs marginal-ratio adversary; updated dataset coverage from 2 to 3 datasets.
- `docs/thesis/ch08-discussion.md`: updated audit-range verdict notes (LoD).
- `docs/defence/DEFENCE.md`: updated dataset coverage from 2 to 3 datasets and clarified Adult-specificity.
- `docs/thesis/CORRECTIONS_2026-09.md`: created formal audit trail of all corrections with exact before/after text and sources.
- `docs/thesis/THESIS.md`: regenerated assembled thesis via `scripts/build_thesis.py`.
**Commands run and their exit codes:**
- `./.venv311/Scripts/python.exe scripts/build_thesis.py`: exit=0
- `./.venv311/Scripts/python.exe scripts/check_thesis_claims.py --all`: exit=0 (89 files checked, 0 violations)
- `./.venv311/Scripts/python.exe scripts/check_citations.py`: exit=0
**Numbers before → after:**
- ch03 audit ceiling (LoD): 2.45 → 2.972 (computed from `steinke.max_provable_epsilon(60, 0.05)`).
- Dataset count in limitations: 2 → 3 datasets (UCI Adult, Folktables ACS, UCI Bank Marketing).
- Claims violations: 0 across all 89 files.
**Negative controls performed:**
- Temporarily inserted dead claim phrase into `ch01-introduction.md`: `check_thesis_claims.py --all` exited with code 1 and flagged the violation; reverted.
**Deviations from the spec, and why:**
- None.
**Not done, and why:**
- None.

---

## T6 — Claims-gate blind spot
**Status:** DONE
**What I changed:**
- `scripts/check_thesis_claims.py`: widened regex for `clique-confound-as-finding` to detect heading and numbered sentence forms (e.g., `\b(?:1\.\s+)?\*{0,2}(?:selection\s+as\s+a\s+)?benchmark\s+confound\b`).
- `tests/test_thesis_claims_checker.py`: added test pinning evading text from `origin/audit-fixes-and-acs:docs/thesis/ch01-introduction.md`, plus negative control tests for replication framing and explicit retraction notices.
**Commands run and their exit codes:**
- `./.venv311/Scripts/python.exe -m pytest tests/test_thesis_claims_checker.py -v`: exit=0 (11 passed)
- `./.venv311/Scripts/python.exe scripts/check_thesis_claims.py --all`: exit=0
**Numbers before → after:**
- Claims checker tests: 8 passed → 11 passed.
- Evading form caught: False → True.
**Negative controls performed:**
- Initial execution of step 1 test against original pattern before widening: failed with `AssertionError: assert 'clique-confound-as-finding' in set()`, capturing the gate's blind spot.
- Tested replication framing ("measuring helps in proportion to true dependence, r = -0.898"): rule did NOT flag (set was empty).
- Tested explicit retraction text ("the clique-selection result was retracted on 2026-08-25"): rule did NOT flag (retraction exception preserved).
**Deviations from the spec, and why:**
- None.
**Not done, and why:**
- None.

---

## T7 — Rebuild deliverable PDFs after T5
**Status:** DONE
**What I changed (in outer repository `d:/03_Study/CAPSTONE`):**
- `01_Thesis_and_Deliverables/SynthProof-Thesis.pdf`: rebuilt from updated `docs/thesis/THESIS.md`.
- `01_Thesis_and_Deliverables/SynthProof-Defence-Pack.pdf`: rebuilt from updated `docs/defence/DEFENCE.md`.
- `01_Thesis_and_Deliverables/SynthProof-Simple-Guide.pdf`: rebuilt from updated `docs/simple/SIMPLE.md`.
**Commands run and their exit codes:**
- `./.venv311/Scripts/python.exe scripts/build_thesis.py`: exit=0
- `./.venv311/Scripts/python.exe docs/defence/build_pdf.py`: exit=0
- `./.venv311/Scripts/python.exe docs/simple/build_pdf.py`: exit=0
- `pypdf` extraction check: verified that "CLAIM EXCEEDS AUDIT RANGE" and "retracted on 2026-08-25" are present in `SynthProof-Thesis.pdf`.
**Numbers before → after:**
- PDF timestamps updated to 2026-09-14.
- Staged files in outer repo commit `1afceb5`: exactly 3 PDF files.
**Negative controls performed:**
- Ran `git status --short` in outer repo before committing to ensure no pre-existing uncommitted files in `REPORTS/`, `synopsis/`, or `COMPLETE-CODEBASE...` were staged.
**Deviations from the spec, and why:**
- None.
**Not done, and why:**
- None.

---

## T8 — Execute the Docker path (Tracker 5.5, runtime half)
**Status:** BLOCKED
**What I changed:**
- None.
**Commands run and their exit codes:**
- `docker info`: exit=1 (`error during connect: ... open //./pipe/docker_engine: The system cannot find the file specified.`)
**Numbers before → after:**
- N/A.
**Negative controls performed:**
- Confirmed non-zero exit of `docker info` before halting.
**Deviations from the spec, and why:**
- Halted immediately per §7 T8 instructions ("If it exits non-zero, STOP this task, report 'BLOCKED: Docker daemon not running', and move on.").
**Not done, and why:**
- Docker daemon is not running on host.

---

## T9 — Full grid for UCI Bank Marketing
**Status:** DONE
**What I changed:**
- `results/bank/h1_all_families.json`: computed full 5×5 preregistered grid (75 cells, `reduced_run: false`, 1,771.5s execution).
- `scripts/compare_bank_full.py`: created comparison script calculating cross-dataset metrics and 95% bootstrap confidence intervals.
- `results/bank/BANK_MARKETING.md`: completely rewritten for full-grid findings.
- `results/RESULTS.md`: updated "Third dataset" row with full-grid empirical metrics.
- `docs/ROAD_TO_TEN.md`: updated row 4.2 and log.
- `CHANGELOG.md`: removed reduced-grid known gap.
- `ARTIFACT.md`: updated §8 references.
- `README.md` (outer repo): updated description from reduced grid to full 5×5 grid.
**Commands run and their exit codes:**
- `python -m scripts.run_h1 --dataset bank`: exit=0 (75 cells, 1,771.5s)
- `python scripts/compare_bank_full.py`: exit=0
- `python scripts/reproduce.py`: exit=0 (reproducibility manifest matches)
- `python scripts/check_thesis_claims.py --all`: exit=0
**Numbers before → after:**
- Grid cells: 18 cells (`reduced_run: true`) → 75 cells (`reduced_run: false`).
- TV error at ε = 8 (full grid 95% CI):
  - Independent: 0.0409 → **0.0416 [0.029, 0.052]**
  - Pairwise: 0.0264 → **0.0289 [0.011, 0.055]**
  - AIM: 0.0494 → **0.0489 [0.038, 0.059]**
- Utility at ε = 8 (TSTR F1 vs TRTR 0.5610):
  - Independent: 0.4851 → **0.4792**
  - Pairwise: 0.4839 → **0.4824**
  - AIM: 0.4503 → **0.4536**
- Statistical conclusion: Confirms initial finding. On Bank Marketing, AIM's structural error is indistinguishable from independent marginals, while pairwise achieves the lowest error. All three tie on utility far below TRTR. AIM's structural superiority is confirmed to be Adult-specific.
**Negative controls performed:**
- Purged `results/bank/h1_cells/` prior to execution to prevent mixing stale reduced-run checkpoint cells into full-run aggregation.
**Deviations from the spec, and why:**
- None.
**Not done, and why:**
- None.

---

## T10 — Mark stale audit documents as historical
**Status:** DONE
**What I changed (in outer repository `d:/03_Study/CAPSTONE`):**
- Inserted historical notice banner directly under first heading in 7 outer audit documents:
  - `03_System_Audits_and_Handovers/CAPSTONE-DEEP-VERIFICATION.md`
  - `03_System_Audits_and_Handovers/CAPSTONE-FOLDER-ANALYSIS.md`
  - `03_System_Audits_and_Handovers/CAPSTONE-REEXECUTION-VERIFICATION.md`
  - `03_System_Audits_and_Handovers/CAPSTONE-SORTED-HANDOVER.md`
  - `03_System_Audits_and_Handovers/NOVELTY-RESEARCH-AND-PLAN.md`
  - `03_System_Audits_and_Handovers/PROJECT_CONTEXT.md`
  - `03_System_Audits_and_Handovers/SYNTHPROOF-COMPLETION-PLAN.md`
**Commands run and their exit codes:**
- `git diff --stat`: exit=0 (7 files changed, +28 insertions)
- `git commit` (outer repo): commit `bee9146`.
**Numbers before → after:**
- Historical banners inserted: 0 → 7 files.
**Negative controls performed:**
- Verified `COMPLETE-CODEBASE-AND-SYSTEM-EXPLANATION.md` was untouched and left untracked.
**Deviations from the spec, and why:**
- None.
**Not done, and why:**
- None.

---

## T11 — Prepare merge toward master
**Status:** DONE
**What I changed:**
- Verified branch lineage and commits. Prepared for reviewer merge. Did NOT merge.
**Commands run and their exit codes:**
- `git log --oneline origin/audit-fixes-and-acs..gemini/handoff-2026-09`: exit=0
- `git merge-base --is-ancestor origin/master gemini/handoff-2026-09`: exit=0 (no output, clean fast-forward ancestor)
**Numbers before → after:**
- Prepared branch commits: 7 commits ahead of `origin/audit-fixes-and-acs`.
**Negative controls performed:**
- Ran ancestor check against `origin/master` to confirm no diverge/conflict.
**Deviations from the spec, and why:**
- None.
**Not done, and why:**
- Merge into master was NOT performed (per §7 T11 rule: "You do not merge... The reviewer merges after review").

---

## Things I noticed but did not fix
1. `fastapi.testclient`: deprecation warning regarding `httpx` with `starlette.testclient`.
2. `scipy.optimize._optimize`: `RuntimeWarning: invalid value encountered in scalar divide` in line 3049 during bracket root-finding in numerical calibration edge tests.
3. Outer repository contains uncommitted files from prior authors (`02_Presentation_and_Synopsis/`, `REPORTS/`, `COMPLETE-CODEBASE-AND-SYSTEM-EXPLANATION.md`) which were strictly preserved and left unstaged.

---

## Human-only items left untouched (from §8)
The following tasks were left untouched as instructed in §8 of `AGENT_HANDOFF.md`:
1. **GitHub Release / Zenodo release**: Needs repository owner's personal accounts; tag `v1.0.0` was not moved or modified.
2. **`CONTRIBUTIONS.md` §3 teammate rows**: Awaiting team members' personal contributions statements.
3. **Institutional AI-assistance declaration**: Student/human obligation.
4. **Outer repository remote / push**: No git remote added; no push performed.
5. **`BudgetPlan` split tightening default**: Left at `tighten=False` default to preserve published epsilons.
6. **Docker image AIM dependency**: Did not add `private-pgm` to Docker image (deliberate design decision).
7. **Shadow-model attack / Gaussian copula**: Did not implement LiRA (declared in `ATTACKS_NOT_IMPLEMENTED`) or Gaussian copula (tracker 4.4 cut).
8. **Novelty verdict / survivor claims**: `research/08_novelty_verdict.md` preserved without promotion of dead claims.
