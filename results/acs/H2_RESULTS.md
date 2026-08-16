# H2 on ACSIncome — the null replicates

Generated from `results/acs/h2_subgroups.json` and `results/acs/h2_analysis.json`.
Every number below is read from those files; none is typed by hand.

- Mechanism: `pairwise` · canaries: 400 (allocated **equally** across subgroups)
- Attributes: SEX, RAC1P · eps grid: [1.0, 8.0] · seeds: [0, 1, 2]
- n = 6000, completed in 38 s

---

## Verdict

> 22 tests at alpha=0.05. Raw p<alpha: 0 (chance alone predicts 1.1). Surviving BH-FDR: 0. Surviving Bonferroni: 0. No subgroup shows significant leakage after FDR control, so H2 is NOT supported. 1 of 22 comparisons are statistically EQUIVALENT to chance within the pre-specified margin — a positive bound on the effect rather than an absence of evidence. With m=44 guesses at alpha=0.05, the smallest detectable audited epsilon is 0.006 (requiring adversary accuracy 0.636), and the largest certifiable value is 2.65. The largest observed bound was 0.096 at accuracy 0.591 — 3.6% of the instrument's range. A null at this scale bounds the effect; it does not establish its absence.

## Cross-dataset comparison

| | UCI Adult | ACSIncome |
|---|---|---|
| subgroup comparisons | 14 | 22 |
| with a positive bound | 4 | 3 |
| surviving BH-FDR | 0 | 0 |
| surviving Bonferroni | 0 | 0 |

Broken out by attribute, because the two attributes get very different instruments:

| attribute | levels | canaries/group | ceiling | comparisons | largest bound |
|---|---:|---:|---:|---:|---:|
| Adult `sex` | 2 | 200 | 4.19 | 4 | 0.000 |
| ACS `SEX` | 2 | 200 | 4.19 | 4 | 0.000 |
| Adult `race` | 5 | 80 | 3.27 | 10 | 0.036 |
| ACS `RAC1P` | 9 | 44 | 2.65 | 18 | 0.096 |

**H2 is not supported on either dataset, and for the same reason.** The instrument's
ceiling, not the mechanisms, is what bounds the answer.

### The one thing that could not be held constant

Equal allocation splits a fixed 400-canary budget across however many levels
an attribute has. `sex`/`SEX` has 2 levels on both datasets, so both get 200 canaries per
group and an identical ceiling of 4.19 — that comparison is clean.

Race is not. Adult's `race` has 5 levels and ACS's `RAC1P` has 9,
so ACS gets **44 canaries per group against Adult's 80**, and a ceiling of
**2.65 against 3.27**. ACS's race instrument is genuinely weaker
*before any mechanism runs*. Raising ACS's budget to equalise the ceilings would have
confounded group count with total canary count instead, so the budget was held fixed and the
difference is reported rather than corrected away.

Pinned by `tests/test_subgroup_audit.py::test_the_per_group_ceiling_falls_as_the_attribute_gains_levels`.

### Detectability on ACS

- Smallest detectable audited epsilon: **0.006** (needs adversary accuracy 0.636)
- Largest certifiable value (ceiling): **2.65**
- Largest observed: **0.096** at accuracy 0.591
- Fraction of the instrument's range used: **3.6%**

A null occupying a few percent of the instrument's range bounds the effect; it does not
establish its absence. That distinction is why the ceiling is reported at all.

## Reproducing

```
make h2-acs
python -m scripts.analyse_h2 --dataset acs
```
