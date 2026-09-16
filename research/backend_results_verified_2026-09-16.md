# Backend results — verified ground truth (2026-09-16)

> Purpose: one place where every number the paper/deck/viva uses is re-checked against the repo,
> so no claim is unbacked. Produced during the guide-feedback engineering pass. Standing honesty
> rules apply: every figure below was read from a file or a passing test today, not from memory.
> Branch `fix/selection-accounting`, HEAD `4e65607`.

## 1. Repo health (checked today)
- `ruff check synthproof` — **All checks passed.**
- `black --check synthproof` — **clean** (4 source files reformatted today: `api/routes/artifacts.py`,
  `api/routes/run.py`, `ledger/signing.py`, `frontier/certificate.py`; whitespace only, no logic change).
- `mypy synthproof` — **Success, no issues in 69 source files.**
- Targeted claim tests — **78 passed** in 174 s (`test_boundary_audit`, `test_release_boundary`,
  `test_imputation`, `test_model_total_is_private`, `test_differential_accounting`).
  (The full suite is ~900+ tests per `CONTRIBUTIONS.md`; only the claim-bearing subset was re-run today.)

## 2. Utility & privacy per dataset/mechanism at target ε = 8 (from results/*.json)
Correlation error: lower = better. tstr_f1: higher = better. mia_auc ≈ 0.5 = safe.

| Dataset | Mechanism | corr_err | tstr_f1 | mia_auc | proved ε | audited ε |
|---|---|--:|--:|--:|--:|--:|
| UCI Adult | independent | 0.0947 | 0.407 | 0.500 | 7.356 | 0.000 |
| UCI Adult | pairwise | 0.0283 | 0.432 | 0.493 | 7.356 | 0.000 |
| **UCI Adult** | **aim** | **0.0105** | 0.506 | 0.501 | 6.543 | 0.000 |
| ACSIncome (CA 2018) | independent | 0.0535 | 0.462 | 0.503 | 7.356 | 0.000 |
| **ACSIncome** | **pairwise** | **0.0202** | 0.522 | 0.497 | 7.356 | 0.000 |
| ACSIncome | aim | 0.0621 | 0.567 | 0.506 | 6.543 | 0.000 |
| UCI Bank Mktg | independent | 0.0416 | 0.479 | 0.494 | 7.341 | 0.029 |
| **UCI Bank Mktg** | **pairwise** | **0.0289** | 0.482 | 0.499 | 7.341 | 0.057 |
| UCI Bank Mktg | aim | 0.0579 | 0.462 | 0.488 | 6.526 | 0.002 |

### Honest reading (IMPORTANT — do not overclaim)
- **"AIM is ~9× better than independent" is ADULT-ONLY** (0.0105 vs 0.0947). On ACS and Bank,
  **pairwise** has the lowest correlation error and AIM is *worst* on that metric. AIM leads on
  downstream utility (tstr_f1) for ACS but not universally. → Say "no single mechanism dominates;
  the best choice is dataset- and metric-dependent." An examiner running the same-dataset check
  will see this, so state it first.
- **audited ε ≈ 0 everywhere while proved ε ≈ 6.5–7.4.** This is the audit-ceiling story, not a
  privacy claim: with 60 canaries the audit's operating range tops out at ~2.97, so a 0.000 means
  "below the instrument's resolution," reported beside the ceiling (see `synthproof/audit/ceiling.py`;
  the 2.97 vs the paired 5.377 are different instruments — do not mix them).
- mia_auc ≈ 0.50 across the board → the membership attack learns nothing at these settings (safe).

## 3. The release-boundary leaks (verified earlier this session)
- Seed replay (`research/release_boundary/seed_replay_probe.json`): true table **15/15** exact
  matches (independent 5/5, pairwise 5/5, aim 5/5), neighbour **0/15**, wrong seed **0/15**, at ε=1.
- D1 undercharge ≥ **1.71×** before fix; fixed (`known_total=None`), control generators reproduce.
- D2–D5 fixed and pinned by `test_release_boundary.py` (each fix reverted → matching test fails).

## 4. Imputation audit (verified earlier this session, results/imputation_audit.json)
- Sanity gates PASS: numeric planted-leak 0.615 [0.609, 0.620]; categorical planted-leak 0.606
  [0.596, 0.618] vs private null 0.497 [0.488, 0.506].
- All handling arms ≈ 0.51 AUC → **bounded negative**: no leak above the DP-charged baseline.
  Honest limit: loose bound (attack power modest), one dataset family, n=1500, two ε.

## 5. Standards comparison — the honest replacement for "15/15 parameters"
Source: `research/15_standards_gap_analysis.md` (each cell justified against the actual spec).
**11 properties P1–P11.** Coverage (Y = expressible):

| Standard | P1 | P2 | P3 | P4 | P5 | P6 | P7 | P8 | P9 | P10 | P11 |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| Croissant 1.1 | N | N | N | N | N | N | N | N | N | N | ~ |
| HF dataset card | N | N | N | N | N | N | N | N | N | N | ~ |
| Datasheets (2021) | N | N | N | N | N | N | N | N | N | N | N |
| Model Cards (2019) | N | N | ~ | N | N | N | N | ~ | N | N | N |
| Dibia DP label (2026) | Y | Y | Y | ~ | N | N | N | ~ | N | N | N |
| **SynthProof PDS + boundary-audit** | **Y** | **Y** | **Y** | **Y** | **Y** | **Y** | **Y** | **Y** | **Y** | **Y** | **Y** |
→ Every other standard expresses only a few of the 11; ours is the only column that expresses all.
This is the true "we cover what they don't" story. **Never phrase it as "15/15 parameters passed".**

## 6. Guide task status after this pass
- **T2-4 (multi-dataset testing): DONE** — 3 datasets, full runs (`reduced_run: false`), 3 mechanisms
  × 5 ε × 5 seeds each: UCI Adult, ACSIncome (CA 2018), UCI Bank Marketing.
- **T2-2 (same-dataset head-to-head): PARTIAL** — UCI Adult is the field-standard DP-synthetic
  benchmark, so our Adult results sit directly alongside prior mechanism work. To finish a *numeric*
  head-to-head we must cite the chosen base paper's own reported Adult numbers (do NOT fabricate).
  BLOCKED ON: team decision of the single base paper (recommend the closest = Dibia et al., but note
  Dibia is a label proposal with no dataset experiments, so a numeric utility head-to-head needs a
  mechanism/audit paper instead — e.g. a paper that reports Adult utility/MIA).
- **F0-1 fixed at source:** the real anchor is §5 above (P1–P11), not "15/15 parameters".

## Open engineering items (need a decision or more compute)
1. Base paper for the numeric comparison (see T2-2) — pick one that reports Adult numbers.
2. Optional: a genuinely *healthcare* dataset (current set is census/finance) — only if it adds signal.
3. Optional: widen canaries to raise the audit ceiling (heavy AIM reruns; one job at a time).
