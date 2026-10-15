# Corrections

Every retracted or corrected result in this project, with its cause and the commit that fixed it.
Newest first. A number that was wrong is listed here even when the conclusion it supported held.

Since 2026-10-16 two CI gates stop the most common cause from recurring:
`scripts/check_number_provenance.py` fails the build when a number in a results document, the
thesis, the defence pack, the explainer, the simple guide, the README or the demo script matches
no committed result (or a reasoned allowlist entry), and `scripts/build_results_docs.py --check`
fails it when a generated results table no longer matches its JSON.

Line-level thesis and defence corrections from September 2026 are in
[`docs/thesis/CORRECTIONS_2026-09.md`](docs/thesis/CORRECTIONS_2026-09.md).

---

## 2026-10-16 — DP correctness sweep (W5)

Tests that check the statistic each charge actually perturbs (`tests/test_sensitivity.py`), an
empirical distinguishing test per mechanism (`tests/test_empirical_dp.py`) and API fuzzing
(`tests/test_fuzz.py`) found four privacy defects and one server bug. Arguments per charge site:
[`docs/SENSITIVITY.md`](docs/SENSITIVITY.md).

| What | Was | Now | Effect on published results |
|---|---|---|---|
| Integer noise on real values (`moments` mean/std, profiler min/max for undeclared ranges, imputation sums) | `true + Z`, Z an integer, so the output kept the true value's fractional part: not DP at any epsilon | real queries rounded onto a Delta/1000 grid first (`noisy_real_query`); same epsilon | `moments` is not in any committed results table; the profiler path only applies to tables without declared bounds (no research grid); imputation A3/A4 re-run, below |
| `moments` sensitivity (audit F5) | clipped mean charged at sensitivity 1.0; true sensitivity (b − a)/n | noisy shifted sum, sum of squares and count, each with a true sensitivity | none committed |
| A4_CHARGED neighbour sum | raw sum perturbed (sensitivity max(\|lo\|, \|hi\|)) while charging width | shifted sum. A4_CHARGED remains a labelled heuristic, not a proven DP mechanism | re-run, below |
| DP-VAE sampling | accounted as Poisson subsampling, trained on fixed-size batches | Poisson in the loop | every DP-VAE imputation cell re-run, below |
| API, `Infinity`/`NaN` in a request | answered 500 (the validation error could not be serialised) | 422 | none |

**Imputation audit re-run (42 cells: every DP-VAE cell, every A3 and A4_CHARGED cell).** The null
holds: all 19 A2/A3 pairs still overlap, the largest |A2 − A3| is 0.00381 (was 0.00358), and no
cell moved by more than 0.008 AUC. The tables in `research/imputation_audit/RESULTS.md` and
`PAPER_SECTION.md` are now generated from the JSON; the DP-VAE rows changed.

**Reproducibility, stated precisely.** With the seed fixed, AIM-family *fitted models* are
bit-identical across processes; private-PGM's float32 *sampler* is not (different tables across
processes and after JAX's compilation caches change). Pinned by `tests/test_reproducible_fits.py`.

## 2026-10-16 — provenance sweep (W1)

A full sweep of 21 results-bearing documents against committed results found **127 numbers in 20
documents that matched no committed result**. Every one was regenerated, corrected, traced to a
named source, or allowlisted with a reason (`scripts/number_provenance_allowlist.json`).

| What | Was | Now | Cause |
|---|---|---|---|
| Selection ablation, Adult `corr(\|true corr\|, effect)` | −0.898 in seven documents; committed JSON said −0.882 | **−0.997** (ACS −0.996) | Tables typed by hand and not updated when `a8a31b1` changed the JSON; then re-run on current code, whose `AIMGenerator` (subclassed by the fixed-workload arm) changed in `c0966fd`/`b2d2a29` |
| "Measuring a near-independent pair makes it worse" (Adult `capital_gain x capital_loss`) | +240.9%, interval clear of zero | −7.9%, interval **spans zero**; no degradation established on either dataset | Did not reproduce on the current estimator. The "crossover calibration" claim built on it is withdrawn |
| Selection ablation confidence intervals | Quoted with no committed source | Bootstrap intervals saved by the runner, tables generated | Intervals were computed outside the committed script |
| Auditor comparison table | Cited a `make audit-compare` target that never existed | Re-run by `scripts/run_auditor_comparison.py`; reproduced except one cell (m = 400, 25% leak, paired: 0.018 → **0.004**) | No committed script behind the published table |
| Adversary comparison prose | Distance range 0.498–0.538; AIM Δ +0.038 → +0.092 | 0.505–0.538; AIM Δ **+0.066 → +0.080** (table now generated) | Prose not updated after the D1 AIM re-run |
| README H1 row | "all three families separate at ε=8 (aim > pairwise > independent)" and the 11.9x/2.3x confound ratios | AIM and pairwise **overlap**; confound reading marked retracted | Not updated after the D1 re-run (`66d145d`) or the confound retraction (`5b2eaf8`) |
| Defence pack §7.2 | Taught the retracted confound as "Finding 2 … the most publishable thing" | Replaced by the retraction and what survived | Missed by the September sweep |
| Thesis ch06 / ch07 / defence: ACS TSTR | 0.704 → 0.581, "CIs do not overlap" | 0.6493 → 0.5668 (D1 re-run), **endpoint CIs overlap** | Pre-D1 values; the ACS domain behaviour that explained them was removed by audit C1 (2026-09-24) |
| Thesis ch05 calibration | "terminates after r = 20 iterations or when \|ε − target\| < 1e-5"; "24 CI configurations … ratio ≤ 0.92"; 7.999605 | Bracket-width rule (1e-4, ≤ 200 iterations); the 24 CI configurations lie in [0.999917, 0.999994]; **7.999622** (`results/calibration_check.json`) | Description did not match `calibration.py`; the single-stage value came from a stale code comment |
| README tamper example | signed sheet says 0.9615567837005196 | 0.9999580768688316 (matches DEMO.md) | Output from an older demo release |
| Several unsourced figures (AUC 0.86/0.67, 0.530/0.552, per-seed p = 0.016) | Quoted as measurements | Removed or reworded | No committed result contains them |
| Provenance checker | Skipped every negative number written with a hyphen (e.g. `-0.0829`) | Checked | Pattern bug found during the sweep |

## Earlier corrections

| Date | What | Correction | Commit |
|---|---|---|---|
| 2026-10-14 | Console correlation matrix | Was SIMULATED from a `sin()` formula; two hard-coded figures and an unfitted curve labelled "empirical". Now shows measured values only | `78e3b8d`, `d10d2c5` |
| 2026-10-11 | H1 headline (Adult, ε = 8, AIM correlation error) | 0.0078 → **0.0105 [0.0059, 0.0153]**. AIM had read the exact row count (D1). AIM and pairwise no longer separate | `a8a31b1`, `66d145d`, `cd31b80` |
| 2026-10-11 | Imputation audit A3 / A4_CHARGED | Under-charged ε; 42 cells re-run. The null holds | `774d93d` |
| 2026-10-11 | Thesis ch07 | Numbers matching no results file, introduced in `eac2e54` (2026-09-12), replaced with committed values | `66d145d` |
| 2026-09-13 | Offline verifier demo capsules | Were fabricated; the audit-range tick was backwards | `5382a14` |
| 2026-09-12 | Offline verifier | Never ran, and its fallback passed forged capsules | `d66bad1` |
| 2026-09-08 | Canary contamination "89%" | Does not replicate (≈4.5% at 40 seeds). Report the fraction axis, never a percentage | `ce7c29f`, `8ac52e5` |
| 2026-09-08 | Quote attributed to Ganev et al. CCS 2025 | Fabricated; retracted | `2da35ea` |
| 2026-09-04 | Clique-selection confound (published three times in-repo) | RETRACTED: the project's own fixed-workload ablation (run 2026-08-25) shows measuring helps in proportion to true dependence | `5b2eaf8` |
| 2026-08-13 | Frontend | Fabricated display values removed | `b7d6638` |
