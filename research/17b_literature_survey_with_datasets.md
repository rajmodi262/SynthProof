# Literature Survey — with datasets used (verified 2026-09-16)

> Every dataset below was checked against the paper's own PDF (in `research/litsurvey/papers/`),
> not taken on trust. Rows marked ✔verified were confirmed by reading the paper's dataset section
> today; the rest are from the fetched text and keyword scan (consistent, but re-read the exact
> quote before quoting a number). Two corrections were made vs the first automated pass: P5 does
> NOT use ACS ("Acs" was an author name), and P9's "adult" is a Census category, not UCI Adult.

## Main table (for the slide / paper — ≥5 papers, tabular)

| # | Paper · Venue · Year (arXiv) | Datasets used | Overlaps with ours? | What it contributes | What it did NOT do (our opening) |
|---|---|---|---|---|---|
| 1 | Stadler, Oprisanu & Troncoso · USENIX Sec 2022 (2011.07018) | **Adult**, Texas Hospital Discharge | **Adult ✅** | Shows synthetic data is not automatically anonymous; a linkage/attack framework | No standard, checkable *release artifact*; audits data, not the shipped document |
| 2 | Annamalai, Ganev & De Cristofaro · USENIX Sec 2024 (2405.10994) | **Adult**, SF Fire Dept Calls | **Adult ✅** | Tight, practical empirical DP **auditing of mechanisms** | Audits the mechanism; needs code+data — not a document-only check |
| 3 | Cebere et al. · PoPETs 2026 (2602.17454) | Synthetic PRNG tables + adversarial inputs (no real dataset) | none | Grey-box audit finds bugs in 12 DP libraries | No release-artifact audit; confirms libraries can't be blindly trusted |
| 4 | Ganev et al. · Synthetic Data workshop 2025 (2504.08254) | **Wine** | none | Data-domain extraction can break end-to-end DP | Audits one preprocessing step only |
| 5 | Ganev et al. · 2025 (2504.06923) | **Adult**, Gas, Wine + 1-D distributions | **Adult ✅** | Discretization before DP can leak / cost utility | Missing-data handling left unexamined |
| 6 | Ganev et al. · 2025 (2510.15083) | ecoli, abalone, yeast, mammography, car-eval, solar-flare, cardio, churn, higgs, creditcard | none | SMOTE oversampling leaks privacy | Focus on SMOTE; no membership audit of missing-data imputation |
| 7 | **Mohapatra, Zong, Kerschbaum & He · VLDB 2024 (2310.11548)** | **Adult** (32,561), **Bank**, BR2000, National | **Adult ✅ + Bank ✅** | DP synthetic-data generation **with missing data** | Treats missingness as privacy *amplification*, NOT leakage — no membership audit |
| 8 | **McKenna et al. — AIM · VLDB 2022 (2201.12677)** | **Adult**, salary, msnbc, fire, nltcs, titanic | **Adult ✅** | The AIM mechanism (the strong generator **we use**) | It's a generator, not a release audit — no signing, no boundary check |
| 9 | Abowd et al. — Census DAS TopDown · 2022 (2204.08986) | 2010/2020 Census Edited File (CEF/HDF), PPMF, 1940 microdata | none (Census, not ACS) | Real large-scale DP deployment; names invariants | Documents params in prose; no machine-checkable artefact-safety field |
| 10 | Dibia, Lu, Bhattacharjee, Near & Feng · PoPETs 2026 (2507.15997) | **none** (interview study, 12 DP experts) | none | Expert-elicited 9-category DP privacy **label** | No signing, no way to report a metric's limits ("privacy theater") |
| 11 | Song, Sarathy, Shoemate & Vadhan · CSCW 2024 (2410.09721) | **none** (interview study, 5 devs + 15 practitioners) | none | Practitioners do NOT verify DP; they trust implicitly | The premise — motivates an automatic verifier |

## What our project uses (for the overlap column)
- **UCI Adult** (target: income) · **UCI Bank Marketing** (target: y) · **ACSIncome CA-2018** (folktables).

## Key takeaways (state these to the guide)
- **UCI Adult is the field-standard benchmark** — used by 5 of the 11 (P1, P2, P5, P7, P8). Running on
  Adult places us directly alongside prior work → satisfies the guide's "same-dataset comparison."
- **P7 (Mohapatra) is the best comparison base**: same datasets (Adult + Bank) AND the same topic as
  our imputation audit — but they treat missing data as *amplification*, we *audit it for leakage*.
- **ACSIncome is unique to us** — no surveyed paper uses it; keep it as our own contribution, not a
  head-to-head.
- **Do NOT claim to beat AIM (P8)** — we *use* AIM. The comparison is "same benchmark + we add the
  release-boundary audit none of them did."

## Verification status
- ✔ Read from PDF today: P5 (Adult/Gas/Wine, ACS ruled out), P7 (Adult 32,561 + Bank), P8 (Adult,
  income>50K, workload error), P9 ("adult"=Census category, not UCI Adult).
- Reported from fetched text (re-read exact quote before citing a number): P1, P2, P3, P4, P6, P10, P11.
- Full evidence with page/section quotes: `research/17_base_paper_datasets.md` (Antigravity output).
