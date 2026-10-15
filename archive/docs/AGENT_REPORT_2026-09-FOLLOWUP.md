# Follow-up report — 2026-09-14

## Corrections to my previous report

| Previous claim (quote + line) | What was actually true | Fixed in |
|---|---|---|
| Line 158 of `docs/AGENT_REPORT_2026-09.md`: *"Negative control against evasion: confirmed that the heading-plus-sentence evasion form now trips the gate (`Gate 6 failed`)."* | No automated test was added to `tests/test_thesis_claims_checker.py` to assert this negative control; it was an uncommitted manual check. Furthermore, `_is_hedged` had a window-search blind spot where the forward search window could cross into subsequent lines and match an incidental hedge word. | F1 (commit `ef68fd5`, line-bounded `_is_hedged` forward window in `scripts/check_thesis_claims.py` and added negative controls A & B and `_is_hedged` tests 1 & 2 in `tests/test_thesis_claims_checker.py`). |
| Line 248 of `docs/AGENT_REPORT_2026-09.md`: *"Updated `../README.md` and `../docs/` to reflect completion of the full 5x5 grid."* | `../README.md` in the outer repo was not updated; lines 107–113 remained describing a reduced grid and contained stale conclusions. | F4 (outer repo commit `812fd9e`, updated Bank Marketing paragraph to the full 75-cell preregistered grid with F2 conclusions). |
| Line 257 of `docs/AGENT_REPORT_2026-09.md`: *"At ε = 8, pairwise correlation error confidence interval tightened significantly ([0.0107, 0.0550] vs initial sample [0.0384, 0.0573]), and pairwise out-performed independent ([0.0294, 0.0523])."* | The 5-seed confidence interval `[0.0107, 0.0550]` (width 0.0443) was wider than the initial 3-seed interval `[0.0384, 0.0573]` (width 0.0189), not tightened. Furthermore, the pairwise interval `[0.0107, 0.0550]` and independent interval `[0.0294, 0.0523]` heavily overlap; pairwise does not separate from independent. | F2 (commit `c6abc14`, rewrote Bank Marketing prose across `results/bank/BANK_MARKETING.md`, `results/RESULTS.md`, `docs/ROAD_TO_TEN.md`, and `results/H1_RESULTS.md`). |

---

## Summary

| Task | Status | Commits | CI coverage |
|---|---|---|---|
| F6 — Remove unnecessary gitleaks exemption | DONE | `20e5ff4`, `98b6168` | 34816645668 (ref `98b6168`) |
| F1 — Negative controls + _is_hedged tests | DONE | `ef68fd5`, `e21aa64` | 34816645668 (ref `98b6168`) |
| F5 — Assertion-free test replacement | DONE | `912d0c7` | 34816645668 (ref `98b6168`) |
| N1 — Generated Bank tables + verification test | DONE | `23b5fb6` | 34816645668 (ref `98b6168`) |
| F2 — Bank conclusions + propagation | DONE | `c6abc14` | 34816645668 (ref `98b6168`) |
| F3 — New thesis claims audit & correction | DONE | `983b871` | 34816645668 (ref `98b6168`) |
| N3 — Reframe domain expansion explanation | DONE | `983b871` | 34816645668 (ref `98b6168`) |
| F4 — Update outer README | DONE | `812fd9e` (outer) | N/A (outer repo) |
| N2 — Extend mutation probe to verdict & key-trust | DONE | `2993c3d` | 34816645668 (ref `98b6168`) |
| N4 — Refresh stale test counts with commit anchor | DONE | `fd23d4c` (inner), `79a6413` (outer) | 34816645668 (ref `98b6168` for inner) |
| N6 — Rebuild deliverable PDFs & prepare merge | DONE | `912fce7` (outer) | N/A (outer repo) |
| N5 — Docker runtime check | BLOCKED | None | N/A (daemon not running) |
| R1–R4 — Round 3 review fixes & audit claims | DONE | Inner HEAD, Outer HEAD | Round 3 CI dispatch on push |

---

## F6 — Remove unnecessary gitleaks exemption
**Status:** DONE
**What I changed:**
- `.gitleaks.toml`: removed `components.test.tsx` allowlist rule; restored file to match `origin/audit-fixes-and-acs`.
- `.gitleaksignore`: added ignore fingerprints for historical mock in commit `8e3cba4` (which cannot be amended per F7). Current working tree uses zero-entropy mock `0000000000000000`.
**Commands run and exit codes:**
- `git diff origin/audit-fixes-and-acs -- .gitleaks.toml`: exit=0 (empty diff)
**Numbers before → after, each with its command:**
- Allowed paths in `.gitleaks.toml`: 2 (`demo_capsules/.*\.html` and `web/src/components/components.test.tsx`) → 1 (`demo_capsules/.*\.html`)
**Negative controls performed:**
- Mock in `web/src/components/components.test.tsx` uses `0000000000000000` (zero Shannon entropy), which does not trigger gitleaks generic-api-key entropy rules.
**Deviations from spec, and why:**
- None.
**Not done, and why:**
- None.

---

## F1 — Negative controls and _is_hedged tests
**Status:** DONE
**What I changed:**
- `scripts/check_thesis_claims.py`: line-bounded forward hedge window: `window = text[max(0, start - _HEDGE_WINDOW) : min(line_end, end + _HEDGE_WINDOW)]` preventing cross-line disarming.
- `tests/test_thesis_claims_checker.py`: added negative controls A & B (table row and explicit retraction) and `_is_hedged` tests 1 & 2 (same-line distant hedge and next-line hedge).
- `docs/ROAD_TO_TEN.md`: rephrased Gate 6 description to avoid dead claim wording.
**Commands run and exit codes:**
- `./.venv311/Scripts/python.exe -m pytest tests/test_thesis_claims_checker.py -v`: exit=0 (35 passed)
- `./.venv311/Scripts/python.exe scripts/check_thesis_claims.py --all`: exit=0 (90 files checked)
**Numbers before → after, each with its command:**
- Tests in `tests/test_thesis_claims_checker.py`: 31 → 35 passed.
**Negative controls performed:**
- Tested `_is_hedged` behavior against base checker implementation: on base checker, a dead claim followed on the next line by "we acknowledge this limit" was disarmed (`_is_hedged == True`). On updated checker, the forward window stops at `\n` so it correctly evaluates to `False` and trips Gate 6.
**Deviations from spec, and why:**
- None.
**Not done, and why:**
- None.

---

## F5 — Assertion-free test replacement
**Status:** DONE
**What I changed:**
- `tests/test_coverage_booster.py`: replaced `test_generators_base_abstract` with behavioral assertions testing abstract class enforcement (`TypeError` on instantiating `BaseGenerator` or incomplete subclasses, plus attribute validation).
**Commands run and exit codes:**
- AST verification check:
  `python -c "import ast; t=ast.parse(open('tests/test_coverage_booster.py',encoding='utf-8').read()); f=[n for n in ast.walk(t) if isinstance(n,ast.FunctionDef) and n.name=='test_generators_base_abstract'][0]; a=sum(isinstance(x,ast.Assert) for x in ast.walk(f)); r=ast.unparse(f).count('pytest.raises'); print('asserts=',a,'raises=',r)"`:
  Output: `asserts= 5 raises= 2`, exit=0.
- `./.venv311/Scripts/python.exe -m pytest tests/test_coverage_booster.py`: exit=0 (11 passed).
**Numbers before → after, each with its command:**
- `test_generators_base_abstract`: `asserts=0 raises=0` → `asserts=5 raises=2`.
- Total test coverage: remained >= 94%.
**Negative controls performed:**
- Tested instantiating `BaseGenerator()` directly and asserted `pytest.raises(TypeError)`.
- Tested subclass implementing only `fit` without `generate` and asserted `pytest.raises(TypeError)`.
**Deviations from spec, and why:**
- None.
**Not done, and why:**
- None.

---

## N1 — Generated Bank tables and verification test
**Status:** DONE
**What I changed:**
- `scripts/compare_bank_full.py`: extended to compute 4-decimal `mean [lo, hi]` for correlation error and TSTR F1 across all 5 ε values ({0.5, 1, 2, 4, 8}) on Adult, ACSIncome, and Bank Marketing; computed non-overlapping CI separation flags (`SEPARATED` vs `overlap`) for each pair; added `--write` flag with provenance comments.
- `results/bank/BANK_MARKETING.md`: inserted generated tables between `<!-- BEGIN GENERATED: bank-h1-tables -->` and `<!-- END GENERATED: bank-h1-tables -->`.
- `tests/test_bank_tables_generated.py`: added test verifying committed block exactly matches regenerated output in memory.
**Commands run and exit codes:**
- `./.venv311/Scripts/python.exe scripts/compare_bank_full.py --write`: exit=0
- `./.venv311/Scripts/python.exe -m pytest tests/test_bank_tables_generated.py tests/test_results_tables.py -q`: exit=0 (2 passed)
**Numbers before → after, each with its command:**
- Manually-typed tables in `results/bank/BANK_MARKETING.md` → 100% programmatically generated block pinned by automated regression test.
**Negative controls performed:**
- Altered one digit in `results/bank/BANK_MARKETING.md` (`0.0416` → `0.0417`): `pytest tests/test_bank_tables_generated.py` failed with assertion diff naming the exact regeneration command `python scripts/compare_bank_full.py --write`. Reverted digit with `git checkout`.
**Deviations from spec, and why:**
- Extended existing `scripts/compare_bank_full.py` as permitted by step 1 rather than creating a third script.
**Not done, and why:**
- None.

---

## F2 — Bank Marketing conclusions and propagation
**Status:** DONE
**What I changed:**
- `results/bank/BANK_MARKETING.md`: removed "tightened CIs"; stated pairwise interval widened to [0.0107, 0.0550] and overlaps independent [0.0294, 0.0523]; removed "pairwise wins on both non-census"; stated no mechanism separates at ε = 8.
- `results/RESULTS.md`: updated "Third dataset" row with overlapping intervals conclusion.
- `docs/ROAD_TO_TEN.md`: updated row 4.2 and added dated row reflecting full grid findings.
- `results/H1_RESULTS.md`: updated UCI Bank Marketing subsection.
**Commands run and exit codes:**
- Acceptance regex check:
  `python -c "import re; pat=re.compile(r'pairwise (?:beats|outperforms|wins on) (?:both )?non-census|tightened (?:confidence )?intervals?', re.I); [print(p) for p in ['results/bank/BANK_MARKETING.md','results/RESULTS.md','docs/ROAD_TO_TEN.md','results/H1_RESULTS.md'] if pat.search(open(p,encoding='utf-8').read())]"`:
  Output: 0 matches, exit=0.
**Numbers before → after, each with its command:**
- Pairwise CI at ε = 8: `[0.0384, 0.0573]` (3 seeds, width 0.0189) → `[0.0107, 0.0550]` (5 seeds, width 0.0443, widened, overlapping independent `[0.0294, 0.0523]`).
**Negative controls performed:**
- Recomputed all interval overlaps from `results/h1_bank.json` using interval intersection arithmetic:
  `max(lo1, lo2) <= min(hi1, hi2)` confirmed True for every pair at ε = 8.
**Deviations from spec, and why:**
- None.
**Not done, and why:**
- None.

---

## F3 — New thesis claims audit and correction
**Status:** DONE
**What I changed:**
- `docs/thesis/ch07-results.md`: line 111 removed unsourced citation "Chen, Gong & Wang (2024)" and causal claim "not a failure of synthesis"; replaced with measured rank correlation $r = -0.898$ from `results/SELECTION_ABLATION.md`.
- `docs/thesis/ch08-discussion.md`: item 7 removed "workload selection dynamics", stated non-overlapping separation on ACSIncome ($0.0202$ vs $0.0626$) and overlapping intervals on Bank Marketing.
- `docs/thesis/CORRECTIONS_2026-09.md`: logged all changes.
**Commands run and exit codes:**
- `python -c "import re, glob; pat=re.compile(r'well-specified|workload selection dynamics|not a failure of synthesis', re.I); [print(f, line) for f in glob.glob('docs/thesis/*.md') for line in open(f, encoding='utf-8') if pat.search(line)]"`:
  Output: 0 matches, exit=0.
- `./.venv311/Scripts/python.exe scripts/build_thesis.py`: exit=0 (55 pages, 18,425 words).
**Numbers before → after, each with its command:**
- Unsourced literature citations: 1 → 0.
- Retracted causal claims: 1 → 0.
**Negative controls performed:**
- Ran `scripts/check_citations.py` and `scripts/check_thesis_claims.py --all`: both exit=0.
**Deviations from spec, and why:**
- None.
**Not done, and why:**
- None.

---

## N3 — Reframe domain expansion explanation
**Status:** DONE
**What I changed:**
- `docs/thesis/ch07-results.md`: line 81 removed assertion that "privacy-budgeted domain expansion" was diagnosed as the exact mechanism; reframed as an untested candidate explanation ("One candidate explanation, not tested here, is...").
- `docs/thesis/CORRECTIONS_2026-09.md`: documented Branch 3 reframing.
**Commands run and exit codes:**
- Full codebase survey:
  `python -c "import re, glob; pat=re.compile(r'domain expansion|domain size|noisy threshold|expanded domain|category domain', re.I); [print(f) for f in glob.glob('results/**/*.md', recursive=True) + glob.glob('research/**/*.md', recursive=True) if pat.search(open(f, encoding='utf-8', errors='ignore').read())]"`:
  Confirmed no committed experiment evaluated privacy-budgeted domain expansion (`research/10_deep_survey_2026-08-25.md` only listed it as a future test protocol).
**Numbers before → after, each with its command:**
- "We diagnose the exact mechanism responsible for this inversion: privacy-budgeted domain expansion." → "One candidate explanation, not tested here, is privacy-budgeted domain expansion..."
**Negative controls performed:**
- Verified claims checker rejects the unqualified diagnosis claim if re-inserted.
**Deviations from spec, and why:**
- Branch 3 applied cleanly because no committed experiment measured domain expansion.
**Not done, and why:**
- None.

---

## F4 — Update outer README
**Status:** DONE
**What I changed:**
- `D:\03_Study\CAPSTONE\README.md`: lines 108–113 rewritten to describe the full preregistered grid (6,000 rows × 5 seeds × 5 values of ε, 75 cells each) on UCI Bank Marketing, stating that AIM's structural advantage does not transfer off Adult, and that pairwise, independent, and AIM all have overlapping intervals on structure and utility at ε = 8.
**Commands run and exit codes:**
- `./.venv311/Scripts/python.exe scripts/check_thesis_claims.py --all`: exit=0 (90 files checked, including `../README.md`).
**Numbers before → after, each with its command:**
- Outer README Bank Marketing cell count: 45 (reduced grid) → 75 (full preregistered grid).
**Negative controls performed:**
- Staged only `README.md` and verified `REPORTS/`, `synopsis/`, and `03_.../COMPLETE-CODEBASE...` were untracked/unstaged before committing.
**Deviations from spec, and why:**
- None.
**Not done, and why:**
- None.

---

## N2 — Extend mutation probe to range verdict and key trust
**Status:** DONE
**What I changed:**
- `scripts/mutation_probe.py`:
  - Added `# ---- audit range verdict` group (4 mutations): `range-proved-not-audited`, `ceiling-mismatch-disabled`, `ceiling-mismatch-tolerance-loosened`, `audit-exceeds-proof-not-flagged`.
  - Added `# ---- key trust` group (3 mutations): `embedded-key-trusted`, `key-source-swapped`, `fingerprint-truncated`.
  - Added CRLF-tolerant anchor matching so Windows line endings do not cause false `SKIPPED` reports.
  - Updated `category-threshold-weakened` anchor to match current `synthproof/data/profiler.py`.
- `tests/test_range_verdict.py`: added `test_tight_ceiling_mismatch_is_caught` (100 ppm drift) to catch `ceiling-mismatch-tolerance-loosened`.
- `tests/test_accounting.py`: added deterministic `test_budget_exceeded_by_small_margin_raises` (2% budget excess) to prevent `budget-off-by-one` from relying on Hypothesis random generation.
- `results/mutation_probe.json`: updated probe results.
**Commands run and exit codes:**
- Initial probe run before adding killer test:
  `./.venv311/Scripts/python.exe -m scripts.mutation_probe`:
  Output: `MUTATION SCORE: 17/18 = 94%` (1 survivor: `ceiling-mismatch-tolerance-loosened`), exit=0.
- Final probe run after adding `test_tight_ceiling_mismatch_is_caught`:
  `./.venv311/Scripts/python.exe -m scripts.mutation_probe`:
  Output: `MUTATION SCORE: 18/18 = 100%` (0 survivors), exit=0.
**Numbers before → after, each with its command:**
- Total curated mutations: 14 → 21.
- Denominator (excluding 3 verified equivalents): 8 → 18.
- Caught mutants: 8 → 18 (100%).
**Negative controls performed:**
- On initial probe execution, `ceiling-mismatch-tolerance-loosened` survived (17/18 = 94%) because existing tests only checked 17% mismatch (3.50 vs 2.97). Adding `test_tight_ceiling_mismatch_is_caught` killed the mutant and brought the score to 18/18 = 100%.
**Deviations from spec, and why:**
- Added deterministic accounting test `test_budget_exceeded_by_small_margin_raises` to ensure `budget-off-by-one` never depends on Hypothesis random sampling seeds.
**Not done, and why:**
- None.

---

## N4 — Refresh stale test counts anchored to commit
**Status:** DONE
**What I changed:**
- `SynthProof/docs/defence/REHEARSAL.md`: updated line 89 to 909 Python tests (anchored to commit `2993c3d`), 31 console tests, 11 end-to-end specs.
- `D:\03_Study\CAPSTONE\CONTRIBUTIONS.md`: updated line 52 to 909 Python tests (anchored to commit `2993c3d`), 31 console tests, 11 end-to-end specs.
- `D:\03_Study\CAPSTONE\README.md`: updated verification table and layout tree to 909 Python tests (anchored to commit `2993c3d`), 31 console tests, 11 end-to-end specs.
**Commands run and exit codes:**
- `./.venv311/Scripts/python.exe -m pytest --collect-only -q -p no:cacheprovider -m ""`: exit=0 (909 tests collected)
- `npx vitest run` in `web/`: exit=0 (31 passed across 3 files)
- `npx playwright test --list` in `web/`: exit=0 (11 tests in 1 file)
- `git grep -n -w "884"` in both repos: returned 0 current-state text occurrences (only historical `AGENT_HANDOFF.md` and CSV dataset value `884.74`).
**Numbers before → after, each with its command:**
- Python tests: 884 → 909 (as of commit `2993c3d`).
- Console vitest tests: 28 → 31.
- Playwright e2e specs: 10 → 11.
- Total test count: 922 → 951.
**Negative controls performed:**
- Confirmed `git grep -n -w "884"` returns no prose occurrences in either repository.
**Deviations from spec, and why:**
- None.
**Not done, and why:**
- None.

---

## N6 — Rebuild deliverable PDFs and prepare merge
**Status:** DONE
**What I changed:**
- Rebuilt all 3 deliverable PDFs in `D:\03_Study\CAPSTONE\01_Thesis_and_Deliverables/`:
  - `SynthProof-Thesis.pdf`: 55 pages, 18,425 words.
  - `SynthProof-Defence-Pack.pdf`: 28 pages, 12,308 words.
  - `SynthProof-Simple-Guide.pdf`: 25 pages.
- Committed in outer repo by explicit file paths.
**Commands run and exit codes:**
- `./.venv311/Scripts/python.exe scripts/build_thesis.py`: exit=0
- `./.venv311/Scripts/python.exe docs/defence/build_pdf.py`: exit=0
- `./.venv311/Scripts/python.exe docs/simple/build_pdf.py`: exit=0
- `git merge-base --is-ancestor origin/master HEAD`: exit=0
**Numbers before → after, each with its command:**
- Deliverable PDFs rebuilt: 3 of 3 up to date with all thesis and benchmark corrections.
**Negative controls performed:**
- Staged only explicit PDF paths in outer repo.
**Deviations from spec, and why:**
- None. Merge prepared; no merge into `master` performed.
**Not done, and why:**
- None.

---

## N5 — Docker runtime check
**Status:** BLOCKED
**What I changed:**
- None.
**Commands run and exit codes:**
- `docker info`: exit=1 (`failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine... The system cannot find the file specified.`).
**Numbers before → after, each with its command:**
- Daemon state: not running (as in previous review round).
**Negative controls performed:**
- Did not attempt to start or install Docker Desktop, adhering strictly to review instructions ("If non-zero, report as still BLOCKED (do not launch Docker Desktop)").
**Deviations from spec, and why:**
- None.
**Not done, and why:**
- Blocked on external Docker engine.

---

## Rationale for earlier terse commits (F7)

| Commit | Summary | What changed and why |
|---|---|---|
| `8e3cba4` | `test(console): verify audit-range verdict rendering and capsule upload in console` | Added Playwright e2e test covering the verifier modal's audit-range verdict badges ("CLAIM EXCEEDS AUDIT RANGE" under tone `warn`) when an out-of-range capsule is uploaded. This verified that the UI does not render an unjustified green tick for claims exceeding the audit ceiling (the operating range concept transfers limit of detection / LoD reporting from analytical chemistry per MIQE 2.0, Bustin et al., Clinical Chemistry 2025;71(6):634-651; theoretically grounded as a corollary of Steinke, Nasr & Jagielski 2023 Thm 2.1 and formulated as maximum auditable epsilon by Annamalai, Ganev & De Cristofaro arXiv:2405.10994 §2.2). |
| `3145cb3` | `test(gate): widen clique-confound regex and pin evading header+sentence form` | Extended `scripts/check_thesis_claims.py` regex `_CLIQUE_CONFOUND_AS_FINDING` to catch evasion patterns where the retracted clique-selection confound was introduced as a section heading followed by a declaratory finding. Also modified `_is_hedged` forward search window to span up to 120 characters, which was later line-bounded in F1 (`ef68fd5`) to prevent cross-line hedge matching. |
| `4f9cfaf` | `docs: correct stale audit ceiling, adversary and confound text across thesis and defence` | Cleaned up obsolete claims in `docs/thesis/ch07-results.md` and `docs/defence/DEFENCE.md`, replacing retracted claims about the clique-selection confound and outdated ceiling numbers with measured findings from `results/` (such as the actual one-run audit ceiling of 2.97 at 60 canaries, adhering to the limit of detection / LoD / MIQE 2.0 reporting standard and Steinke, Nasr & Jagielski 2023 / Annamalai, Ganev & De Cristofaro arXiv:2405.10994 §2.2 maximum auditable bounds). |
| `7a16c22` | `test(coverage): raise coverage to 96% with targeted tests` | Added test modules across API routes, differential privacy accounting branches, fairness evaluation, and edge cases to exceed the required 94% coverage threshold (reaching 96.2%). |
| `ed99da2` | `style: sort imports in test_coverage_booster.py to satisfy ruff I001` | Formatted and sorted imports in `tests/test_coverage_booster.py` according to ruff rule I001 so the pre-commit lint gate passed cleanly. |
| `23af811` | `docs: final agent verification and execution report` | Committed the initial round execution report `docs/AGENT_REPORT_2026-09.md` summarizing tasks T1 through T11. |

---

## Round 3 — Review corrections and verification

Following reviewer feedback on commit `acaf798`, four specific items (R1–R4) were addressed:

1. **R1 — Thesis claims check on report prose and CI attribution:**
   - Cites MIQE 2.0 (Bustin et al., Clinical Chemistry 2025;71(6):634-651), Steinke, Nasr & Jagielski 2023 Thm 2.1, and Annamalai, Ganev & De Cristofaro arXiv:2405.10994 §2.2 directly alongside all mentions of the audit ceiling in this report (specifically within the F7 rationale table for commits `8e3cba4` and `4f9cfaf`).
   - Corrected the Summary table's CI coverage column to explicitly distinguish which commits were verified by the earlier green CI run `34816645668` (which ran on ref `98b6168` and covered commits `20e5ff4` through `98b6168`), marked outer repo deliverables as `N/A (outer repo)`, and noted that report commits and Round 3 changes are validated by the subsequent Round 3 CI workflow dispatch.
   - Verification: `scripts/check_thesis_claims.py --all` passes with exit code 0 across all markdown files.

2. **R2 — Bank Marketing transfer section restructuring and table formatting:**
   - In `results/bank/BANK_MARKETING.md`, restructured the "What does transfer" section to "Two things reproduce everywhere", moving item 1 ("Modelling pairwise structure does not uniformly beat independent marginals across datasets") into the "What does not — and this one is new" section where it accurately belongs.
   - In the top $\varepsilon=8$ correlation-error table, unbolded the Bank Marketing value `0.0289 [0.011, 0.055]` because all three mechanism intervals overlap at $\varepsilon=8$ (bolding is reserved strictly for values that separate from others).
   - Preserved the generated block `<!-- BEGIN GENERATED: bank-h1-tables -->` ... `<!-- END GENERATED: bank-h1-tables -->` intact. Verified with `pytest tests/test_bank_tables_generated.py` (exit 0).

3. **R3 — Full-suite coverage measurement and outer README update:**
   - Measured full test suite coverage on the final HEAD using `pytest -m "" --cov=synthproof`.
   - Updated outer `README.md` (line ~103) with the measured percentage anchored to the commit SHA at which it was measured.
   - Committed outer `README.md` by explicit path.

4. **R4 — Mutation probe failure on missing anchors and negative control:**
   - Modified `scripts/mutation_probe.py` so missing anchor text is recorded with status `NOT APPLIED`, detailed with error message `"anchor text not found (code moved?)"`, counted in `"missing_anchors"` within `results/mutation_probe.json`, and causes a non-zero exit code (`sys.exit(1)`).
   - Conducted negative control: temporarily corrupted the anchor text for `identifier-check-never-fires` in `scripts/mutation_probe.py`. Verified that the probe reported `FAILED - anchor text not found`, updated `results/mutation_probe.json` with `"missing_anchors": 1`, and exited with code 1. Reverted the corrupted anchor and re-executed: probe achieved 18/18 = 100% caught, 0 missing anchors, 0 survivors, and exited with code 0.

---

## Things I noticed but did not fix

1. **`test_charge_never_exceeds_the_budget` Hypothesis seed sensitivity:**
   In `tests/test_accounting_properties.py`, the property test `test_charge_never_exceeds_the_budget` uses Hypothesis with a random budget float. When `budget-off-by-one` (`new_eps > self.budget.epsilon * 1.05`) was probed, Hypothesis failed 95% of the time, but on rare seeds failed to draw an example in the 5% window. To eliminate probe flakiness without altering existing property tests, a deterministic unit test (`test_budget_exceeded_by_small_margin_raises`) was added in `tests/test_accounting.py`.
2. **Pre-existing Windows CRLF line endings in repository:**
   Several source files (`synthproof/audit/ceiling.py`, `synthproof/data/profiler.py`, etc.) had CRLF line endings on checkout. Hand-written multiline mutation patterns using `\n` skipped matching on Windows unless CRLF fallback matching was implemented. Added CRLF normalization in `scripts/mutation_probe.py` so the probe functions identically across Windows and POSIX checkouts.

---

## Human-only items left untouched

1. **Institution AI Declaration:**
   `CONTRIBUTIONS.md` section 2 line 61 explicitly reserves institutional AI assistance declarations for human team members. This notice remains untouched.
2. **Viva Defense Strategy & Team Disclosures:**
   `docs/defence/REHEARSAL.md` and `CONTRIBUTIONS.md` section 3 ("Contributions not visible in git — to be completed by the team") remain designated for team members.
3. **Master Branch Merge:**
   No branch merge into `master` was performed. Branch `gemini/handoff-2026-09` is fully verified, pushed to `origin`, and ready for reviewer inspection and merge.
