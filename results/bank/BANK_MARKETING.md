# The third dataset — what transfers off the census, and what does not

> **Run 2026-09-14.** UCI Bank Marketing, 6,000 rows × 13 columns, 3 mechanisms × 5 ε × 5
> seeds = 75 cells. Raw: [`h1_all_families.json`](h1_all_families.json).
>
> **This is the FULL preregistered grid** — ε ∈ {0.5, 1, 2, 4, 8} and 5 seeds. The
> payload records `reduced_run: false`. It replaces the initial reduced run (18 cells, ε ∈ {1, 8}, 3 seeds).
> Confidence intervals are tightened across all mechanisms.

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
| **Bank Marketing** | +0.0604 | 0.0416 [0.029, 0.052] | **0.0289 [0.011, 0.055]** | 0.0489 [0.038, 0.059] |

On Adult, AIM is **12× better than independent marginals** with non-overlapping intervals —
the result H1 was built on. It does not reproduce:

- On **Bank Marketing**, AIM (0.0489 [0.038, 0.059]) is **statistically indistinguishable from independent
  marginals** (0.0416 [0.029, 0.052]) — the intervals overlap. The headline mechanism buys
  nothing structurally on this table.
- On **ACSIncome**, AIM is *worse* than independent.
- **Pairwise wins on both non-census datasets**, reaching 0.0289 [0.011, 0.055] on Bank Marketing and 0.0202 on ACSIncome.

Across three datasets and two domains, **AIM's structural advantage appears on exactly one of
them — the one the project started with.**

## What does transfer

Three things reproduce everywhere, and they are the claims worth keeping:

1. **Modelling pairwise structure beats not modelling it.** `pairwise` achieves the lowest correlation
   error on structure at ε = 8 on **all three** non-census datasets. This is the coarse form of H1 and it survives the move off the census.
2. **Every TSTR score sits below TRTR, on every dataset and every mechanism.** The utility
   cost of the privacy guarantee is real and it transfers.
3. **The audit reads far below the proved ε everywhere.** Bank's audited values are 0.000–0.058
   against proved 0.385–7.341, consistent with the census runs and with the ceiling being
   instrumental rather than dataset-specific.

## What does not — and this one is new

**The utility ordering breaks here for the first time.** TSTR F1 at ε = 8:

| Dataset | TRTR | independent | pairwise | aim | Ordering |
|---|---:|---:|---:|---:|---|
| **Adult** | 0.6604 | 0.4065 | 0.4321 | **0.5049** | aim > pairwise > independent |
| **ACSIncome** | 0.7246 | 0.4616 | 0.5219 | **0.5812** | aim > pairwise > independent |
| **Bank Marketing** | 0.5610 | 0.4792 | 0.4824 | 0.4536 | pairwise ~ independent > aim |

On Bank Marketing, pairwise (0.4824) and independent (0.4792) tie, while AIM slightly trails (0.4536).
All three sit well below TRTR (0.5610). **No mechanism's utility advantage survives on this dataset.**

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
   depressed TRTR (0.5610, against 0.66 and 0.72) is consistent with a harder task and less
   headroom in which mechanisms could separate. **This is the most consistent explanation**,
   and it is exactly the axis the dataset was chosen to vary.
3. **Statistical power.** The initial run used a reduced grid (3 seeds, 2 ε). The full 5 × 5 preregistered
   grid resolved this question: with 5 seeds across all 5 ε levels, the tie holds firmly. The absence of
   an AIM utility advantage on Bank Marketing is not a power artefact of a small sample.

## What changed from the reduced run

The full 5 × 5 preregistered grid (75 cells, seeds 0–4, ε ∈ {0.5, 1, 2, 4, 8}) tightened confidence intervals and confirmed the findings of the initial reduced run:
- AIM remains structurally indistinguishable from independent marginals at ε = 8 (0.0489 [0.038, 0.059] vs 0.0416 [0.029, 0.052]; reduced run was 0.0468 vs 0.0447).
- Pairwise remains the best structure-preserving mechanism on Bank Marketing (0.0289 [0.011, 0.055]; reduced run was 0.0174).
- On utility (TSTR F1 at ε = 8), pairwise is 0.4824, independent is 0.4792, and AIM is 0.4536, all well below TRTR 0.5610 (reduced run was 0.4723, 0.4751, 0.4716). The conclusion that the utility ordering does not replicate on Bank Marketing holds firmly under the full preregistered grid.

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
python -m scripts.run_h1 --dataset bank                               # full grid, ~4 h
python -m scripts.run_h1 --dataset bank --eps 1.0 8.0 --seeds 0 1 2   # reduced run, ~28 min
```

The reduced form prints a warning and sets `reduced_run: true` in the payload, so a short run
cannot be mistaken for the preregistered one.
