# H1 — Mechanism families on UCI Adult

> **Status: SUPPORTED on structure and utility. The privacy half is DISQUALIFIED by the
> auditor's working range (§3.6).**
>
> **This is the full preregistered protocol**: 3 mechanism families × 5 ε values × 5 seeds =
> **75 cells**, bootstrapped 95% CIs, utility measured on a canary-free second fit.
> Raw output: [`h1_all_families.json`](h1_all_families.json) · Runner: `scripts/run_h1.py` ·
> Regenerate with `make h1` (resumable; ~4 h).

**H1 (preregistered):** the ratio of empirical audited privacy loss to the formal bound, and
the utility a mechanism buys at fixed ε, differ across generator mechanism families.

Two earlier versions of this document reported the opposite conclusion. §4 explains why they
were wrong — the cause was a defect in our own measurement harness — and §5 explains why even
the corrected *reduced* grid gave a different mechanism ordering than this one.

---

## 1. Setup

| | |
|---|---|
| Dataset | UCI Adult, SHA-256 verified, 30,162 complete rows; **6,000-row subsample** |
| Columns | 12 (4 numeric, 8 categorical); `fnlwgt` and `education_num` excluded |
| Schema | Hand-declared public bounds (age ∈ [17,90], hours ∈ [1,99], …) |
| Mechanisms | `independent` (1-way marginals) · `pairwise` (tree-structured 2-way) · `aim` (private-PGM, adaptive selection) |
| ε grid | **0.5, 1.0, 2.0, 4.0, 8.0** · δ = 1e-5 (δ < 1/n = 1.7e-4) |
| Seeds | **5 per cell** · bootstrapped 95% CI (4,000 resamples) |
| Auditor | One-run (Steinke), 60 canaries |
| Utility target | `income` — the benchmark's own binary task |
| Structure metric | Mean absolute correlation error over `age` × `hours_per_week` (true correlation **0.1034**) |

This matches the preregistration exactly on seeds, ε grid and δ. Deviations are logged in
`docs/thesis/ch06-methodology.md` §6.8; the material one is that ACS PUMS was not run.

---

## 2. Results

| Mechanism | target ε | proved ε | Correlation error (95% CI) | TSTR F1 (95% CI) |
|---|---:|---:|---|---|
| independent | 0.5 | 0.456 | 0.0934 [0.0802, 0.1063] | 0.472 [0.417, 0.525] |
| independent | 1.0 | 0.912 | 0.0930 [0.0817, 0.1044] | 0.470 [0.432, 0.508] |
| independent | 2.0 | 1.828 | 0.0939 [0.0818, 0.1057] | 0.426 [0.340, 0.504] |
| independent | 4.0 | 3.664 | 0.0935 [0.0808, 0.1057] | 0.467 [0.352, 0.575] |
| independent | 8.0 | 7.356 | 0.0947 [0.0817, 0.1071] | 0.406 [0.297, 0.515] |
| pairwise | 0.5 | 0.456 | 0.0611 [0.0219, 0.1143] | 0.483 [0.380, 0.568] |
| pairwise | 1.0 | 0.912 | 0.0694 [0.0380, 0.1213] | 0.428 [0.351, 0.499] |
| pairwise | 2.0 | 1.828 | 0.0493 [0.0170, 0.0950] | 0.418 [0.335, 0.468] |
| pairwise | 4.0 | 3.664 | **0.0197** [0.0048, 0.0464] | 0.427 [0.362, 0.477] |
| pairwise | 8.0 | 7.356 | 0.0283 [0.0132, 0.0517] | 0.432 [0.368, 0.478] |
| **aim** | 0.5 | 0.385 | 0.0827 [0.0258, 0.1395] | 0.498 [0.478, 0.517] |
| **aim** | 1.0 | 0.778 | 0.0424 [0.0142, 0.0708] | **0.540** [0.515, 0.565] |
| **aim** | 2.0 | 1.576 | 0.0564 [0.0139, 0.1007] | 0.470 [0.445, 0.496] |
| **aim** | 4.0 | 3.201 | 0.0260 [0.0015, 0.0681] | 0.460 [0.440, 0.482] |
| **aim** | 8.0 | 6.543 | **0.0078** [0.0031, 0.0125] | 0.505 [0.468, 0.544] |

**TRTR baseline (real → held-out real): 0.660 [0.646, 0.674]**

**ε_audited = 0.000 in every cell.** See §3.6 — this is a property of the instrument, not of
the mechanisms.

---

## 3. Findings

### 3.1 The families separate — H1 supported ✅

Non-overlapping 95% CIs on correlation error:

| ε | independent vs pairwise | independent vs aim | pairwise vs aim |
|---:|---|---|---|
| 0.5 | overlap | overlap | overlap |
| 1.0 | overlap | **separated** | overlap |
| 2.0 | overlap | overlap | overlap |
| 4.0 | **separated** | **separated** | overlap |
| 8.0 | **separated** | **separated** | **separated** |

At ε = 8 all three families are mutually separated:

```
independent   [0.0817, 0.1071]
pairwise      [0.0132, 0.0517]     entirely below independent
aim           [0.0031, 0.0125]     entirely below both
```

**Separation appears only at ε ≥ 4.** At ε ≤ 2 the DP noise dominates the 0.1034 correlation
being measured and no family is distinguishable. That threshold is itself a useful
practitioner result: *below ε ≈ 4 on this data, paying for a structured mechanism buys nothing
measurable.*

### 3.2 The trend is right, and the control is flat

| mechanism | ε = 0.5 → 8.0 | change |
|---|---|---:|
| independent | 0.0934 → 0.0930 → 0.0939 → 0.0935 → 0.0947 | **+0.0012** |
| pairwise | 0.0611 → 0.0694 → 0.0493 → 0.0197 → 0.0283 | −0.0328 |
| aim | 0.0827 → 0.0424 → 0.0564 → 0.0260 → **0.0078** | **−0.0749** |

The independent baseline is **flat to within 0.0012 across a 16× budget range**. That is the
control working exactly as it should: a mechanism that models no dependence cannot convert
extra budget into structure. Its stability across five ε values and five seeds is also the best
available evidence that the measurement pipeline is not drifting.

Neither structured mechanism is perfectly monotone — pairwise rises at ε = 8 and AIM at ε = 2.
With 5 seeds and overlapping intervals those are within noise; the honest statement is a
downward trend, not a monotone one.

### 3.3 AIM wins on both metrics, and does it at a lower spend

AIM has the lowest correlation error at ε = 8 (**0.0078**, an order of magnitude below the
baseline) and the best downstream utility throughout (TSTR **0.540** at ε = 1, **0.505** at
ε = 8, against a TRTR ceiling of 0.660).

It also does this at a **lower actual privacy spend**. AIM composes to 0.77–0.82 × target
where the other two reach 0.91–0.92, because it spends a quarter of its synthesis budget on
adaptive selection:

| mechanism | proved/target across the grid |
|---|---|
| independent, pairwise | 0.912, 0.912, 0.914, 0.916, 0.919 |
| aim | 0.771, 0.778, 0.788, 0.800, 0.818 |

So AIM's advantage is **understated** by this table, not overstated: it achieves the best
structure and utility while spending roughly 11% less ε than the mechanisms it beats.

### 3.4 Calibration holds across the full grid

proved/target never exceeds 1.0 in any of the 75 cells. For the two non-adaptive mechanisms it
sits between 0.912 and 0.919 — the residual is RDP composition being sublinear across the
profile and synthesis stages. Safe, and it leaves a little utility unclaimed.

### 3.5 Utility is dominated by model class, not by budget

TSTR barely moves with ε for any mechanism — independent goes 0.472 → 0.406, pairwise 0.483 →
0.432, AIM 0.498 → 0.505. **The binding constraint at this scale is model expressiveness, not
noise.** A practitioner reading this should not expect a larger ε to buy downstream accuracy on
a 12-column table at n = 6,000; they should expect it to buy joint structure.

### 3.6 ε_audited = 0 everywhere — and this half of H1 is disqualified ⚠️

These runs use **m = 60 canaries**, where
([`AUDITOR_COMPARISON.md`](AUDITOR_COMPARISON.md)):

- the **floor** is roughly 25% verbatim copying — a bar every DP mechanism clears trivially;
- the **ceiling** is **2.97** — the maximum reportable value, measured against a release that
  is 100% verbatim training data with TPR 1.00 and FPR 0.00.

The proved ε here reaches **7.356**.

> **The gap was structurally guaranteed.** The instrument could not have reported
> `ε_audited > 2.97` at this canary count even if a mechanism had published its training set
> verbatim. "7.36 versus 0.00" is a property of the measurement, not of the mechanisms.

**No claim about ε_audited / ε_proved is made from this table.** Only the structure and utility
halves of H1 are answered. Raising the canary count does not fix it — certifying ε = 7.36 needs
roughly 4,700 perfectly-detected canaries.

---

## 4. Why the first two versions were wrong

`run_cell` originally fitted **one** model on the canary-augmented split and used it for
everything. Canaries are extreme by construction and 60 of them move the joint distribution:

```
corr(age, hours_per_week)   fit split        0.1014
                            + 60 canaries    0.0109     89% of the signal destroyed
```

The generator trained on a table with almost no correlation and was scored against one that had
it. Mechanisms that model dependence faithfully reproduced the flattened structure and were
penalised for it; the independent baseline was unaffected. **The better a mechanism was, the
worse it scored.**

The fix fits **twice** — once on the augmented split for the audit, once on the clean split for
utility and structure. Isolated on a synthetic table with true correlation 0.975, pairwise
improved 58% at ε = 8 (0.1098 → 0.0459) while independent was unchanged.

A measurement instrument that systematically penalises the thing it is trying to detect
produces a confident null, and nothing about that null looks wrong from the outside. Both
earlier documents reported it in good faith.

## 5. Why the reduced grid also gave the wrong ordering

The 3-seed × 2-ε run reported **pairwise** as the best structure mechanism. On the full
protocol it is **AIM**, by a factor of 3.6 at ε = 8.

Nothing was fixed in between — the difference is sampling. AIM's per-seed variance is high
(its CI at ε = 0.5 spans [0.026, 0.140]) because adaptive selection makes different clique
choices under different noise draws. Three seeds was not enough to rank two mechanisms whose
intervals overlap.

**This is the concrete argument for the preregistered seed count.** A reduced grid did not
merely widen the intervals; it inverted the ordering of the two best mechanisms. Any reader
tempted to trust a 3-seed comparison in this literature should note that.

---

## 6. Threats to validity

- **The privacy half of H1 is unanswered**, and the auditor cannot answer it at any canary
  count this project can run. §3.6.
- **One dataset.** ACS PUMS was not run; every conclusion here is single-dataset. Logged as
  preregistration deviation D1.
- **The structure metric is one column pair.** `capital_gain` (91.6% zeros) and `capital_loss`
  (95.5%) are degenerate and excluded, leaving `age` × `hours_per_week`. A mechanism that
  happens to measure that pair is advantaged — this is the most likely challenge to §3.3.
- **6,000-row subsample**, not the full 30,162.
- **Weak true correlation (0.1034).** The separation is real but small in absolute terms; on a
  synthetic table with correlation 0.975 the same comparison separates far more sharply.
- **`pairwise` uses a fixed public chain**, not data-adaptive structure selection, so it pays
  nothing for structure while AIM does — which makes AIM's win the more conservative reading.
- **AIM's model size is bounded** to 128 MB; cliques exceeding it are refused and recorded in
  `skipped_cliques_`. On this table none were refused.

## 7. Next

| | |
|---|---|
| **M2.1+** | A stronger adversary. The audit ceiling caps what canary counts can certify, so the remaining lever is adversary strength, not sample size |
| M1.4 | ACS PUMS — removes the single-dataset limitation |
| — | A workload-wide fidelity metric (k-way marginal TV error), so §6's single-pair caveat goes away |
| — | Full 30,162-row run |
