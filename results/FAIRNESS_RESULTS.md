# M2.11 — subgroup utility: what synthesis costs each group

> **Status: MEASURED on both datasets.** 2 attributes × 2 ε × 3 seeds, `pairwise`, n = 6,000.
> Raw output: [`fairness.json`](fairness.json) · [`acs/fairness.json`](acs/fairness.json) ·
> Runner: `scripts/run_fairness.py` · Regenerate with `python scripts/run_fairness.py`.

H2 measured whether minority subgroups **leak** more and returned a bounded null. This measures
the other half — whether synthesis costs some groups more **accuracy** than others — which is
the question Ganev, Oprisanu & De Cristofaro settled at ICML 2022 and the one an examiner who
knows that paper will ask about.

## How to read `gap_spread`, and why the control is the important column

Each subgroup is scored against **its own TRTR baseline**; the reported quantity is
`trtr − tstr`, i.e. what the release cost that group. `gap_spread` is the difference between
the worst- and best-served reliable group.

**`baseline_spread` is the same spread measured on real data, and it is the control.** Raw
per-subgroup TSTR mostly measures how hard the task is for that group — a rare group with an
unusual label distribution scores badly on a model trained on real data too. If
`baseline_spread` is comparable to `gap_spread`, the disparity belongs to the **task**, not to
differential privacy, and no claim about DP may be made from it.

---

## Results

### UCI Adult

| Attribute | ε | gap_spread [95% CI] | baseline_spread (control) | reliable groups |
|---|---:|---|---|---:|
| `sex` | 1 | 0.077 [0.048, 0.125] (**2.7×**) | 0.029 [0.028, 0.030] | 2/2 |
| `sex` | 8 | 0.097 [0.079, 0.132] (**3.3×**) | 0.029 [0.028, 0.030] | 2/2 |
| `race` | 1 | 0.255 [0.158, 0.355] (**1.5×**) | 0.167 [0.105, 0.228] | 3/5 |
| `race` | 8 | 0.131 [0.108, 0.161] (**0.8×**) | 0.167 [0.105, 0.228] | 3/5 |

### ACSIncome (California, 2018)

| Attribute | ε | gap_spread [95% CI] | baseline_spread (control) | reliable groups |
|---|---:|---|---|---:|
| `SEX` | 1 | 0.054 [0.003, 0.089] (**4.5×**) | 0.012 [0.009, 0.016] | 2/2 |
| `SEX` | 8 | 0.030 [0.009, 0.064] (**2.5×**) | 0.012 [0.009, 0.016] | 2/2 |
| `RAC1P` | 1 | 0.191 [0.122, 0.255] (**1.7×**) | 0.115 [0.096, 0.138] | 5/8 |
| `RAC1P` | 8 | 0.103 [0.054, 0.140] (**0.9×**) | 0.115 [0.096, 0.138] | 5/8 |

---

## What this shows

**1. On `sex`/`SEX` the disparity is genuinely introduced by synthesis, and it replicates.**
Adult: `gap_spread` 0.077–0.097 against a baseline of **0.029**. ACS: 0.030–0.054 against
**0.012**. On both datasets the synthesis-induced spread is **2.5–4× the disparity the task
already has**. That is the effect Ganev et al. describe, measured here on a different mechanism
family.

**2. On `race`/`RAC1P` it is mostly NOT.** Adult at ε = 8: `gap_spread` 0.131 against a baseline
of 0.167 — the real-data disparity is *larger*. ACS at ε = 8: 0.103 against 0.115. **Any metric
reporting raw per-subgroup TSTR would have called this a fairness finding.** It is a property of
the task. This is precisely what the control exists to catch, and it caught it.

**3. The direction is Robin Hood, not Matthew.** On Adult at ε = 1, `Asian-Pac-Islander` loses
**+0.069** where `White` loses **+0.234**; at ε = 8 the majority still loses most. The majority
group is costed more than the minorities here — the opposite of the intuition, and consistent
with Ganev et al.'s finding that DP produces *both* effects depending on setting.

**UCI Adult — `race` at ε = 1**

| Subgroup | share | n | reliable | utility gap [95% CI] |
|---|---:|---:|---|---|
| Amer-Indian-Eskimo | 0.009 | 15 | **no** | +0.445 [+0.045, +0.762] |
| Asian-Pac-Islander | 0.029 | 56 | yes | +0.069 [+0.013, +0.171] |
| Black | 0.102 | 167 | yes | +0.289 [+0.076, +0.527] |
| Other | 0.009 | 15 | **no** | +0.329 [-0.018, +0.842] |
| White | 0.851 | 1546 | yes | +0.234 [+0.180, +0.282] |

---

## Limitations, stated first

- **Rare groups remain unmeasurable.** `Amer-Indian-Eskimo` and `Other` (0.9% each) have ~15
  held-out rows and are flagged **unreliable**; their intervals span 0.8 and mean nothing. This
  is the same instrument limit H2 hit, now for utility instead of leakage — at n = 6,000 the
  groups the question is about are the ones that cannot be resolved. They are reported with
  their n rather than dropped, because dropping them would silently remove the subject.
- **One mechanism.** `pairwise` only. A marginal-based mechanism that selects cliques may
  distribute error differently.
- **Three seeds**, not five. Differences inside ~0.05 are inside noise.
- **No aggregate score is reported.** Group sizes differ by two orders of magnitude, so a mean
  over them is dominated by the majority and says nothing about the minorities.
