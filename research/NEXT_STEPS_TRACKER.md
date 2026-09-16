# SynthProof — Next-Steps Task Tracker
> Started 2026-09-17. Updated after every run. Status: ☐ todo · ◐ in-progress · ✅ done · ⚠ blocked.
> Honesty rules apply: no fabricated numbers/citations; bounded results stay bounded.

## Legend of tasks
| ID | Task | Effort | Status |
|---|---|---|---|
| T1 | Same-dataset comparison on **Adult** vs P7 (Mohapatra) & P8 (AIM) | cheap | ◐ |
| T2 | Add **`domain_source`** check to `boundary-audit` (turns P4/P5 into a checkable field) | cheap | ✅ |
| T3 | **Census invariants** worked example — boundary-audit labels "fields outside ε" | cheap | ☐ |
| T4 | **Audit-power honesty** — state the black-box loose bound + cite P2 (or stronger estimator) | medium | ☐ |
| T5 | **Scale the case study** beyond public hubs (real DP registries) | medium | ☐ |
| T6 | Extend `boundary-audit` to more mechanisms / multi-table; propose as Croissant/Dibia extension | big | ☐ |

## Run log
- **2026-09-17 run 0** — created tracker; reading `synthproof/audit/boundary.py` + the Privacy Data Sheet to plan T2. Next: T1 comparison + T2 code.
- **2026-09-17 run 1 — T2 DONE.** Found RB6 `domain_source` check already exists in `boundary.py` and is wired through `certificate.py`/`cli.py`/`croissant.py` and tested. **Real defect fixed:** `api/routes/run.py` shipped `domain_source="SynthProof Autonomous Verification Pipeline"` (a marketing string RB6 can't read) and `contribution_bound="bounded_one"` (should be int `1`). Added `state.domain_source_for(name)` (declared for adult/toy; inferred-nonprivate for demo/uploads, tied to Ganev P4/P5), wired the route to it, fixed contribution_bound. Added regression test `test_api.py::test_domain_source_is_a_valid_boundary_value_not_a_marketing_string`. Verified: ruff+black clean; 36 boundary/cli tests + 1 new test pass. Next: T1 (Adult comparison), T3 (Census example).
