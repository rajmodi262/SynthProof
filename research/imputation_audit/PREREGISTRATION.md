# Pre-Registration: Privacy Audit of Missing-Data Imputation in Differentially Private Tabular Synthesis

**Document:** Formal Pre-Registration Specification  
**Status:** COMMITTED AND FROZEN PRIOR TO EXPERIMENTAL EXECUTION  
**Date:** 2026-09-15  
**Repository:** `SynthProof` (Branch: `fix/selection-accounting`)  
**Adversarial / Honesty Protocol:** In effect (`CLAUDE.md`, `ANTIGRAVITY_IMPUTATION_AUDIT_BRIEF.md`)

---

## 1. Background, Motivation & Research Question

Differential Privacy (DP) synthetic-data pipelines universally perform data preprocessing prior to fitting the generative mechanism. A recent series of privacy audits by Ganev, Annamalai, Mahiou, and De Cristofaro systematically examined three common pre-synthesis preprocessing steps:
1. Domain extraction (arXiv:2504.08254, ICLR-W 2025)
2. Discretization / binning (arXiv:2504.06923, CCS 2025)
3. SMOTE oversampling (arXiv:2510.15083, ICLR 2026)

**Missing-data handling is the fourth universal preprocessing step and has never been privacy-audited.** The solitary existing paper examining differential privacy and missing data (Mohapatra et al., PVLDB 2024, arXiv:2310.11548) focused entirely on utility and privacy amplification—positing that incomplete records naturally enhance privacy by diminishing per-record influence—and contained zero membership inference attacks or adversarial auditing.

This creates an unmeasured, live tension:
- **Amplification theory** argues that missingness protects individual privacy.
- **The preprocessing-audit programme** predicts that data-dependent imputation fitted across records on private data, without formal DP accounting, injects an uncharged privacy leak that survives synthesis.

**Research Question:** Does fitting missing-data imputation across private records without DP budget accounting introduce measurable membership leakage in downstream synthetic releases, compared to a baseline where the same imputation is formally charged under DP?

---

## 2. Hypotheses & Pre-Registered Decision Rules

### Primary Hypothesis ($H_1$)
A synthetic data release produced after fitting imputation across private records without budget accounting (**Arm A2: Uncharged Imputation**) leaks membership information above the identical imputation mechanism charged to the DP budget (**Arm A3: Charged DP Imputation**).
- **Formal Criterion for Confirmation:** Hypothesis $H_1$ is confirmed if and only if the 95% bootstrap confidence interval of Arm A2's member-vs-non-member AUC lies strictly above Arm A3's 95% bootstrap confidence interval ($\text{CI}_{\text{lo}}(A_2) > \text{CI}_{\text{hi}}(A_3)$) across the primary auditor (`DistanceMIABaseline`).

### Null Hypothesis / Interpretable Null ($H_0$)
The member-vs-non-member AUC confidence intervals for Arm A2 and Arm A3 overlap:
$$\text{CI}(A_2) \cap \text{CI}(A_3) \ne \emptyset$$

### Pre-Registered Interpretation of Results
1. **If $H_1$ is Confirmed:** The uncharged imputation step represents an empirical privacy violation in end-to-end DP tabular synthesis pipelines, validating the Ganev preprocessing-audit pattern for missing-data imputation.
2. **If $H_0$ is Observed (Interpretable Null):** Imputation fitted across records does not introduce leakage detectable above the charged baseline at this instrument's empirical resolution.
   - **Crucial Boundary Caveat:** Per the passed K3 audit-power gate (`research/imputation_audit/K3_FINDINGS.md`), our primary auditor (`DistanceMIABaseline`) resolves a known planted partial leak corresponding to a 25% verbatim-copy release at $n=1500$ (AUC $\approx 0.54$ vs private $\approx 0.50$). Therefore, an observed null means:
     *"Uncharged statistical imputation introduces less membership leakage than a 25% verbatim copy under this setup."*
   - It will **NOT** be claimed as *"imputation is proven safe"*, nor as a project failure. An interpretable null is an empirical finding directly counterbalancing the Ganev series and informing practical deployment standards.
3. **Scope Discipline on Complete-Case Drop (`dropna`):** Arm A0 (`dropna`) is a row-wise stability-1 filter under add/remove-one adjacency and does not violate DP. Arm A0 is evaluated strictly for utility/selection bias, and will **never** be claimed as a DP bug.

---

## 3. The Four Experimental Arms

All arms operate on a tabular dataset containing missing values and return a completed table which is subsequently passed to the downstream DP synthesiser. The only factor varied across arms is the handling of missingness:

| Arm | Name | Mechanism Description | DP Budget Charged? | Role in Study |
|---|---|---|---|---|
| **A0** | Complete-Case Drop | Drops any row containing missing values (`df.dropna()`). | None (Stability-1 row filter) | Baseline for selection bias; negative control for leak claim. |
| **A1** | Sentinel Category | Categorical: `"__MISSING__"` level; Numeric: declared sentinel / out-of-range value. | Zero private query (No private stats read) | Structural control; isolates effect of domain expansion without imputation. |
| **A2** | Uncharged Imputation | Imputes using column statistics computed on the private dataset: mode for categoricals; mean/median for numerics. | **UNCHARGED** ($\varepsilon_{imp} = 0$) | **The Arm Under Test (Suspected Violation).** |
| **A3** | Charged DP Imputation | Computes the identical imputation statistics under DP: Laplace mechanism for numerics; noisy histogram/noisy max for categoricals. | **CHARGED** ($\varepsilon_{imp} = 0.1 \varepsilon$) to `synthproof.accounting.Accountant` | **The Correct DP Baseline.** |

*Note on symmetry:* Arms A2 and A3 use identical statistical estimators (mean/mode imputation). The solely manipulated variable is whether the estimators are perturbed by DP noise and charged to the privacy accountant.

---

## 4. Missingness Conditions

The evaluation tests two data regimes:
1. **Native Missingness (Primary Condition):**
   - Benchmark: UCI Adult dataset.
   - Real-world missing values (`?` in `workclass`, `occupation`, `native_country`) retained from the raw data without pre-dropping.
2. **Injected Overlays (Comparability with Mohapatra et al., PVLDB 2024):**
   - Synthetically introduced missingness on fully observed columns across three standard mechanisms:
     - **MCAR (Missing Completely At Random):** Probability of missingness is independent of observed and unobserved data.
     - **MAR (Missing At Random):** Probability of missingness depends on an observed covariate (e.g. `age` determines missingness in `hours_per_week`).
     - **MNAR (Missing Not At Random):** Probability of missingness depends on the value of the missing variable itself (e.g. high `capital_gain` is missing).
   - Injected missingness rates: 10% and 20%.

---

## 5. Experimental Grid, Auditor & Specifications

### Sample Size & Split
- $n = 1500$ training members, $n = 1500$ disjoint non-members sampled from the population.
- Members are used to fit the preprocessing and synthesis pipelines; non-members serve as the held-out unobserved population.

### Generative Mechanisms
1. `IndependentMarginalGenerator` (Fast baseline, marginal synthesis).
2. `DPVAEGenerator` (DP-SGD neural generative model).
3. `AIMGenerator` (Graphical marginal selection under Private-PGM).
   - *Resource Constraint:* Executed **strictly one process at a time** to prevent virtual memory exhaustion (AIM requires ~9 GB per instance).

### Privacy Parameters
- $\varepsilon \in \{1.0, 4.0\}$.
- $\delta = 10^{-5}$.
- Random seeds: $S \ge 8$ independent runs per cell (default $S = 8$).

### Membership Inference Auditors
1. **Primary Auditor:** `synthproof.attacks.distance_mia.DistanceMIABaseline` (Euclidean distance to closest synthetic record; member vs non-member AUC). Verified as the most sensitive instrument in K3.
2. **Secondary Auditor:** `synthproof.attacks.domias.DOMIAS` (Density-ratio estimation).
3. **Categorical Auditor:** `synthproof.attacks.marginal_ratio.MarginalRatioRisk` (Ratio test on marginal distributions).

### Statistical Readout
- For every cell, we report the sample mean AUC across seeds and the **95% bootstrap confidence interval** (4,000 bootstrap iterations over seeds).
- Non-overlapping bootstrap CIs between A2 and A3 determine statistical significance.

### Mandatory Sanity Gate (Self-Check)
Prior to running the grid or interpreting any null result:
- Confirm that a 100% planted verbatim leak (`LeakyGenerator`) achieves AUC $\ge 0.65$ and separates from the private baseline with non-overlapping CIs under this exact runner.
- If the sanity gate fails, the instrument is blind and the experiment halts.

---

## 6. Pre-Registered Stopping Rule

The experimental grid, dataset splits, seeds ($S=8$), mechanisms, and auditor parameters defined herein are **fixed in advance**.  
No cells, seeds, or post-hoc arm variations will be added or pruned based on observed AUC values. Both positive leaks and interpretable nulls will be reported transparently in `research/imputation_audit/RESULTS.md`.

---

## 7. Pre-Registration Amendment (2026-09-15): Imputation Audit Correction

### Reason for Amendment
Post-run audit of the initial grid revealed a fatal methodological flaw:
1. **Instrument Blind Spot:** Adult's native missingness occurs exclusively in categorical attributes (`workclass`, `occupation`). However, the two auditors previously reported (`DistanceMIABaseline` and `DOMIAS`) evaluate strictly numeric columns (`is_numeric_dtype`). Consequently, neither auditor ever read the columns modified by the imputation arms under the native missingness condition. The observed $\approx 0.50$ AUC was an artifact of instrument blindness rather than empirical privacy preservation.
2. **Low-Sensitivity Marginal Estimators:** Arms A2 and A3 implemented empirical mode/median, which are $O(1/n)$-stable univariate statistics where DP mode $\approx$ empirical mode, testing the least-leaky possible imputation.

### Corrective Specifications (Pre-Registered Prior to Re-Run)

#### 1. Categorical-Leak Sanity Gate
Before any categorical condition is interpreted, a dedicated **Categorical Sanity Gate** must execute:
- Construct a planted categorical leak where the members' categorical columns are released verbatim alongside randomized holdout numeric columns.
- Compare against a known null baseline drawn entirely from an unobserved holdout population.
- Audit using `MarginalRatioScorer` over 1-way, 2-way, and 3-way categorical cliques.
- **Pass Criteria:** The categorical leak must achieve mean AUC $\ge 0.58$ with non-overlapping 95% bootstrap confidence intervals relative to the null baseline at $n = 1500$.
- **Hard Rule:** If this gate fails, no categorical null can be reported; the outcome must be stated as "instrument blind, inconclusive".

#### 2. Primary Auditor Designation
- `MarginalRatioScorer` (`synthproof.attacks.marginal_ratio`) is designated as the **Primary Auditor** for all categorical missingness conditions (including `native`).
- Numeric auditors (`DistanceMIABaseline`, `DOMIAS`) remain secondary and are restricted to evaluating injected numeric missingness.

#### 3. Cross-Record Imputation Arm (A4 & A4_CHARGED)
To test whether multi-attribute individual correlation structure leaks when imputed across records:
- **Arm A4 (Uncharged $k$-NN):** Imputes missing categorical attributes via plurality vote across the $k=5$ nearest sensitive member records in standardized feature space without DP accounting.
- **Arm A4_CHARGED (DP-Charged $k$-NN):** Identical $k$-NN pooling, but applying Report-Noisy-Max with discrete Laplace noise to category counts and formally debiting the budget from `Accountant`.

#### 4. Grounded Interpretation Rule
A null result is scientifically accepted **only** when certified by a passed same-column-type sanity gate. Any condition where the auditor could not detect a known leak of that column type must be reported as "instrument blind, inconclusive," never "imputation does not leak."

