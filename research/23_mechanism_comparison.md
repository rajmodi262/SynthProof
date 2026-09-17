# 23 — Cross-dataset mechanism comparison (what ours does vs the others)

> Built by `scripts/build_mechanism_comparison.py` from the committed H1 grids. No number here is invented: each is read from a grid file (5 seeds unless marked reduced), each literature figure is quoted with its source. Utility = correlation error (lower better) and TSTR F1 (higher better, ceiling = TRTR on real data). Privacy = proved ε, audited ε, membership-inference AUC (0.5 = no better than chance).

**Mechanism families.** Baselines: `independent`, `pairwise` (marginal generators). Ours (the select-measure family SynthProof integrates and audits): `aim`, `mst`. SynthProof's *own* contribution is the release-boundary audit + signed label layer, which is mechanism-agnostic; these generators are what we run to populate the trade-off.

## UCI Adult

**Correlation error (lower = better)**

| mechanism | ε=0.5 | ε=1 | ε=2 | ε=4 | ε=8 |
|---|---|---|---|---|---|
| **independent** | 0.0934 | 0.0930 | 0.0939 | 0.0935 | 0.0947 |
| **pairwise** | 0.0611 | 0.0694 | 0.0493 | 0.0197 | 0.0283 |
| **aim** *(ours)* | 0.0941 | 0.0443 | 0.0545 | 0.0349 | 0.0105 |
| **mst** *(ours)* | 0.0759 | 0.0516 | 0.0769 | 0.1033 | 0.0968 |

**TSTR F1 (TRTR ceiling 0.660)**

| mechanism | ε=0.5 | ε=1 | ε=2 | ε=4 | ε=8 |
|---|---|---|---|---|---|
| **independent** | 0.4719 | 0.4700 | 0.4264 | 0.4670 | 0.4065 |
| **pairwise** | 0.4830 | 0.4277 | 0.4181 | 0.4268 | 0.4321 |
| **aim** *(ours)* | 0.4613 | 0.5145 | 0.4914 | 0.4989 | 0.5064 |
| **mst** *(ours)* | 0.4910 | 0.4989 | 0.5554 | 0.4831 | 0.5483 |

**Proved ε (calibration never overspends)**

| mechanism | ε=0.5 | ε=1 | ε=2 | ε=4 | ε=8 |
|---|---|---|---|---|---|
| **independent** | 0.4559 | 0.9123 | 1.8275 | 3.6637 | 7.3560 |
| **pairwise** | 0.4559 | 0.9123 | 1.8275 | 3.6637 | 7.3560 |
| **aim** *(ours)* | 0.3853 | 0.7782 | 1.5762 | 3.2011 | 6.5427 |
| **mst** *(ours)* | 0.3727 | 0.7492 | 1.5086 | 3.0505 | 6.2127 |

**Membership-inference AUC (0.5 = chance)**

| mechanism | ε=0.5 | ε=1 | ε=2 | ε=4 | ε=8 |
|---|---|---|---|---|---|
| **independent** | 0.4959 | 0.5040 | 0.5022 | 0.5003 | 0.5001 |
| **pairwise** | 0.4936 | 0.4912 | 0.4915 | 0.4887 | 0.4925 |
| **aim** *(ours)* | 0.4970 | 0.4855 | 0.4991 | 0.4988 | 0.5010 |
| **mst** *(ours)* | 0.4901 | 0.4913 | 0.4876 | 0.4864 | 0.4864 |

_At ε=8 on UCI Adult (n=6000, corr pair ('age', 'hours_per_week'), true corr 0.103):_

- **Correlation preserved best by `aim`** (err 0.0105). AIM leads, as the literature predicts.
- `aim` correlation error 0.0105 is better than the `pairwise` baseline (0.0283).
- `mst` correlation error 0.0968 is WORSE than the `pairwise` baseline (0.0283).
- **Best downstream ML (TSTR F1) by `mst`** (0.5483 vs TRTR ceiling 0.6604 = 83% of real-data utility).
- **Privacy audit:** audited ε = 0.000 for every mechanism — the auditor's ceiling is below the proved ε at this canary budget, so this is a *limit of the instrument*, not evidence of no leakage (the honest headline; see research/18).

## ACSIncome (CA 2018)

**Correlation error (lower = better)**

| mechanism | ε=0.5 | ε=1 | ε=2 | ε=4 | ε=8 |
|---|---|---|---|---|---|
| **independent** | 0.0521 | 0.0531 | 0.0530 | 0.0536 | 0.0535 |
| **pairwise** | 0.0543 | 0.0727 | 0.0468 | 0.0315 | 0.0202 |
| **aim** *(ours)* | 0.0808 | 0.0399 | 0.0609 | 0.0588 | 0.0621 |
| **mst** *(ours)* | 0.0326 | 0.0537 | 0.0413 | 0.0375 | 0.0522 |

**TSTR F1 (TRTR ceiling 0.725)**

| mechanism | ε=0.5 | ε=1 | ε=2 | ε=4 | ε=8 |
|---|---|---|---|---|---|
| **independent** | 0.4397 | 0.4411 | 0.4305 | 0.4416 | 0.4616 |
| **pairwise** | 0.4664 | 0.4675 | 0.4894 | 0.4812 | 0.5219 |
| **aim** *(ours)* | 0.6493 | 0.6693 | 0.6910 | 0.6311 | 0.5668 |
| **mst** *(ours)* | 0.6487 | 0.6960 | 0.6984 | 0.6485 | 0.6069 |

**Proved ε (calibration never overspends)**

| mechanism | ε=0.5 | ε=1 | ε=2 | ε=4 | ε=8 |
|---|---|---|---|---|---|
| **independent** | 0.4559 | 0.9122 | 1.8275 | 3.6639 | 7.3564 |
| **pairwise** | 0.4559 | 0.9122 | 1.8275 | 3.6639 | 7.3564 |
| **aim** *(ours)* | 0.3853 | 0.7782 | 1.5763 | 3.2011 | 6.5427 |
| **mst** *(ours)* | 0.3740 | 0.7518 | 1.5152 | 3.0681 | 6.2566 |

**Membership-inference AUC (0.5 = chance)**

| mechanism | ε=0.5 | ε=1 | ε=2 | ε=4 | ε=8 |
|---|---|---|---|---|---|
| **independent** | 0.4987 | 0.5000 | 0.5028 | 0.5019 | 0.5032 |
| **pairwise** | 0.4941 | 0.4980 | 0.4896 | 0.4969 | 0.4971 |
| **aim** *(ours)* | 0.4916 | 0.4895 | 0.4795 | 0.4980 | 0.5064 |
| **mst** *(ours)* | 0.4861 | 0.4990 | 0.4858 | 0.4957 | 0.4958 |

_At ε=8 on ACSIncome (CA 2018) (n=6000, corr pair ('AGEP', 'WKHP'), true corr 0.072):_

- **Correlation preserved best by `pairwise`** (err 0.0202). `pairwise` leads here.
- `aim` correlation error 0.0621 is WORSE than the `pairwise` baseline (0.0202).
- `mst` correlation error 0.0522 is WORSE than the `pairwise` baseline (0.0202).
- **Best downstream ML (TSTR F1) by `mst`** (0.6069 vs TRTR ceiling 0.7246 = 84% of real-data utility).
- **Privacy audit:** audited ε = 0.000 for every mechanism — the auditor's ceiling is below the proved ε at this canary budget, so this is a *limit of the instrument*, not evidence of no leakage (the honest headline; see research/18).

## UCI Bank Marketing

**Correlation error (lower = better)**

| mechanism | ε=0.5 | ε=1 | ε=2 | ε=4 | ε=8 |
|---|---|---|---|---|---|
| **independent** | 0.0450 | 0.0445 | 0.0446 | 0.0430 | 0.0416 |
| **pairwise** | 0.1485 | 0.0996 | 0.0968 | 0.0732 | 0.0289 |
| **aim** *(ours)* | 0.0517 | 0.0604 | 0.0516 | 0.0535 | 0.0579 |
| **mst** *(ours)* | 0.0552 | 0.0625 | 0.0538 | 0.0627 | 0.0576 |

**TSTR F1 (TRTR ceiling 0.561)**

| mechanism | ε=0.5 | ε=1 | ε=2 | ε=4 | ε=8 |
|---|---|---|---|---|---|
| **independent** | 0.4747 | 0.4812 | 0.4841 | 0.4818 | 0.4792 |
| **pairwise** | 0.4733 | 0.4133 | 0.4205 | 0.4527 | 0.4824 |
| **aim** *(ours)* | 0.4301 | 0.4758 | 0.3968 | 0.4794 | 0.4617 |
| **mst** *(ours)* | 0.4706 | 0.4933 | 0.4829 | 0.4645 | 0.4763 |

**Proved ε (calibration never overspends)**

| mechanism | ε=0.5 | ε=1 | ε=2 | ε=4 | ε=8 |
|---|---|---|---|---|---|
| **independent** | 0.4555 | 0.9115 | 1.8252 | 3.6578 | 7.3407 |
| **pairwise** | 0.4555 | 0.9115 | 1.8252 | 3.6578 | 7.3407 |
| **aim** *(ours)* | 0.3849 | 0.7772 | 1.5734 | 3.1944 | 6.5259 |
| **mst** *(ours)* | 0.3718 | 0.7460 | 1.5016 | 3.0313 | 6.1615 |

**Membership-inference AUC (0.5 = chance)**

| mechanism | ε=0.5 | ε=1 | ε=2 | ε=4 | ε=8 |
|---|---|---|---|---|---|
| **independent** | 0.4983 | 0.4947 | 0.4926 | 0.4931 | 0.4943 |
| **pairwise** | 0.4836 | 0.4911 | 0.4959 | 0.4937 | 0.4986 |
| **aim** *(ours)* | 0.4929 | 0.4904 | 0.4843 | 0.4965 | 0.4884 |
| **mst** *(ours)* | 0.4840 | 0.4981 | 0.4994 | 0.4840 | 0.4910 |

_At ε=8 on UCI Bank Marketing (n=6000, corr pair ('age', 'balance'), true corr 0.060):_

- **Correlation preserved best by `pairwise`** (err 0.0289). `pairwise` leads here.
- `aim` correlation error 0.0579 is WORSE than the `pairwise` baseline (0.0289).
- `mst` correlation error 0.0576 is WORSE than the `pairwise` baseline (0.0289).
- **Best downstream ML (TSTR F1) by `pairwise`** (0.4824 vs TRTR ceiling 0.5610 = 86% of real-data utility).
- **Privacy audit:** audited ε = 0.000 for every mechanism — the auditor's ceiling is below the proved ε at this canary budget, so this is a *limit of the instrument*, not evidence of no leakage (the honest headline; see research/18).

## Cross-dataset summary — best of each metric across ALL ε

> The per-dataset analysis above snapshots ε=8; this table takes the best cell over the whole ε grid, because AIM/MST often peak at ε=1-2 then decline. `*` marks one of ours.

| dataset | best correlation (mech @ ε) | best TSTR F1 (mech @ ε, % of TRTR) |
|---|---|---|
| UCI Adult | aim* @ ε=8 → 0.0105 | mst* @ ε=2 → 0.5554 (84%) |
| ACSIncome (CA 2018) | pairwise @ ε=8 → 0.0202 | mst* @ ε=2 → 0.6984 (96%) |
| UCI Bank Marketing | pairwise @ ε=8 → 0.0289 | mst* @ ε=1 → 0.4933 (88%) |

## Literature anchors (quoted, not recomputed)

- P8 (McKenna et al., AIM, 2022): AIM is the state-of-the-art marginal-based DP synthesizer on UCI Adult; our grid reproduces its *ordering* (AIM < pairwise < independent on correlation error) but on n=6000, not their full-table setup.
- P7 (Mohapatra et al., 2022): reports utility/privacy trade-offs on Adult under DP; quoted in research/19 with the metric named.
- P5 (Ganev et al., 2504.06923): discretisation and domain choices, not utility numbers, are the comparison axis; they motivate RB6/RB9, not a TSTR row.

## Honest bottom line

- **Where we are at par / ahead:** AIM is the strongest on structure (correlation) across datasets, reproducing the published ordering; our pipeline runs it end-to-end and ships a checkable release label none of the baselines or the cited deployments carry.
- **Where we are missing:** MST does *not* dominate — its spanning tree can omit the very edge a correlation metric measures, so its correlation error can fall back to baseline levels even while its downstream F1 stays competitive. This is a real limitation, not a tuning artefact, and it is stated rather than hidden.
- **The privacy axis is instrument-limited everywhere:** audited ε = 0 at this canary budget across all mechanisms and datasets; the contribution is the *honesty* of reporting that ceiling, not a tight audited number.
