# H1 on ACSIncome — results and a contradiction

**Status: reporting, not concluding.** The ACS grid contradicts the mechanism ordering
established on UCI Adult. Per the project's standing rules the analysis has **not** been
adjusted to accommodate it. This file records the raw numbers and a diagnosis of the cause;
the decision about what H1 now claims is not made here.

- Grid: 75 cells (3 mechanisms x 5 epsilon x 5 seeds), completed in 4,586 s, no failures.
- Data: `results/acs/h1_all_families.json`
- Cross-dataset tables: `results/acs/CROSS_DATASET.md` (`python -m scripts.compare_datasets`)
- Protocol held identical to Adult: n = 6,000, seeds 0-4, eps in {0.5, 1, 2, 4, 8}.

---

## 1. The contradiction

Correlation error at eps = 8, mean [95% bootstrap CI], lower is better:

| mechanism | UCI Adult | ACSIncome |
|---|---|---|
| independent | 0.0947 [0.0817, 0.1071] | 0.0535 [0.0471, 0.0604] |
| pairwise | 0.0283 [0.0132, 0.0517] | **0.0202 [0.0076, 0.0383]** |
| aim | **0.0078 [0.0031, 0.0125]** | 0.0626 [0.0432, 0.0753] |

- **Adult:** aim > pairwise > independent, all three CIs mutually non-overlapping.
- **ACS:** pairwise > independent > aim, and independent vs aim **do not separate**.

AIM goes from the clear best on Adult to statistically indistinguishable from the
independent-marginals baseline on ACS.

TSTR macro F1 at eps = 8 tells a different story — that ordering **does** reproduce
(aim > pairwise > independent on both) — but on Adult none of its adjacent pairs separate,
so it carries little weight there.

## 2. AIM's utility on ACS *falls* as epsilon rises

This is the more surprising number, and the CIs at the endpoints do not overlap, so it is
not noise:

| eps | AIM TSTR F1 [95% CI] | AIM corr err | selects AGEP x WKHP? |
|---:|---|---|---|
| 0.5 | 0.7039 [0.6946, 0.7126] | 0.0977 | no |
| 1.0 | 0.6918 [0.6831, 0.7016] | **0.0395** | **yes** |
| 2.0 | 0.6498 [0.6212, 0.6750] | 0.0521 | no |
| 4.0 | 0.6510 [0.6333, 0.6696] | 0.0732 | no |
| 8.0 | 0.5812 [0.5386, 0.6289] | 0.0626 | no |

(TRTR baseline on ACS: 0.725 [0.707, 0.742].)

More privacy budget, worse downstream utility. That is backwards, so it was diagnosed
before anything was written down.

## 3. Diagnosis

**Ruled out.** The model-size bound added after the AIM `MemoryError` is *not* responsible:
`skipped_cliques_` is empty at both eps = 0.5 and eps = 8, and 17 cliques are measured at
both. Accounting is unaffected (`proved_eps` behaves normally) and the synthetic income
share matches the real one to within 0.003 at every eps.

**The actual mechanism.** The DP domain profiler suppresses rare categories, and it
suppresses far fewer of them as the budget grows. On ACS this changes the domain enormously,
because the coarsened columns still carry real cardinality:

| column | categories at eps=0.5 | at eps=8 |
|---|---:|---:|
| OCCP | 3 | 23 |
| RELP | 3 | 14 |
| COW | 2 | 7 |
| MAR | 2 | 5 |
| RAC1P | 3 | 6 |

AIM's clique budget is roughly fixed (6 two-way cliques here), so as the domain grows those
six cliques cover proportionally less of it — and fewer of them land on the columns the
metrics happen to measure. The selected two-way cliques bear this out:

- **eps = 0.5:** `SCHL x income`, `MAR x income`, `WKHP x income` — *three* cliques touching
  the target, hence TSTR 0.704, within striking distance of the 0.725 real-data baseline.
- **eps = 8:** `MAR x RELP`, `SCHL x OCCP`, `AGEP x MAR`, `POBP x RAC1P`, `AGEP x RELP`,
  `OCCP x income` — only *one* clique touching the target, hence TSTR 0.581.

AIM optimises a global marginal-approximation objective, not a downstream classification
task. On a dataset whose domain grows sharply with the budget, spending more budget spreads
a fixed clique allowance thinner over the task-relevant marginals. Nothing is broken; the
mechanism is doing what it was designed to do.

## 4. The part that bears on Adult, and matters more

The structure metric is the correlation error of **one column pair**. AIM's score on it is
essentially determined by whether that single pair is among the ~6 two-way cliques AIM
selects.

Selection of the measured pair, across the full epsilon grid:

| eps | Adult: selects `age x hours_per_week`? | ACS: selects `AGEP x WKHP`? |
|---:|---|---|
| 0.5 | yes | no |
| 1.0 | yes | yes |
| 8.0 | yes | no |

On Adult, AIM selects the measured pair at **every** epsilon tested. On ACS it selects it at
**one**. ACS's AIM correlation error tracks that selection exactly: 0.0977 (not selected) ->
0.0395 (selected) -> 0.0626 (not selected).

So Adult's headline "AIM reproduces structure 3.6x better than pairwise" is, to a degree this
grid cannot bound, a statement about a coincidence between the metric's chosen column pair and
AIM's clique selection — not a general claim about structure preservation. ACS did not
reproduce the finding because on ACS the coincidence does not hold.

This was not visible from a single dataset. It is the kind of thing a second dataset exists
to expose.

## 5. What was and was not changed in response

Per the standing rules:

- **The analysis was not changed** to accommodate the disagreement. No metric was swapped,
  reweighted, or supplemented after seeing the result.
- **No committed Adult metric was touched.** `results/h1_all_families.json` was re-derived
  during a manifest refresh and every cell came back byte-identical; only header metadata
  (`dataset`, `dataset_label`, `corr_cols`, `elapsed_seconds`) differs from the previous
  commit. `results/h2_subgroups.json` was genuinely re-run (22.9 s -> 34.5 s) and also
  reproduced byte-identically — independent evidence that the pipeline is deterministic
  under seed.
- **Deviation D1 is now closed**, and the wording says what actually happened: external
  validity was *tested* and the H1 structure ordering *did not transfer*. It does not claim
  external validity was established. See `docs/thesis/ch06-methodology.md` §6.8 and the new
  §6.9, which records the disagreement, the diagnosis, and the two caveats that could not be
  held constant across the datasets.
- **H2 was subsequently run on ACS** and replicates the Adult null (0 of 22 comparisons
  survive BH-FDR or Bonferroni, against 0 of 14 on Adult). See `results/acs/H2_RESULTS.md`.

## 6. Reproducing this

```
make h1-acs
python -m scripts.compare_datasets
```

Clique-selection diagnosis is pinned by
`tests/test_acs_h1_findings.py::test_aim_selects_the_measured_pair_on_adult_at_every_epsilon`.
