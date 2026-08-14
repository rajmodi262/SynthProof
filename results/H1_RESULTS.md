# H1 — Mechanism families on UCI Adult

> **Status: SUPPORTED, with the caveats in §5.** UCI Adult, 3 mechanism families, 3 seeds per
> cell, bootstrapped 95% CIs. Utility and structure measured on a **canary-free second fit**.
> Raw output: [`h1_all_families.json`](h1_all_families.json) · Runner: `scripts/run_h1.py`
> · Regenerate with `make h1`.

**H1 (preregistered):** the empirical-to-formal privacy ratio, and the utility a mechanism
buys at fixed ε, differ across generator mechanism families.

This document supersedes two earlier versions, both of which reported the opposite conclusion.
§4 explains why they were wrong — the cause was a defect in our own measurement harness, not a
property of the mechanisms, and it is worth reading before the numbers.

---

## 1. Setup

| | |
|---|---|
| Dataset | UCI Adult, SHA-256 verified, 30,162 complete rows; **3,000-row subsample** for runtime |
| Columns | 12 (4 numeric, 8 categorical); `fnlwgt` and `education_num` excluded |
| Schema | Hand-declared public bounds (age ∈ [17,90], hours ∈ [1,99], …) |
| Mechanisms | `independent` (1-way marginals) · `pairwise` (tree-structured 2-way) · `aim` (private-PGM, adaptive selection) |
| ε grid | 1.0, 8.0 · δ = 1e-5 |
| Seeds | 3 per cell · bootstrapped 95% CI (4,000 resamples) |
| Utility target | `income` — the benchmark's own binary task |
| Structure metric | Mean absolute correlation error over `age` × `hours_per_week` (true correlation **0.093**) |
| Canaries | 60 planted per audit fit; **utility measured on a separate fit with none** |

---

## 2. Results

| Mechanism | target ε | proved ε | Correlation error (95% CI) | TSTR F1 (95% CI) | MIA AUC | audit p |
|---|---:|---:|---|---|---:|---:|
| independent | 1.0 | 0.912 | 0.0824 [0.0579, 0.0975] | 0.377 [0.302, 0.443] | 0.489 | 0.569 |
| independent | 8.0 | 7.356 | 0.0832 [0.0527, 0.1044] | 0.431 [0.245, 0.591] | 0.499 | 0.596 |
| **pairwise** | 1.0 | 0.912 | **0.0298** [0.0138, 0.0490] | 0.467 [0.441, 0.517] | 0.483 | 0.476 |
| **pairwise** | 8.0 | 7.356 | **0.0153** [0.0073, 0.0200] | 0.456 [0.441, 0.465] | 0.489 | 0.532 |
| **aim** | 1.0 | 0.778 | 0.0790 [0.0367, 0.1239] | 0.511 [0.446, 0.570] | 0.494 | 0.541 |
| **aim** | 8.0 | 6.543 | **0.0309** [0.0269, 0.0336] | **0.548** [0.518, 0.584] | 0.487 | 0.650 |

**TRTR baseline (real → held-out real): 0.704 [0.673, 0.739]**

**ε_audited = 0.000 in every cell**, with audit p-values consistent with the null (0.48–0.65).

---

## 3. Findings

### 3.1 The families separate on structure — H1 supported ✅

At ε = 8 the confidence intervals **do not overlap**:

```
independent   [0.0527, 0.1044]
aim           [0.0269, 0.0336]     entirely below independent
pairwise      [0.0073, 0.0200]     entirely below both
```

Both dependence-modelling mechanisms reproduce the joint structure substantially better than
the independent baseline: pairwise by **5.4×**, AIM by **2.7×**.

### 3.2 The trend is now in the right direction

Structured mechanisms improve as the budget grows; the baseline does not.

| mechanism | ε = 1 → 8 | reading |
|---|---|---|
| independent | 0.0824 → 0.0832 | **flat** — it models no dependence, so extra budget buys no structure |
| pairwise | 0.0298 → 0.0153 | **halves** |
| aim | 0.0790 → 0.0309 | **improves 2.6×** |

That the baseline is flat is the control working. It never preserves correlation, so
contamination could neither flatter nor penalise it — and it doesn't move.

### 3.3 AIM buys utility; pairwise buys structure

AIM has the best downstream utility (TSTR **0.548** at ε = 8, against a TRTR ceiling of 0.704
— a gap of 0.16), while pairwise has the lowest correlation error. They optimise different
things: AIM adaptively selects whichever marginal is currently worst approximated across all
12 columns, whereas pairwise measures a fixed public chain that happens to include the pair
this structure metric scores.

**This is a real caveat, not a footnote.** The structure metric looks at one column pair. A
mechanism that spends budget on that specific pair will win it. A workload-wide fidelity
metric would likely rank these two differently, and §5 records it as a threat to validity.

### 3.4 AIM's proved ε is lower, and that is not free

AIM composes to 6.543 where the others reach 7.356 at the same target, because it spends 25%
of its synthesis budget on the exponential-mechanism-equivalent selection step. It therefore
achieves its results at a **11% smaller actual privacy spend** than the mechanisms it is
compared against — which makes its structure result slightly understated relative to the
others, not overstated.

### 3.5 ε_audited is 0 everywhere — and we now know exactly why ⚠️

The detection-floor study ([`DETECTION_FLOOR.md`](DETECTION_FLOOR.md)) has since measured what
the auditor can see, and the answer disqualifies the privacy half of this table.

These runs use **m = 60 canaries**. At that count:

- **Floor.** The auditor detects nothing below roughly 25% verbatim copying — a bar every DP
  mechanism clears trivially.
- **Ceiling.** `ε_audited = log(TPR_lo / FPR_hi)` from Clopper-Pearson intervals is bounded by
  the sample size. At m = 60 the maximum reportable value is ≈ **2.7**, measured against a
  release that is 100% verbatim training data with TPR 1.00 and FPR 0.00.

The proved ε here is **7.36**.

> **The gap was structurally guaranteed.** The instrument could not have reported
> `ε_audited > 2.7` at this canary count even if a mechanism had published its training set
> verbatim. The observed "7.36 versus 0.00" is a property of the measurement, not of the
> mechanisms.

**No claim about ε_audited / ε_proved is made from this table, and none should be.** Only the
utility and structure halves of H1 are answered here. The privacy half is blocked on M2.1 —
the full Steinke one-run construction — not merely on a larger canary count, since even
m = 800 only lifts the ceiling to 5.38.

---

## 4. Why the two earlier versions were wrong

Both previous runs reported that the families were indistinguishable, and the 13 Aug run had
pairwise getting *worse* as the budget grew (0.110 → 0.196 → 0.236). That is backwards, and it
was our harness.

`run_cell` fitted **one** model on the canary-augmented split and used it for everything.
Canaries are extreme by construction, and 60 of them move the joint distribution:

```
corr(age, hours_per_week)   fit split        0.1014
                            + 60 canaries    0.0109     89% of the signal destroyed
```

The generator was therefore trained on a table with almost no correlation and scored against
one that had it. Mechanisms that model dependence faithfully reproduced the flattened
structure and were penalised for it; the independent baseline, which reports no correlation
either way, was unaffected. **The better a mechanism was, the worse it scored.**

The 13 Aug fix randomised the canary direction per column. That removed a *different* artefact
(canaries clustered in one corner, inflating correlation to 0.334) and changed the sign of the
bias, but not its size.

The fix in this run: fit **twice** — once on the augmented split for the audit, once on the
clean split for utility and structure. Isolated on a synthetic table with true correlation
0.975:

| mechanism | ε | contaminated | decoupled |
|---|---:|---:|---:|
| independent | 1.0 | 0.9769 | 0.9776 |
| independent | 8.0 | 0.9804 | 0.9778 |
| pairwise | 1.0 | 0.2283 | 0.1880 |
| pairwise | 8.0 | 0.1098 | **0.0459** |

The baseline is unchanged; pairwise improves 58% at ε = 8.

**The methodological point is worth more than the result.** A measurement instrument that
systematically penalises the thing it is trying to detect will produce a confident null, and
nothing about the null looks wrong from the outside. Both earlier documents reported that null
in good faith.

---

## 5. Threats to validity

- **ε_audited = 0 throughout.** The privacy half of H1 is untested. See §3.5.
- **The structure metric is one column pair.** `capital_gain` (91.6% zeros) and
  `capital_loss` (95.5%) are degenerate and excluded, leaving only `age` × `hours_per_week`.
  A mechanism that happens to measure that pair is advantaged — see §3.3.
- **3,000-row subsample**, not the full 30,162. Larger n narrows CIs.
- **3 seeds and 2 ε points**, against 5 seeds and 5 points in the preregistration.
- **Weak true correlation (0.093).** The separation is real but small in absolute terms; the
  synthetic check in §4 shows the effect is far larger when dependence is strong.
- **One dataset.** The preregistration also commits to ACS PUMS.
- **`pairwise` uses a fixed public chain**, not data-adaptive structure selection, so it pays
  nothing for structure while AIM does.

---

## 6. Next

| | Task |
|---|---|
| **M2.2** | **Detection-floor study — the blocker.** Sweep canary count against a known-leaky mechanism until the auditor fires, so ε_audited = 0 becomes a calibrated statement instead of an absence |
| M1.4 | ACS PUMS — a second dataset, stronger dependence, subgroup labels for H2 |
| — | Full grid: 5 seeds × 5 ε values on all 30,162 rows |
| — | A workload-wide fidelity metric, so §3.3's single-pair caveat goes away |
