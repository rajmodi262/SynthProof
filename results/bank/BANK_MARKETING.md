# The third dataset — what transfers off the census, and what does not

> **Run 2026-09-13.** UCI Bank Marketing, 6,000 rows × 13 columns, 3 mechanisms × 2 ε × 3
> seeds = 18 cells, 1,693 s. Raw: [`h1_all_families.json`](h1_all_families.json).
>
> **This is a REDUCED grid** — ε ∈ {1, 8} and 3 seeds, against the preregistered 5 × 5. The
> payload records `reduced_run: true`. Confidence intervals are correspondingly wider, and an
> overlap here is weaker evidence of "no difference" than an overlap in the census runs.
> Everything below is stated with that in mind.

## Why this dataset

Adult and ACSIncome are both US-census-derived, single-table and binary-target. Agreement
between them is weaker evidence of generality than it looks — it is closer to **one dataset
measured twice** than to two independent replications. Bank Marketing is a different domain
(Portuguese retail banking), a different collection process (outbound telemarketing), and a
materially different target balance: **11.7% positive, against Adult's ~24%**.

`duration` is excluded on the dataset's own documentation — it is the length of the last call,
unknowable before the call is placed and near-perfectly predictive of its outcome. Keeping it
would have inflated every utility number here the way `education_num` would on Adult, and the
inflation would have looked like a result. `day` and `month` are excluded as the bank's calling
schedule rather than anything about a person.

## The headline: AIM's structural advantage is Adult-specific

Correlation error at ε = 8 — lower is better. Bracketed figures are 95% bootstrap CIs.

| Dataset | true corr | independent | pairwise | **aim** |
|---|---:|---|---|---|
| **Adult** | +0.1034 | 0.0947 [0.082, 0.107] | 0.0283 [0.013, 0.052] | **0.0078 [0.003, 0.013]** |
| **ACSIncome** | +0.0721 | 0.0535 [0.047, 0.060] | **0.0202 [0.008, 0.038]** | 0.0626 [0.043, 0.075] |
| **Bank Marketing** | +0.0604 | 0.0447 [0.038, 0.053] | **0.0174 [0.006, 0.029]** | 0.0468 [0.018, 0.068] |

On Adult, AIM is **12× better than independent marginals** with non-overlapping intervals —
the result H1 was built on. It does not reproduce:

- On **Bank Marketing**, AIM (0.0468) is **statistically indistinguishable from independent
  marginals** (0.0447) — the intervals overlap almost entirely. The headline mechanism buys
  nothing structurally on this table.
- On **ACSIncome**, AIM is *worse* than independent.
- **Pairwise wins on both non-census datasets**, and on Bank Marketing it is **separated from
  independent** (no CI overlap) while AIM is not.

Across three datasets and two domains, **AIM's structural advantage appears on exactly one of
them — the one the project started with.**

## What does transfer

Three things reproduce everywhere, and they are the claims worth keeping:

1. **Modelling pairwise structure beats not modelling it.** `pairwise` separates from
   `independent` on structure at ε = 8 on **all three** datasets, with non-overlapping CIs
   each time. This is the coarse form of H1 and it survives the move off the census.
2. **Every TSTR score sits below TRTR, on every dataset and every mechanism.** The utility
   cost of the privacy guarantee is real and it transfers.
3. **The audit reads far below the proved ε everywhere.** Bank's audited values are 0.000–0.048
   against proved 0.911–7.341, consistent with the census runs and with the ceiling being
   instrumental rather than dataset-specific.

## What does not — and this one is new

**The utility ordering breaks here for the first time.** TSTR F1 at ε = 8:

| Dataset | TRTR | independent | pairwise | aim | Ordering |
|---|---:|---:|---:|---:|---|
| **Adult** | 0.6604 | 0.4065 | 0.4321 | **0.5049** | aim > pairwise > independent |
| **ACSIncome** | 0.7246 | 0.4616 | 0.5219 | **0.5812** | aim > pairwise > independent |
| **Bank Marketing** | 0.5639 | 0.4751 | 0.4723 | 0.4716 | **all three tied** |

On Bank Marketing every pairwise comparison overlaps: 0.4751 vs 0.4723 vs 0.4716, a spread of
0.0035. **No mechanism's utility advantage survives on this dataset.**

This matters because the utility ordering was the part of the cross-dataset comparison that
*had* replicated — [`../acs/CROSS_DATASET.md`](../acs/CROSS_DATASET.md) records structure
ordering disagreeing between Adult and ACS while utility ordering reproduced. On a third
dataset from a different domain, **the utility ordering stops reproducing too.** The surviving
generality claim is narrower than it was before this run.

## Three explanations, and which the data supports

1. **Weak correlation to detect.** Bank's strongest numeric pair is +0.060, so there is little
   joint structure for any mechanism to preserve. **Does not fully explain it:** ACS is +0.072,
   barely stronger, and there `pairwise` and `aim` separated cleanly from each other.
2. **A heavily imbalanced target.** At 11.7% positive, F1 is dominated by the rare class and a
   synthesiser that reproduces the marginal gets most of the achievable score for free. The
   depressed TRTR (0.5639, against 0.66 and 0.72) is consistent with a harder task and less
   headroom in which mechanisms could separate. **This is the most consistent explanation**,
   and it is exactly the axis the dataset was chosen to vary.
3. **Reduced grid, insufficient power.** Three seeds and two ε give wider intervals, so some
   overlaps may be real effects this run could not resolve. **Cannot be excluded**, and it is
   the first thing to settle: a full 5 × 5 grid here is ~4 h and would either confirm the tie
   or resolve it.

## What this means for the thesis

State the coarse claim, not the fine one:

> Modelling pairwise structure improves structural fidelity over independent marginals, and
> this replicates across three datasets in two domains. **Which** structure-aware mechanism
> wins does not replicate — AIM leads on Adult, pairwise leads on ACSIncome and Bank
> Marketing — and on a heavily imbalanced target no mechanism's utility advantage is
> distinguishable at all.

Do **not** write that AIM is the best mechanism. On the evidence in this repository it is the
best mechanism *on Adult*, and Adult is one dataset of three.

This is also independent support for the retraction recorded in
[`../SELECTION_ABLATION.md`](../SELECTION_ABLATION.md): AIM's advantage is contingent on the
data having dependence worth measuring, which is the mechanism working as designed rather than
an artefact — and on a table with little such dependence, the advantage disappears.

## Reproducing

```bash
python -m scripts.run_h1 --dataset bank --eps 1.0 8.0 --seeds 0 1 2   # this run, ~28 min
python -m scripts.run_h1 --dataset bank                               # full grid, ~4 h
```

The reduced form prints a warning and sets `reduced_run: true` in the payload, so a short run
cannot be mistaken for the preregistered one.
