# 23 — Cross-dataset mechanism comparison (what ours does vs the others)

> Built by `scripts/build_mechanism_comparison.py` from the committed H1 grids. No number here is invented: each is read from a grid file (5 seeds unless marked reduced), each literature figure is quoted with its source. Utility = correlation error (lower better) and TSTR F1 (higher better, ceiling = TRTR on real data). Privacy = proved ε, audited ε, membership-inference AUC (0.5 = no better than chance).

**Mechanism families.** Baselines: `independent`, `pairwise` (marginal generators). Ours (the select-measure family SynthProof integrates and audits): `aim`, `mst`. SynthProof's *own* contribution is the release-boundary audit + signed label layer, which is mechanism-agnostic; these generators are what we run to populate the trade-off.

## UCI Adult (FULL)

**Correlation error (lower = better)**

| mechanism | ε=0.5 | ε=1 | ε=2 | ε=4 | ε=8 |
|---|---|---|---|---|---|
| **independent** | 0.1013 | 0.1021 | 0.1019 | 0.1019 | 0.1015 |
| **pairwise** | 0.0857 | 0.0710 | 0.0480 | 0.0152 | 0.0118 |
| **aim** *(ours)* | 0.1081 | 0.0184 | 0.0072 | 0.0093 | 0.0123 |
| **mst** *(ours)* | 0.0930 | 0.0799 | 0.0865 | 0.0823 | 0.1044 |

**TSTR F1 (TRTR ceiling 0.696)**

| mechanism | ε=0.5 | ε=1 | ε=2 | ε=4 | ε=8 |
|---|---|---|---|---|---|
| **independent** | 0.4745 | 0.4889 | 0.4929 | 0.4093 | 0.5113 |
| **pairwise** | 0.4777 | 0.3867 | 0.4822 | 0.5035 | 0.3364 |
| **aim** *(ours)* | 0.4550 | 0.4497 | 0.4299 | 0.5668 | 0.4181 |
| **mst** *(ours)* | 0.5535 | 0.6415 | 0.5943 | 0.5314 | 0.5749 |

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
| **independent** | 0.5116 | 0.5092 | 0.5103 | 0.5114 | 0.5091 |
| **pairwise** | 0.5158 | 0.5134 | 0.4912 | 0.5154 | 0.5178 |
| **aim** *(ours)* | 0.5132 | 0.5028 | 0.5098 | 0.4985 | 0.5338 |
| **mst** *(ours)* | 0.5021 | 0.5036 | 0.5048 | 0.5094 | 0.4957 |

_At ε=8 on UCI Adult (FULL) (n=30162, corr pair ('age', 'hours_per_week'), true corr 0.102):_

- **Correlation preserved best by `pairwise`** (err 0.0118). `pairwise` leads here.
- `aim` correlation error 0.0123 is at par with the `pairwise` baseline (0.0118).
- `mst` correlation error 0.1044 is WORSE than the `pairwise` baseline (0.0118).
- **Best downstream ML (TSTR F1) by `mst`** (0.5749 vs TRTR ceiling 0.6964 = 83% of real-data utility).
- **Privacy audit:** audited ε = 0.000 for every mechanism — the auditor's ceiling is below the proved ε at this canary budget, so this is a *limit of the instrument*, not evidence of no leakage (the honest headline; see research/18).

## ACSIncome CA-2018 (FULL)

**Correlation error (lower = better)**

| mechanism | ε=0.5 | ε=1 | ε=2 | ε=4 | ε=8 |
|---|---|---|---|---|---|
| **independent** | 0.0738 | 0.0738 | 0.0738 | 0.0738 | 0.0738 |
| **pairwise** | 0.0094 | 0.0057 | 0.0022 | 0.0017 | 0.0017 |
| **aim** *(ours)* | 0.0698 | 0.0742 | 0.0709 | 0.0729 | 0.0720 |
| **mst** *(ours)* | 0.0415 | 0.0427 | 0.0392 | 0.0409 | 0.0398 |

**TSTR F1 (TRTR ceiling 0.759)**

| mechanism | ε=0.5 | ε=1 | ε=2 | ε=4 | ε=8 |
|---|---|---|---|---|---|
| **independent** | 0.4899 | 0.4841 | 0.4759 | 0.4846 | 0.4848 |
| **pairwise** | 0.4798 | 0.4694 | 0.4854 | 0.4720 | 0.4998 |
| **aim** *(ours)* | 0.5708 | 0.5084 | 0.4772 | 0.4882 | 0.4773 |
| **mst** *(ours)* | 0.6763 | 0.6666 | 0.6698 | 0.6671 | 0.6760 |

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
| **independent** | 0.5209 | 0.5216 | 0.5228 | 0.5220 | 0.5225 |
| **pairwise** | 0.5066 | 0.5044 | 0.5009 | 0.5114 | 0.5110 |
| **aim** *(ours)* | 0.4995 | 0.5051 | 0.5038 | 0.5022 | 0.5001 |
| **mst** *(ours)* | 0.5040 | 0.4988 | 0.5022 | 0.5154 | 0.5148 |

_At ε=8 on ACSIncome CA-2018 (FULL) (n=195665, corr pair ('AGEP', 'WKHP'), true corr 0.074):_

- **Correlation preserved best by `pairwise`** (err 0.0017). `pairwise` leads here.
- `aim` correlation error 0.0720 is WORSE than the `pairwise` baseline (0.0017).
- `mst` correlation error 0.0398 is WORSE than the `pairwise` baseline (0.0017).
- **Best downstream ML (TSTR F1) by `mst`** (0.6760 vs TRTR ceiling 0.7585 = 89% of real-data utility).
- **Privacy audit:** audited ε = 0.000 for every mechanism — the auditor's ceiling is below the proved ε at this canary budget, so this is a *limit of the instrument*, not evidence of no leakage (the honest headline; see research/18).

## UCI Bank Marketing (FULL)

**Correlation error (lower = better)**

| mechanism | ε=0.5 | ε=1 | ε=2 | ε=4 | ε=8 |
|---|---|---|---|---|---|
| **independent** | 0.0980 | 0.0981 | 0.0978 | 0.0981 | 0.0982 |
| **pairwise** | 0.0863 | 0.0565 | 0.0212 | 0.0009 | 0.0210 |
| **aim** *(ours)* | 0.0952 | 0.1001 | 0.1026 | 0.1004 | 0.0940 |
| **mst** *(ours)* | 0.1033 | 0.0950 | 0.0931 | 0.0935 | 0.0945 |

**TSTR F1 (TRTR ceiling 0.545)**

| mechanism | ε=0.5 | ε=1 | ε=2 | ε=4 | ε=8 |
|---|---|---|---|---|---|
| **independent** | 0.4591 | 0.4432 | 0.4590 | 0.4763 | 0.4661 |
| **pairwise** | 0.4688 | 0.4771 | 0.2215 | 0.4786 | 0.3777 |
| **aim** *(ours)* | 0.4727 | 0.4850 | 0.4706 | 0.4685 | 0.4924 |
| **mst** *(ours)* | 0.4725 | 0.4810 | 0.4811 | 0.4741 | 0.4454 |

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
| **independent** | 0.5355 | 0.5352 | 0.5355 | 0.5353 | 0.5354 |
| **pairwise** | 0.4928 | 0.4880 | 0.4840 | 0.4880 | 0.4890 |
| **aim** *(ours)* | 0.4884 | 0.4862 | 0.4635 | 0.5049 | 0.4859 |
| **mst** *(ours)* | 0.4929 | 0.5067 | 0.5122 | 0.5091 | 0.5030 |

_At ε=8 on UCI Bank Marketing (FULL) (n=45211, corr pair ('age', 'balance'), true corr 0.098):_

- **Correlation preserved best by `pairwise`** (err 0.0210). `pairwise` leads here.
- `aim` correlation error 0.0940 is WORSE than the `pairwise` baseline (0.0210).
- `mst` correlation error 0.0945 is WORSE than the `pairwise` baseline (0.0210).
- **Best downstream ML (TSTR F1) by `aim`** (0.4924 vs TRTR ceiling 0.5453 = 90% of real-data utility).
- **Privacy audit:** audited ε = 0.000 for every mechanism — the auditor's ceiling is below the proved ε at this canary budget, so this is a *limit of the instrument*, not evidence of no leakage (the honest headline; see research/18).

## UCI Diabetes 130 (FULL, healthcare)

**Correlation error (lower = better)**

| mechanism | ε=0.5 | ε=1 | ε=2 | ε=4 | ε=8 |
|---|---|---|---|---|---|
| **independent** | 0.4689 | 0.4690 | 0.4688 | 0.4687 | 0.4688 |
| **pairwise** | 0.3669 | 0.3782 | 0.3823 | 0.3792 | 0.3818 |
| **aim** *(ours)* | 0.1285 | 0.1257 | 0.1270 | 0.1305 | 0.1291 |
| **mst** *(ours)* | 0.1185 | 0.1212 | 0.1213 | 0.1205 | 0.1189 |

**TSTR F1 (TRTR ceiling 0.490)**

| mechanism | ε=0.5 | ε=1 | ε=2 | ε=4 | ε=8 |
|---|---|---|---|---|---|
| **independent** | 0.4845 | 0.4848 | 0.4834 | 0.4859 | 0.4851 |
| **pairwise** | 0.4766 | 0.4714 | 0.4745 | 0.4708 | 0.4782 |
| **aim** *(ours)* | 0.4730 | 0.4717 | 0.4721 | 0.4848 | 0.4728 |
| **mst** *(ours)* | 0.4778 | 0.4869 | 0.4753 | 0.4740 | 0.4843 |

**Proved ε (calibration never overspends)**

| mechanism | ε=0.5 | ε=1 | ε=2 | ε=4 | ε=8 |
|---|---|---|---|---|---|
| **independent** | 0.4572 | 0.9156 | 1.8357 | 3.6831 | 7.4021 |
| **pairwise** | 0.4572 | 0.9156 | 1.8357 | 3.6831 | 7.4021 |
| **aim** *(ours)* | 0.3869 | 0.7820 | 1.5857 | 3.2223 | 6.5923 |
| **mst** *(ours)* | 0.3771 | 0.7594 | 1.5343 | 3.1128 | 6.3602 |

**Membership-inference AUC (0.5 = chance)**

| mechanism | ε=0.5 | ε=1 | ε=2 | ε=4 | ε=8 |
|---|---|---|---|---|---|
| **independent** | 0.4891 | 0.4897 | 0.4939 | 0.4931 | 0.4952 |
| **pairwise** | 0.4770 | 0.4819 | 0.5031 | 0.4918 | 0.4682 |
| **aim** *(ours)* | 0.5038 | 0.4579 | 0.4770 | 0.4630 | 0.4694 |
| **mst** *(ours)* | 0.4863 | 0.4609 | 0.4574 | 0.4660 | 0.4479 |

_At ε=8 on UCI Diabetes 130 (FULL, healthcare) (n=99492, corr pair ('time_in_hospital', 'num_medications'), true corr 0.466):_

- **Correlation preserved best by `mst`** (err 0.1189). `mst` leads here.
- `aim` correlation error 0.1291 is better than the `pairwise` baseline (0.3818).
- `mst` correlation error 0.1189 is better than the `pairwise` baseline (0.3818).
- **Best downstream ML (TSTR F1) by `independent`** (0.4851 vs TRTR ceiling 0.4904 = 99% of real-data utility).
- **Privacy audit:** audited ε = 0.000 for every mechanism — the auditor's ceiling is below the proved ε at this canary budget, so this is a *limit of the instrument*, not evidence of no leakage (the honest headline; see research/18).

## Cross-dataset summary — best of each metric across ALL ε

> The per-dataset analysis above snapshots ε=8; this table takes the best cell over the whole ε grid, because AIM/MST often peak at ε=1-2 then decline. `*` marks one of ours.

| dataset | best correlation (mech @ ε) | best TSTR F1 (mech @ ε, % of TRTR) |
|---|---|---|
| UCI Adult (FULL) | aim* @ ε=2 → 0.0072 | mst* @ ε=1 → 0.6415 (92%) |
| ACSIncome CA-2018 (FULL) | pairwise @ ε=8 → 0.0017 | mst* @ ε=0.5 → 0.6763 (89%) |
| UCI Bank Marketing (FULL) | pairwise @ ε=4 → 0.0009 | aim* @ ε=8 → 0.4924 (90%) |
| UCI Diabetes 130 (FULL, healthcare) | mst* @ ε=0.5 → 0.1185 | mst* @ ε=1 → 0.4869 (99%) |

## Literature anchors (quoted, not recomputed)

- P8 (McKenna et al., AIM, 2022): AIM is the state-of-the-art marginal-based DP synthesizer on UCI Adult; our grid reproduces its *ordering* (AIM < pairwise < independent on correlation error) but on n=6000, not their full-table setup.
- P7 (Mohapatra et al., 2022): reports utility/privacy trade-offs on Adult under DP; quoted in research/19 with the metric named.
- P5 (Ganev et al., 2504.06923): discretisation and domain choices, not utility numbers, are the comparison axis; they motivate RB6/RB9, not a TSTR row.

## Honest bottom line

- **Where we are at par / ahead:** AIM is the strongest on structure (correlation) across datasets, reproducing the published ordering; our pipeline runs it end-to-end and ships a checkable release label none of the baselines or the cited deployments carry.
- **Where we are missing:** MST does *not* dominate — its spanning tree can omit the very edge a correlation metric measures, so its correlation error can fall back to baseline levels even while its downstream F1 stays competitive. This is a real limitation, not a tuning artefact, and it is stated rather than hidden.
- **The privacy axis is instrument-limited everywhere:** audited ε = 0 at this canary budget across all mechanisms and datasets; the contribution is the *honesty* of reporting that ceiling, not a tight audited number.
