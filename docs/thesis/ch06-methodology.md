# Chapter 6 — Experimental Methodology

This chapter specifies the experimental methodology used to evaluate SynthProof. To protect scientific validity against post-hoc hypothesis construction, the evaluation was governed by a version-controlled preregistration protocol, a multi-dataset comparative design, and rigorous statistical hypothesis testing incorporating false discovery rate corrections and equivalence testing.

---

## 6.1 Preregistration

Scientific claims in empirical privacy and synthetic data are frequently compromised by unacknowledged researcher degrees of freedom: adjusting privacy budgets, selecting favorable utility metrics, or omitting null results after inspecting experimental outcomes. To prevent these practices, the core hypotheses, experimental grid, evaluation metrics, and primary statistical tests were formally registered in `docs/preregistration.md` prior to executing any committed experimental sweeps.

The preregistration commit is tagged as `prereg-v1` in the repository's Git history, pointing directly to commit `8a8e21d` (2026-08-07). Version control audit logs confirm that no result artifact in the `results/` directory predates this commit. The protocol commits the authors to reporting results across all tested conditions regardless of outcome direction. In particular, both the refutation of H1 on ACSIncome and the bounded null findings for H2 (demographic subgroup parity) and H3 (utility-weighted privacy allocation) are fully presented in Chapter 7 in strict accordance with this pre-commitment.

---

## 6.2 Datasets

Empirical evaluations are conducted across two benchmark tabular datasets representing demographic, socioeconomic, and employment data:

1. **UCI Adult Census Dataset**: The standard benchmark in differential privacy and algorithmic fairness literature, containing 48,842 records extracted from the 1994 United States Census across 14 demographic and occupational attributes. To maintain computational tractability across 75 experimental grid configurations evaluated over 5 independent random seeds per cell (yielding 375 full synthesis, auditing, and utility evaluation cycles), we draw a stratified subsample of $n = 6,000$ records, partitioned into an 80/20 train/test split ($n_{\text{train}} = 4,800$, $n_{\text{test}} = 1,200$). The downstream prediction target is binary income classification (`income > 50K`).
2. **ACSIncome Benchmark**: Drawn from the American Community Survey (ACS) Public Use Microdata Sample (PUMS) for California (2018 1-Year release) using the `folktables` package (Ding et al., NeurIPS 2021). ACSIncome was developed explicitly to address the documented temporal and geographic limitations of the 1994 UCI Adult dataset. Following an identical protocol, we extract a subsample of $n = 6,000$ records across 10 attributes, partitioned into an 80/20 train/test split ($n_{\text{train}} = 4,800$, $n_{\text{test}} = 1,200$), with the binary target defined as personal income exceeding $50,000 (`PINCP > 50K`).

### Subgroup Attributes for Privacy and Fairness Auditing
To evaluate demographic privacy parity (H2) and subgroup utility fairness, two primary demographic axes are evaluated:
- **Sex**: Binary indicator (`Male`, `Female` in Adult; `SEX` 1 and 2 in ACSIncome).
- **Race**: Categorical attribute with 5 distinct levels in Adult (`White`, `Black`, `Asian-Pac-Islander`, `Amer-Indian-Eskimo`, `Other`) and 9 levels in ACSIncome via `RAC1P`.

All dataset splits are deterministically generated and pinned using SHA-256 integrity checksums stored in `synthproof/data/datasets.py` to ensure exact cross-experiment repeatability.

---

## 6.3 Experimental Design

The primary empirical evaluation follows a full-factorial experimental design:
- **Privacy Budget Grid**: Target privacy expenditures are evaluated across five geometric steps: $\varepsilon_{\text{target}} \in \{0.5, 1.0, 2.0, 4.0, 8.0\}$. In all experiments, the catastrophic failure parameter is fixed at $\delta = 10^{-5}$, strictly satisfying the cryptographic safety condition $\delta \ll 1/n = 1/6000$.
- **Random Replications**: Every experimental cell is evaluated across 5 independent random seeds ($0, 1, 2, 3, 4$). The random seed controls the discrete noise generator, the canary sample partition, and the train/test split bootstrapping; the attribute schema, mechanism configurations, and evaluation pipelines remain identical.
- **Evaluated Mechanism Families**: We evaluate three primary synthesis paradigms: (i) `IndependentMarginal` (measuring univariate marginals independently, serving as a zero-cross-correlation ablation), (ii) `Pairwise` (dense two-way marginal contingency tables), and (iii) `AIM` (Adaptive Iterative Mechanism using `private-pgm` graphical models with discrete Gaussian noise).

### Train on Synthetic, Test on Real (TSTR) Protocol
Machine learning utility is evaluated using the Train on Synthetic, Test on Real (TSTR) protocol. For each experimental cell, downstream predictive classifiers (Random Forest, Gradient Boosted Trees, and Logistic Regression) are trained exclusively on the generated synthetic table $\widetilde{D}_{\text{train}}$ and evaluated strictly against the untouched, held-out real test set $D_{\text{test}}$. The empirical Train on Real, Test on Real (TRTR) baseline is computed on the identical real test split, eliminating optimistic in-sample evaluation biases that confounded earlier synthetic data benchmarks.

---

## 6.4 Evaluation Metrics

The experimental evaluation assesses privacy, security, and utility across quantitative dimensions:

### 1. Privacy Metrics
- **Formally Proved Privacy ($\varepsilon_{\text{proved}}$)**: The upper bound on cumulative privacy expenditure computed via Google's `dp_accounting` engine under Rényi Differential Privacy composition converted to $(\varepsilon, \delta)$.
- **Empirically Audited Privacy ($\varepsilon_{\text{audited}}$)**: The empirical lower bound on privacy loss estimated via Steinke et al.'s (2023) one-run binomial auditor on planted canary records.
- **Audit Ceiling ($\varepsilon_{\text{max}}$)**: The information-theoretic upper bound on the auditor's measurement reach, transferring the Limit of Detection (LoD/LLOQ) reporting standard from molecular diagnostics and clinical assays (MIQE 2.0, Bustin et al., Clinical Chemistry 2025;71(6):634–651; ISO 11843), as formalized by Annamalai, Ganev & De Cristofaro (arXiv:2405.10994 §2.2).

### 2. Empirical Disclosure Attacks (EDPB Guidelines)
We evaluate the five concrete threat models mandated by European Data Protection Board (EDPB) guidelines:
- **Membership Inference Attacks (MIA)**: Evaluated via metric-space nearest-neighbour distance (`distance_mia`) and density-ratio estimation (`domias`, van Breugel et al., 2023). In accordance with the methodology of Carlini et al. (2022), attacks are scored using Area Under the ROC Curve (AUC) and True Positive Rate at a low false alarm rate of 1% FPR (`tpr_at_1pct_fpr`), demonstrating why average-case accuracy is an inadequate metric for high-confidence privacy leakage.
- **Attribute Inference**: Evaluated via supervised classifier reconstruction of sensitive features from non-sensitive quasi-identifiers (`attribute_inference`).
- **Singling Out**: Evaluated via exact match collision metrics (`exact_match_risk`).
- **Linkability**: Evaluated via split-attribute bipartite matching across disjoint synthetic releases (`linkability`).

### 3. Utility Metrics
- **Machine Learning Classification Fidelity**: Evaluated via the macro-averaged F1 score under the TSTR protocol.
- **Univariate Distribution Fidelity**: Evaluated via average Wasserstein-1 distance across all marginal distributions.
- **Multivariate Correlation Preservation**: Evaluated via the mean absolute difference in pairwise Pearson correlation matrices between real and synthetic tables.

---

## 6.5 Statistical Analysis and Multiplicity Control

To prevent spurious empirical claims arising from random noise, all reported point estimates are accompanied by 95% non-parametric bootstrap confidence intervals computed over 1,000 bootstrap resamples.

### Multiplicity Correction
When evaluating subgroup privacy parity (H2), multiple simultaneous statistical hypotheses are tested across demographic levels (14 pairwise comparisons on Adult, 22 on ACSIncome). To control the family-wise error rate and false discovery rate:
- **Benjamini-Hochberg False Discovery Rate (BH-FDR)**: Applied at a nominal significance threshold of $\alpha = 0.05$.
- **Bonferroni Adjustment**: Applied as a conservative upper bound across family comparisons.

### Two-One-Sided-Test (TOST) Equivalence
When an empirical attack fails to detect a significant disparity between demographic subgroups, declaring "no difference" is a fallacy of accepting the null hypothesis. We evaluate empirical nulls using the Two-One-Sided-Test (TOST) equivalence framework, testing whether the observed subgroup difference $\Delta_{\text{subgroup}}$ falls strictly within an *a priori* specified region of practical equivalence $[-\Delta_{\text{equiv}}, +\Delta_{\text{equiv}}]$.

---

## 6.6 Reproducibility and Checkpoint Integrity

Reproducibility is enforced at two distinct operational tiers:

1. **Fast Checkpoint Verification (`python scripts/reproduce.py --run`)**: Verifies checkpoint integrity by reloading raw experimental cell outputs from `results/h1_cells/` and re-aggregating all summary metrics, bootstrap confidence intervals, and hypothesis tests in under 1 second. This verifies that reported tables match raw results without requiring expensive GPU/CPU re-synthesis.
2. **Full End-to-End Synthesis Sweep (`make reproduce`)**: Re-runs the complete computational pipeline from scratch across all 75 cells, 5 seeds, and both datasets. The end-to-end sweep requires approximately 4 hours per dataset on standard workstation hardware.

Following execution, all output files, seeds, execution environments, and package dependencies are cryptographically hashed and recorded in `results/manifest.json`.

---

## 6.7 The Preregistration Tag — What It Does and Does Not Establish

`docs/preregistration.md` is tagged `prereg-v1`. State the following in the chapter, in these terms, because a reviewer will check it and a stronger claim is not supportable:

**What is verifiable**: The tag points at commit `8a8e21d` (2026-08-07), the repository's first commit, which is where `preregistration.md` first appears. **No result file in this repository predates that commit** — `git log --reverse -- results/` confirms the earliest result artefacts are in the same commit or later. The hypotheses, ε grid, δ, seed count and primary metrics were therefore fixed in version control before any committed experiment ran.

**What is NOT verifiable, and must be said**: Three qualifications:
1. **The tag was applied retroactively**, on 2026-08-15, pointing at the historical commit. It was not created at the time. Git tags carry their own creation date, so this is discoverable and should be declared rather than left for a reviewer to notice.
2. **The document is dated 2026-08-05, two days before its first commit.** There is no independent timestamp for that earlier date. The earliest *verifiable* existence of the preregistration is 2026-08-07.
3. **This is not a third-party registration.** An OSF or AsPredicted entry is timestamped by a party with no interest in the outcome. A git tag is timestamped by us, and we control the repository. The correct description is a **version-controlled commitment**, not a preregistration in the clinical-trials sense.

**Why it is still worth having**: The commitment predates every committed result, the deviations below are declared rather than discovered, and both H1's partial refutation and H2's null are reported. That is the substance preregistration exists to protect. Overstating its formal status would undermine exactly the credibility it is meant to supply.

---

## 6.8 Deviations from the Preregistration

Transparent scientific reporting requires documenting all deviations from the initial protocol, providing the methodological rationale for each modification and analyzing its direction of effect on statistical inference. In empirical software engineering and privacy research, deviations frequently occur as systems mature, but failing to declare them transforms exploratory analysis into confirmatory claims.

We document five explicit deviations (D1 through D5) from our initial protocol. Each modification was logged contemporaneously in version control. Rather than attempting to conceal methodological adjustments that arose during experimentation, we analyze how each change impacted our statistical conclusions. For example, closing deviation D1 by introducing the ACSIncome benchmark demonstrated that the structural superiority of AIM observed on Adult did not generalize, reversing our initial expectations. Similarly, adopting Steinke's one-run binomial auditor (D3) improved estimation efficiency over paired estimators, while measuring utility on canary-free synthetic datasets (D2) ensured that canary records did not distort downstream machine learning models. The five deviations are summarized below:

| # | Deviation | Reason | Effect on inference |
|---|---|---|---|
| ~~D1~~ | ~~**ACSIncome not run.** UCI Adult only~~ **CLOSED.** Both hypotheses now run on ACSIncome (CA 2018, n=6,000) under the identical protocol — same seeds, epsilon grid, and structure column pair | — | See §6.9. External validity was **tested**, and the H1 structure ordering **did not transfer**. That is now a reported finding rather than an unexamined limitation |
| D2 | **Utility measured on a second, canary-free fit** | Measuring it on the canary-trained model contaminates the signal being measured: planting canaries flattens the joint structure the fidelity metric scores. **The effect size originally reported here does not replicate** — see `results/CANARY_DOSE_RESPONSE.md`; it scales with canary FRACTION, not count, and is significant only above ~3% | Removes a bias that had been penalising exactly the mechanisms that model dependence. Direction: made H1 *measurable*; without it H1 was falsely null | **[SUPERSEDED 2026-09-06 — does not replicate; see `results/CANARY_DOSE_RESPONSE.md`]**
| D3 | **Auditor changed** from paired Clopper-Pearson to the one-run construction | The paired estimator spends two canaries per comparison and saturates sooner | Slightly raises the audited bound at fixed canary budget. Both are reported and compared |
| D4 | **H1 primary metric supplemented.** Preregistration named TSTR macro F1; correlation error was added as a structure metric | TSTR alone cannot distinguish an independent-marginal mechanism from a structured one on this data | Additive, not substitutive — TSTR is still reported. The structure metric is what separates the families |
| ~~D5~~ | ~~**H3 not run**~~ **CLOSED.** H3 now run on both datasets, 5 epsilon values x 5 seeds x 2 arms | — | See §6.10. H3 is **not supported** on either dataset, and the null replicates |

The documentation of these five deviations illustrates the importance of adaptive self-auditing in computational privacy research. By recording both the original design decisions and their subsequent refinements, we ensure that every empirical result reported in Chapter 7 can be traced to its exact methodological lineage without unacknowledged researcher degrees of freedom.

---

## 6.9 External Validity: What the Second Dataset Changed

D1 was closed by running the full preregistered protocol on **ACSIncome (California, 2018)** via `folktables` — the dataset Ding et al. (NeurIPS 2021) built as UCI Adult's modern replacement. Everything the protocol controls was held identical: n = 6,000, seeds 0-4, ε ∈ {0.5, 1, 2, 4, 8}, and the same structure-metric column pair by analogy (`AGEP`×`WKHP` for `age`×`hours_per_week`). A difference between the datasets is therefore attributable to the data, not the procedure. This is enforced by `tests/test_experiment_scripts.py::test_the_two_datasets_share_the_protocol_that_makes_them_comparable`.

Two things could not be held identical, and both are reported rather than corrected away:

1. **The true correlation differs** (Adult 0.1034, ACS 0.0721), so *absolute* correlation error is not comparable across the datasets. Only the mechanism **ordering** transfers.
2. **The per-subgroup audit ceiling differs.** Transferred from analytical chemistry's Limit of Detection (LoD) standard (MIQE 2.0, Bustin et al. 2025) and formalised as the 'maximum auditable epsilon' (Annamalai, Ganev & De Cristofaro 2024; Steinke et al. 2023 Thm 2.1), the ceiling sets the instrument's reach. H2 allocates a fixed 400-canary budget equally across an attribute's levels; `race` has 5 levels on Adult and `RAC1P` has 9 on ACS, giving 80 vs 44 canaries per group and ceilings of 3.27 vs 2.65. ACS's race instrument is genuinely weaker *before any mechanism runs*. Raising ACS's budget to equalise the ceilings would have confounded group count with total canary count instead.

### What Transferred, and What Did Not

**H2 replicated.** The null holds on both datasets and for the same reason. On Adult, 0 of 14 comparisons survive BH-FDR or Bonferroni; on ACS, 0 of 22. On ACS the largest observed bound was 0.096 at adversary accuracy 0.591, against a ceiling of 2.65 — 3.6% of the instrument's range. The conclusion is unchanged and is now dataset-independent: at this canary budget the instrument cannot resolve subgroup differences, which bounds the effect rather than establishing its absence.

**H1's structure ordering did not.** At ε = 8 on Adult the three families separate with mutually non-overlapping CIs, `aim` (0.0078) < `pairwise` (0.0283) < `independent` (0.0947). On ACS the ordering inverts — `pairwise` (0.0202) < `independent` (0.0535) ≈ `aim` (0.0626) — and AIM is **not statistically distinguishable** from the independent-marginals baseline.

Per the analysis plan, a contradicting result is diagnosed, not adjusted. The diagnosis:
- The engineering model-size bound is **not** responsible — `skipped_cliques_` is empty at both ε = 0.5 and ε = 8, with 17 cliques measured at each.
- The structure metric is the correlation of a **single column pair**, and AIM's score on it is largely determined by whether that pair is among the ~6 two-way cliques AIM selects. On Adult, AIM selects `age`×`hours_per_week` at *every* ε tested. On ACS it selects `AGEP`×`WKHP` at one of three, and the ACS correlation error tracks that selection exactly: 0.0977 (not selected) → 0.0395 (selected) → 0.0626 (not selected).

This was later tested directly rather than left as an inference from one pair, by recording AIM's error and its clique selection for EVERY numeric pair across the grid (`scripts/run_clique_confound.py`). The test weakened the claim, and the weakened version is what this thesis states.

It is **not** true that AIM beats the no-dependence baseline only on pairs it selects — each dataset has one unselected pair where it still wins, which is mechanistically expected, since measuring a clique constrains the joint and a graphical model propagates that constraint outside the clique. What is true is a large difference in degree, which itself does not transfer:

| Dataset | Largest advantage on selected pair | Largest advantage on unselected pair | Ratio |
|---|---:|---:|---:|
| Adult | +0.0852 | +0.0072 | 11.9x |
| ACS | +0.0285 | +0.0123 | 2.3x |

On Adult, AIM's advantage on the pair it selects is nearly twelve times its best advantage anywhere else, and `age x hours_per_week` — the pair the H1 headline measured — is that pair, selected in 22 of 25 cells. On ACS the effect is roughly five times weaker and the run's own verdict is inconclusive.

The defensible claim is therefore narrower than a first reading of the single-pair evidence suggested: **the structure metric's choice of column pair materially affects the measured ranking, and on Adult it happened to fall on AIM's strongest pair by an order of magnitude.** That still carries a generalisable warning — a benchmark scoring a marginal-based mechanism on a small fixed set of low-order statistics may be measuring which statistics the mechanism chose to spend budget on — but it does not support the stronger reading that AIM's advantage is entirely an artefact of selection. The cross-dataset pattern is the same one H1 itself showed: an effect on Adult that does not carry to ACS.

A secondary observation, reported because it is counter-intuitive and was verified before being written down: on ACS, AIM's downstream utility **falls** as ε rises (TSTR F1 0.704 [0.695, 0.713] at ε = 0.5 against 0.581 [0.539, 0.629] at ε = 8; the endpoint CIs do not overlap). The cause is the same mechanism — the DP profiler suppresses far fewer rare categories at a larger budget (OCCP 3 → 23 categories, RELP 3 → 14), so a roughly fixed clique allowance covers proportionally less of the domain and fewer cliques land on the target column. AIM optimises global marginal approximation, not a downstream task.

These observations are pinned by `tests/test_acs_h1_findings.py`, so the prose above cannot drift from the committed results without a test failing.

---

## 6.10 H3: Utility-Weighted Budget Allocation

D5 was closed by running H3 on both datasets under the same protocol as H1: 5 epsilon values, 5 seeds, and a paired design in which the two arms differ **only** in how a fixed total budget is split across columns.

**Where the weights come from, because that is the whole design question**: They are *declared*, not measured. The analyst names the columns they care about — for Adult, `income`, `education`, `hours_per_week`, `occupation` — and those columns receive weight 4 while every other column keeps weight 1. That declaration is public metadata, exactly like the schema's numeric bounds, and so costs nothing.

Deriving the weights from the data instead — mutual information with the target, a feature-importance run, anything measured — would be a data-dependent parameter choice made with an uncharged query, and every epsilon reported here would be a false statement. That version of H3 is not testable at any budget and was not run.

**How the split is priced**: `calibrate_weighted_scales` fixes the *shape* of the allocation analytically (for Gaussian mechanisms under RDP the per-query cost goes as `1/scale^2`, so a column of weight `w` takes `scale ∝ 1/sqrt(w)`) and then finds its *size* by bisecting against the accountant, exactly as the scalar calibration does. No epsilon in this section is computed by hand. Two properties are asserted by test rather than assumed: a uniform weight vector reproduces the scalar calibration to within tolerance, and the weighted arm never composes to more than the uniform arm. The second matters most — a weighted arm that quietly overspent would manufacture a utility gain out of extra privacy loss.

### Result: Not Supported, on Either Dataset

**UCI Adult** — TSTR macro F1, paired weighted-minus-uniform gap with 95% bootstrap CI:

| Target ε | Uniform F1 | Weighted F1 | Gap [95% CI] | Supports H3 |
|---:|---:|---:|---|---|
| 0.5 | 0.4314 | 0.4493 | +0.0179 [-0.1142, +0.1145] | no |
| 1.0 | 0.4160 | 0.4333 | +0.0173 [-0.0268, +0.0519] | no |
| 2.0 | 0.3983 | 0.4289 | +0.0305 [-0.0136, +0.0857] | no |
| 4.0 | 0.4663 | 0.4427 | -0.0236 [-0.0549, +0.0076] | no |
| 8.0 | 0.4698 | 0.4749 | +0.0051 [-0.0266, +0.0486] | no |

**ACSIncome (CA 2018)**:

| Target ε | Uniform F1 | Weighted F1 | Gap [95% CI] | Supports H3 |
|---:|---:|---:|---|---|
| 0.5 | 0.4753 | 0.4796 | +0.0043 [-0.0070, +0.0149] | no |
| 1.0 | 0.4850 | 0.4828 | -0.0023 [-0.0115, +0.0073] | no |
| 2.0 | 0.4829 | 0.4869 | +0.0040 [-0.0184, +0.0265] | no |
| 4.0 | 0.4871 | 0.4854 | -0.0016 [-0.0148, +0.0147] | no |
| 8.0 | 0.4893 | 0.4873 | -0.0021 [-0.0142, +0.0076] | no |

At none of the ten dataset-epsilon combinations does the paired gap have an interval excluding zero. On Adult the point estimates are mixed in sign (three positive, two negative) and the intervals are wide; on ACS the gaps are smaller still ($|\text{gap}| \le 0.004$) with tighter intervals, which is the stronger null of the two.

**Reading it honestly**: This is a null about *this mechanism*, not about budget allocation in general. The independent-marginal generator measures one 1-way marginal per column and samples each column independently, so a better-measured marginal on the target improves that column's own distribution and nothing else — there is no cross-column structure for the extra budget to sharpen. The result is therefore consistent with the mechanism's design, and the interesting version of H3 would repeat it on `pairwise` or `aim`, where budget could be steered toward *cliques* rather than columns. That is stated as future work rather than claimed here.

---

## 6.11 Subgroup Utility Fairness and Linkability Protocols

To complement the core H1–H3 hypotheses, two additional empirical evaluations were conducted in response to regulatory requirements:

### Subgroup Utility Fairness (`scripts/run_fairness.py`)
To test whether differential privacy disproportionately degrades downstream utility for protected demographic subgroups, predictive models trained under TSTR are evaluated across subgroup slices:
- Evaluated across 2 demographic attributes (`sex` and `race`), 2 privacy regimes ($\varepsilon \in \{1.0, 8.0\}$), and 3 random seeds per cell.
- Fairness metrics include demographic parity differences and equalized odds gaps between majority and minority cohorts.
- Crucially, an unperturbed control baseline (TRTR) is evaluated concurrently. This control established that while the observed accuracy gap on `sex` reflects privacy noise distortion, the apparent accuracy gap on `race` was already present in the underlying training data, demonstrating that baseline controls are mandatory to avoid misattributing societal disparities to privacy mechanisms.

### Linkability Attack Protocol (`synthproof/attacks/linkability.py`)
To satisfy EDPB requirements regarding the linkability of disjoint releases, we implement bipartite split-attribute linkage. The attribute schema is partitioned into two disjoint subsets $\mathcal{S}_A$ and $\mathcal{S}_B$, released as separate synthetic tables $\widetilde{D}_A$ and $\widetilde{D}_B$. The adversary attempts to reconstruct the original joint records by computing nearest-neighbor bipartite matching across common quasi-identifiers. Linkage success is scored against a random guessing baseline, quantifying the empirical resistance of differentially private mechanisms to multi-release correlation attacks.
