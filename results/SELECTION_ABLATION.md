# Selection ablation — does measuring a pair help because it was *selected*, or because it is *dependent*?

<!-- provenance: results/clique_confound.json, results/selection_ablation.json, results/acs/selection_ablation.json -->

> **First run 2026-08-25; re-run on current code 2026-10-16.** UCI Adult: 175 fits (7 arms x 5
> epsilon x 5 seeds); ACSIncome: 100 fits (4 arms x 5 epsilon x 5 seeds); n = 6,000 each.
> Raw output: [`selection_ablation.json`](selection_ablation.json),
> [`acs/selection_ablation.json`](acs/selection_ablation.json) ·
> Runner: `scripts/run_selection_ablation.py` · Regenerate: `python -m scripts.run_selection_ablation`
> (add `--dataset acs`), then `python -m scripts.build_results_docs` for the tables below.
>
> **This experiment refutes part of our own published reading.** It was designed with its
> falsification criterion fixed in the runner's docstring *before* it was run.
>
> **Every table in this file is generated from the JSON.** The earlier tables were typed by hand
> and went stale when the JSON changed; see "Why the numbers changed" below and
> [`../CORRECTIONS.md`](../CORRECTIONS.md).

---

## Why it was run

[`clique_confound.json`](clique_confound.json) records `"confound_confirmed": true` and a verdict
saying AIM's structure advantage "exists exactly where it spent a clique". That verdict does not
survive scrutiny, for a reason found by the deep survey
([`../research/10_deep_survey_2026-08-25.md`](../research/10_deep_survey_2026-08-25.md), Axis C):

**AIM selects almost exactly the most-dependent numeric pair and nothing else.**

| \|true corr\| | selection rate | pair |
|---:|---:|---|
| 0.1034 | **0.88** | `age x hours_per_week` |
| 0.0797 | 0.00 | `hours_per_week x capital_gain` |
| 0.0736 | 0.00 | `age x capital_gain` |
| 0.0646 | 0.00 | `age x capital_loss` |
| 0.0412 | 0.00 | `hours_per_week x capital_loss` |
| 0.0306 | 0.00 | `capital_gain x capital_loss` |

`corr(|true corr|, selection rate)` = **+0.700** on Adult, **+0.809** on ACS. "Selected" and
"strongly dependent" are therefore confounded, and the within-pair analysis that would break the
confound has **one** pair in both states on each dataset with **no confidence interval**
(`pairs_with_both_states: 1`, `delta_ci: null`).

Chen, Gong & Wang ([arXiv:2511.13893](https://arxiv.org/abs/2511.13893) §6.3) state the rival
explanation for Adult directly: the unselected pairs there are nearly independent, so the
independent-marginals baseline is a **correct** model on them, not a weak one.

## Design

`FixedWorkloadGenerator` takes a **public, explicit** workload, so measurement can be decoupled
from dependence. For each target pair we fit an arm whose workload is exactly that one pair, then
evaluate correlation error on **every** pair. Every arm has an identical budget structure — four
one-way marginals plus exactly one two-way — and differs only in *which* pair was measured. A
`none` arm measuring no two-way marginal is the floor.

Because the evaluated pair is the same on both sides of each comparison, **true dependence is
held fixed by construction**. That is the control the original confound analysis lacked.

Intervals are 95% percentile bootstraps (4,000 resamples, each side resampled independently) of
the difference of means, computed in the runner and saved in the JSON.

## Result — UCI Adult

<!-- BEGIN GENERATED: selection-table-adult -->
| pair | \|true corr\| | err measured | err not measured | effect | 95% CI | relative |
|---|---:|---:|---:|---:|---|---:|
| `age x hours_per_week` | 0.1034 | 0.0177 | 0.1025 | −0.0848 | [−0.0919, −0.0766] | −82.8% |
| `hours_per_week x capital_gain` | 0.0797 | 0.0266 | 0.0797 | −0.0530 | [−0.0602, −0.0454] | −66.6% |
| `age x capital_gain` | 0.0736 | 0.0228 | 0.0731 | −0.0503 | [−0.0589, −0.0389] | −68.8% |
| `age x capital_loss` | 0.0646 | 0.0249 | 0.0639 | −0.0390 | [−0.0512, −0.0248] | −61.1% |
| `hours_per_week x capital_loss` | 0.0412 | 0.0242 | 0.0413 | −0.0171 | [−0.0240, −0.0091] | −41.4% |
| `capital_gain x capital_loss` | 0.0306 | 0.0266 | 0.0289 | −0.0023 | [−0.0108, +0.0071] *(spans 0)* | −7.9% |

`corr(|true corr|, effect)` = **−0.997** over all 6 pairs. Measuring helped on 6 of 6 pairs. *Generated from `results/selection_ablation.json`.*
<!-- END GENERATED: selection-table-adult -->

## What this means, honestly

**1. The strong confound claim is withdrawn.** The benefit of measuring a pair scales tightly
with that pair's true dependence. AIM selects the most dependent pair; measurement helps most
there; therefore AIM's advantage on `age x hours_per_week` is **the mechanism working as
designed**, not an artefact of selection. Chen, Gong & Wang's explanation stands, and
`clique_confound.json`'s `"confound_confirmed": true` is superseded by this better-controlled
experiment.

**2. What survives is an evaluation-design claim, and it is still substantial.** Measuring the
scored pair cuts its error on five of the six Adult pairs with an interval clear of zero, by the
most on the headline pair (the `relative` column above). A benchmark that scores a single fixed
low-order statistic therefore reports, to a large degree, *whether the mechanism chose to spend
budget on that statistic*. That remains true even though the choice is rational. The correct
framing is about **benchmark construction**, never about the mechanism being flattered by an
artefact.

**3. The degradation observation did NOT reproduce, and it was never novel.** The 2026-08-25 run
reported that measuring the *least* dependent pair (`capital_gain x capital_loss`) made its error
**+240.9%** worse, with an interval clear of zero, and the 2026-09-16 run read +248.5%. On the
current code that pair reads in the table above: a small reduction whose interval **spans
zero**. The degradation is therefore **not established on either dataset** and must not be
quoted. Why the number moved is recorded below.

> ⚠️ **NOT NOVEL even when it appeared. Checked 2026-08-25 and killed.** An earlier version of
> this section called the degradation "a new result, and the most interesting thing here". It is
> neither new nor ours.
>
> **PrivSyn** (Zhang, Wang, Li, Honorio, Backes, He, Chen & Zhang,
> [arXiv:2012.15128](https://arxiv.org/abs/2012.15128), 2020) §3.2 states it in one sentence,
> verified directly against the ar5iv full text:
>
> > *"When some attributes are independent, capturing the relationship among them actually
> > increases the amount of noise."*
>
> And §4.2 formalises the decision as exactly the tradeoff this experiment varies —
> `minimize sum_i [psi_i * x_i + phi_i * (1 - x_i)]`, noise error against dependency error, with
> the dependency term approximated by `InDif_{a,b} = |M_{a,b} - M_a x M_b|_1`, which *is* the
> deviation-from-independence signal.
>
> **AIM's own Eq. (1)** encodes the same rule as a quality score — current model error minus
> expected measurement noise, described as "expected improvement" and explicitly allowed to go
> negative. `CONFIDENCE: high` on the kill.

**The "crossover calibration" claim is withdrawn with it.** An earlier version said this
experiment located where the sign flips (below |corr| ~ 0.03-0.05 on Adult). With no pair
degrading significantly on the current code, there is no measured crossover to report.

**Still unchecked:** private-PGM ([arXiv:1901.09136](https://arxiv.org/abs/1901.09136)) could not
be retrieved. It is the most likely home for a "more measurements never hurt" monotonicity
theorem. Treat it as UNCHECKED, not as clear.

## ACS replication

<!-- BEGIN GENERATED: selection-table-acs -->
| pair | \|true corr\| | err measured | err not measured | effect | 95% CI | relative |
|---|---:|---:|---:|---:|---|---:|
| `AGEP x WKHP` | 0.0721 | 0.0269 | 0.0764 | −0.0496 | [−0.0563, −0.0424] | −64.8% |
| `WKHP x SCHL` | 0.0457 | 0.0201 | 0.0433 | −0.0231 | [−0.0311, −0.0142] | −53.5% |
| `AGEP x SCHL` | 0.0077 | 0.0149 | 0.0105 | +0.0045 | [−0.0015, +0.0113] *(spans 0)* | +42.7% |

`corr(|true corr|, effect)` = **−0.996** over all 3 pairs. Measuring helped on 2 of 3 pairs. *Generated from `results/acs/selection_ablation.json`.*
<!-- END GENERATED: selection-table-acs -->

**The ACS correlation is not meaningful on its own** — ACS has only three numeric pairs, and a
near-perfect correlation over three points is close to arithmetic inevitability. It is reported
for completeness, not as evidence.

## Against the stricter floor — measuring nothing at all

The tables above compare "measured" with "some *other* pair was measured". The stricter baseline
is the **`none` arm**, which measures no two-way marginal:

<!-- BEGIN GENERATED: selection-floor-table -->
| dataset | pair | \|true corr\| | err measured | err none arm | effect vs none | 95% CI |
|---|---|---:|---:|---:|---:|---|
| Adult | `age x hours_per_week` | 0.1034 | 0.0177 | 0.1028 | −0.0851 | [−0.0937, −0.0757] |
| Adult | `hours_per_week x capital_gain` | 0.0797 | 0.0266 | 0.0762 | −0.0496 | [−0.0586, −0.0408] |
| Adult | `age x capital_gain` | 0.0736 | 0.0228 | 0.0776 | −0.0548 | [−0.0649, −0.0424] |
| Adult | `age x capital_loss` | 0.0646 | 0.0249 | 0.0623 | −0.0375 | [−0.0511, −0.0220] |
| Adult | `hours_per_week x capital_loss` | 0.0412 | 0.0242 | 0.0425 | −0.0183 | [−0.0273, −0.0093] |
| Adult | `capital_gain x capital_loss` | 0.0306 | 0.0266 | 0.0291 | −0.0025 | [−0.0114, +0.0074] *(spans 0)* |
| ACS | `AGEP x WKHP` | 0.0721 | 0.0269 | 0.0683 | −0.0414 | [−0.0487, −0.0338] |
| ACS | `WKHP x SCHL` | 0.0457 | 0.0201 | 0.0482 | −0.0281 | [−0.0373, −0.0181] |
| ACS | `AGEP x SCHL` | 0.0077 | 0.0149 | 0.0124 | +0.0025 | [−0.0040, +0.0099] *(spans 0)* |

*Generated from `results/selection_ablation.json` and `results/acs/selection_ablation.json`.*
<!-- END GENERATED: selection-floor-table -->

**What this establishes:** the main result holds against the floor on both datasets — measuring
helps most on the most dependent pair, which is the pair AIM selects, so the withdrawal of the
confound reading holds on both. On the least dependent pair of each dataset the interval spans
zero: **no degradation is established anywhere**.

**A consistency check worth recording:** for every pair, "measured vs another pair measured" and
"measured vs nothing measured" agree closely. Measuring some *other* pair does little to the
evaluated pair, which is what the single-clique design predicts and is evidence the arms behave
as intended.

## Why the numbers changed (2026-10-16)

The runner, its seeds and its grid are unchanged apart from saving the intervals. What changed is
the code under it: `FixedWorkloadGenerator` subclasses `AIMGenerator`, which was rewritten after
the 2026-09-16 run (the D1 noisy-row-count fix in `c0966fd` and the memory fix in `b2d2a29`). The
same experiment on the current estimator gives the tables above. We did not isolate which change
moved the `capital_gain x capital_loss` pair; the earlier degradation rested on that one pair and
its estimate was not robust to a change in the estimator, which is itself the reason not to have
led with it.

The headline conclusion — dependence, not selection, explains AIM's advantage — was the same in
all three runs.

---

## Limits

- **Two datasets**, Adult and ACSIncome, and the main direction holds on both.
- Six numeric pairs on Adult, **three on ACS**. Correlations over so few points are indicative,
  not tight, and the ACS correlation should not be quoted as evidence.
- One clique per arm, which is not how AIM runs. The single-clique design buys clean attribution
  at the cost of realism.
- **No degradation is established.** The zero-inflation question it raised is moot until a pair
  degrades significantly.
- The main result (measuring helps in proportion to true dependence) is the solid one, and it
  holds on both datasets against the `none` floor.
