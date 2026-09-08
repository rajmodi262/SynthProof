# Canary contamination — dose-response over canary fraction and canary type

> Regenerate: `python -m scripts.run_canary_dose_response`. Raw:
> [`canary_dose_response.json`](canary_dose_response.json). UCI Adult,
> 40 seeds per cell. No model is fitted.

## THE HEADLINE: the 89% figure does not replicate, and must not be quoted

Running the **real** `CanaryAuditor` over 40 seeds, at the H1 configuration
(n = 6,000, m = 60), the destruction of corr('age', 'hours_per_week') is **4.5%** — not 89%.

Two things were wrong with the original number, and both are corrections this project
must make itself before an examiner makes them for it:

1. **The canary COUNT is the wrong axis; the FRACTION m/(n+m) is the right one.** The
   effect rises monotonically with fraction across four independent sizes, and 60
   canaries means something completely different at n = 600 than at n = 6,000.
2. **No individual cell resolves at 40 seeds — which is a statement about our power,
   not about safety.** The seed-to-seed spread
   swamps the shift: `effect / seed-sd` sits near 0.25 everywhere, and the one-sample
   t against the clean value does not reach 2 at any size. At 8 seeds the same cells
   read 9.5%/17.4%/35.7%/54.9%; at 40 they read roughly half that. **A number that
   halves when you add seeds was never a measurement.**

The most likely origin of 89% is that it predates the canary-direction fix recorded in
`audit/canary.py`. If so it describes a defect that was repaired, not a property of
auditing — which is the honest reading and the one to put in the thesis.

**What survives is the SHAPE, not any number:** contamination scales with canary
fraction, and the two extreme canary designs move the statistic in opposite directions.

## `CanaryAuditor` — % of the scored correlation destroyed, by canary fraction

| n | m | fraction | clean corr | augmented | % destroyed | effect/sd | t | 2σ? |
|---:|---:|---:|---:|---:|---:|---:|---:|:--:|
| 6000 | 10 | 0.17% | +0.1034 | +0.1028 | +0.6% | 0.10 | 0.65 | no |
| 3000 | 10 | 0.33% | +0.0930 | +0.0921 | +1.0% | 0.07 | 0.44 | no |
| 1200 | 10 | 0.83% | +0.0951 | +0.0922 | +3.0% | 0.09 | 0.59 | no |
| 6000 | 60 | 0.99% | +0.1034 | +0.0988 | +4.5% | 0.29 | 1.85 | no |
| 600 | 10 | 1.64% | +0.0879 | +0.0834 | +5.2% | 0.08 | 0.48 | no |
| 3000 | 60 | 1.96% | +0.0930 | +0.0866 | +6.9% | 0.22 | 1.40 | no |
| 6000 | 200 | 3.23% | +0.1034 | +0.0935 | +9.7% | 0.46 | 2.93 | **yes** |
| 1200 | 60 | 4.76% | +0.0951 | +0.0796 | +16.3% | 0.28 | 1.76 | no |
| 3000 | 200 | 6.25% | +0.0930 | +0.0816 | +12.3% | 0.34 | 2.13 | **yes** |
| 6000 | 400 | 6.25% | +0.1034 | +0.0915 | +11.6% | 0.53 | 3.34 | **yes** |
| 600 | 60 | 9.09% | +0.0879 | +0.0677 | +23.0% | 0.24 | 1.53 | no |
| 3000 | 400 | 11.77% | +0.0930 | +0.0813 | +12.6% | 0.37 | 2.35 | **yes** |
| 1200 | 200 | 14.29% | +0.0951 | +0.0711 | +25.2% | 0.48 | 3.01 | **yes** |
| 600 | 200 | 25.00% | +0.0879 | +0.0600 | +31.7% | 0.46 | 2.90 | **yes** |
| 1200 | 400 | 25.00% | +0.0951 | +0.0689 | +27.6% | 0.66 | 4.14 | **yes** |
| 600 | 400 | 40.00% | +0.0879 | +0.0568 | +35.3% | 0.71 | 4.47 | **yes** |

**Read the last three columns before quoting any cell.** `effect/sd` answers *can one
seed be trusted?* and does not improve with more seeds. `t` answers *is the mean shift
real?* and does. Where the 2σ column says **no**, the cell is a direction, not a number.

## Canary type, at matched n and m

| n | m | auditor_actual | outlier_fixed_top | marginal_resampled |
|---:|---:|---:|---:|---:|
| 600 | 10 | +5.2% | -255.6% | +1.3% |
| 600 | 60 | +23.0% | -664.4% | +9.8% |
| 600 | 200 | +31.7% | -860.2% | +24.5% |
| 600 | 400 | +35.3% | -918.6% | +40.5% |
| 1200 | 10 | +3.0% | -124.5% | +0.7% |
| 1200 | 60 | +16.3% | -440.0% | +4.7% |
| 1200 | 200 | +25.2% | -684.3% | +14.1% |
| 1200 | 400 | +27.6% | -777.6% | +26.2% |
| 3000 | 10 | +1.0% | -56.9% | +0.4% |
| 3000 | 60 | +6.9% | -259.9% | +2.7% |
| 3000 | 200 | +12.3% | -522.0% | +7.8% |
| 3000 | 400 | +12.6% | -666.7% | +11.1% |
| 6000 | 10 | +0.6% | -25.2% | +0.2% |
| 6000 | 60 | +4.5% | -130.8% | +1.2% |
| 6000 | 200 | +9.7% | -317.2% | +2.8% |
| 6000 | 400 | +11.6% | -457.1% | +6.1% |

`outlier_fixed_top` is a **positive control**: it is the pre-fix design, known to INFLATE
the correlation rather than destroy it (documented in `audit/canary.py`: 0.093 → 0.334).
A negative percentage there means inflation, and its presence confirms the harness can see
contamination in both directions. `marginal_resampled` is the **floor**.

## What this settles, and what it does not

**Settled, and it is a negative result:** the 89% does not replicate against the current
auditor at the configuration it was recorded for. What survives is a monotone dependence
on canary fraction and a strong dependence on canary design — a shape, not a number.

**DO NOT READ THE 2σ COLUMN AS A SAFETY THRESHOLD.** t = 1.85 at 0.99% and t = 2.93 at
3.23% is a boundary of THIS DESIGN'S POWER at 40 seeds, not a property of canary
contamination. The point estimate at 0.99% is still 4.5% of the correlation destroyed —
an UNDERPOWERED effect, not an absent one. Declaring the n = 6,000 / m = 60 configuration
*safe* because p > 0.05 would be accepting the null, which is the error standing rule 5
exists to prevent. This sweep never showed that configuration to be safe; it showed only
that it could not resolve the effect at 40 seeds. Raising seeds would move the boundary.

**Not claimed:** that canary insertion costs utility (Panda et al. arXiv:2503.06808;
Mitchell et al. arXiv:2606.10481). Nor the two-fit remedy — Mitchell et al. S3 recommends
it verbatim; we only QUANTIFY the separation. Nor the diffuse-contamination idea — Mitchell
et al. S4 states it in prose. Nor that a per-record insertion has a generator-dependent
utility effect — Stadler et al. USENIX Security 2022 S6.3.2 report exactly that, on tabular
data, in this project's own generator family.

**What is left, and it is narrow:** that the damage lands on the JOINT rather than on a
scalar aggregate, and whether it is mechanism-DIFFERENTIAL — corrupting the RANKING between
mechanisms rather than taxing them equally. That second half needs the independent-marginals
arm run through synthesis and is **not** settled by this table.
