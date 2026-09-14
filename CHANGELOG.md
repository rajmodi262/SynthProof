# Changelog

## Unreleased

- **Zenodo DOI minted** from the GitHub Release `v1.1.0`: concept DOI `10.5281/zenodo.22746910` (all
  versions — cite this) and version DOI `10.5281/zenodo.22746911` (v1.1.0 exactly). This closes the 1.1.0
  known gap "No Zenodo DOI", which is left as written in the released notes below. The README
  badge and `CITATION.cff` `doi:` use the concept DOI; `identifiers:` lists both.

## 1.1.0 — 2026-09-14

Work done after 1.0.0 on branch `gemini/handoff-2026-09`, reviewed commit by commit in three
rounds against [`docs/AGENT_HANDOFF.md`](docs/AGENT_HANDOFF.md). The agent reports are
[`docs/AGENT_REPORT_2026-09.md`](docs/AGENT_REPORT_2026-09.md) and
[`docs/AGENT_REPORT_2026-09-FOLLOWUP.md`](docs/AGENT_REPORT_2026-09-FOLLOWUP.md).

### Known gaps in this release

- **`docker compose up` has still not been executed.** No Docker daemon was available.
- **No Zenodo DOI.** Minting needs the owner's Zenodo account.
- **Real AIM is not available in the Docker image** — private-pgm installs from git.
- **`CONTRIBUTIONS.md` still awaits one row per team member**, to be written by that member.
- **No shadow-model membership attack is implemented.** The marginal-ratio adversary uses oracle
  focal points and is not MAMA-MIA; LiRA remains deliberately unimplemented.

### Closed from the 1.0.0 known gaps

- **One version everywhere is now actually true.** The 1.0.0 notes said the version was stated
  consistently, but `web/package-lock.json` still recorded the console as 0.2.0. It is 1.1.0
  with everything else.

- **Coverage gate raised from 90% to 94%**, enforced in CI on Python 3.11, 3.12 and 3.13.
- **UCI Bank Marketing now carries the full preregistered grid** (5 ε × 5 seeds, 75 cells,
  `reduced_run: false`).

### Fixed — security

- **Signature verification trusted the key embedded in the file.** Both the capsule verifier and
  `/api/certificate/verify` fell back to the sheet's own public key and reported success, so a
  sheet signed with anyone's key verified. Reports now separate a valid signature from an
  authenticated publisher (`key_source`, `key_fingerprint`, `publisher_authenticated`), the CLI
  warns when no publisher key was supplied, and a forgery test pins it.
- **gitleaks exemption narrowed.** A file-wide allowlist for a console test file was removed; the
  three historical fake fingerprints it had covered are listed individually in `.gitleaksignore`.

### Fixed — honesty of results and documents

- **Bank Marketing conclusions corrected to the full grid.** At ε = 8 no mechanism separates on
  structure or on utility; pairwise separates from independent on structure only at ε = 0.5 and
  ε = 2.0. AIM's structural advantage remains specific to UCI Adult. The reduced run had shown a
  pairwise-vs-independent separation at ε = 8 that the full grid does not.
- **Bank Marketing tables are generated, not typed**, with per-pair interval-overlap flags, and a
  test fails if the committed tables drift from the result files.
- **Thesis corrections**, recorded before and after in
  [`docs/thesis/CORRECTIONS_2026-09.md`](docs/thesis/CORRECTIONS_2026-09.md): the retracted
  clique-selection result is no longer listed as contribution 1; an audit ceiling of 2.45 that
  matched no canary budget is replaced with 2.972 at 60 canaries (the one-run ceiling is a corollary of Steinke, Nasr & Jagielski 2023 Thm 2.1, named the maximum auditable epsilon by Annamalai, Ganev & De Cristofaro, arXiv:2405.10994 §2.2, and reported as a limit per MIQE 2.0); dataset coverage is stated as
  three datasets; "privacy-budgeted domain expansion" is reframed as an untested candidate
  explanation; an unsourced literature attribution is removed.

### Fixed — gates and tests

- **Claims checker:** it now catches the heading-plus-sentence form that let the retracted result
  sit in thesis chapter 1, and its hedge window stops at the end of the line — a hedge word on the
  next line no longer disarms a claim, and a distant hedge on a long line no longer blinds it. Both
  behaviours and two negative controls are pinned by tests that fail on the 1.0.0 checker.
- **Mutation probe** extended to the audit-range verdict and key trust; a mutation whose anchor
  text is missing now fails the run instead of being skipped. `results/mutation_probe.json`
  records 18 of 18 caught.
- Console tests for the verdict's three tones and an end-to-end capsule upload; an
  assertion-free coverage test replaced with behavioural assertions.

## 1.0.0 — 2026-09-13

The first tagged release. It is the state of the project after the remediation tracked in
[`docs/ROAD_TO_TEN.md`](docs/ROAD_TO_TEN.md), which records the evidence for every item below.

**Version numbers before this release were inconsistent** — `pyproject.toml` and
`synthproof/__init__.py` said 0.1.0, `web/package.json` and `CITATION.cff` said 0.2.0 — and no
release was ever tagged. 1.0.0 is the first version stated consistently everywhere.

### Known gaps in this release

Stated first, because a release note that lists only what worked is the thing this project
exists to argue against.

- **Coverage gate is 90%, not the planned 94%.** The fast lane measures 92% overall; `cli.py`
  is at 89%, `api/routes/artifacts.py` at 55%. The gate was not raised on a partial run.
- **`docker compose up` has not been executed.** The Dockerfile was rewritten after static
  review (see below), but no Docker daemon was available to run it.
- **No Zenodo DOI.** `.zenodo.json` is prepared; minting needs the owner's Zenodo account.
- **Bank Marketing carries a reduced grid** (2 ε × 3 seeds), recorded as `reduced_run: true`.
  *(Restored in 1.1.0: this line was deleted from the released 1.0.0 notes when the full grid
  landed. Released notes are a record of what was true at the tag; the gap is closed in 1.1.0.)*
- **Real AIM is not available in the Docker image** — private-pgm installs from git and is not
  a declared dependency.
- **The thesis's contributions statement is incomplete**: `CONTRIBUTIONS.md` leaves one row per
  team member to be completed by that member.

### Fixed — correctness

- **The audit-range verdict was computed backwards on every surface.** The capsule, CLI, API and
  console each showed a green `NOT DETECTED (< LoD)` when `audited < ceiling`, never comparing
  the *proved* ε with the ceiling — so a release proving ε = 7.36 against a 2.97 ceiling rendered
  green. Replaced by one `audit.ceiling.range_verdict`, which also recomputes the ceiling from
  the declared estimator, budget and α. `lod_safe` is removed.
- **The demo capsules were fabricated.** Both were hand-typed sheets signed with a real key, with
  audit ceilings their declared audits cannot produce (3.50 at 60 canaries; the maximum is
  2.972). Rebuilt from real `synthproof run --sign` releases; the fabricated ACS capsule is
  deleted.
- **The prototype launcher advertised releases and audit results that were never computed**,
  including a release on a dataset that exists nowhere in the repository. The seeded ledger
  entries are now labelled illustrative where the console displays them.
- **Two schema bounds truncated real rows** in the Bank Marketing loader (`previous` 0–60 against
  a true tail at 275), behind a test that could not fail because it compared against data already
  clipped to those bounds.
- **The capsule verifier could show a green tick** for a capsule whose cryptographic check had not
  run; it now has three outcomes and shares one verifier source with the console.
- **Budget under-spend** from linear splitting of a sublinear composition is now recoverable with
  `BudgetPlan.split(tighten=True)` — off by default, because enabling it changes every published ε.

### Fixed — honesty gates

- **73 dead claims → 0** across the repository; the claims gate runs repo-wide in CI.
- **The gate was blind to the repository root**, where it then found "append-only" in
  `CITATION.cff` and the README and a retracted canary percentage in `ARTIFACT.md`.

### Added

- A third benchmark, **UCI Bank Marketing**, from outside the census, with the full preregistered
  5 × 5 grid (75 cells, 5 ε × 5 seeds) confirming that AIM's structural advantage does not transfer.
- A second adversary, the **marginal-ratio (ζ) attack**, which reaches AUC 0.59 where the
  nearest-neighbour baseline sits at chance.
- `scripts/setup_demo.py`, so the rehearsed demo can actually be run.
- A four-rung **offline fallback** for the demo, and a rehearsal pack for the hardest viva
  questions.
- 10 Playwright end-to-end specs against the real service.

### Changed

- **Results.** AIM's structural advantage is Adult-specific: on Bank Marketing it is
  indistinguishable from independent marginals, and the utility ordering that had replicated on
  both census tables no longer reproduces.
- `api/main.py` split from 1,225 lines into seven modules.
- `mypy` clean (79 errors → 0) and blocking in CI.
- CI runs real AIM; it had silently skipped every AIM test because private-pgm was never
  installed.
- One tracker (`docs/ROAD_TO_TEN.md`) replaces four planning documents that had drifted.
