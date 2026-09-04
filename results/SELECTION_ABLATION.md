# Selection ablation — does measuring a pair help because it was *selected*, or because it is *dependent*?

> **Run 2026-08-25.** 175 fits: 7 arms x 5 epsilon x 5 seeds, UCI Adult, n = 6,000.
> Raw output: [`selection_ablation.json`](selection_ablation.json) ·
> Runner: `scripts/run_selection_ablation.py` · Regenerate: `python -m scripts.run_selection_ablation`
>
> **This experiment refutes part of our own published reading.** It was designed with its
> falsification criterion fixed in the runner's docstring *before* it was run.

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

## Result

| pair | \|true corr\| | err measured | err not measured | effect | 95% CI | relative |
|---|---:|---:|---:|---:|---|---:|
| `age x hours_per_week` | 0.1034 | 0.0211 | 0.1039 | **-0.0829** | [-0.0885, -0.0764] | **-79.7%** |
| `hours_per_week x capital_gain` | 0.0797 | 0.0419 | 0.0787 | -0.0368 | [-0.0480, -0.0221] | -46.8% |
| `age x capital_gain` | 0.0736 | 0.0291 | 0.0727 | -0.0436 | [-0.0511, -0.0344] | -60.0% |
| `age x capital_loss` | 0.0646 | 0.0286 | 0.0639 | -0.0353 | [-0.0481, -0.0197] | -55.2% |
| `hours_per_week x capital_loss` | 0.0412 | 0.0324 | 0.0414 | -0.0090 | [-0.0225, +0.0079] *(spans 0)* | -21.7% |
| `capital_gain x capital_loss` | 0.0306 | 0.1147 | 0.0337 | **+0.0811** | [+0.0583, +0.1077] | **+240.9%** |

`corr(|true corr|, effect)` = **-0.898** over all six pairs, and **-0.960** with the degrading
pair excluded — so the relationship is *not* an artefact of that outlier.

## What this means, honestly

**1. The strong confound claim is withdrawn.** The benefit of measuring a pair scales tightly
with that pair's true dependence. AIM selects the most dependent pair; measurement helps most
there; therefore AIM's advantage on `age x hours_per_week` is **the mechanism working as
designed**, not an artefact of selection. Chen, Gong & Wang's explanation stands, and
`clique_confound.json`'s `"confound_confirmed": true` is superseded by this better-controlled
experiment.

**2. What survives is an evaluation-design claim, and it is still substantial.** Measuring the
scored pair cuts its error by **53% on average and 80% on the headline pair**. A benchmark that
scores a single fixed low-order statistic therefore reports, to a very large degree, *whether the
mechanism chose to spend budget on that statistic*. That remains true even though the choice is
rational. The correct framing is about **benchmark construction**, never about the mechanism
being flattered by an artefact.

**3. The degradation observation — and it is PUBLISHED, so it is not a finding.** Measuring the
*least* dependent pair made its error **240% worse** on Adult (CI [+0.058, +0.108]).

> ⚠️ **NOT NOVEL. Checked 2026-08-25 and killed.** An earlier version of this section called this
> "a new result, and the most interesting thing here". It is neither new nor ours.
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
> negative. That is the second time in one day that a claim of ours turned out to be in the AIM
> paper. `CONFIDENCE: high` on the kill.

**What is left, and it is small:** PrivSyn and AIM *assert* and *use* this rule; neither isolates
it empirically. This experiment measures where the crossover actually falls for this engine —
sign flip below roughly |corr| ~ 0.03-0.05 on Adult — with the selector deleted so only the
measure/don't-measure bit varies. That is a **calibration of a known rule**, belongs in a
validation-methodology chapter, and must never be pitched as a mechanism finding or a critique of
AIM.

**Still unchecked:** private-PGM ([arXiv:1901.09136](https://arxiv.org/abs/1901.09136)) could not
be retrieved. It is the most likely home for a "more measurements never hurt" monotonicity
theorem, which would complicate the framing above. Treat it as UNCHECKED, not as clear.

It remains a mechanism-level explanation for **H3's null**, and that use is safe because it is
offered as an explanation citing PrivSyn, not as a discovery.


## ACS replication (run 2026-08-25, 100 fits: 4 arms x 5 epsilon x 5 seeds)

| pair | \|true corr\| | err measured | err not measured | effect | relative |
|---|---:|---:|---:|---:|---:|
| `AGEP x WKHP` | 0.0721 | 0.0255 | 0.0695 | -0.0440 | -63.3% |
| `WKHP x SCHL` | 0.0457 | 0.0205 | 0.0438 | -0.0232 | -53.1% |
| `AGEP x SCHL` | 0.0077 | 0.0155 | 0.0111 | **+0.0044** | **+40.1%** |

`corr(|true corr|, effect)` = -1.000. **That number is not meaningful on its own** — ACS has only
three numeric pairs, and a perfect correlation over three points is close to arithmetic
inevitability. It is reported for completeness, not as evidence.

### CORRECTION 2026-08-25 — the ACS degradation is NOT significant, and an earlier draft of this file said it replicated

The comparison above comes from "measured" vs "some *other* pair was measured". The stronger and
more honest baseline is the **`none` arm — measuring no two-way marginal at all** — which the
experiment already runs and which the effects table above excluded. Against that floor:

| dataset | pair | \|corr\| | measured | none arm | effect | 95% CI | verdict |
|---|---|---:|---:|---:|---:|---|---|
| Adult | `capital_gain x capital_loss` | 0.0306 | 0.1147 | 0.0327 | **+0.0821** | [+0.0584, +0.1093] | **worse than not measuring** |
| ACS | `AGEP x SCHL` | 0.0077 | 0.0155 | 0.0111 | +0.0044 | **[-0.0023, +0.0116]** | **spans zero — not significant** |

**So the degradation is established on Adult and NOT established on ACS.** The direction is
consistent, the magnitude is not resolvable at this sample size, and an earlier version of this
section called it a replication. It is not one. The corrected statement:

> On UCI Adult, measuring a near-independent pair produced a correlation error significantly
> **worse than measuring nothing at all**. On ACSIncome the effect points the same way but its
> confidence interval includes zero, so ACS neither confirms nor refutes it.

The zero-inflation confound therefore also remains **partly open**: `AGEP x SCHL` is not
zero-inflated and did degrade directionally, which is suggestive, but a non-significant effect
cannot resolve a confound.

**What the ACS run does establish**, and it is not nothing: the *main* result replicates cleanly.
Measuring helps most on the most dependent pair (`AGEP x WKHP`, -0.0464 against the none arm,
CI [-0.0537, -0.0389]), which is the pair AIM selects — so the withdrawal of the confound reading
holds on both datasets.

**A consistency check worth recording:** for every pair, "measured vs another pair measured" and
"measured vs nothing measured" agree to within a few thousandths. Measuring some *other* pair
does essentially nothing to the evaluated pair, which is what the single-clique design predicts
and is evidence the arms are behaving as intended.

The main finding also replicates in direction: measuring helps most on the most dependent pair
(-63.3% on `AGEP x WKHP`), which is the pair AIM selects — so the withdrawal of the confound
reading holds on both datasets.

---

## Limits

- **Two datasets now**, Adult and ACSIncome, and the direction holds on both.
- Six numeric pairs on Adult, **three on ACS**. Correlations over so few points are indicative,
  not tight, and the ACS `r = -1.000` should not be quoted as evidence.
- One clique per arm, which is not how AIM runs (it measures ~6). The single-clique design buys
  clean attribution at the cost of realism.
- **The zero-inflation confound is still OPEN.** `AGEP x SCHL` is not zero-inflated and degrades
  directionally, which is suggestive, but its interval spans zero and a non-significant effect
  cannot resolve a confound. Settling it needs a pair that is near-independent, NOT zero-inflated,
  and measured with enough power — which this grid does not have.
- **The degradation result rests on ONE pair, on ONE dataset.** It is the most interesting thing
  here and the least established. Do not lead with it until it replicates significantly.
- The main result (measuring helps in proportion to true dependence) is the solid one, and it
  holds on both datasets against the `none` floor.
