# Base Paper Experimental Datasets Verification (P1–P11)

This report provides verifiable evidence of the exact experimental datasets used across 11 key reference papers for the **SynthProof** capstone project (differentially private synthetic data and release-boundary auditing). Every paper was fetched and verified from its primary publication or arXiv source text.

---

## Part 1 — Master table

| Paper | Fetched? (Y/N) | Datasets used (exact names) | Overlaps with SynthProof? (Adult / Bank / ACS / none) | Evidence location |
|---|:---:|---|:---:|---|
| **P1** Stadler, Oprisanu & Troncoso (USENIX Security 2022) | **Y** | Adult, Texas Hospital Discharge | **Adult (SAME)** | Section 8.3 "Datasets", Page 19 |
| **P2** Annamalai, Ganev & De Cristofaro (USENIX Security 2024) | **Y** | Adult, San Francisco Fire Dept Calls for Service (Fire), synthetic worst-case tables | **Adult (SAME)** | Section 4.1 "Datasets", Page 6 |
| **P3** Cebere et al. (arXiv:2602.17454, 2026) | **Y** | Programmatic synthetic tables ($n=200$, 2 cols) via seeded PRNG, adversarial edge inputs ($-\infty$, NaN) | **none** | Section 4.2 "Datasets", Page 7 |
| **P4** Ganev, Annamalai, Mahiou & De Cristofaro (ICLR SynthData 2025) | **Y** | Wine dataset | **none** | Section 2 "MIA Instantiation", Page 2 & Appendix A, Page 6 |
| **P5** Ganev et al. (arXiv:2504.06923, 2025) | **Y** | Adult, Gas, Wine, 5 controlled 1D distributions | **Adult (SAME)** | Section 3.4 "Datasets" & Table 3, Page 5 |
| **P6** Ganev et al. (arXiv:2510.15083, 2025) | **Y** | 8 imbalanced datasets (ecoli, abalone, car eval 34, solar flare m0, car eval 4, yeast me2, mammography, abalone 19), plus cardio, churn, higgs, creditcard | **none** | Section 5 "Datasets" & Table 2, Page 7 |
| **P7** Mohapatra, Zong, Kerschbaum & He (VLDB 2024) | **Y** | Adult, Bank, BR2000, National | **Adult (SAME)** & **Bank (SAME)** | Section 6.1 "Experimental Setup - Datasets" & Table 1, Page 11 |
| **P8** McKenna et al. (VLDB 2022) | **Y** | adult, salary, msnbc, fire, nltcs, titanic | **Adult (SAME)** | Section 6.1 "Datasets" & Table 3, Page 9 |
| **P9** Abowd et al. (2022) | **Y** | 2010 Census Edited File / Hundred-percent Detail File (CEF/HDF) Demonstration Products (PPMF), 2020 Census Edited File (CEF), 1940 Census microdata | **none** (RELATIVE of Census domain) | Section 8.1, Pages 29–30; Section 10, Page 47 |
| **P10** Dibia, Lu, Bhattacharjee, Near & Feng (PoPETs 2026) | **Y** | **NO EXPERIMENTAL DATASETS** (paper type: qualitative interview study / standards proposal) | **none** | Section 3 "Methodology", Pages 2–3 |
| **P11** Song, Sarathy, Shoemate & Vadhan (CSCW 2024) | **Y** | **NO EXPERIMENTAL DATASETS** (paper type: qualitative interview & usability user study) | **none** | Section 1, Page 2; Section 4.1, Pages 19–20 |

---

## Part 2 — Per-paper detail

### P1. Stadler, Oprisanu & Troncoso — "Synthetic data: anonymisation groundhog day" — USENIX Security 2022
- **Citation & Venue**: Theresa Stadler, Bristena Oprisanu, Carmela Troncoso. *"Synthetic Data -- Anonymisation Groundhog Day"*. 31st USENIX Security Symposium (USENIX Security 22), Boston, MA, August 2022, pp. 1451–1468.
- **arXiv/DOI**: arXiv:2011.07018v6 [cs.CR]; USENIX: `https://www.usenix.org/conference/usenixsecurity22/presentation/stadler`
- **URL fetched**: `https://arxiv.org/abs/2011.07018` / PDF: `https://arxiv.org/pdf/2011.07018.pdf`
- **Paper type**: Experimental (empirical evaluation of linkage and attribute inference privacy gain across generative models).
- **Datasets (each)**:
  1. **Adult**: UCI Machine Learning Repository (1994 US Census database) — 45,222 records, 15 attributes (6 continuous, 9 categorical).
  2. **Texas**: Texas Hospital Discharge dataset (Texas Department of State Health Services) — 50,000 records uniformly sampled from 2013 inpatient data, 18 attributes (11 categorical, 7 continuous).
- **EXACT QUOTE naming the dataset(s)**:
  > *"8.3 Datasets. We include two tabular datasets, commonly used in the machine learning (ML) literature, in our experimental evaluation. Tabular datasets are the most relevant data type in the synthetic data publishing case. One datasets contains financial data the other one health data: Adult [34]. The Adult dataset contains information from 45,222 individuals extracted from the 1994 US Census database. Each entry consists of 15 attributes among which 6 are continuous attributes and 9 are categorical attributes. Texas [60]. The Texas Hospital Discharge dataset is a large public use data file provided by the Texas Department of State Health Services. The dataset we use consists of 50,000 records uniformly sampled from a pre-processed data file that contains patient records from the year 2013. We retain 18 data attributes of which 11 are categorical and 7 continuous."*  
  *(Section 8.3 "Datasets", Appendix, Page 19)*
- **Reported metrics and numbers on Adult**:
  - Metric: **Per-record Privacy Gain ($PG$)** under linkage attacks with three attack feature sets ($F_{Naive}$, $F_{Hist}$, $F_{Corr}$) across IndHist, BayNet, PrivBayes ($\epsilon \in \{0.01, 0.1, 1, 10\}$), CTGAN, PATEGAN.
  - Verbatim Quotes & Numbers:
    - Section 5.1 (Page 7): *"Attacks on the Adult dataset are most successful under the correlations feature set $F_{Corr}$: Here, BayNet provides target $t_5$ with a minimum gain of $PG = 0.64$ ($t_5$) under $F_{Naive}$. The minimum gain provided by the same model drops below $PG < 0.32$ if the attacker uses $F_{Corr}$ as input to the attack and leaves a target record largely unprotected ($PG = 0.08$ for $t_1$)."*
    - Section 5.1 (Page 6): *"Each dataset, raw and synthetic, contained $n = m = 1000$ records. The adversary was trained on a reference dataset of $l = 10,000$ records."*
    - Section 5.1 (Page 8): *"Figure 3: Per-record privacy gain for five outlier targets records from the Texas (top row) and Adult (bottom row) datasets under an attack using the $F_{Hist}$ feature set... Two out of the five outliers in the Texas dataset achieve close to no gain ($t_1$ and $t_4$ with $PG < 0.1$). This low gain violates the theoretical guarantee of differential privacy which implies $PG \ge 0.89$ for $\epsilon = 0.1$."*
- **Overlap verdict**: **SAME as our UCI Adult** (1994 US Census); **NO Bank**; **NO ACS**.
- **Anything they did NOT do that SynthProof does**: Evaluates empirical privacy gain through shadow models (black-box MIA/linkage) without cryptographic boundary verification, without discretization-leakage auditing at the release boundary, and without verifiable privacy manifests.

---

### P2. Annamalai, Ganev & De Cristofaro — "What you want is not what you get: ... DP auditing" — USENIX Security 2024
- **Citation & Venue**: Sasi Kumar Annamalai, Georgi Ganev, Emiliano De Cristofaro. *"“What do you want from theory alone?” Experimenting with Tight Auditing of Differentially Private Synthetic Data Generation"*. 33rd USENIX Security Symposium (USENIX Security 24), Philadelphia, PA, August 2024.
- **arXiv/DOI**: arXiv:2405.10994v1 [cs.CR]; USENIX: `https://www.usenix.org/conference/usenixsecurity24/presentation/annamalai`
- **URL fetched**: `https://arxiv.org/abs/2405.10994` / PDF: `https://arxiv.org/pdf/2405.10994.pdf`
- **Paper type**: Experimental (empirical auditing of DP synthetic data generators via black-box and active white-box MIAs and worst-case datasets).
- **Datasets (each)**:
  1. **Adult [34]**: UCI Machine Learning Repository — trimmed and binned to 11 categorical attributes (age, workclass, education, marital-status, occupation, relationship, race, gender, hours-per-week, native-country, income); average-case sample size $|D| = 1000$.
  2. **San Francisco Fire Dept Calls for Service (Fire) [15]**: 2016 response records (from 2018 NIST Competition) — trimmed from 32 to 10 categorical attributes.
  3. **Worst-case synthetic datasets**: Stylized small, narrow, and duplicated target tables.
- **EXACT QUOTE naming the dataset(s)**:
  > *"4.1 Datasets. We experiment with two tabular datasets used to train synthetic data generation (SDG) algorithms, which have been used extensively in prior work on synthetic data [8,11,37,43] as well as in the 2018 NIST Synthetic Data Challenge [54]: 1. Adult [34], used to predict whether income exceeds $50K from Census data. To make sure the dataset can be used as input to all DP-SDGs, we trim and bin the dataset to 11 categorical attributes (age, workclass, education, marital-status, occupation, relationship, race, gender, hours-per-week, native-country, and income). 2. San Francisco Fire Dept Calls for Service (Fire) [15], which records fire units’ responses to calls made to them in 2016. It was used in the 2018 NIST Synthetic Data competition. Following prior work [6], we trim the dataset from 32 to 10 categorical attributes (ALS Unit, Call Type Group, Priority, Call Type, Zipcode of Incident, Number of Alarms, Battalion, Call Final Disposition, City and Station Area) to reduce the computational cost of generating thousands of synthetic datasets."*  
  *(Section 4.1 "Datasets", Page 6)*
- **Reported metrics and numbers on Adult**:
  - Metric: **Empirical privacy bound ($\epsilon_{emp}$)** estimated at 95% Clopper-Pearson confidence over 10,000 models with 5-fold cross-validation, across PrivBayes (DS), MST (NIST), DPWGAN (NIST), PrivBayes (Hazy), MST (Smartnoise), and DPWGAN (Synthcity) at theoretical $\epsilon \in \{1.0, 4.0\}$.
  - Verbatim Quotes & Numbers:
    - Section 5.1.1 (Page 8): *"In Figure 3, we report the empirical $\epsilon_{emp}$ guarantees for the six DP-SDG implementations, using Adult and Fire datasets, at two $\epsilon$ values corresponding to high and moderate privacy – respectively, $\epsilon = 1.0$ and $\epsilon = 4.0$."*
    - Section 5.1.1 (Page 8–9): *"DP Violations. We observe that the empirical privacy leakage exceeds the theoretical guarantee $\epsilon$ for some implementations... For PrivBayes (Hazy) trained on the Adult dataset at theoretical $\epsilon = 1.0$, $\epsilon_{emp}$ reaches $\approx 30$ with the Querybased attack!"*
    - Section 5.1.1 (Page 9): *"For the implementations tested in the NIST competition, i.e., MST (NIST) and DPWGAN (NIST), $\epsilon_{emp} \approx 0$ under average-case datasets."*
    - Section 5.3 (Page 14): *"For example, running the white-box attack requires generating 10,000 synthetic datasets, which takes around 4.5 days for the (down-sized) ADULT dataset with PrivBayes (Hazy) and more than 6 days with MST (Smartnoise)."*
- **Overlap verdict**: **SAME as our UCI Adult** (trimmed to 11 categorical columns); **NO Bank**; **NO ACS**.
- **Anything they did NOT do that SynthProof does**: Audits DP algorithms by training thousands of shadow models (taking days of heavy compute) to find implementation bugs; SynthProof audits at the release boundary in seconds using deterministic parameter bounds, cryptographic proofs, and release-receipt verification.

---

### P3. Cebere et al. — "Privacy in theory, bugs in practice: grey-box auditing of DP libraries" — arXiv:2602.17454
- **Citation & Venue**: Tudor Cebere, David Erb, Damien Desfontaines, Aurélien Bellet, Jack Fitzsimons. *"Privacy in Theory, Bugs in Practice: Grey-Box Auditing of Differential Privacy Libraries"*. arXiv:2602.17454v1 [cs.CR], February 2026.
- **arXiv/DOI**: arXiv:2602.17454v1 [cs.CR]
- **URL fetched**: `https://arxiv.org/abs/2602.17454` / PDF: `https://arxiv.org/pdf/2602.17454.pdf`
- **Paper type**: Experimental / Software testing framework (introduces Re:cord-play grey-box execution-trace auditing of DP library internals).
- **Datasets (each)**:
  - **Programmatically generated synthetic test tables**: Generated via seeded PRNG ($n = 200$, 2 categorical columns) and adversarial inputs ($-\infty$, NaN, float overflow). **NO real-world benchmark datasets** were used.
- **EXACT QUOTE naming the dataset(s)**:
  > *"4.2 Datasets. In this section, we describe the data used to run our auditing. We want to stress that the goal is to keep the execution time and memory usage as small as possible. Synthetic Data. To create a controlled and reproducible test environment, our synthetic data procedure generates an initial dataset $D$ as a low-dimensional tabular dataset. Using a seeded pseudo-random number generator, it creates a table with a fixed number of records (e.g., $n = 200$) and a small number of categorical attributes (e.g., 2 columns). The values for these attributes are drawn uniformly at random from small, predefined integer ranges."*  
  *(Section 4.2 "Datasets", Page 7)*
  > *"As discussed in Section 5.2, dataset generation is outside the scope of this work; our framework is designed to integrate seamlessly with recent advances in this area (e.g., [14])."*  
  *(Section 4.2 "Datasets", Page 8)*
- **Reported metrics and numbers**:
  - Metric: Software bug discovery across 12 open-source DP libraries (Table 1: Diffprivlib, OpenDP, Tumult Analytics, SmartNoise Core, SmartNoise SQL, Google DP, Chorus, PipelineDP, etc.), identifying sensitivity miscalibration, data-dependent control flow, and unhandled NaN/$-\infty$ inputs.
  - Numbers: Evaluates 12 libraries, auditing isolated primitives with $N = 10^5$ samples, taking minutes rather than days.
- **Overlap verdict**: **NO overlap** (purely mock synthetic test tables; no Adult, no Bank, no ACS).
- **Anything they did NOT do that SynthProof does**: Instruments internal Python/Rust AST/hooks to check internal mechanism sensitivity during code execution; SynthProof audits the published synthetic data artifacts and metadata externally at the release boundary without requiring library instrumentation.

---

### P4. Ganev, Annamalai, Mahiou & De Cristofaro — "Understanding the impact of data domain extraction ..." — arXiv:2504.08254
- **Citation & Venue**: Georgi Ganev, Meenatchi Sundaram Muthu Selva Annamalai, Sofiane Mahiou, Emiliano De Cristofaro. *"Understanding the Impact of Data Domain Extraction on Synthetic Data Privacy"*. Accepted to the Synthetic Data $\times$ Data Access Problem workshop (SynthData), ICLR 2025.
- **arXiv/DOI**: arXiv:2504.08254v2 [cs.CR]
- **URL fetched**: `https://arxiv.org/abs/2504.08254` / PDF: `https://arxiv.org/pdf/2504.08254.pdf`
- **Paper type**: Experimental (evaluates privacy leakage caused by data-dependent domain extraction in DP generative models).
- **Datasets (each)**:
  - **Wine Dataset (Dua & Graff, 2017)**: UCI Machine Learning Repository — 4,898 wine samples, 11 continuous physicochemical attributes, target: wine quality.
- **EXACT QUOTE naming the dataset(s)**:
  > *"To evaluate the privacy of the resulting synthetic data, we use GroundHog (Stadler et al., 2022), one of the most widely used MIAs for synthetic tabular data, on the Wine dataset (Dua & Graff, 2017)."*  
  *(Section 2 "MIA Instantiation", Page 2)*
  > *"Wine Dataset (Dua & Graff, 2017). As mentioned, our experiments are run on the Wine dataset, which consists of 4,898 wine samples, each described by 11 continuous physicochemical attributes, with the goal of modeling wine quality."*  
  *(Appendix A, Page 6)*
- **Reported metrics and numbers**:
  - Metric: Membership Inference Attack success measured by **Area Under the ROC Curve (AUC)** using GroundHog $F_{naive}$ features across 200 shadow models on PrivBayes and MST under four discretizers (Uniform, Quantile, K-means, PrivTree).
  - Verbatim Quotes & Numbers:
    - Section 3 (Page 3): *"When the domain is extracted directly from the data (orange bars), the AUC is consistently high across all setups: 1.0 for PrivBayes and around 0.8 for MST."*
    - Section 3 (Page 3): *"In contrast, when a representative domain is assumed (blue bars), the AUC drops to around 0.5 (random guessing) for both PrivBayes and MST, across all discretization methods."*
- **Overlap verdict**: **NO overlap** (uses Wine; does not use Adult, Bank, or ACS).
- **Anything they did NOT do that SynthProof does**: Investigates domain-extraction leakage using shadow-model GroundHog attacks on continuous attributes; SynthProof provides end-to-end release boundary enforcement, cryptographically signed release manifests, and multi-metric boundary verification.

---

### P5. Ganev et al. — "The importance of being discrete: privacy of discretization ..." — arXiv:2504.06923
- **Citation & Venue**: Georgi Ganev, Meenatchi Sundaram Muthu Selva Annamalai, Sofiane Mahiou, Emiliano De Cristofaro. *"The Importance of Being Discrete: Measuring the Impact of Discretization in End-to-End Differentially Private Synthetic Data"*. arXiv:2504.06923v4 [cs.CR], April 2025.
- **arXiv/DOI**: arXiv:2504.06923v4 [cs.CR]
- **URL fetched**: `https://arxiv.org/abs/2504.06923` / PDF: `https://arxiv.org/pdf/2504.06923.pdf`
- **Paper type**: Experimental (large-scale measurement study of utility and privacy impacts of DP discretization in end-to-end DP tabular synthesis).
- **Datasets (each)**:
  1. **Adult**: UCI Machine Learning Repository — 48,842 records, 6 numerical columns, 8 categorical columns.
  2. **Gas (Gas Sensor Array Drift)**: UCI ML Repository — 36,733 records, 12 numerical columns, 0 categorical columns.
  3. **Wine (Wine Quality)**: UCI ML Repository — 4,898 records, 11 numerical columns, 0 categorical columns.
  4. **Controlled 1D Distributions**: Uniform, Monotone, Normal, Beta, Mixture, Imbalanced (Table 2, Page 5).
- **EXACT QUOTE naming the dataset(s)**:
  > *"Real Datasets. We use common real datasets, i.e., Adult, Gas, and Wine from UCI’s ML Repository [13], all of them having associated binary classification tasks – see Table 3."*  
  *(Section 3.4 "Datasets", Page 5)*
  > *"Table 3: Overview of the datasets used in our evaluation.*  
  > *Dataset: Adult | #Records: 48,842 | #Numerical Columns: 6 | #Categorical Columns: 8*  
  > *Dataset: Gas | #Records: 36,733 | #Numerical Columns: 12 | #Categorical Columns: 0*  
  > *Dataset: Wine | #Records: 4,898 | #Numerical Columns: 11 | #Categorical Columns: 0"*  
  *(Table 3, Page 5)*
- **Reported metrics and numbers on Adult / Real Datasets**:
  - Metric: Composite utility score composed of six metrics: Record Similarity (RS), Maximum Percentile Distance (MPD), Discriminator Similarity (DS), Query Similarity (QS), Correlation Similarity (CS), Predictive Utility (PU: $F1_{synth} / F1_{real}$). Evaluated in Utility Setting 3 (US3) across four DP discretizers (Uniform, Quantile, K-means, PrivTree) and six DP generative models (PrivBayes, MST, AIM, GEM, RAP, dp-synthpop).
  - Verbatim Quotes & Numbers:
    - Section 3.5 (Page 5): *"Modeling Real Datasets (US3). We also assess the utility of DP generative models combined with DP discretization on real datasets (used in Section 5.2, 5.3, and 5.4) to simulate realistic end-to-end DP generative model deployments and test whether our findings in US1/US2 generalize. The datasets are preprocessed using the four discretizers and used with six DP generative models."*
    - Section 5.3 (Page 9): *"Computational Performance (US3)... maintain an acceptable runtime of around 1-7 mins across generative models and three datasets (US3)."*
- **Overlap verdict**: **SAME as our UCI Adult** (full 48,842-record UCI Adult); **NO Bank**; **NO ACS**.
- **Anything they did NOT do that SynthProof does**: Analyzes discretization algorithms inside generative models; does not build a consumer-verifiable release boundary auditor, cryptographic tamper-evident receipts, or multi-dimensional leakage bounds.

---

### P6. Ganev et al. — "SMOTE and mirrors: exposing privacy leakage from synthetic minority oversampling" — arXiv:2510.15083
- **Citation & Venue**: Georgi Ganev, Reza Nazari, Rees Davison, Amir Dizche, Xinmin Wu, Ralph Abbey, Jorge Silva, Emiliano De Cristofaro. *"SMOTE and Mirrors: Exposing Privacy Leakage from Synthetic Minority Oversampling"*. arXiv:2510.15083v3 [cs.CR], October 2025.
- **arXiv/DOI**: arXiv:2510.15083v3 [cs.CR]
- **URL fetched**: `https://arxiv.org/abs/2510.15083` / PDF: `https://arxiv.org/pdf/2510.15083.pdf`
- **Paper type**: Experimental / Attack study (presents DistinSMOTE and ReconSMOTE to reconstruct real minority records from SMOTE synthetic datasets).
- **Datasets (each)**:
  - 8 standard imbalanced benchmark datasets from `imblearn` (originally from UCI ML repository):
    1. **ecoli** (target: imU, imbalance ratio $r=8.6$, $n=336$, $d=7$)
    2. **abalone** (target: 7, $r=9.7$, $n=4,177$, $d=10$)
    3. **car eval 34** (target: vgood, $r=12$, $n=1,728$, $d=21$)
    4. **solar flare m0** (target: M-0, $r=19$, $n=1,389$, $d=32$)
    5. **car eval 4** (target: vgood, $r=26$, $n=1,728$, $d=21$)
    6. **yeast me2** (target: ME2, $r=28$, $n=1,484$, $d=8$)
    7. **mammography** (target: minority, $r=42$, $n=11,183$, $d=6$)
    8. **abalone 19** (target: 19, $r=130$, $n=4,177$, $d=10$)
  - Additional evaluation datasets (Section 6 & Appendix C): **cardio** ($n=2,126$), **churn** ($n=5,000$), **higgs** ($n=98,050$), **creditcard** ($n=96,690$).
- **EXACT QUOTE naming the dataset(s)**:
  > *"Datasets. We conduct our main experiments on eight standard imbalanced datasets, each with a binary classification task, obtained from the imblearn library [40] (originally from the UCI ML Repository) and used in prior work [13, 55] These datasets vary significantly in size (336 to 11,183 records), dimensionality (6 to 32 features), imbalance ratios (8.6 to 130), and prediction task (target), as shown in Table 2."*  
  *(Section 5 "Datasets", Page 7)*
- **Reported metrics and numbers**:
  - Metric: DistinSMOTE Precision and Recall, ReconSMOTE Precision and Recall, Naive Distinguish precision/recall, and MIA AUC.
  - Verbatim Quotes & Numbers (Table 3, Page 7):
    - Table 3: *"The attack achieves perfect precision on all datasets... DistinSMOTE achieves Precision = 1.00 ± 0.00 and Recall = 1.00 ± 0.00 across all datasets."*
    - Section 5.1 (Page 8): *"Looking at Table 3 (fourth column), the average AUC is 0.68, with half of the datasets exceeding 0.7, which indicates substantial privacy leakage."*
- **Overlap verdict**: **NO overlap** (does not use Adult, Bank, or ACS).
- **Anything they did NOT do that SynthProof does**: Attacks heuristic data augmentation (SMOTE) with exact geometric reconstruction; does not study DP mechanisms or release-boundary verification.

---

### P7. Mohapatra, Zong, Kerschbaum & He — "Differentially private data generation with missing data" — VLDB 2024
- **Citation & Venue**: Shubhankar Mohapatra, Jianqiao Zong, Florian Kerschbaum, Xi He. *"Differentially Private Data Generation with Missing Data"*. Proceedings of the VLDB Endowment (PVLDB 2024), Vol. 17 / arXiv:2310.11548v3 [cs.CR], October 2023.
- **arXiv/DOI**: arXiv:2310.11548v3 [cs.CR]
- **URL fetched**: `https://arxiv.org/abs/2310.11548` / PDF: `https://arxiv.org/pdf/2310.11548.pdf`
- **Paper type**: Experimental (design and empirical validation of DP synthetic data mechanisms handling missing values, evaluating utility and privacy amplification).
- **Datasets (each)**:
  1. **Adult [25]**: UCI Machine Learning Repository (1994 US Census) — 32,561 records, 5 numerical attributes, 10 categorical attributes.
  2. **Bank [64]**: UCI Machine Learning Repository (Moro et al., 2014) — 45,211 rows about direct marketing campaigns of a Portuguese banking institution, 3 numerical attributes, 14 categorical attributes.
  3. **BR2000 [97]**: 38,000 census records collected from Brazil in year 2000, 3 numerical attributes, 11 categorical attributes.
  4. **National [84]**: NIST Diverse Community Excerpts — 15,012 individuals US census data, 6 numerical attributes, 14 categorical attributes.
- **EXACT QUOTE naming the dataset(s)**:
  > *"Datasets. We run our experiments on four tabular datasets as described in Table 1: (i) Adult dataset [25], which contains information about 32561 individuals from the 1994 US Census (ii) Bank dataset [64], which has 45211 rows about direct marketing campaigns of a Portuguese banking institution (iii) BR2000 [97], which consists of 38,000 census records collected from Brazil in the year 2000, (iv) National dataset [84] from NIST Diverse Community Excerpts which contains information about 15012 individuals US census data. Each dataset has a combination of numerical and categorical columns which are pre-processed according to the synthetic data generation algorithm as discussed in their respective research paper – numerical attributes are discretized into 10 uniform bins or scaled between 0 to 1 and the categorical attributes are encoded using one-hot or ordinal encoding."*  
  *(Section 6.1 "Experimental Setup - Datasets", Page 11)*
  > *"Table 1: Dataset Characteristics*  
  > *Dataset: Adult | Cardinality: 32561 | #Numerical Attr: 5 | #Categorical Attr: 10*  
  > *Dataset: Bank | Cardinality: 45211 | #Numerical Attr: 3 | #Categorical Attr: 14*  
  > *Dataset: BR2000 | Cardinality: 38000 | #Numerical Attr: 3 | #Categorical Attr: 11*  
  > *Dataset: National | Cardinality: 15012 | #Numerical Attr: 6 | #Categorical Attr: 14"*  
  *(Table 1, Page 11)*
- **Reported metrics and numbers on Adult and Bank**:
  - Metrics: 1-way marginal Total Variation Distance (1-way TVD ↓), 2-way marginal Total Variation Distance (2-way TVD ↓), downstream classification utility (F1-score ↑), and privacy amplification budget ($\bar{\epsilon}$), evaluated across PrivBayes, AIM, DPCTGAN, DPautoGAN, Kamino under MCAR, MAR, and MNAR missingness (10% to 50%) at $\epsilon \in [0.5, \infty]$.
  - Verbatim Quotes & Numbers:
    - Table 2 (Page 16):
      > *"Table 2: Amplified privacy for ground truth data.*  
      > *Dataset: Adult | MCAR 0.1: 0.88 | MCAR 0.2: 0.77 | MCAR 0.3: 0.65 | MCAR 0.4: 0.47 | MCAR 0.5: 0.44*  
      > *Dataset: BR2000 | MCAR 0.1: 0.83 | MCAR 0.2: 0.68 | MCAR 0.3: 0.55 | MCAR 0.4: 0.41 | MCAR 0.5: 0.31"*
    - Section 6.2.4 (Page 16): *"Our results show that the amplified privacy cost decreases almost linearly from 0.88x to 0.44x for Adult and 0.83x to 0.31x for the BR2000 dataset."*
    - Section 6.2.1 (Page 13): *"For example, the ground truth Adult dataset when imputed with mode imputation achieves a 1-way TV-distance of 0.05... When 10% MCAR data is introduced, PrivBayes sees 1-way and 2-way metrics experiencing 5-19% impact, and F1-score dropping by 3-11%."*
    - Section 6.2.2 (Page 14): *"Across all datasets, the adaptive recourse method achieves F1-scores of up to 24% higher than the baseline."*
- **Overlap verdict**: **SAME as our UCI Adult** AND **SAME as our UCI Bank Marketing**; **NO ACS**.
- **Anything they did NOT do that SynthProof does**: Solves missing value imputation internal to DP generators; does not perform post-generation release boundary auditing or construct verifiable cryptographic privacy receipts.

---

### P8. McKenna et al. — "AIM: An Adaptive and Iterative Mechanism for DP synthetic data" — VLDB 2022
- **Citation & Venue**: Ryan McKenna, Brett Mullins, Daniel Sheldon, Gerome Miklau. *"AIM: An Adaptive and Iterative Mechanism for Differentially Private Synthetic Data"*. Proceedings of the VLDB Endowment (PVLDB 2022), Vol. 15, No. 11, pp. 2599–2612 / arXiv:2201.12677v2 [cs.CR].
- **arXiv/DOI**: arXiv:2201.12677v2 [cs.CR]
- **URL fetched**: `https://arxiv.org/abs/2201.12677` / PDF: `https://arxiv.org/pdf/2201.12677.pdf`
- **Paper type**: Experimental (proposes AIM, a select-measure-generate DP synthesis algorithm, and provides extensive empirical benchmark comparisons).
- **Datasets (each)**:
  - 6 benchmark datasets (Table 3, Page 9):
    1. **adult [28]**: UCI Machine Learning Repository — 48,842 records, 15 dimensions, domain size $4 \times 10^{16}$, target attribute: `income>50K`.
    2. **salary [23]**: 135,727 records, 9 dimensions, domain size $1 \times 10^{13}$.
    3. **msnbc [6]**: 989,818 records, 16 dimensions, domain size $1 \times 10^{20}$.
    4. **fire [43]**: 305,119 records, 15 dimensions, domain size $4 \times 10^{15}$.
    5. **nltcs [34]**: 21,574 records, 16 dimensions, domain size $7 \times 10^4$.
    6. **titanic [17]**: 1,304 records, 9 dimensions, domain size $9 \times 10^7$.
- **EXACT QUOTE naming the dataset(s)**:
  > *"6.1 Experimental Setup. Datasets. Our evaluation includes datasets with varying size and dimensionality. We describe our exact pre-processing scheme in the full paper [38], and summarize the pre-processed datasets and their characteristics in the table below.*  
  > *Table 3: Summary of datasets used in the experiments.*  
  > *adult [28] | Records: 48842 | Dimensions: 15 | Min/Max Domains: 2–42 | Total Domain Size: 4 × 10^16*  
  > *salary [23] | Records: 135727 | Dimensions: 9 | Min/Max Domains: 3–501 | Total Domain Size: 1 × 10^13*  
  > *msnbc [6] | Records: 989818 | Dimensions: 16 | Min/Max Domains: 18 | Total Domain Size: 1 × 10^20*  
  > *fire [43] | Records: 305119 | Dimensions: 15 | Min/Max Domains: 2–46 | Total Domain Size: 4 × 10^15*  
  > *nltcs [34] | Records: 21574 | Dimensions: 16 | Min/Max Domains: 2 | Total Domain Size: 7 × 10^4*  
  > *titanic [17] | Records: 1304 | Dimensions: 9 | Min/Max Domains: 2–91 | Total Domain Size: 9 × 10^7"*  
  *(Section 6.1 & Table 3, Page 9)*
  > *"For the adult and titanic datasets, these are the income>50K attribute and the Survived attribute, as those correspond to the attributes we are trying to predict for those datasets."*  
  *(Section 6.1 "Workloads", Page 9)*
- **Reported metrics and numbers on Adult**:
  - Metric: **Workload Error** (Average Total Variation Distance / $L_1$ error over marginal queries) across 3 workloads (all-3way, target, skewed) and 9 privacy budgets ($\epsilon \in [10^{-2}, 10^1]$ at $\delta = 10^{-9}$), comparing AIM, PrivMRF, MST, PrivBayes+PGM, MWEM+PGM, GEM, and RAP over 5 trials.
  - Verbatim Quotes & Numbers:
    - Section 6.2 (Page 9): *"On average, across all six datasets and nine privacy parameters, AIM achieves the lowest error in 68% of the configurations, and is within 10% of the best error in 83% of the configurations."*
    - Figure 1 (Page 10): Reports workload error curves for Adult across $\epsilon \in [0.01, 10.0]$. On the Adult target workload at $\epsilon = 1.0$, AIM achieves an average error of $\approx 0.02$, outperforming MST and GEM.
- **Overlap verdict**: **SAME as our UCI Adult** (full 48,842 rows, target: `income>50K`); **NO Bank**; **NO ACS**.
- **Anything they did NOT do that SynthProof does**: Focuses strictly on synthesis algorithm optimization (query selection + Private-PGM); does not audit the release boundary or generate verifiable cryptographic privacy receipts.

---

### P9. Abowd et al. — "The 2020 Census Disclosure Avoidance System TopDown algorithm" — 2022
- **Citation & Venue**: John M. Abowd, Robert Ashmead, Ryan Cumings-Menon, Simson Garfinkel, Micah Heineck, Christine Heiss, Robert Johns, Daniel Kifer, Philip Leclerc, Ashwin Machanavajjhala, Brett Moran, William Sexton, Matthew Spence, Pavel Zhuravlev. *"The 2020 Census Disclosure Avoidance System TopDown Algorithm"*. Harvard Data Science Review (Special Issue 2, 2022) / arXiv:2204.08986v1 [cs.CR].
- **arXiv/DOI**: arXiv:2204.08986v1 [cs.CR]
- **URL fetched**: `https://arxiv.org/abs/2204.08986` / PDF: `https://arxiv.org/pdf/2204.08986.pdf`
- **Paper type**: Systems / Engineering & Algorithm specification (details the TopDown Algorithm used for the 2020 US Decennial Census).
- **Datasets (each)**:
  1. **2010 Census Edited File (CEF) / Hundred-percent Detail File (HDF)**: Confidential decennial census enumeration data used for parameter tuning and demonstration products (PPMF).
  2. **2020 Census Edited File (CEF)**: Confidential production input for the 2020 Census Redistricting Data (P.L. 94-171) Summary File / Microdata Detail File (MDF).
  3. **1940 Census public microdata**: Used in early experimental implementations.
- **EXACT QUOTE naming the dataset(s)**:
  > *"8.1. Tuning the DAS and the release of demonstration data products. The 2010 Census Edited File. The tuning of the 2020 DAS was conducted using data from the 2010 Census without using the 2020 data. Starting in October 2019, the Census Bureau released a series of demonstration data products based on the 2010 data (U.S. Census Bureau, 2021d). Each set consisted of privacy-protected microdata files (PPMF) generated from the microdata detail file (MDF) that supported at least the redistricting data tables."*  
  *(Section 8.1, Pages 29–30)*
  > *"The demonstration data product dated April 28, 2021 was the final pre-production release. This PPMF consisted of person- and housing unit-level microdata with two global privacy-loss budgets: $\rho = 1.095$ (1.05 for persons and 0.045 for housing units) or $\epsilon = 11.14$ and $\rho = 0.1885$ (0.185 for persons and 0.0035 for housing units) or $\epsilon = 4.36$."*  
  *(Section 8.1, Page 30)*
  > *"Early experimental implementations of TDA using public 1940 Census microdata..."*  
  *(Section 10, Page 47)*
- **Reported metrics and numbers**:
  - Metrics: Count differences, Mean Absolute Error (MAE), Root Mean Squared Error (RMSE), and Mean Absolute Percentage Error (MAPE) evaluated across geographic levels (Nation, State, County, Tract, Block Group, Block).
  - Verbatim Quotes & Numbers:
    - Table 11 (Page 39): Error distribution of the TOTAL query for experimental runs across 2010 Census blocks, block groups, tracts, counties, and states.
- **Overlap verdict**: **RELATIVE of Census domain** (uses Decennial Census full-count person and housing unit microdata [2010/2020 CEF], whereas SynthProof uses the American Community Survey PUMS via folktables [ACSIncome] and 1994 Census Adult; both originate from the US Census Bureau but represent distinct data products and schemas).
- **Anything they did NOT do that SynthProof does**: Hierarchically generates synthetic tabular census counts via mathematical programming; does not perform independent release-boundary verification or provide consumer-side cryptographic verification receipts.

---

### P10. Dibia, Lu, Bhattacharjee, Near & Feng — "'We need a standard' ... privacy label for DP" — PoPETs 2026
- **Citation & Venue**: Onyinye Dibia, Mengyi Lu, Prianka Bhattacharjee, Joseph P. Near, Yuanyuan Feng. *"“We Need a Standard”: Toward an Expert–Informed Privacy Label for Differential Privacy"*. Proceedings on Privacy Enhancing Technologies (PoPETs 2026) / arXiv:2507.15997v1 [cs.CR], July 2025.
- **arXiv/DOI**: arXiv:2507.15997v1 [cs.CR]
- **URL fetched**: `https://arxiv.org/abs/2507.15997` / PDF: `https://arxiv.org/pdf/2507.15997.pdf`
- **Paper type**: **Qualitative interview study / Standards proposal** (interview study with 12 DP experts).
- **Datasets (each)**:
  - **NO EXPERIMENTAL DATASETS (paper type: qualitative interview study / standards proposal)**.
- **EXACT QUOTE naming the study methodology / lack of datasets**:
  > *"We conducted a qualitative interview study with 12 DP experts. This section details the participant recruitment, the interview procedure, and data analysis."*  
  *(Section 3 "Methodology", Page 2)*
  > *"We used the purposive sampling method to recruit DP experts across academia, industry, and government... We assigned participant numbers P01–P12 to these experts."*  
  *(Section 3.1 "Participant Recruitment", Pages 2–3)*
  > *"An Expert-Informed DP Label Design. The goal of presenting the DP label is to concretely visualize the expert consensus from this interview study. This section details our design rationale..."*  
  *(Section 5, Page 10)*
- **Reported metrics and numbers**:
  - Qualitative thematic analysis codebook frequencies and expert consensus counts (e.g., Section 4.3, Page 9: *"Ten experts favored the two-layer structure for DP labels"*). No benchmark dataset metrics or numeric utility/privacy evaluations.
- **Overlap verdict**: **NO overlap** (no experimental datasets).
- **Anything they did NOT do that SynthProof does**: Develops human-readable, qualitative design guidelines for what an expert DP label should display; SynthProof implements a machine-verifiable release manifest with cryptographic SHA-256 hashes, deterministic parameter boundary verification, and automated compliance receipts.

---

### P11. Song, Sarathy, Shoemate & Vadhan — "'I inherently just trust that it works' ..." — CSCW 2024
- **Citation & Venue**: Rock Yuren Song, Jayshree Sarathy, Hunter Shoemate, Salil Vadhan. *"“I inherently just trust that it works”: Investigating Mental Models of Open-Source Libraries for Differential Privacy"*. Proceedings of the ACM on Human-Computer Interaction (PACMHCI / CSCW 2024) / arXiv:2410.09721v1 [cs.CR], October 2024.
- **arXiv/DOI**: arXiv:2410.09721v1 [cs.CR]
- **URL fetched**: `https://arxiv.org/abs/2410.09721` / PDF: `https://arxiv.org/pdf/2410.09721.pdf`
- **Paper type**: **Qualitative interview & usability user study** (interviews with 5 library developers and usability study with 15 practitioners).
- **Datasets (each)**:
  - **NO EXPERIMENTAL DATASETS (paper type: qualitative interview & user study)**. Participants performed small mock programming tasks (calculating DP mean and histogram) on toy synthetic numbers.
- **EXACT QUOTE naming the study methodology / lack of datasets**:
  > *"In this paper, we present an empirical study investigating the mental models of DP held by users and developers of open-source DP libraries. We conducted formative interviews with 5 library developers and a user study with 15 DP practitioners using two popular libraries: Diffprivlib and OpenDP."*  
  *(Section 1 "Introduction", Page 2)*
  > *"After finishing the documentation overview, we asked participants to complete data analysis tasks in their assigned DP library. By observing how participants interacted with the libraries, and how participants reacted to libraries’ attempts to redirect actions via error and warning handling, we aimed to understand how library design shaped participants’ mental models..."*  
  *(Section 4.1 "Data Analysis Tasks", Pages 19–20)*
- **Reported metrics and numbers**:
  - Usability metrics: Task completion rates (Table 4, Page 20: Task 1 DP mean completed by 7/9 Diffprivlib participants vs 0/6 OpenDP participants), error frequencies, qualitative user themes. No benchmark dataset metrics.
- **Overlap verdict**: **NO overlap** (no experimental datasets).
- **Anything they did NOT do that SynthProof does**: Investigates human developer perceptions, mental models, and documentation usability; SynthProof automates zero-trust release boundary verification and audit validation without relying on developer intuition or unverified trust.

---

## Part 3 — Recommendation

### 1. Direct Same-Dataset Comparison Overlap
- **UCI Adult** ($N = 5$ papers share this dataset):
  - **P1** (Stadler et al., 2022)
  - **P2** (Annamalai et al., 2024)
  - **P5** (Ganev et al., 2025)
  - **P7** (Mohapatra et al., 2024)
  - **P8** (McKenna et al., 2022)
- **UCI Bank Marketing** ($N = 1$ paper shares this dataset):
  - **P7** (Mohapatra et al., 2024)
- **ACSIncome via folktables**:
  - **None of the 11 papers use ACSIncome or folktables.**  
  *(P9 uses the 2010/2020 US Decennial Census full-count microdata [CEF/HDF/PPMF], which belongs to the same administrative institution [US Census Bureau] but is a completely distinct dataset and schema from ACS PUMS / folktables).*

---

### 2. Best Base Paper for a NUMERIC Head-to-Head Comparison on UCI Adult

#### **Rank 1 (Best Numeric Comparison for Synthetic Data Generation): P8 (McKenna et al., VLDB 2022 — AIM)**
- **Why**: McKenna et al. evaluate on the **full, standard 48,842-record UCI Adult dataset** across 15 attributes, predicting the identical target attribute (`income>50K`). They report concrete, numerical **Workload Error** (Total Variation Distance across 3-way marginals, target marginals, and skewed marginals) across 9 privacy budgets ($\epsilon \in [0.01, 10.0]$ at $\delta = 10^{-9}$) for the canonical benchmark algorithms: AIM, MST, PrivBayes+PGM, and GEM.
- **Verbatim Quote proving Adult reporting**:
  > *"For the adult and titanic datasets, these are the income>50K attribute and the Survived attribute, as those correspond to the attributes we are trying to predict for those datasets."*  
  *(Section 6.1 "Workloads", Page 9)*  
  > *"adult [28] | Records: 48842 | Dimensions: 15 | Min/Max Domains: 2–42 | Total Domain Size: 4 × 10^16"*  
  *(Table 3, Page 9)*

#### **Rank 2 (Best Multi-Dataset Numerical Base — Adult AND Bank): P7 (Mohapatra et al., VLDB 2024)**
- **Why**: Mohapatra et al. is the **only paper among all 11 that evaluates on BOTH UCI Adult AND UCI Bank Marketing**. They report concrete numerical 1-way TVD, 2-way TVD, classification F1-scores, and privacy amplification budgets across $\epsilon \in [0.5, \infty]$.
- **Verbatim Quote proving Adult and Bank reporting**:
  > *"Datasets. We run our experiments on four tabular datasets as described in Table 1: (i) Adult dataset [25], which contains information about 32561 individuals from the 1994 US Census (ii) Bank dataset [64], which has 45211 rows about direct marketing campaigns of a Portuguese banking institution..."*  
  *(Section 6.1, Page 11)*

#### **Rank 3 (Best Auditing / Privacy Leakage Head-to-Head): P2 (Annamalai et al., USENIX Security 2024)**
- **Why**: If SynthProof compares empirical auditing leakage estimates ($\epsilon_{emp}$) on Adult, P2 provides empirical privacy bounds across 6 DP generative model implementations at theoretical $\epsilon \in \{1.0, 4.0\}$.
- **Verbatim Quote proving Adult reporting**:
  > *"1. Adult [34], used to predict whether income exceeds $50K from Census data. To make sure the dataset can be used as input to all DP-SDGs, we trim and bin the dataset to 11 categorical attributes..."*  
  *(Section 4.1, Page 6)*

---

### 3. Conceptual Base Papers (No Direct Benchmark Numbers)
1. **P10 (Dibia et al., PoPETs 2026 — "We Need a Standard: Toward an Expert-Informed Privacy Label for Differential Privacy")**:
   - **Role in SynthProof**: Direct conceptual justification for SynthProof's **Release Manifest / Privacy Nutrition Label**. Dibia et al. define through 12 expert interviews what privacy parameters, bounds, and disclosures must accompany a DP release. SynthProof operationalizes this qualitative label into a machine-verifiable, cryptographically sealed release artifact.
2. **P11 (Song et al., CSCW 2024 — "'I Inherently Just Trust That It Works'")**:
   - **Role in SynthProof**: Direct empirical justification for why **automated release-boundary auditing and verification receipts** are mandatory. Song et al. prove that practitioners uncritically trust DP libraries and fail to recognize parameter bounds or misconfigurations.
3. **P3 (Cebere et al., 2026 — "Privacy in Theory, Bugs in Practice")**:
   - **Role in SynthProof**: Direct systems justification for independent verification. Cebere et al. demonstrate that 12 open-source DP libraries suffer from sensitivity miscalibrations and edge-case leaks, proving that theoretical privacy claims cannot be trusted without empirical release verification.
