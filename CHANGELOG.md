# Changelog

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

- A third benchmark, **UCI Bank Marketing**, from outside the census.
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
