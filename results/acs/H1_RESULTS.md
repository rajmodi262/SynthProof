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

> ### ⚠️ Replication note — 2026-09-09
>
> The full 150-cell grid was re-fitted from raw data on different hardware and a different OS
> (Linux, Python 3.11.15, same `requirements.lock` pins). **All 15 ACS aggregate means landed
> inside the committed 95% CIs, and every `independent`/`pairwise` cell was bit-identical.**
> Two statements on this page did *not* survive that re-run, and both should be weakened
> before they are defended:
>
> 1. **The eps-monotonicity result loses its separation.** Committed: TSTR 0.7039
>    [0.6946, 0.7126] at eps=0.5 falling to 0.5812 [0.5386, 0.6289] at eps=8 — endpoints
>    disjoint. Re-run: 0.6624 [0.6019, 0.7224] falling to 0.6110 [0.5913, 0.6307] — **the
>    endpoint CIs overlap.** The *direction* replicates; the *significance* does not. Report
>    it as a direction, or raise the seed count until the separation is stable.
> 2. **The eps=8 mechanism ordering is not stable.** Committed has AIM worst on correlation
>    error (0.0626 vs independent 0.0535); the re-run puts AIM *better* (0.0521 vs 0.0535).
>    The robust claim — true in both runs — is that **AIM and the independent baseline are
>    statistically indistinguishable on ACS**, which is this file's actual point. Do not rank
>    them.
>
> Verified separately: AIM-family results are reproducible in distribution but not
> bit-identically, because `mbi`'s sampler is unseeded (see `scripts/reproduce.py`).

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

### 4a. Tested directly — and the claim above needs weakening

The argument in §4 rests on one measured pair per dataset. `scripts/run_clique_confound.py`
tests it properly: for every numeric pair, at every epsilon and seed, record AIM's correlation
error and whether that pair was among its selected cliques, with the independent-marginal
generator — which models no cross-column dependence — as the floor.

**Adult, per pair (25 cells each):**

| pair | AIM selected | AIM err | independent err | AIM beats floor |
|---|---:|---:|---:|---|
| age x hours_per_week | 22/25 | 0.0263 | 0.1115 | yes |
| hours_per_week x capital_loss | 0/25 | 0.0431 | 0.0502 | yes |
| age x capital_gain | 0/25 | 0.0742 | 0.0758 | no |
| age x capital_loss | 0/25 | 0.0671 | 0.0691 | no |
| capital_gain x capital_loss | 0/25 | 0.0311 | 0.0296 | no |
| hours_per_week x capital_gain | 0/25 | 0.0805 | 0.0795 | no |

**ACS, per pair:**

| pair | AIM selected | AIM err | independent err | AIM beats floor |
|---|---:|---:|---:|---|
| AGEP x WKHP | 12/25 | 0.0541 | 0.0826 | yes |
| WKHP x SCHL | 0/25 | 0.0440 | 0.0564 | yes |
| AGEP x SCHL | 0/25 | 0.0187 | 0.0167 | no |

**What this does and does not establish.**

It does NOT establish "AIM only beats the baseline on pairs it selects". That is false on both
datasets — each has one unselected pair where AIM still wins. That is mechanistically
expected rather than anomalous: measuring a clique constrains the joint distribution, and a
graphical model propagates that constraint to pairs outside the clique.

What it does establish is a large difference in DEGREE, and that the difference itself does
not transfer:

| | largest advantage on a selected pair | largest on an unselected pair | ratio |
|---|---:|---:|---:|
| Adult | +0.0852 | +0.0072 | **11.9x** |
| ACS | +0.0285 | +0.0123 | **2.3x** |

On Adult, AIM's advantage on the pair it selects is nearly twelve times its best advantage
anywhere else — and `age x hours_per_week`, the pair the H1 headline measured, is exactly
that pair, selected in 22 of 25 cells. On ACS the same effect is present but roughly five
times weaker, and the ACS run's own verdict is INCONCLUSIVE.

So the defensible claim is narrower than §4 originally implied: **the structure metric's choice
of column pair materially affects the measured ranking, and on Adult it happened to select
AIM's strongest pair by an order of magnitude.** The stronger reading — that AIM's advantage
is entirely an artefact of selection — is not supported, and the cross-dataset picture is the
same pattern H1 itself showed: an effect on Adult that does not carry to ACS.

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
