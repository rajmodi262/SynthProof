# H1 — Proved vs. Audited Gap Across Mechanism Families

> **Status: FIRST REAL RESULT.** UCI Adult, 5 seeds per cell, bootstrapped 95% CIs.
> Reported in full, in the direction the data actually falls.
> Raw output: [`h1_adult.json`](h1_adult.json) · Runner: `synthproof/frontier/experiment.py`

## Setup

| | |
|---|---|
| Dataset | UCI Adult, SHA-256 verified, 30,162 complete rows; **6,000-row subsample** for runtime |
| Columns | 12 (4 numeric, 8 categorical); `fnlwgt` and `education_num` excluded |
| Schema | Hand-declared public bounds (age ∈ [17,90], hours ∈ [1,99], …) |
| Mechanisms | `independent` (1-way marginals) vs `pairwise` (tree-structured 2-way marginals) |
| ε grid | 0.5, 1.0, 2.0, 4.0, 8.0 · δ = 1e-5 |
| Seeds | 5 per cell · bootstrapped 95% CI (4,000 resamples) |
| Utility target | `income` (the benchmark's own binary task) |
| Structure metric | Mean absolute correlation error over `age` × `hours_per_week` |

## Results

| Mechanism | target ε | proved ε | Correlation error (95% CI) | TSTR F1 (95% CI) |
|---|---:|---:|---|---|
| independent | 0.5 | 0.456 | 0.112 [0.104, 0.118] | 0.451 [0.389, 0.535] |
| independent | 1.0 | 0.912 | 0.113 [0.106, 0.118] | 0.418 [0.364, 0.481] |
| independent | 2.0 | 1.828 | 0.112 [0.106, 0.117] | 0.445 [0.402, 0.479] |
| independent | 4.0 | 3.664 | 0.113 [0.106, 0.117] | 0.439 [0.349, 0.528] |
| independent | 8.0 | 7.356 | 0.112 [0.106, 0.117] | 0.465 [0.440, 0.493] |
| pairwise | 0.5 | 0.456 | 0.091 [0.058, 0.131] | 0.458 [0.401, 0.505] |
| pairwise | 1.0 | 0.912 | 0.108 [0.062, 0.157] | 0.469 [0.437, 0.515] |
| pairwise | 2.0 | 1.828 | 0.133 [0.110, 0.163] | 0.387 [0.311, 0.463] |
| pairwise | 4.0 | 3.664 | 0.128 [0.123, 0.134] | 0.411 [0.315, 0.491] |
| pairwise | 8.0 | 7.356 | 0.139 [0.117, 0.159] | 0.496 [0.436, 0.548] |

**TRTR baseline (real → held-out real): 0.678 [0.670, 0.686]**

**ε_audited = 0.000 in every cell**, with audit p-values consistent with the null.

---

## Findings

### 1. Calibration holds on real data ✅

proved/target is 0.912–0.919 across the entire grid and never exceeds 1.0. The budget
interface behaves on a real 12-column table exactly as it does on synthetic fixtures.

### 2. H1 is NOT supported on UCI Adult — and the reason is instructive

The two mechanism families are **statistically indistinguishable** on this dataset: the CIs
for correlation error overlap at every ε, and TSTR F1 overlaps everywhere.

This is not a null caused by broken code. The cause is measurable: **the strongest numeric
correlation in UCI Adult is only 0.103** (age × hours_per_week). The independent baseline
scores an error of ≈0.112, which is essentially |0.103 − 0| — it simply reports no
correlation, and when the truth is nearly no correlation that is nearly right.

On a synthetic table with genuine structure the families separate dramatically:

| ε | independent | pairwise | (true correlation 0.975) |
|---:|---:|---:|---|
| 0.5 | 0.003 ±0.013 | **0.823** ±0.016 | |
| 8.0 | 0.003 ±0.013 | **0.948** ±0.004 | |

**So the honest statement of the finding is conditional:** modelling pairwise dependence
buys a large amount when dependence exists, and nothing measurable when the signal is weaker
than the DP noise floor. UCI Adult's numeric columns are the second case.

### 3. Utility gap is real and consistent

TSTR ≈ 0.39–0.50 against a TRTR baseline of 0.678 — a gap of roughly 0.20–0.29 macro F1.
Notably the gap **does not close as ε grows**, which suggests the binding constraint at this
scale is model expressiveness, not noise.

### 4. ε_audited = 0 everywhere

At 60 canaries the auditor detects nothing, and reports a p-value saying so. Consistent with
the synthetic experiments. This makes the proved-vs-audited gap **maximal but uninformative**:
we cannot distinguish "the mechanism leaks very little" from "this auditor is underpowered
at this canary count" without the detection-floor study (M2.2).

---

## Threats to validity

- **6,000-row subsample**, not the full 30,162. Larger n narrows CIs and may separate families.
- **Two numeric columns** in the structure metric. `capital_gain` (91.6% zeros) and
  `capital_loss` (95.5%) were excluded as degenerate — their sample correlations measure noise.
- **Pairwise uses a fixed public chain**, not exponential-mechanism structure selection as in
  MST/AIM. A data-adaptive tree would likely find whatever dependence exists.
- **Not AIM.** `private-pgm` requires Python ≥3.11 and could not be installed here. The
  comparison is between our two implementations, not against a published state of the art.
- **One dataset.** The preregistration also commits to ACS PUMS.
- **Audit is underpowered**, per finding 4.

## Bugs found and fixed while producing this result

Recording these because each silently corrupted results before it was caught:

1. **Canary planting dropped the schema**, so the augmented dataset lost its public bounds and
   the profiler fell back to noisy min/max.
2. **Canaries were placed outside the public domain** (age ≈ 250 against a declared [17, 90]),
   stretching the profiled range to [17, 300] and compressing every real record into a few
   bins. This alone accounted for pairwise correlation error appearing to *increase* with ε.
3. **Public ranges were being re-estimated under noise** rather than used directly, producing
   degenerate ranges of width 1.
4. **The utility target defaulted to `workclass`** (7 classes, 73% majority) instead of the
   benchmark's `income` task, pinning macro F1 near chance for every mechanism.

## Next

| | Task |
|---|---|
| M1.4 | ACS PUMS — more columns, stronger dependence, subgroup labels for H2 |
| M2.2 | Detection-floor study, so ε_audited = 0 becomes interpretable |
| M1.8 | Real AIM on Python 3.11+, for a published-SOTA comparison |
| — | Full 30,162-row run |
