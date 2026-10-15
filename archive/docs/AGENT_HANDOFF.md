# SynthProof — Agent Handoff

> **Audience:** an AI coding agent picking this project up cold (written for Gemini).
> **Author of this handoff:** Claude, who did the remediation work up to 2026-09-13.
> **What happens after you finish:** Claude will review everything you did, commit by commit,
> using the checklist in [§10](#10-how-your-work-will-be-verified). Work as if every number you
> write will be recomputed and every claim you make will be checked, because it will be.

---

## Table of contents

0. [Read this first — the contract](#0-read-this-first--the-contract)
1. [The project in two minutes](#1-the-project-in-two-minutes)
2. [Environment](#2-environment)
3. [Rules you must not break](#3-rules-you-must-not-break)
4. [Traps that have already cost hours](#4-traps-that-have-already-cost-hours)
5. [Current state, as of 2026-09-13](#5-current-state-as-of-2026-09-13)
6. [What has been done](#6-what-has-been-done)
7. [What has to be done — task specifications](#7-what-has-to-be-done--task-specifications)
8. [Tasks you must NOT attempt](#8-tasks-you-must-not-attempt)
9. [Order of work, and how to report](#9-order-of-work-and-how-to-report)
10. [How your work will be verified](#10-how-your-work-will-be-verified)
11. [Reference: numbers, files, commands](#11-reference-numbers-files-commands)

---

## 0. Read this first — the contract

This project's single defining property is that **it does not claim anything it has not
measured**. Its own documentation, CI and tests are built around that. Several of the most
serious defects found so far were not bugs in the maths — they were documents, tests or
artefacts that *said* something was true without it being checked:

- a signed demo capsule whose numbers were typed by hand;
- a test that could not fail, because it compared data against bounds the data had already
  been clipped to;
- a demo script that said "every command here was run" and depended on a folder that did not
  exist;
- a verdict that said "Verified"/"safe" without the comparison that would justify it.

**Your job is to finish the remaining work without adding a single defect of that kind.**

Concretely, the contract is:

1. **Never write a number you did not compute in this session.** Copy it from a command's
   output, and keep the command. If you cannot compute it, write `[NOT MEASURED]`.
2. **Never mark a task done that you did not verify by executing its acceptance check.**
   "Should work" is not done. "I ran X and it printed Y" is done.
3. **Never make a check pass by weakening the check.** Not a test, not the coverage gate, not
   the claims checker. If a check is genuinely wrong, fix it *and* add a test proving the fix
   does not blind it (see how `tests/test_thesis_claims_checker.py` does this).
4. **When blocked, stop that task and report it as blocked with the reason.** Do not work
   around a block by simulating the result.
5. **Report failures as plainly as successes.** A reported failure is useful to the reviewer; a
   hidden one will be found and will discredit everything else in the report.

---

## 1. The project in two minutes

**SynthProof** is a B.Tech capstone (MIT World Peace University, Pune, CSE-AIDS, 2026–27). It is
a differentially private (DP) synthetic tabular data pipeline that:

1. profiles a sensitive table and charges every read to a **privacy accountant**
   (`dp_accounting`, cross-checked by `autodp`);
2. synthesises data with one of several **mechanisms** (`independent`, `pairwise`, real `aim`
   via private-PGM, `fixed_workload`, a DP-SGD VAE);
3. **audits** the release empirically (canary auditing, one-run Steinke auditor, membership and
   attribute attacks);
4. emits a **Privacy Data Sheet**, signed with **Ed25519**, recorded in a **hash-chained ledger**
   whose signed head commits to `(entry_count, tip_hash)`, and exportable as an **MLCommons
   Croissant 1.1** record and as a self-verifying offline **HTML capsule**.

**Its central finding is negative, about the measurement:** a canary audit can certify at most
`log(r / ln(1/α))` epsilon with `r` canaries — a corollary of Steinke, Nasr & Jagielski (2023)
Thm 2.1. At the 60 canaries used, that ceiling is **2.972**, while the proved epsilons reach
**7.36**. So the audit could not have confirmed the claims regardless of leakage. The project
reports this ceiling inside every artefact — a transfer of limit-of-detection (LoD) reporting
from analytical chemistry (MIQE 2.0, Bustin et al., *Clinical Chemistry* 2025;71(6):634–651).
**The ceiling is not the project's theorem, and must never be described as one.**

**Novelty position: integration, not invention.** The project's own adversarial review
(`research/08_novelty_verdict.md`) killed eight of its candidate contributions. Three narrow
differences survive, always stated with their caveats:

| ID | Survivor | Required caveat |
|---|---|---|
| S1 | Reporting the measurement's operating range *inside* the released artefact | no reporting standard was found; transfers MIQE 2.0 |
| S2 | Cryptographically signing the privacy claim | engineering novelty, not science |
| S3 | Data-blind release refusal (reads schema + row count only) | **unrefuted, never "novel"** — the SDC Handbook was unreachable |

Never describe any of these as "the first", "novel" without the caveat, or "we discovered".

**Repository layout (two git repositories):**

```text
D:\03_Study\CAPSTONE\                 <- OUTER repo. NO git remote. Deliverables, audits.
├── README.md, INDEX.md, CONTRIBUTIONS.md
├── 01_Thesis_and_Deliverables\       <- built PDFs (generated, never hand-edited)
├── 02_Presentations_and_Pitches\     <- built pitch deck + SoK
├── 03_System_Audits_and_Handovers\   <- historical audit documents
├── 04_Demo_CSV_Datasets\
├── REPORTS\  research\  synopsis\  UPGRADE\  archive\
└── SynthProof\                       <- CODE repo. remote: github.com/rajmodi262/SynthProof
    ├── synthproof\    (package)       ├── tests\        (pytest)
    ├── web\           (React console, pitch deck, Playwright e2e)
    ├── scripts\       (experiments, gates, builders)
    ├── results\       (every experiment, including nulls and retractions)
    ├── docs\          (ROAD_TO_TEN.md tracker, thesis\, defence\, conventions)
    └── research\      (novelty assessment)
```

---

## 2. Environment

| Item | Value |
|---|---|
| OS | Windows 11. Both a POSIX shell (Git Bash) and PowerShell are available |
| Code repo | `D:\03_Study\CAPSTONE\SynthProof` |
| Python | **Always** `./.venv311/Scripts/python.exe` (Python 3.11.4) from the code repo root. Never the system Python |
| Node | v20.18.1; console in `SynthProof/web` |
| GitHub CLI | `gh` is authenticated for `rajmodi262/SynthProof` |
| Docker | CLI installed, **daemon NOT running** (Docker Desktop not started). `docker info` exits 1 |
| `make` | Do not rely on it. Every task below gives the raw command |
| Console encoding | cp1252. Python that prints `ε`, `μ`, `·` must run with `PYTHONIOENCODING=utf-8` |

**Standard commands (run from `D:\03_Study\CAPSTONE\SynthProof`):**

```bash
PY=./.venv311/Scripts/python.exe

# tests
$PY -m pytest -p no:cacheprovider -m "not slow" -q            # fast lane, ~3 min
$PY -m pytest -p no:cacheprovider -m "" -q                    # EVERYTHING incl. slow, 10-40 min
$PY -m pytest -p no:cacheprovider -m "" --cov=synthproof --cov-report=term-missing   # CI-equivalent

# quality gates (all must pass before any commit)
$PY -m ruff check synthproof tests scripts
$PY -m black --check synthproof tests scripts
$PY -m mypy synthproof
$PY scripts/check_thesis_claims.py --all        # honesty gate: retracted claims
$PY scripts/check_citations.py                  # honesty gate: citations

# console
cd web && npx tsc --noEmit && npx vitest run --config vitest.config.ts && cd ..
cd web && npm run test:e2e && cd ..            # Playwright, 9 specs (1 more tagged @slow)
```

**CI does not run on a branch push.** `.github/workflows/ci.yml` triggers on push to
`master`/`main`, on pull requests, weekly, and on `workflow_dispatch`. To test your branch:

```bash
gh workflow run CI --ref <your-branch>
SHA=$(git rev-parse HEAD)
# the run takes a few seconds to appear -- poll, do not assume
for i in $(seq 1 30); do
  ID=$(gh run list --branch <your-branch> --limit 5 --json databaseId,headSha \
       --jq "[.[] | select(.headSha==\"$SHA\")][0].databaseId // empty")
  [ -n "$ID" ] && break; sleep 10
done
gh run watch "$ID" --exit-status > /dev/null 2>&1; echo "ci exit=$?"
gh run view "$ID" --json conclusion,jobs --jq '.conclusion, (.jobs[] | "\(.name): \(.conclusion)")'
```

CI has 7 jobs: `test (3.11)`, `test (3.12)`, `test (3.13)`, `security`, `console`,
`auditor-guard`, `calibration-guard`. **A task touching code is not done until all 7 are green on
the commit that contains it.**

---

## 3. Rules you must not break

### 3.1 The project's standing rules (enforced by review and partly by CI)

1. **Never write a bound that cannot be cited.** Composition is delegated to `dp_accounting`.
2. **Never report a number that was not computed.** No hardcoded fallbacks, no derived
   stand-ins, no "illustrative" value that is not labelled as such where it is displayed.
3. **A mechanism that is charged must be applied.**
4. **Name things what they are.** A nearest-neighbour heuristic is not LiRA.
5. **Illustrative values must be labelled where they are displayed** — in the UI, the file,
   the page, not only in a commit message.
6. **A null result is a result.** H2 and H3 are nulls and stay reported as nulls.

### 3.2 Git rules

| Rule | Why |
|---|---|
| **Create and work on a new branch** `gemini/handoff-2026-09` from `origin/audit-fixes-and-acs` | The reviewer diffs your branch against that base |
| **Never push to `master`. Never move, delete or recreate tag `v1.0.0`** | `v1.0.0` is a released, CI-verified commit (`28dc59d`) |
| **Never `git push --force`, `git rebase` a pushed branch, or `git commit --amend` a pushed commit** | History is evidence here |
| **One task = one or more commits whose subject starts with the task ID**, e.g. `[T3] test(api): ...` | Makes review per task possible |
| **Every commit you author ends with the trailer** `Assisted-by: Gemini` | The project discloses AI authorship in git history (`CONTRIBUTIONS.md`). A missing or misattributed trailer corrupts that record |
| **Commit message body explains WHY, and names any number with its source** | Match the existing history's style: `git log -20` |
| **In the OUTER repo, stage only files you changed, by explicit path.** Never `git add -A` / `git add .` there | The outer repo has *pre-existing* uncommitted changes that are not yours (see §5.4) |
| Push the code branch after each completed task: `git push origin gemini/handoff-2026-09` | So progress is recoverable and reviewable |

### 3.3 Things that look like improvements and are forbidden

- **Do not flip `BudgetPlan.split(tighten=...)` to `True` by default.** It changes every
  published epsilon (proved 7.356 → ~8.0) and invalidates the committed results. Human decision.
- **Do not edit `docs/thesis/THESIS.md` directly.** It is generated from the chapter files
  `docs/thesis/ch0*.md` by `scripts/build_thesis.py`. Edit chapters, then rebuild.
- **Do not edit PDFs, `demo_capsules/*.html`, `results/*.json`, or the standalone pitch deck by
  hand.** They are generated. Regenerate them with their builder and commit the output.
- **Do not lower `--cov-fail-under` or add `# pragma: no cover` to reach a coverage number.**
- **Do not add entries to any "allowlist", exemption or skip to silence a gate** unless the task
  explicitly says so, and then with a stated reason next to the entry.
- **Do not describe AIM as "the best mechanism".** It is best on UCI Adult only (see §5.3).
- **Do not delete retraction notices, SUPERSEDED markers, or "corrected on" notes.** They are
  the record.
- **Do not run `scripts/reproduce.py --update` or regenerate the manifest** unless the task says
  so, and never without reading the diff first.

---

## 4. Traps that have already cost hours

Each of these happened on this project. Assume they will happen to you.

1. **Exit codes through a pipe lie.** `cmd | tail -5; echo $?` prints `tail`'s status. Use
   `cmd > log 2>&1; echo "exit=$?"` or `${PIPESTATUS[0]}`. This mistake was made four times.
2. **Bash heredocs mangle Python.** A `<<'EOF'` heredoc containing a complex Python edit script
   failed to parse in this environment and edited nothing, silently to a skim-reader. For any
   non-trivial edit script, **write the script to a file first, then run the file**, and have the
   script `assert` each replacement matched exactly once and print what it changed.
3. **`\b` in a heredoc became a literal backspace (0x08)**, so regexes silently never matched.
4. **`TabularDataset` clips data to the declared schema bounds on construction.** Any test that
   compares declared bounds against a *loaded* table's min/max is comparing a thing to itself.
   Compare against the raw file.
5. **The capsule HTML is a Python f-string.** Values substituted into it are inserted verbatim
   and not rescanned; do not double braces in substituted values. Literal `{` `}` in the template
   itself must be doubled.
6. **API routers must read shared state as `state.GLOBAL_LEDGER`**, after
   `from synthproof.api import state`. `from synthproof.api.state import GLOBAL_LEDGER` binds a
   copy that goes stale after a reset, and a tamper then hits one chain while verification reads
   another.
7. **`monkeypatch.setattr` on the wrong module does nothing, silently.** After the API split,
   `DEMO_MODE` lives in `synthproof.api.state`, not `synthproof.api.main`.
8. **Playwright:** `getByRole('spinbutton', {name})` finds nothing when the label is a sibling
   `<span>`; an input inside a closed `<details>` is "not visible". A test that asserts
   `toHaveCount(0)` can pass before the UI has done anything — wait for the positive state first.
   Every failed locator costs a full timeout.
9. **`gh run list` right after `gh workflow run` often does not show the new run yet.** Poll by
   commit SHA (see §2). A watcher that grabbed an empty run ID reported "failure" once.
10. **A recursive `grep -r` over the whole tree times out** (`.venv311`, `node_modules`, `data`).
    Restrict the path or use `rg`/the search tool.
11. **On Windows, `subprocess.run(["npm", ...])` cannot find `npm.cmd`.** Resolve it with
    `shutil.which("npm") or shutil.which("npm.cmd")`.
12. **The claims gate sweeps the repo root, `docs/`, `results/`, `research/`, `CITATION.cff` and
    the outer `README.md`/`INDEX.md`/`CONTRIBUTIONS.md`/`REPORTS/`.** Two of its rules will fire on
    ordinary new prose:
    - `missing-lod-transfer`: any document that mentions the audit ceiling, an operating range,
      or a maximum auditable epsilon must also mention MIQE / limit of detection / LoD, *near
      where it makes the claim*;
    - `missing-ceiling`: any document that reports an audited epsilon must mention the ceiling.

    Run `scripts/check_thesis_claims.py --all` after every documentation edit.
13. **`black` reformats; `ruff` then passes.** Run `black` first, then `ruff`, then re-run tests.
14. **Slow tests download data** (ACS PUMS, UCI Bank Marketing). They are marked `@pytest.mark.slow`
    and need network on a cold cache.
15. **Counts go stale the moment you commit.** Anchor any commit count to a named commit or tag
    (`git rev-list --count v1.0.0`), never to "now".

---

## 5. Current state, as of 2026-09-13

### 5.1 Git and CI

| Ref | Commit | Notes |
|---|---|---|
| tag `v1.0.0` | `28dc59d` (tag object `9999417`) | Released. CI run `34759699144` green, all 7 jobs |
| `origin/master` | `28dc59d` | Fast-forwarded from `256c67f`. CI run `34760116086` green |
| `origin/audit-fixes-and-acs` | `9ec49d5` | **3 doc-only commits ahead of master**: `8ce7dc0`, `0673521`, `9ec49d5`. CI green on `0673521` (run `34760116360`); `9ec49d5` (tracker row only) not run |
| outer repo `HEAD` | `df2a79c` | **No remote.** Commits are local only |

**No GitHub Release exists for `v1.0.0` — on purpose.** Zenodo archives only Releases published
after its webhook is enabled; that toggle is a human task (§8).

### 5.2 Test and quality status

| Check | Status | How measured |
|---|---|---|
| pytest | **884 tests collected** | `pytest --collect-only -m ""` |
| Coverage | **92%** on the fast lane; the full-suite figure was **not re-measured** after today's additions | `pytest -m "not slow" --cov=synthproof` |
| Coverage gate | `--cov-fail-under=90` in `.github/workflows/ci.yml` line 73 | |
| vitest | **28 tests**, 3 files, green | |
| Playwright | **10 specs**; `npm run test:e2e` runs 9 (1 tagged `@slow`) | `npx playwright test --list` |
| mypy / ruff / black | clean | |
| Claims gate / citations gate | exit 0 | |

Weakest modules (fast-lane coverage): `api/routes/artifacts.py` **55%**, `evaluate/fairness.py`
86%, `accounting/types.py` 87%, `generators/base.py` 87%, `frontier/checkpoint.py` 88%,
`accounting/differential.py` 89%, `cli.py` 89%. (`data/datasets.py` and `data/acs.py` read low only
because the fast lane excludes the slow tests that exercise them.)

### 5.3 The results, in numbers (copy these, do not retype from memory)

Correlation error at ε = 8, mean [95% bootstrap CI] — lower is better:

| Dataset | true corr | independent | pairwise | aim |
|---|---:|---|---|---|
| UCI Adult | +0.1034 | 0.0947 [0.082, 0.107] | 0.0283 [0.013, 0.052] | **0.0078** [0.003, 0.013] |
| ACSIncome CA 2018 | +0.0721 | 0.0535 [0.047, 0.060] | **0.0202** [0.008, 0.038] | 0.0626 [0.043, 0.075] |
| UCI Bank Marketing* | +0.0604 | 0.0447 [0.038, 0.053] | **0.0174** [0.006, 0.029] | 0.0468 [0.018, 0.068] |

TSTR F1 at ε = 8:

| Dataset | TRTR | independent | pairwise | aim |
|---|---:|---:|---:|---:|
| UCI Adult | 0.6604 | 0.4065 | 0.4321 | 0.5049 |
| ACSIncome | 0.7246 | 0.4616 | 0.5219 | 0.5812 |
| UCI Bank Marketing* | 0.5639 | 0.4751 | 0.4723 | 0.4716 |

\* Bank Marketing is a **reduced grid**: ε ∈ {1, 8}, seeds {0, 1, 2}. Payload field
`reduced_run: true`. Source files: `results/h1_all_families.json`,
`results/acs/h1_all_families.json`, `results/bank/h1_all_families.json`.

**Readings the evidence supports:** pairwise beats independent on structure on all three
datasets (non-overlapping CIs). AIM's structural advantage appears on Adult only. The utility
ordering holds on the two census tables and does **not** reproduce on Bank Marketing, where all
three mechanisms tie. Every TSTR < TRTR everywhere.

### 5.4 The outer repo's pre-existing uncommitted changes — NOT YOURS

`git status` in `D:\03_Study\CAPSTONE` shows, and these predate the handoff:

```text
 M 01_Thesis_and_Deliverables/SynthProof-Defence-Pack.pdf
 M 01_Thesis_and_Deliverables/SynthProof-Simple-Guide.pdf
 M 01_Thesis_and_Deliverables/SynthProof-Thesis.pdf
 M REPORTS/00-MASTER-REPORT.md   (and 01, 02, 03, 05, 06, README.md)
 D synopsis/CrossTrace-Synopsis.docx / .pdf
 D synopsis/RedHarness-Synopsis.docx / .pdf
?? 03_System_Audits_and_Handovers/COMPLETE-CODEBASE-AND-SYSTEM-EXPLANATION.md
```

**Do not stage, commit, revert, restore or delete any of these** unless a task explicitly tells
you to regenerate a specific file — and then stage only that file, by path, and say in your
report that it had pre-existing modifications.

---

## 6. What has been done

The tracker is [`docs/ROAD_TO_TEN.md`](ROAD_TO_TEN.md). Read it. It holds the evidence for every
row. Summary: **30 of 33 tasks DONE, 1 deliberately CUT, 2 PARTIAL.**

### 6.1 Phases P0–P6 of the tracker

| ID | Task | Status | Evidence |
|---|---|---|---|
| 0.1 | Clear 74 ruff errors | DONE | `68d8186` |
| 0.2 | Regenerate the reproducibility manifest | DONE | `1e9105b` |
| 0.3 | Both honesty gates into CI | DONE | `04fb41a` |
| 1.1 | Restore missing `try {` in capsule JS | DONE | `d66bad1` |
| 1.2 | Remove the capsule's green-tick bypass (three outcomes now) | DONE | `d66bad1` |
| 1.3 | Single-source the capsule verifier (`synthproof/capsule/verifier.js`) | DONE | `aaab786` |
| 1.4 | Fix demo presets; the 400-row refusal is a feature | DONE | `1f9498b` |
| 1.5 | Repoint the three PDF builders | DONE | `a84c3aa` |
| 1.6 | Bind `make serve` to 127.0.0.1 | DONE | `a84c3aa` |
| 2.1–2.6 | Honesty pass: 73 dead claims → 0; gate repo-wide in CI | DONE | `73694d9`, `d933708`, `258509a` |
| 3.1 | mypy 79 → 0, blocking | DONE | `6b88bee` |
| **3.2** | **Coverage 92% → 95%, gate at 94%** | **PARTIAL** | see T4 |
| 3.3 | Console component tests 10 → 28 | DONE | `280dde3` |
| 3.4 | Playwright e2e, 10 specs | DONE | `248a4b5` |
| 3.5 | Split `api/main.py` 1,225 lines → 7 modules | DONE | `9d3e7af` |
| 3.6 | Fast lane under 5 min | DONE | `280dde3` |
| 4.1 | Second adversary: marginal-ratio (ζ) attack, AUC 0.59 vs NN at chance | DONE | `synthproof/attacks/marginal_ratio.py`, `results/ADVERSARY_COMPARISON.md` |
| 4.2 | Third dataset, UCI Bank Marketing (reduced grid) | DONE | `76a14ff`, `results/bank/BANK_MARKETING.md` |
| 4.3 | Budget tightening, off by default | DONE | `synthproof/accounting/calibration.py`, `tests/test_budget_tightening.py` |
| 4.4 | Gaussian copula | **CUT** (deliberate) | see tracker |
| 5.1 | Kill stale planning docs; one tracker | DONE | `6a03701` |
| 5.2 | Rewrite outer README | DONE | outer `c9a7f5c` |
| 5.3 | One INDEX, one archive, one pitch deck | DONE | outer `3b15c6c` |
| 5.4 | Merge to master, tag v1.0.0 | DONE | tag on `28dc59d` |
| **5.5** | **Zenodo DOI; verify `docker compose up`** | **PARTIAL** | see T8 and §8 |
| 6.1 | Rehearsed offline demo with fallback | DONE | `scripts/setup_demo.py`, `docs/DEMO_SCRIPT.md` |
| 6.2 | `CONTRIBUTIONS.md` matching git history | DONE | outer `d4767fc`, `df2a79c` |
| 6.3 | Rehearsal pack for the hardest questions | DONE | `docs/defence/REHEARSAL.md` |

### 6.2 Fixes made on 2026-09-13 that are not separate tracker rows

| Commit | What | Why it matters to you |
|---|---|---|
| `45969ec` | Claims gate now sweeps repo root, `CITATION.cff`, outer docs; found 4 live dead claims; `ceiling-as-ours` regex given a word boundary | New prose anywhere is now checked (§4 trap 12) |
| `7fb908d` | Dockerfile rewritten: 3 real stages, console built in-image, non-root, `.dockerignore` added | **Never executed** — see T8 |
| `7190098` | Tests for `audit-power` and `export-capsule`; `run_h1.H1_ONLY` declares Bank as H1-only | `tests/test_cli_audit_power_and_capsule.py` |
| `5382a14` | **Audit-range verdict rewritten** (below); demo capsules rebuilt from real releases | The most important change of the day |
| `1447837` | Prototype launcher banner no longer lists fabricated releases; demo ledger seeds labelled `illustrative-` | `run_prototype.py`, `synthproof/api/state.py` |
| `28dc59d` | Version 1.0.0 everywhere; `CHANGELOG.md` with known gaps first | |
| `8ce7dc0` | `ARTIFACT.md` limitations corrected (three had become false) | |

**The audit-range verdict** (`synthproof/audit/ceiling.py::range_verdict`) is the single source
used by the capsule, CLI (`verify-capsule`), API (`/api/capsule/verify`,
`/api/certificate/verify`) and the console (`web/src/components/VerifierModal.tsx`). Checks, in
priority order:

| # | Condition | `code` | `tone` |
|---|---|---|---|
| 1 | audited > proved | `AUDIT_CONTRADICTS_PROOF` | fail |
| 2 | estimator is `gdp` (ceiling in μ) | `CEILING_UNITS` | warn |
| 3 | reported ceiling ≠ `ceiling_for(estimator, budget, alpha)` | `CEILING_MISMATCH` | fail |
| 4 | no ceiling | `NO_CEILING` | warn |
| 5 | no proved ε | `NO_CLAIM` | warn |
| 6 | proved > ceiling | `CLAIM_EXCEEDS_AUDIT_RANGE` | warn |
| 7 | in range, audited = 0 | `IN_RANGE_NOT_DETECTED` | ok |
| 8 | in range, audited > 0 | `IN_RANGE_CONSISTENT` | ok |

Report fields: `claim_in_audit_range`, `range_code`, `range_tone`, `range_explanation`,
`lod_status` (the human label), `recomputed_ceiling`. **There is no `lod_safe` field any more,
and no outcome is called "safe". Do not reintroduce either.** Tests: `tests/test_range_verdict.py`.

Demo capsules (built by `scripts/generate_demo_capsules.py` from real `synthproof run --sign`
releases on 3,000 UCI Adult rows):

| File | proved ε | audited | ceiling (30 canaries) | verdict |
|---|---:|---:|---:|---|
| `demo_capsules/uci_adult_verified_capsule.html` | 0.912 | 0.000 | 2.254 | IN RANGE · NOT DETECTED |
| `demo_capsules/uci_adult_eps8_claim_exceeds_audit_range_capsule.html` | 7.356 | 0.000 | 2.254 | CLAIM EXCEEDS AUDIT RANGE |

---

## 7. What has to be done — task specifications

Every task has: **Why**, **Files**, **Steps**, **Acceptance** (commands + expected result — all
must be executed and their output kept for your report), and **Do not**.

Priority: **P1** = correctness/security, **P2** = integrity of submitted documents,
**P3** = completeness.

---

### T1 — Set up your branch  ·  P1  ·  ~5 min

**Steps**

```bash
cd D:/03_Study/CAPSTONE/SynthProof
git fetch origin
git status --short          # must print nothing; if not, STOP and report
git switch -c gemini/handoff-2026-09 origin/audit-fixes-and-acs
git log --oneline -1        # must be 9ec49d5
```

Run the baseline so you know what "green" looked like before you touched anything:

```bash
./.venv311/Scripts/python.exe -m pytest -p no:cacheprovider -m "not slow" -q > /tmp/baseline.txt 2>&1; echo "exit=$?"
tail -3 /tmp/baseline.txt
./.venv311/Scripts/python.exe scripts/check_thesis_claims.py --all > /dev/null 2>&1; echo "claims exit=$?"
```

**Acceptance:** branch exists at `9ec49d5`; baseline exit codes recorded in your report. If the
baseline is **not** green, record exactly which tests fail and continue — do not "fix" them
unless they are in scope of a later task.

---

### T2 — Close the verification key-trust gap  ·  P1 (security)  ·  ~2–3 h

**Why.** `signing.verify_datasheet` is documented correctly: *"Verifying against the key embedded
in the sheet would prove only that the sheet signed itself."* But two callers do exactly that:

- `synthproof/capsule/generator.py`, `verify_capsule()` (around line 520): when no key is supplied
  it loads `sheet["public_key"]` and verifies against it, then returns `"verified": True`.
- `synthproof/api/routes/artifacts.py`, `verify_certificate_endpoint()` (line 45):
  `pubkey = req.public_key or sheet.get("public_key")`, then `signature_valid = True`.

So anyone can generate a keypair, write any sheet, sign it, and get `verified: True` /
`signature_valid: True`. The signature is internally consistent, but nothing ties it to the
publisher. This is the same failure the project already fixed in its docs ("a signature proves
who made a claim, not that it is true") — here it does not even prove *who*.

**Required behaviour (implement exactly this; do not invent a different model):**

1. Distinguish two outcomes in every verify report:
   - `key_source: "supplied"` — the verifier passed a key (CLI `--key-path`, API `public_key`)
     and the signature verifies against it.
   - `key_source: "embedded"` — no key was supplied; the signature verifies only against the key
     the sheet carries.
2. Add `key_fingerprint`: the first 16 hex characters of SHA-256 over the raw public key bytes,
   so a person can compare it with a published fingerprint.
3. `verified` / `signature_valid` stays `True` only for a mathematically valid signature, but add
   `publisher_authenticated: bool` which is `True` **only** when `key_source == "supplied"`.
4. **CLI `verify-capsule`:** when no `--key-path` is given, still print the signature result, but
   print a yellow line stating the key was not checked against a publisher key, with the
   fingerprint. Exit code: unchanged (0) for embedded-key success; 1 for any invalid signature,
   and 1 (as today) for a `fail` range tone.
5. **API `/api/certificate/verify`:** same fields. If neither `public_key` nor an embedded key
   exists, keep the existing error message.
6. **Console `VerifierModal.tsx`:** when `publisher_authenticated` is false, show an amber note
   "Signature is valid, but was checked only against the key inside the file (fingerprint
   XXXX). Compare this fingerprint with the publisher's before trusting it." Update the TS
   types in `web/src/types.ts` and `web/src/lib/api.ts`.
7. **The offline capsule's in-browser verifier** (`synthproof/capsule/verifier.js`) necessarily
   uses the embedded key. Make its success message say the same thing (valid signature by key
   with fingerprint X; publisher not authenticated). **`verifier.js` is inlined into the capsule
   by `generator.py::_verifier_source()` and read by `web/src/lib/capsuleVerify.test.ts` — both
   must keep passing.** After changing it, regenerate the demo capsules:
   `PYTHONIOENCODING=utf-8 ./.venv311/Scripts/python.exe scripts/generate_demo_capsules.py`.

**Files:** `synthproof/capsule/generator.py`, `synthproof/api/routes/artifacts.py`,
`synthproof/cli.py`, `synthproof/capsule/verifier.js`, `web/src/types.ts`, `web/src/lib/api.ts`,
`web/src/components/VerifierModal.tsx`, `demo_capsules/*.html` (regenerated), new tests.

**Tests to add** (new file `tests/test_verify_key_trust.py`):

- a sheet signed with key A, verified with no key → `verified True`, `key_source "embedded"`,
  `publisher_authenticated False`, fingerprint = SHA-256(A)[:16];
- same sheet verified with key A supplied → `publisher_authenticated True`;
- same sheet verified with key B supplied → verification fails (raises / `verified False`);
- **the forgery case, as its own test:** generate an attacker key, sign a sheet claiming ε = 0.01,
  verify with no key → assert `publisher_authenticated is False` (this is the test that proves
  the gap is closed);
- API: POST `/api/certificate/verify` with and without `public_key`, asserting the new fields;
- CLI: `verify-capsule` without `--key-path` prints the not-authenticated warning and exits 0;
  with a wrong `--key-path` exits 1.

**Acceptance**

```bash
./.venv311/Scripts/python.exe -m pytest tests/test_verify_key_trust.py tests/test_capsule.py \
  tests/test_cli_commands.py tests/test_api_tamper_and_verify.py tests/test_range_verdict.py \
  -p no:cacheprovider -m "" -q                    # all pass
cd web && npx tsc --noEmit && npx vitest run --config vitest.config.ts && cd ..   # all pass
./.venv311/Scripts/python.exe -m mypy synthproof     # clean
grep -n "publisher_authenticated" demo_capsules/uci_adult_verified_capsule.html || true   # only if you embed it
```

Plus: CI green on the commit (all 7 jobs).

**Do not:** remove the embedded key from sheets; change the signing payload format (that would
invalidate every existing signature); make embedded-key verification *fail* (the offline capsule
must still work); change `range_verdict`.

---

### T3 — Test the audit-range verdict in the console  ·  P1  ·  ~1–2 h

**Why.** The verdict was rewired in the console in `5382a14`, but `web/src/components/components.test.tsx`
has no test for the range box. The previous version rendered green for a claim no audit could
certify; nothing in the console suite would catch that coming back.

**Steps**

1. In `web/src/components/components.test.tsx`, in the `VerifierModal` `describe` block, add
   tests that mock `api.verifyCertificate` (follow how existing tests mock the API in that file)
   and render the result for three responses:
   - `range_tone: 'ok'`, label `IN RANGE · NOT DETECTED` → the range box has `border-signal-ok/50`;
     the explanation text is rendered;
   - `range_tone: 'warn'`, label `CLAIM EXCEEDS AUDIT RANGE` → `border-signal-warn/50`; no
     `signal-ok` class anywhere in the box;
   - `range_tone: 'fail'`, label `CEILING DOES NOT MATCH ITS AUDIT` → `border-signal-bad/50`.
2. Add one assertion that the old strings are absent: `valid detection zone`, `MIQE 2.0 Operating Range`.
3. Add a Playwright spec in `web/e2e/console.spec.ts`: upload
   `demo_capsules/uci_adult_eps8_claim_exceeds_audit_range_capsule.html` through the verifier's
   file input and assert the badge text `CLAIM EXCEEDS AUDIT RANGE` is visible. Read the existing
   capsule spec (`the capsule, end to end`, around line 164) first and reuse its setup. **Wait for
   the badge to be visible before any negative assertion** (trap 8).

**Acceptance**

```bash
cd web
npx vitest run --config vitest.config.ts        # 28 + your new tests, all pass
npx playwright test --list                      # shows your new spec
npm run test:e2e                                # all non-slow specs pass
```

Negative control (mandatory, report it): temporarily change `RANGE_BOX.warn` in
`VerifierModal.tsx` to the `ok` classes, confirm your warn test **fails**, then revert. State in
your report that you did this and paste the failing line.

**Do not:** snapshot-test the whole modal (brittle, and it would pin the explanation wording).

---

### T4 — Finish coverage (tracker 3.2)  ·  P3  ·  ~3–5 h

**Why.** The gate is 90%. The plan was 94%. The fast lane measures 92%. The gate may only be
raised on a **full-suite** measurement, locally and in CI.

**Steps**

1. Measure the full suite first and save it:

   ```bash
   ./.venv311/Scripts/python.exe -m pytest -p no:cacheprovider -m "" \
     --cov=synthproof --cov-report=term-missing > cov_full_before.txt 2>&1; echo "exit=$?"
   grep "^TOTAL" cov_full_before.txt
   ```

2. Write **behavioural** tests (assert outcomes, not just that code ran) for, in this order:
   - `synthproof/api/routes/artifacts.py` — `/api/certificate/verify` (lines ~42–89): valid
     signature with supplied key; missing key → `error` set and `signature_valid False`; tampered
     `total_proved_eps` → `error` set; the four range tones appear in the response for sheets
     built to hit them; `/api/croissant/export` with an unsigned sheet → HTTP 400 whose detail
     contains "unsigned". Use `fastapi.testclient.TestClient(app)` and the ledger-reset fixture
     pattern in `tests/test_api_tamper_and_verify.py`. Build signed sheets with
     `signing.generate_keypair(key_dir=tmp_path)` + `signing.sign_datasheet(sheet, key_path=...)`
     as `tests/test_capsule.py` does.
   - `synthproof/evaluate/fairness.py` (86%)
   - `synthproof/frontier/checkpoint.py` (88%)
   - `synthproof/accounting/differential.py` (89%)
   - `synthproof/generators/base.py`, `synthproof/accounting/types.py` (87%)
   - remaining `synthproof/cli.py` lines (run coverage on it to list them)
3. Re-measure the full suite (`cov_full_after.txt`).
4. **Only if** the local full-suite TOTAL is **≥ 94%**: change `--cov-fail-under=90` to `94` at
   `.github/workflows/ci.yml` line 73, push, dispatch CI, and confirm the three `test` jobs pass.
   If CI measures below 94 (CI runs on Linux with all three Python versions), **revert the gate to
   90 in a follow-up commit** and report both numbers.
5. Update tracker row 3.2 in `docs/ROAD_TO_TEN.md` with before/after numbers copied from the
   files, and the CI run ID.

**Acceptance:** before/after TOTAL lines quoted verbatim in your report; all new tests pass; CI
green; tracker row updated. If 94 is not reached, row stays PARTIAL with the measured number.

**Do not:** use `# pragma: no cover`; add tests that only import a module; lower any other gate;
change `pyproject.toml` coverage `omit` lists.

---

### T5 — Correct stale and retracted content in the thesis and defence pack  ·  P2  ·  ~2–4 h

**Why.** These documents are submitted and examined. The claims gate passes them, but they
contain statements that are now false. **This is prose owned by the student team, so your job is
minimal factual correction plus a written record of every change — not rewriting their argument.**

**Known items (verify each by opening the file at the line; line numbers may drift by a few):**

| # | File : line | Problem | Required correction |
|---|---|---|---|
| 1 | `docs/thesis/ch01-introduction.md` : ~55 (§1.4, contribution 1) | Lists the **clique-selection result as contribution #1** ("We show that…"). That result was **retracted on 2026-08-25** — see `results/SELECTION_ABLATION.md` and `results/RESULTS.md` | Replace contribution 1 with the replication framing already used in `results/RESULTS.md` (a replication with a selection-deleted control arm; measuring helps in proportion to true dependence, r = −0.898; the phenomenon was published three times — AIM's paper arXiv:2201.12677 §5, Ganev/Xu/De Cristofaro CCS 2024 §5.3, Chen/Gong/Wang arXiv:2511.13893 §6.3). Copy numbers only from those files |
| 2 | `docs/thesis/ch07-results.md` : ~109 | Frames the same result as a benchmark confound | Add the retraction note; do not delete the numbers, relabel their interpretation per `results/SELECTION_ABLATION.md` |
| 3 | `docs/thesis/ch03-threat-model.md` : ~81 | Quotes an audit ceiling of **2.45** against proved **8.0**. 2.45 matches no budget: the one-run ceiling at α = 0.05 is 2.254 at 30 canaries, 2.415 at 35, 2.554 at 40, 2.972 at 60 | Replace with a sourced pair: ceiling **2.972** at 60 canaries against proved **7.36** (the H1 grid), citing `results/DETECTION_FLOOR.md`. Recompute the ceiling yourself: `./.venv311/Scripts/python.exe -c "from synthproof.audit.steinke import max_provable_epsilon as m; print(m(60,0.05))"` |
| 4 | `docs/thesis/ch08-evidence.md` : ~63 (limit 1) | "The adversary is a nearest-neighbour score. MAMA-MIA-class attacks… stronger" | A marginal-ratio adversary now exists (`results/ADVERSARY_COMPARISON.md`): NN at chance (0.498–0.538 AUC) on structured mechanisms; marginal-ratio reaches 0.59 (+0.092). It uses oracle focal points and is **not** MAMA-MIA. State both facts; the limit remains that no shadow-model attack is implemented |
| 5 | `docs/thesis/ch08-evidence.md` : ~65 (limit 3) and `docs/defence/DEFENCE.md` : ~531, ~855 | "Two datasets, both US census-derived" | Three datasets: two census-derived with the full grid, plus UCI Bank Marketing (non-census) on a reduced grid, with the transfer finding from `results/bank/BANK_MARKETING.md` |
| 6 | `docs/thesis/ch01-introduction.md` : ~39, `docs/thesis/ch08-discussion.md` : ~27 | Describe the artefact as reporting non-detections as "Not Detected, < LoD" | The convention transfer is correct and stays. Add that the artefact's verdict compares the **proved** ε with the ceiling and reports `CLAIM EXCEEDS AUDIT RANGE` when the audit could not certify the claim (see `docs/MEASUREMENT_CONVENTIONS.md` §2 correction note) |
| 7 | Anywhere in `docs/thesis/ch0*.md` or `docs/defence/*.md` | Any sentence implying AIM is the best mechanism in general | Restrict to UCI Adult; cite `results/bank/BANK_MARKETING.md` |

**Also search for, and treat the same way:**

```bash
rg -n -i "two datasets|both datasets|best mechanism|nearest-neighbour score|846|lod_safe|Bounded under MIQE" docs/thesis/ch0*.md docs/defence/ docs/simple/SIMPLE.md
```

Note: "both datasets" is **correct** where it refers to H2/H3, which were run on Adult and ACS
only. Do not change those; change only statements about the project's dataset coverage.

**Steps**

1. Make each correction in the chapter source. Keep the authors' voice; change the minimum.
2. Create `docs/thesis/CORRECTIONS_2026-09.md`: one table row per change — file, line, **exact
   before text**, **exact after text**, source file for any number.
3. Rebuild the assembled thesis: `./.venv311/Scripts/python.exe scripts/build_thesis.py`. Commit
   the regenerated `docs/thesis/THESIS.md` in the same commit.
4. Run the claims gate and fix any hit **in the prose**.

**Acceptance**

```bash
./.venv311/Scripts/python.exe scripts/check_thesis_claims.py --all > /dev/null 2>&1; echo "claims exit=$?"   # 0
./.venv311/Scripts/python.exe scripts/check_citations.py > /dev/null 2>&1; echo "citations exit=$?"          # 0
git diff --stat origin/audit-fixes-and-acs -- docs/thesis docs/defence   # only intended files
```

**Do not:** rewrite sections wholesale; add new claims or new citations you did not open and
read; touch `docs/thesis/WRITING_NOTICE.md`'s quoted dead-claim lists; change any number without a
source file.

---

### T6 — Close the claims-gate blind spot that let T5 item 1 through  ·  P2  ·  ~1–2 h

**Why.** `scripts/check_thesis_claims.py` has a rule `clique-confound-as-finding`, yet
`docs/thesis/ch01-introduction.md` §1.4 lists the retracted result as a numbered, bold
contribution and the gate reports `OK`. A gate that passes the contributions list of the thesis
is the most expensive blind spot it can have.

**Steps (order matters — test first):**

1. **Before T5 changes ch01** (or using `git show origin/audit-fixes-and-acs:docs/thesis/ch01-introduction.md`),
   copy the exact evading text of contribution 1 (heading + first sentence) into a new test in
   `tests/test_thesis_claims_checker.py`, following the existing pattern (`_write(tmp_path, text)`
   then `labels(check(path))`). Assert `"clique-confound-as-finding" in labels(...)`. Run it and
   **confirm it fails** on the current rule. Paste the failure in your report.
2. Widen the rule's pattern in `DEAD_CLAIMS` so the test passes. Add a comment above the pattern
   explaining the shape it now catches and the date, in the same style as neighbouring comments.
3. Add **negative controls** so it has not gone blind the other way:
   - the replication framing from `results/RESULTS.md` (the "Selection ablation" row) must NOT
     trip it;
   - a sentence that mentions the retraction ("the clique-selection result was retracted") must
     NOT trip it.
4. Run the whole checker suite and the repo-wide gate.

**Acceptance**

```bash
./.venv311/Scripts/python.exe -m pytest tests/test_thesis_claims_checker.py -p no:cacheprovider -q   # all pass
./.venv311/Scripts/python.exe scripts/check_thesis_claims.py --all > /dev/null 2>&1; echo "exit=$?"  # 0 after T5
```

Also report: running the gate on `git show origin/audit-fixes-and-acs:docs/thesis/ch01-introduction.md`
saved to a temp file must now **flag** it.

**Do not:** add ch01 or any file to an exemption; loosen any other rule; delete existing tests.

---

### T7 — Rebuild the deliverable PDFs after T5  ·  P2  ·  ~30 min + build time

**Why.** `01_Thesis_and_Deliverables/*.pdf` in the outer repo are built from the Markdown. After
T5 they are stale. The rule in `INDEX.md`: if a PDF disagrees with its source, the source is right.

**Steps**

```bash
cd D:/03_Study/CAPSTONE/SynthProof
./.venv311/Scripts/python.exe scripts/build_thesis.py            > build_thesis.log 2>&1; echo "exit=$?"
./.venv311/Scripts/python.exe docs/defence/build_pdf.py          > build_defence.log 2>&1; echo "exit=$?"
./.venv311/Scripts/python.exe docs/simple/build_pdf.py           > build_simple.log 2>&1; echo "exit=$?"
ls -la ../01_Thesis_and_Deliverables/*.pdf                        # timestamps must be new
```

If a builder fails because a dependency is missing, **report it as blocked** with the error. Do
not install system packages without saying so in the report.

**Commit (outer repo, explicit paths only):**

```bash
cd D:/03_Study/CAPSTONE
git add "01_Thesis_and_Deliverables/SynthProof-Thesis.pdf" \
        "01_Thesis_and_Deliverables/SynthProof-Defence-Pack.pdf" \
        "01_Thesis_and_Deliverables/SynthProof-Simple-Guide.pdf"
git status --short        # confirm REPORTS/, synopsis/, 03_.../COMPLETE-CODEBASE... are NOT staged
git commit -m "[T7] build: regenerate deliverable PDFs after the 2026-09 corrections ..."
```

State in the commit message and your report that these three PDFs **had pre-existing uncommitted
modifications** before your rebuild (§5.4), and that the rebuild replaced them.

**Acceptance:** three builders exit 0; new timestamps; only the three PDFs staged; spot-check one
corrected sentence from T5 appears in the rebuilt thesis PDF (extract text with
`./.venv311/Scripts/python.exe -c "import pypdf; ..."` if `pypdf` is available, otherwise state you
could not check).

**Do not:** commit anything else in the outer repo in this task; add a git remote.

---

### T8 — Execute the Docker path (tracker 5.5, runtime half)  ·  P3  ·  ~1 h, needs Docker

**Why.** The Dockerfile was rewritten after static review only; it has never been built.

**Precondition:** `docker info` must exit 0. **If it exits non-zero, STOP this task, report
"BLOCKED: Docker daemon not running", and move on.** Do not start Docker Desktop yourself unless
you are certain you are allowed to, and do not claim any result.

**Steps (if unblocked)**

```bash
cd D:/03_Study/CAPSTONE/SynthProof
docker compose build > docker_build.log 2>&1; echo "build exit=$?"
docker compose up -d;                          echo "up exit=$?"
# wait for health, polling -- do not sleep blindly
for i in $(seq 1 30); do curl -fsS http://127.0.0.1:8000/api/health && break; sleep 2; done
curl -fsS http://127.0.0.1:8000/ | head -c 300            # console HTML, not a 404
curl -fsS http://127.0.0.1:8000/api/mechanisms
docker compose exec api id                                # uid must be 10001 (non-root)
docker compose down
```

Also run one release through the API (look at `tests/test_api.py::_run` for the request body)
and record the proved ε it returns.

**Acceptance:** all exit codes 0; `/api/health` JSON quoted; console HTML present; `uid=10001`;
`/api/mechanisms` output quoted — **it is expected to show AIM as unavailable** (private-pgm is not
in the image; that is a documented decision, not a bug for you to fix). Update tracker row 5.5
(runtime half) and `CHANGELOG.md` "Known gaps" only with what you actually observed.

**Do not:** add private-pgm / a git dependency to the image; change `docker-compose.yml` ports or
volumes unless the build fails, and then explain why.

---

### T9 — Full grid for UCI Bank Marketing  ·  P3  ·  ~4–5 h of compute

**Why.** The finding that AIM's advantage does not transfer rests on a **reduced** grid, whose
weakest point is statistical power. The full preregistered grid either confirms the tie or
resolves it. Either outcome must be reported.

**Steps**

1. Run in the background with a log. Checkpoints are written per cell to
   `results/bank/h1_cells/`, so the run is resumable.

   ```bash
   PYTHONIOENCODING=utf-8 ./.venv311/Scripts/python.exe -m scripts.run_h1 --dataset bank \
     > results/bank/h1_full.log 2>&1; echo "exit=$?"
   ```

   This overwrites `results/bank/h1_all_families.json` with `reduced_run: false`,
   5 ε × 5 seeds × 3 mechanisms = 75 cells. **Delete `results/bank/h1_cells/` first**, or the
   18 reduced-run checkpoints will be reused and mixed in — check `scripts/run_h1.py` and
   `synthproof/frontier/checkpoint.py` to confirm how checkpoints are keyed before deciding.

2. Generate the comparison tables **with a script**, not by hand. Adapt the snippet in
   `results/bank/BANK_MARKETING.md`'s history (the cross-dataset table in §5.3 above was produced by
   reading the three JSON files). Save the script as `scripts/compare_bank_full.py` and commit it.
3. Rewrite `results/bank/BANK_MARKETING.md` for the full grid: keep the structure; replace every
   number from the script output; keep a short "what changed from the reduced run" section.
   **If the conclusion changes, say so in the first paragraph.**
4. Update: `results/RESULTS.md` (the "Third dataset" row), `docs/ROAD_TO_TEN.md` row 4.2 and its
   log, `CHANGELOG.md` known gaps (remove the reduced-grid item), outer `README.md` (the
   "reduced grid" sentence), `ARTIFACT.md` §8.
5. Reproducibility manifest: `./.venv311/Scripts/python.exe scripts/reproduce.py` — if it reports a
   difference for the Bank files, **read the diff**, then update the manifest per the script's own
   instructions, and quote the diff summary in the commit message.

**Acceptance:** JSON has `reduced_run: false` and 15 aggregated cells (3 mech × 5 ε); every number
in the rewritten document matches the script output (reviewer will diff them); claims gate exit 0.

**Do not:** cherry-pick seeds; drop a mechanism; rerun until a result looks better; hand-type a
single table cell.

---

### T10 — Mark stale audit documents as historical  ·  P3  ·  ~45 min

**Why.** `03_System_Audits_and_Handovers/*.md` (outer repo) are not swept by the claims gate and
contain wording that is now retracted or false (e.g. old ledger wording, the unreplicated canary
figure, the old badge text, "5 core novelties"). A reader can mistake them for current.

**Steps.** For each of these files in the outer repo:
`CAPSTONE-DEEP-VERIFICATION.md`, `CAPSTONE-FOLDER-ANALYSIS.md`, `CAPSTONE-REEXECUTION-VERIFICATION.md`,
`CAPSTONE-SORTED-HANDOVER.md`, `NOVELTY-RESEARCH-AND-PLAN.md`, `PROJECT_CONTEXT.md`,
`SYNTHPROOF-COMPLETION-PLAN.md` — insert **directly under the first heading** a banner:

```markdown
> **Historical record (banner added 2026-09).** This document describes the project as it was
> when written and is kept as evidence. Parts of it are superseded or retracted. For the current
> state see `SynthProof/docs/ROAD_TO_TEN.md` and `SynthProof/CHANGELOG.md`; for retractions see
> `SynthProof/results/RESULTS.md`.
```

Do **not** edit the body text. Do **not** touch
`COMPLETE-CODEBASE-AND-SYSTEM-EXPLANATION.md` (it is untracked and not yours — §5.4).

**Acceptance:** 7 files changed, each diff is exactly the banner insertion
(`git diff --stat` and `git diff` quoted briefly); committed in the outer repo with explicit paths.

---

### T11 — Merge your branch's verified work toward master: PREPARE ONLY  ·  P3

**You do not merge.** When all your tasks are done and CI is green on your branch HEAD:

1. `git log --oneline origin/audit-fixes-and-acs..gemini/handoff-2026-09` — list it in the report.
2. Confirm `git merge-base --is-ancestor origin/master gemini/handoff-2026-09` prints nothing and
   exits 0 (fast-forward possible).
3. Stop. The reviewer merges after review.

---

## 8. Tasks you must NOT attempt

These need a human, an account, or a decision that belongs to the team. **Mention them in your
report as untouched.**

| Item | Why it is not yours |
|---|---|
| Create a GitHub Release, or anything on Zenodo | Needs the owner's accounts; order matters (enable Zenodo webhook first, then Release from tag `v1.0.0`). See `ARTIFACT.md` §7 |
| Fill `CONTRIBUTIONS.md` §3 teammate rows | Each member must write their own |
| The institutional AI-assistance declaration | A human obligation |
| Add a git remote to the outer repo, or push it anywhere | Publishing decision |
| Flip `BudgetPlan` tightening on by default | Changes every published ε |
| Add private-pgm (AIM) to the Docker image | Adds a git dependency to the image; a deliberate decision |
| Move or recreate tag `v1.0.0`; push to `master` | Released, CI-verified state |
| Adding a shadow-model attack or a Gaussian copula | LiRA stays unimplemented by decision (declared in `ATTACKS_NOT_IMPLEMENTED`); tracker 4.4, the copula, was cut |
| Rewrite the novelty verdict or promote any survivor claim | `research/08_novelty_verdict.md` is the adversarial record |

---

## 9. Order of work, and how to report

### 9.1 Order

```text
T1  branch + baseline
T6  step 1 only (write the failing test against the ORIGINAL ch01 text)   <- before T5
T2  key-trust gap            (code; CI)
T3  console verdict tests    (code; CI)
T5  thesis/defence corrections
T6  steps 2-4 (widen the rule; gate green with T5 applied)
T7  rebuild PDFs             (after T5)
T4  coverage                 (after T2/T3, which add tests)
T8  Docker                   (skip if blocked)
T9  Bank full grid           (start the run early in the background; it takes hours)
T10 historical banners
T11 prepare, do not merge
```

Start T9's run in the background right after T1 if you can, since it only reads committed code
paths that the other tasks do not change (`scripts/run_h1.py`, `synthproof/frontier/experiment.py`,
the generators). If any other task changes those files, stop T9 and restart it afterwards.

### 9.2 Report format — produce exactly this, in a file `docs/AGENT_REPORT_2026-09.md`, committed last

```markdown
# Agent report — <date>

## Summary
| Task | Status (DONE / PARTIAL / BLOCKED / NOT STARTED) | Commits | CI run ID |

## T<n> — <title>
**Status:** ...
**What I changed:** files, one line each
**Commands run and their exit codes** (copied, not paraphrased):
**Numbers before → after**, each with the command that produced it:
**Negative controls performed** (what I broke on purpose, what failed, how I reverted):
**Deviations from the spec, and why:**
**Not done, and why:**

## Things I noticed but did not fix
## Human-only items left untouched (from §8)
```

Rules for the report: no number without a command; no "should", "likely", "probably" about
something you could have run; list every failed attempt that changed your approach.

---

## 10. How your work will be verified

The reviewer (Claude) will run, at minimum:

1. **History:** `git log --format='%h %s%n%b' origin/audit-fixes-and-acs..gemini/handoff-2026-09`
   — every commit has a task ID, a reason, and the `Assisted-by: Gemini` trailer; no force-push
   (`git reflog` on the remote-tracking branch), `master` and `v1.0.0` unchanged.
2. **CI:** every run ID you cite exists, targets the SHA you claim, and is green on all 7 jobs.
3. **Full test suite locally**, including slow tests, and the full-suite coverage number,
   compared to the number you reported.
4. **Gates:** ruff, black, mypy, claims gate, citations gate, `tsc`, vitest, Playwright.
5. **Negative controls re-done** for T2 (forged sheet), T3 (tone swap), T6 (original ch01 text).
6. **Number audit:** at least five numbers from your documents recomputed from the JSON/results
   files or the code. A single invented or retyped-wrong number fails the task it appears in.
7. **Scope audit:** `git diff --stat` for both repos — nothing outside each task's file list; none
   of §5.4's pre-existing outer files staged; no exemptions or `pragma: no cover` added; no gate
   lowered.
8. **Behaviour checks:** open both demo capsules; run `verify-capsule` with and without a key and
   with a wrong key; POST a forged sheet to `/api/certificate/verify`.
9. **Report honesty:** every "DONE" backed by its acceptance output; every "BLOCKED" genuinely
   blocked.

---

## 11. Reference: numbers, files, commands

### 11.1 Numbers you may need (with how to recompute)

| Quantity | Value | Recompute |
|---|---:|---|
| One-run ceiling, α = 0.05, r = 30 | 2.254 | `max_provable_epsilon(30, 0.05)` in `synthproof.audit.steinke` |
| … r = 60 | 2.972 | same, `60` |
| … r = 100 | 3.493 | same, `100` |
| Paired Clopper-Pearson ceiling, m = 800 (measured) | 5.377 | `synthproof/audit/ceiling.py::_PAIRED_CP_MEASURED` |
| Canaries needed to certify ε = 1.0 / 7.36 | 10 / 4,711 | `canaries_needed_for(eps, 0.05)` |
| CLI release, pairwise, ε target 1.0 → proved | 0.912 | `synthproof run --eps 1.0` on 3,000 Adult rows |
| … ε target 8.0 → proved | 7.356 | same, `--eps 8.0` |
| Largest proved ε in H1 grid | 7.36 (AIM composes to 6.54) | `results/h1_all_families.json` |
| Budget under-spend, linear split / tightened | 0.908 / > 0.995 of target | `tests/test_budget_tightening.py` |
| NN attack AUC on structured mechanisms | 0.498–0.538 | `results/adversary_comparison.json` |
| Marginal-ratio attack best AUC / max gain | 0.59 / +0.092 | same |
| Commits at `v1.0.0` / with Claude trailer | 151 / 146 | `git rev-list --count v1.0.0`; `git log v1.0.0 --format=%B \| grep -c "Co-Authored-By: Claude"` |

### 11.2 Where things are

| Thing | Path |
|---|---|
| Tracker (source of truth for status) | `docs/ROAD_TO_TEN.md` |
| Release notes / known gaps | `CHANGELOG.md` |
| Audit-range verdict | `synthproof/audit/ceiling.py` (`range_verdict`, `recompute_ceiling`, `ceiling_for`) |
| Signing | `synthproof/ledger/signing.py` |
| Ledger | `synthproof/ledger/ledger.py` |
| Privacy Data Sheet | `synthproof/frontier/certificate.py` (`PrivacyDataSheet`, `ATTACKS_NOT_IMPLEMENTED = ["LiRA"]`) |
| Capsule generator + Python verifier | `synthproof/capsule/generator.py` |
| Capsule browser verifier (shared with console tests) | `synthproof/capsule/verifier.js` |
| CLI | `synthproof/cli.py` (click) |
| API | `synthproof/api/main.py`, `state.py`, `routes/{run,datasets,ledger,artifacts}.py` |
| Console | `web/src/components/*.tsx`, types in `web/src/types.ts`, client in `web/src/lib/api.ts` |
| E2E | `web/e2e/console.spec.ts`, config `web/playwright.config.ts` |
| H1 runner | `scripts/run_h1.py` (`--dataset {adult,acs,bank} --eps ... --seeds ... --out ...`) |
| Claims gate + its tests | `scripts/check_thesis_claims.py`, `tests/test_thesis_claims_checker.py` |
| Demo capsules builder | `scripts/generate_demo_capsules.py` |
| Demo fixtures builder | `scripts/setup_demo.py` |
| Thesis chapters / builder | `docs/thesis/ch0*.md` → `scripts/build_thesis.py` → `docs/thesis/THESIS.md` |
| Defence pack / builder | `docs/defence/DEFENCE.md` → `docs/defence/build_pdf.py` |
| Measurement convention (MIQE transfer, ceiling attribution) | `docs/MEASUREMENT_CONVENTIONS.md` |
| Results index (incl. retractions) | `results/RESULTS.md` |
| Novelty verdict | `research/08_novelty_verdict.md` |
| CI | `.github/workflows/ci.yml` (coverage gate line 73) |

### 11.3 Glossary

| Term | Meaning here |
|---|---|
| ε_proved | Formal upper bound on privacy loss from the accountant |
| ε_audited | Empirical lower bound from canary auditing |
| Audit ceiling | The largest ε an audit of a given budget could certify against a perfect adversary |
| Canary | A planted record used to test whether a release leaks membership |
| TSTR / TRTR | Train-on-synthetic / train-on-real, test-on-real, F1 on the target |
| Reduced grid | Fewer ε values or seeds than the preregistered 5 × 5; always flagged `reduced_run: true` |
| Claims gate | `scripts/check_thesis_claims.py`: fails CI when a document asserts a killed/retracted claim |
| Fast lane | `pytest -m "not slow"` |
