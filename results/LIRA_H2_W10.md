# LiRA at 64 shadows and a powered H2 (W10b)

<!-- provenance: results/lira_w10.json, results/h2_w10.json, results/h2_w10_analysis.json -->

> **Run 2026-10-16**, as preregistered in [`docs/prereg/W10b_lira_h2.md`](../docs/prereg/W10b_lira_h2.md)
> before either job started (each output records its SHA-256). Raw: [`lira_w10.json`](lira_w10.json),
> [`h2_w10.json`](h2_w10.json), [`h2_w10_analysis.json`](h2_w10_analysis.json).

## LiRA (Carlini et al. 2022), UCI Adult, train size 1000

<!-- BEGIN GENERATED: lira-w10-table -->
| Mechanism | eps | AUC [95% CI] | TPR @ 1% FPR | TPR @ 10% FPR | targets | shadows |
|---|---:|---|---:|---:|---:|---:|
| `leaky_1.0` | control | 1.000 [1.000, 1.000] | 1.000 | 1.000 | 40 | 64 |
| `independent` | 1 | 0.536 [0.476, 0.592] | 0.019 | 0.106 | 40 | 64 |
| `independent` | 8 | 0.510 [0.461, 0.563] | 0.025 | 0.125 | 40 | 64 |
| `pairwise` | 1 | 0.504 [0.450, 0.563] | 0.031 | 0.081 | 40 | 64 |
| `pairwise` | 8 | 0.519 [0.455, 0.576] | 0.050 | 0.150 | 40 | 64 |

*Generated from `results/lira_w10.json`; preregistration SHA-256 2bf68c5a6673...*
<!-- END GENERATED: lira-w10-table -->

The positive control (a generator that copies its training rows verbatim) must reach AUC ≥ 0.9
before any DP mechanism is attacked, and it did. Every DP cell's interval contains 0.5: **no
attack advantage was detected at 64 shadows**. That is a bounded null (a stronger attack, more
shadows or more targets could find what this one did not), not evidence that the releases are
private. MST and AIM were not run: an MST fit costs about 270 s at this train size, about 200 hours
a cell here (stated in the preregistration).

## H2: per-subgroup leakage with an instrument that can resolve epsilon 1

<!-- BEGIN GENERATED: h2-w10-table -->
| Attribute | subgroup | eps | canaries | ceiling | audited eps, mean over seeds | max over seeds | mean accuracy |
|---|---|---:|---:|---:|---:|---:|---:|
| sex | Female | 1 | 2000 | 6.50 | 0.0000 | 0.0000 | 0.4987 |
| sex | Male | 1 | 2000 | 6.50 | 0.0000 | 0.0000 | 0.5022 |
| sex | Female | 8 | 2000 | 6.50 | 0.0001 | 0.0014 | 0.4960 |
| sex | Male | 8 | 2000 | 6.50 | 0.0027 | 0.0275 | 0.5018 |
| race | Amer-Indian-Eskimo | 1 | 800 | 5.59 | 0.0051 | 0.0513 | 0.5035 |
| race | Asian-Pac-Islander | 1 | 800 | 5.59 | 0.0000 | 0.0000 | 0.4923 |
| race | Black | 1 | 800 | 5.59 | 0.0000 | 0.0000 | 0.5084 |
| race | Other | 1 | 800 | 5.59 | 0.0000 | 0.0000 | 0.5033 |
| race | White | 1 | 800 | 5.59 | 0.0021 | 0.0212 | 0.4988 |
| race | Amer-Indian-Eskimo | 8 | 800 | 5.59 | 0.0001 | 0.0012 | 0.4975 |
| race | Asian-Pac-Islander | 8 | 800 | 5.59 | 0.0011 | 0.0112 | 0.4945 |
| race | Black | 8 | 800 | 5.59 | 0.0000 | 0.0000 | 0.4936 |
| race | Other | 8 | 800 | 5.59 | 0.0000 | 0.0000 | 0.5012 |
| race | White | 8 | 800 | 5.59 | 0.0000 | 0.0000 | 0.4950 |

**14 subgroup tests; surviving Benjamini-Hochberg: 0; surviving Bonferroni: 0. Equivalent to chance within the pre-specified margin: 14 of 14.** Largest subgroup mean audited eps 0.0051 against a ceiling of 5.59 at 800 canaries per subgroup.

*Generated from `results/h2_w10.json` and `results/h2_w10_analysis.json`; 4000 canaries, 10 seeds; preregistration SHA-256 2bf68c5a6673...*
<!-- END GENERATED: h2-w10-table -->

At epsilon 1 each subgroup's ceiling exceeds the proved epsilon, so the audit could have
certified the whole budget in any subgroup; it found essentially nothing, and no subgroup differs
after multiplicity control. **H2 (minority subgroups leak more) is not supported.** At epsilon 8 the
ceilings sit below the proved epsilon, so those cells bound the effect only within the instrument's
range. This is one mechanism (pairwise) on one dataset (Adult), as preregistered.

The earlier, smaller runs (16 shadows; 400 canaries, 3 seeds) stay in
[`lira.json`](lira.json) and [`h2_subgroups.json`](h2_subgroups.json).
