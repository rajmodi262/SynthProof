# SynthProof — Next-Steps Task Tracker
> Started 2026-09-17. Updated after every run. Status: ☐ todo · ◐ in-progress · ✅ done · ⚠ blocked.
> Honesty rules apply: no fabricated numbers/citations; bounded results stay bounded.

## Legend of tasks
| ID | Task | Effort | Status |
|---|---|---|---|
| T1 | Same-dataset comparison on **Adult** vs P7 (Mohapatra) & P8 (AIM) | cheap | ✅ |
| T2 | Add **`domain_source`** check to `boundary-audit` (turns P4/P5 into a checkable field) | cheap | ✅ |
| T3 | **Census invariants** worked example — boundary-audit labels "fields outside ε" | cheap | ✅ |
| T4 | **Audit-power honesty** — state the black-box loose bound + cite P2 (or stronger estimator) | medium | ✅ |
| T5 | **Scale the case study** beyond public hubs (real DP registries) | medium | ✅ |
| T6 | Extend `boundary-audit` to more mechanisms / multi-table; propose as Croissant/Dibia extension | big | ✅ (a–c built; d designed as future) |
| T6a | New RB checks (public_invariants, discretization_source, amplification) | cheap | ✅ |
| T6b | Formal signed+checkable DP-release label spec (Croissant/Dibia extension) | medium | ✅ |
| T6c | More generators (MST/PrivBayes) emitting boundary-clean sheets | medium | ✅ (MST H1 grid now run on all 3 datasets) |
| T6d | Multi-table / relational release boundary | BIG (research) | ✅ designed → declared future/Paper 2 |

## Run log
- **2026-09-17 run 0** — created tracker; reading `synthproof/audit/boundary.py` + the Privacy Data Sheet to plan T2. Next: T1 comparison + T2 code.
- **2026-09-17 run 1 — T2 DONE.** Found RB6 `domain_source` check already exists in `boundary.py` and is wired through `certificate.py`/`cli.py`/`croissant.py` and tested. **Real defect fixed:** `api/routes/run.py` shipped `domain_source="SynthProof Autonomous Verification Pipeline"` (a marketing string RB6 can't read) and `contribution_bound="bounded_one"` (should be int `1`). Added `state.domain_source_for(name)` (declared for adult/toy; inferred-nonprivate for demo/uploads, tied to Ganev P4/P5), wired the route to it, fixed contribution_bound. Added regression test `test_api.py::test_domain_source_is_a_valid_boundary_value_not_a_marketing_string`. Verified: ruff+black clean; 36 boundary/cli tests + 1 new test pass. Next: T1 (Adult comparison), T3 (Census example).
- **2026-09-17 run 2 — T1 DONE.** Wrote `research/19_adult_same_dataset_comparison.md`: our verified
  Adult utility/privacy grid (AIM 0.0105 vs independent 0.0947 at ε=8 → ~9×, reproduces P8's ordering);
  quoted P7/P8/P5 Adult numbers with the metric named; honest caveats (our n=6k subsample vs their
  32k/48k; different metrics; audited ε loose per P2). Differentiator shown with a **live boundary-audit
  run** on `demo/sheet.json` (5 open channels incl. the new RB6 domain_source). No new heavy runs needed.
- **2026-09-17 run 3 — T3 DONE.** Wrote `research/20_census_invariants_worked_example.md` with a live
  boundary-audit demo: Census-style invariants **unlabelled → RB4 LEAK (FAILED)**; **declared outside ε
  → PASSED**; and RB2 still marks the exact population total UNVERIFIABLE (honest asymmetry). Turns P9's
  prose-only invariants into a checkable label. Noted a `public_invariants` field as a future extension.
- **T4 status (◐):** the loose-bound honesty statement (black-box audits read ε≈0, cite P2) is now
  written across research 18/19/20. Remaining: add one sentence + [P2] cite to `paper/synthproof_ieee.tex`
  §IX, and (optional, medium) trial a GDP/white-box estimator. T5, T6 still ☐.
- **2026-09-17 run 4 — T4 DONE (stated-bound path).** Added to `paper/synthproof_ieee.tex` §IX: the
  audited ε=0.000 is explicitly a *black-box loose bound*, with Annamalai et al.~\cite{annamalai2024}
  (black-box reads ε≈0 even at true ε=4; tight needs white-box/worst-case). ⚠ the compiled
  `paper/synthproof_ieee.pdf` is now stale — recompile on Overleaf (pdflatex ×2). Optional future:
  trial a GDP/white-box estimator to get a tighter number. **Remaining: T5 (scale case study — needs
  DP-registry data), T6 (extend auditor to more mechanisms/multi-table + propose as Croissant/Dibia
  extension — big).**
- **2026-09-17 run 5 — T5 DONE.** Fetched Damien Desfontaines' real-world DP registry (the one P10
  cites) and audited **12 flagship real deployments** (Apple, Facebook, Google, LinkedIn, Microsoft,
  US Census ×2, Wikimedia, Israel MoH synthetic births) against P1–P11 → `research/21`. Result:
  ε 12/12, mechanism 12/12, unit-of-privacy 11/12, δ 6/12; **P10 tamper-evidence 0/12, P11
  machine-checkable 0/12, all artefact-safety P5–P9 ≈0**. Corroborates HF 0/286 from the
  best-documented end. Honest caveats recorded (query vs synthetic release types; registry-summary basis).
- **2026-09-17 run 6 — T6 SCOPED** → `research/22_T6_scope.md`: T6a new RB checks (cheap, first),
  T6b formal signed+checkable Croissant/Dibia label spec (medium), T6c more generators (compute),
  T6d multi-table (BIG → Future/Paper 2). Approved: DO ALL 6 a,b,c,d.
- **2026-09-17 run 7 — T6a DONE** (commit ed12d38). Added RB8 `public_invariants` (P9/Census),
  RB9 `discretization_source` (P5/Ganev), RB10 `amplification_disclosure` (P7/Mohapatra) to
  `synthproof/audit/boundary.py`, each with a reintroduction negative-control test. 16 boundary
  tests pass; ruff+black clean.
- **2026-09-17 run 8 — T6b DONE.** Wrote `docs/design/DP_RELEASE_LABEL_SPEC.md` (v0.1): the
  Privacy Data Sheet as a Croissant 1.1 extension implementing Dibia's nine categories + the two
  gaps Dibia leaves (Ed25519 signature, operating-range/LoD field), with **conformance defined as
  passing boundary-audit RB1–RB10**. Built `scripts/validate_release_label.py` — composes the
  existing signature check + operating-range coherence + boundary-audit into one verdict with
  distinct exit codes (0 conformant / 1 non-conformant / 2 not-fully-checked). Verified live on
  real demo artefacts (all three exit paths) + 8 negative-control tests in
  `tests/test_release_label.py` (leak, tamper, incoherent range, unsigned, unpinned, uninformative
  audit). Honesty: unverifiable channels do NOT fail conformance (spec §5); asymmetry principle
  restated (conformant ≠ private). ruff+black clean. **Side finding:** two Click commands both
  named `boundary-audit` in `cli.py` (the second shadows the first → dead code); flagged as a
  spawn-task chip, not fixed here. Next: T6c (MST/PrivBayes generators, compute-bound), T6d
  (multi-table, Paper 2 / declared future).
- **2026-09-17 run 9 — T6c DONE (engineering; full grid run deferred).** Added
  `synthproof/generators/mst.py` — an **MST generator** (McKenna/Miklau/Sheldon, NIST 2018
  winner): same select-measure-generate family as AIM over private-PGM, but the model class is
  fixed to a **spanning tree** (d-1 edges chosen Kruskal-style with a union-find no-cycle
  constraint). It **reuses AIM's exact accounting primitives** — same `Accountant.charge` calls,
  same Gaussian(sens 1)/Laplace(sens 2) split — so the composed ε is charged through the verified
  path; the only change is restricting the report-noisy-max argmax to cycle-free candidates, which
  does not change selection sensitivity. Registered as `mst` behind the mbi guard in
  `experiment.py`. Tests `tests/test_mst.py` (10; 9 run + 1 skip-without-mbi): spanning-tree
  property (exactly 2 edges over 3 columns, cycle refused), charges selection+measurement without
  overspending, preserves correlation, respects schema bounds, degrades to 1-way under a tiny
  model budget, union-find cycle detection. **Verified live:** `synthproof run --mechanism mst`
  emits a sheet that **boundary-audit PASSES (0 leaks, exit 0)**, proved ε=3.72 < requested 4.0.
  ruff+black clean; generators+AIM regression green. Honest deferral: the full **H1 5×5 grid
  benchmark row** for MST is the compute-bound remainder (deliberate run, extends committed
  results) — the mechanism is grid-ready but the grid was not run here. PrivBayes not added (MST
  is the representative second select-measure mechanism; PrivBayes is a different family and a
  larger add). Next: T6d (multi-table, declared future / Paper 2).
- **2026-09-17 run 10 — T6d DONE (design; declared future / Paper 2).** Wrote
  `docs/design/MULTITABLE_RELEASE_BOUNDARY.md` (v0.1, design only): defines the relational release
  boundary rigorously — why single-table RB1–RB10 do not transfer, the **entity-level neighbour
  relation** (row vs entity vs edge unit), **per-entity contribution over joins** via degree
  truncation (cf. Cebere P3), and four **candidate** channel checks with no single-table analogue
  (RB11 relational_unit, RB12 fk_degree, RB13 join_cardinality, RB14 cross_table_fingerprint).
  **Explicitly NOT built and NOT validated** (honesty guardrail: never describe multi-table as
  done/in-progress) — no relational generator, no RB11–RB14 in `boundary.py`, no relational label
  fields; the doc states this in §6. This is the honest deliverable for a research-bet item: the
  scope, not a rushed generator emitting unverifiable guarantees. **T6 parent COMPLETE:** a–c
  built+tested, d designed as declared future work. Standing follow-ups: (1) run the MST H1 grid
  benchmark when compute allows; (2) recompile `paper/synthproof_ieee.pdf` on Overleaf (T4 left it
  stale); (3) the duplicate `boundary-audit` CLI command chip. All T6 work committed on
  `fix/selection-accounting`; push next.
- **2026-09-17 run 11 — MST H1 grid RUN on all 3 datasets + cross-dataset comparison.** Ran the
  full MST H1 grid (5 seeds × 5 ε) on **Adult, ACS, Bank** (`results/h1_mst_adult.json`,
  `results/{acs,bank}/h1_mst.json`); the committed 3-mechanism grids were untouched (MST written to
  separate files, merged at report time). Added `--mechanisms`/`--checkpoints` overrides to
  `scripts/run_h1.py` and put `mst` in the default grid tuple. Built `build_mechanism_comparison.py`
  → `research/23_mechanism_comparison.md` and `gen_comparison_report.py` →
  `research/Mechanism-Comparison.{html,pdf}` (colourful, colour-coded, honest). **Findings:**
  our select-measure mechanisms (AIM/MST) take the **best TSTR F1 on all 3 datasets** — MST hits
  **96% of real-data F1 on ACS at ε=2**; AIM leads on structure (corr err 0.0105 on Adult,
  reproducing the published ordering). **Honest limits:** MST does NOT dominate on correlation (its
  spanning tree can omit the measured edge → falls to baseline level on Adult/Bank); on weakly-
  correlated Bank all mechanisms converge; **audited ε = 0 for every mechanism/dataset**
  (instrument-limited — the honesty is the point). Proved-ε and MIA-AUC shown as context, not
  highlighted as a contest (differences are noise around chance). ruff+black clean. Commit + push.
