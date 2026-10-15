# SynthProof — Deep Audit (2026-08-13)

> ## This is a historical record, not the current plan.
>
> **The live tracker is [`ROAD_TO_TEN.md`](ROAD_TO_TEN.md).** Go there for what is done and
> what is left. This file is kept because three things in it are still cited from across the
> repository and are still true: the **standing rules** (§7), the **numbered findings** F1–F11
> and G1–G7 (§2), and the **ε-calibration table** (§3). Nothing here should be read as a
> statement about the project's present state.
>
> It is frozen rather than deleted because a finding is evidence: `docs/thesis/DATA_PACK.md`
> cites F4, `.coderabbit.yaml` and `results/RESULTS.md` cite §7, and the defence pack cites
> both. A record that other documents rest on cannot be rewritten in place without
> invalidating them.
>
> **Why this was frozen.** The scorecard below was three weeks stale and had drifted in the
> direction that flatters nobody: it scored Generators 2.0 ("independent marginals only"),
> Attack suite 2.0, Empirical rigor 2.0 ("toy data, 1 seed") and Documentation 1.5 ("thesis
> is 161 words") — when real AIM, four attacks, a five-seed grid with confidence intervals and
> a ~5,700-word thesis had all landed. Understating is as false as overstating, and this is
> the file an examiner opens to find weaknesses. The fix for a document that keeps drifting is
> to stop maintaining two of them, not to correct it a third time.

---

## 1. Verdict

> ### **6.0 / 10** as a research capstone — up from 3.5 at the first audit
>
> *(as assessed on 2026-08-13, after F5 closed and CSV ingestion landed. **This score and the
> scorecard below are superseded** — see the notice at the top of this file. They are left
> unedited so the trajectory in §8 remains a record of what was believed when.)*
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
| F9 — experiments violate the preregistration | ✅ **Closed after this audit.** The preregistered grid runs on UCI Adult, ACSIncome and UCI Bank Marketing at 6,000 rows × 5 seeds × 5 ε with bootstrap CIs. The toy sweep that prompted the finding was deleted, not disclaimed |
| F10 — data sheet neither signed nor ledgered | ✅ **Closed after this audit.** Ed25519 signing shipped; the signed head commits to `(entry_count, tip_hash)`, which is what makes truncation detectable |
| F11 — README claims features that do not exist | ✅ **Fixed** |

### New findings from this scan

| ID | Finding | Status |
|---|---|---|
| **G1** | Web console hardcoded four `PASSED` attack verdicts with invented figures, including a pass for **attribute reconstruction, which does not exist in the codebase** | ✅ Fixed this session |
| **G2** | The `Anonymeter Risk 0.040` metric card had **no data source** — the data sheet carries no singling-out field | ✅ Fixed this session |
| **G3** | Copula categorical branch **charged ε and applied no noise**, releasing exact category frequencies | ✅ Fixed this session |
| **G4** | **No CSV ingestion anywhere.** No `read_csv`, no upload endpoint, no `--input` flag | ✅ Fixed this session — `Schema`, `from_csv`, `synthproof run --input` |
| **G5** | Thesis is **161 words**; threat model 177; preregistration 218 | ⚠️ **Partially closed after this audit.** ~5,700 words of ~15,700. Still the project's binding constraint — tracked in [`ROAD_TO_TEN.md`](ROAD_TO_TEN.md), not here |
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
but it leaves a little utility unclaimed.

> **Closed after this audit.** `BudgetPlan.split(tighten=True)` bisects an outer multiplier on
> the stage shares until the composed total meets the target, recovering the gap from 0.908 of
> target to >0.995 while preserving the never-overspend invariant. It is **off by default**,
> because switching it on changes every published ε in this repository (proved 7.356 → ~8.0)
> and invalidates the committed grid until a full re-run. See `tests/test_budget_tightening.py`.

A CI job asserts this across 24 mechanism × step × target configurations. If the claim
regresses, every certificate the project emits becomes false, so it gets its own gate.

---

## 4–6. What is left, and in what order

**Superseded in full by [`ROAD_TO_TEN.md`](ROAD_TO_TEN.md).**

These three sections held a gap list, a mandatory/optional split and a schedule. They were
rewritten once already, on 2026-08-23, after a scan found the previous version "understated
the project in almost every row". Maintaining a second forward plan alongside the live tracker
is what produced that drift both times, so the sections are removed rather than corrected
again. The tracker carries the same content with an acceptance criterion per task and a rule
that nothing moves to DONE until its criterion has been executed and the output recorded.

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

See [`ROAD_TO_TEN.md`](ROAD_TO_TEN.md) for the trackable breakdown. (`TASKBOARD.md` and the
root `TASKS.md` were deleted on 2026-09-13 — see §4–6 above for why.)
