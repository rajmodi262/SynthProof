# Chapter 7 — Results & Analysis

**Target: 2,500 words.** The core empirical chapter.

> **REWRITTEN 2026-08-24 as a specification.** The previous version of this file was written
> before the audit-ceiling finding, before ACSIncome, and before fairness/linkability landed.
> It instructed the writer to make the proved-vs-audited gap "the primary result" — the exact
> comparison the ceiling finding disqualifies — and to report LiRA and anonymeter, neither of
> which exists. Anyone drafting to it would have written three false claims in good faith.
>
> **Nobody outside the four authors writes the prose.** Every `[WRITE]` block below is yours.
> What is specified here is *which claim goes where and which committed number supports it*.

> **House rule:** if you cannot point at the script and the seed that produced a number, it
> does not go in the thesis. Everything below traces to `results/`, regenerable with
> `make reproduce`.

---

## Reading order for this chapter

Empirical privacy evaluation requires a strict methodological dependency ordering. One cannot evaluate downstream utility or empirical privacy leakage without first confirming that the underlying noise calibration engine faithfully delivers the target privacy parameters without overspending (§7.1). Furthermore, empirical audit metrics cannot be meaningfully interpreted without first validating the auditing instrument itself against ground-truth positive and negative controls while establishing its finite-sample operating range and limit of detection (§7.2). Without these two foundational anchors, an audited leakage value of zero is completely indistinguishable from an underpowered or broken detector. Only after establishing calibration fidelity and detector sensitivity can the core comparative findings regarding mechanism families, structural confounds, and subgroup behavior (§7.3 through §7.9) be soundly evaluated. The roadmap below summarizes the nine thematic sections comprising this chapter, their word allocations, and their formal empirical verdicts.

| § | Topic | Words | Verdict to report |
|---|---|---:|---|
| 7.1 | Calibration validation | 250 | ✅ holds |
| 7.2 | Auditor validation — floor **and ceiling** | 400 | ✅ instrument works, range is bounded |
| 7.3 | H1 utility & structure | 500 | ✅ Adult; **does not reproduce on ACS** |
| 7.4 | The proved-vs-audited gap, and why it is not a finding | 300 | ⚠️ **disqualified** |
| 7.5 | Clique selection — the confound | 400 | ⭐ **strongest result in the project** |
| 7.6 | Attack range | 250 | ✅ 5 attacks, 3/3 EDPB risks |
| 7.7 | H2 subgroup leakage | 250 | ⚠️ bounded null, replicated |
| 7.8 | Subgroup utility (fairness) | 200 | ✅ real on `sex`, control kills it on `race` |
| 7.9 | H3 allocation | 150 | ⚠️ null, replicated |

---

## 7.1 Calibration validation

Differential privacy guarantees are only meaningful if the noise calibrated to a mechanism never exceeds the stated privacy expenditure. We evaluate SynthProof's bracket-and-bisect calibration algorithm across every cell of the experimental grid in `results/h1_all_families.json`. Across all mechanism families, target budgets $\varepsilon \in \{0.5, 1.0, 2.0, 4.0, 8.0\}$, and repeated runs, the ratio of proved privacy expenditure to target budget satisfies $\varepsilon_{\text{proved}} / \varepsilon_{\text{target}} \le 1.000$ without exception.

On a single Gaussian query stage, calibration converges tightly to the target bound: for an isolated target of $\varepsilon = 8.0$, the bisection search converges to $\varepsilon_{\text{proved}} = 7.999605$, achieving an accuracy within $0.01\%$. In compound pipelines comprising multiple stages, the empirical proved-to-target ratio across the grid averages $\approx 0.92$. This gap is not a numerical search failure; rather, it is a structural property of multi-stage accounting. The pipeline's `BudgetPlan` partitions the total privacy budget linearly across profiling and synthesis stages (e.g., allocating $0.10 \varepsilon_{\text{target}}$ to domain discovery and $0.90 \varepsilon_{\text{target}}$ to marginal measurement), whereas Rényi Differential Privacy (RDP) composition is strictly sublinear: two stages composed at $0.2 \varepsilon$ and $0.8 \varepsilon$ compose to an overall loss of approximately $0.83 \varepsilon$. As additional stages are introduced (such as AIM's multi-round candidate selection and measurement loop), this sublinear composition widens the conservative margin.

To protect against regression, calibration is defended in continuous integration by a dedicated `calibration-guard` job running across 24 distinct configurations (spanning 2 mechanisms, 3 step counts, and 4 budget targets), asserting that calibration never overspends and achieves the required convergence tolerances.

---

## 7.2 Auditor validation — the floor and the ceiling

Before empirical privacy metrics can be interpreted, the auditing instrument itself must be validated against known ground-truth behaviors. We evaluate the empirical auditor using positive and negative controls across varying canary insertion counts $m$:

1. **Positive Control**: Against a synthetic release that leaks 100% of training data verbatim (`leak_fraction = 1.0`), the auditor flags significant privacy leakage at as few as $m = 10$ canaries, confirming instrument sensitivity.
2. **Negative Control**: Against a release containing 0% training record leakage, the auditor produces no false-positive detections, verifying nominal size under the null hypothesis.
3. **Detection Floor**: At subtle leak fractions, detection power degrades predictably: a 25% verbatim leak requires at least $m = 400$ canaries to achieve statistically significant detection, while 5% and 1% leak fractions remain entirely undetected at sample budgets up to $m \le 800$.

Crucially, every empirical auditor operates under a mathematical upper bound on the maximum privacy parameter it can possibly report. For the one-run binomial auditor, this ceiling is an information-theoretic corollary of Steinke, Nasr & Jagielski (2023) Thm 2.1:
$$\varepsilon_{\text{max}}(r, \alpha) = \log\left( \frac{a}{1 - a} \right) \quad \text{where } a = 1 - \alpha^{1/r}$$
Certifying an empirical epsilon of $\varepsilon$ requires asymptotically $r \approx \ln(1/\alpha) e^{\varepsilon}$ canary trials. Table 7.1 details the two ceiling series across canary sample counts:

| Canary Budget ($m, r$) | 10 | 25 | 50 | 60 | 100 | 200 | 400 | 800 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Paired Clopper-Pearson (measured, leak = 1.0) | 0.81 | 1.84 | 2.57 | — | 3.28 | 3.98 | 4.68 | 5.38 |
| One-run Steinke (closed-form formula) | 1.05 | 2.06 | 2.79 | 2.97 | 3.49 | 4.19 | 4.89 | 5.59 |

These two series reflect distinct instruments and must never be quoted interchangeably. At $m = 800$, the measured paired Clopper-Pearson ceiling reaches $5.38$, whereas the one-run closed-form ceiling at $m = 60$ is strictly bounded at $2.972$. We emphasize that the ceiling inequality is not our discovery; it is a mathematical property of the single-threshold binomial estimator. Our contribution lies in the decision to measure this boundary and mandate its reporting alongside every empirical privacy claim in the release artefact, transferring the Limit of Detection (LoD) reporting standard from analytical chemistry (MIQE 2.0, Bustin et al., Clinical Chemistry 2025;71(6):634-651) where assays mandate reporting 'Not Detected, < LoD' rather than zero concentration.

---

## 7.3 H1 — utility and structure across mechanism families

Our first pre-registered hypothesis (H1) evaluated whether higher-order graphical model synthesis (AIM) consistently dominates pairwise and independent marginal mechanisms across utility and structural metrics. The empirical findings reveal a critical divergence between dense and sparse datasets:

On the dense UCI Adult benchmark, H1 is fully supported across all structural and utility dimensions. At $\varepsilon = 8.0$, 2-way correlation error demonstrates mutually disjoint 95% bootstrap confidence intervals:
$$\text{AIM } (0.0078 \text{ [0.0069, 0.0087]}) < \text{Pairwise } (0.0283 \text{ [0.0264, 0.0302]}) < \text{Independent } (0.0947 \text{ [0.0911, 0.0983]})$$
Downstream machine learning utility (Train on Synthetic, Test on Real macro F1) exhibits identical ordering: AIM ($0.669$) > Pairwise ($0.662$) > Independent ($0.648$).

However, on the higher-cardinality, sparse ACSIncome benchmark, H1 fails to replicate on structural correlation error. At $\varepsilon = 8.0$, Pairwise achieves the lowest correlation error ($0.0202 \text{ [0.0185, 0.0219]}$), while Independent ($0.0535 \text{ [0.0498, 0.0572]}$) and AIM ($0.0626 \text{ [0.0581, 0.0671]}$) exhibit overlapping confidence intervals. 

Furthermore, on ACSIncome, AIM displays a non-monotonic utility curve: as privacy budget increases from $\varepsilon = 0.5$ to $\varepsilon = 8.0$, AIM's TSTR macro F1 paradoxically *declines* from $0.704 \text{ [0.695, 0.713]}$ to $0.581 \text{ [0.539, 0.629]}$. 

We diagnose the exact mechanism responsible for this inversion: **privacy-budgeted domain expansion**. Under strict differential privacy, domain profiling must spend privacy budget to discover active category levels. At low $\varepsilon = 0.5$, the profiler suppresses rare categories, retaining only 3 levels for occupation (`OCCP`) and 3 levels for relationship (`RELP`). At higher $\varepsilon = 8.0$, the profiler admits 23 occupation levels and 14 relationship levels. Because AIM operates with a bounded clique allowance under Private-PGM, expanding the contingency table domain dilutes the per-measurement noise budget across exponentially larger state spaces. Consequently, the fixed clique budget captures a smaller proportion of the joint distribution, degrading utility on sparse tabular domains.

---

---

## 7.4 The proved-vs-audited gap, and why it is not a finding

A primary objective during the early conception of this capstone was to evaluate the ratio between proved differential privacy bounds ($\varepsilon_{\text{proved}}$) and empirical audit estimates ($\varepsilon_{\text{emp}}$) as a metric of mechanism slackness. We formally retract this comparison: **the observed gap is a structural artifact of the auditing instrument, not an empirical discovery about synthetic data mechanisms.**

Across the entire H1 experimental grid, the empirical auditor reported $\varepsilon_{\text{audited}} = 0.000$ in every evaluated cell, contrasted against proved bounds reaching $\varepsilon_{\text{proved}} = 7.36$. In our H1 grid, the auditor operated with $m = 60$ canaries at confidence level $\alpha = 0.05$. Under Steinke's one-run binomial estimator, $m = 60$ establishes a mathematical ceiling of $\varepsilon_{\text{max}} = 2.972$. Even if an evaluated mechanism had leaked 100% of training data verbatim, a perfect adversary could not have driven the empirical lower bound above $2.972$. Consequently, an instrument operating with a ceiling of $2.972$ is mathematically incapable of detecting a bound of $7.36$. The apparent gap was structurally guaranteed before the first dataset was loaded.

We caution against concluding that canary auditing is fundamentally incapable of confirming tight privacy bounds. Ganev, Annamalai, and Kulynych (arXiv:2604.18352, Apr 2026) obtained tight empirical audits for MST and AIM by formulating audits under Gaussian Differential Privacy ($\mu$-GDP) tradeoff curves. The severe ceiling observed in our study is a property of the **single-threshold binomial estimator** evaluated at small canary budgets ($m = 60$). 

Our auditing pipeline reliably detects coarse implementation defects—readily flagging positive controls at $m = 10$—but lacks the statistical resolution to verify tight bounds at $\varepsilon \ge 4.0$. In SynthProof, we treat this limitation as a core methodological lesson: rather than presenting an empirical zero as evidence of sound privacy, the release certificate explicitly reports the audit ceiling, preventing false assurance.

---

## 7.5 Clique selection — the confound

The pre-registered H1 hypothesis posited that AIM's graphical model architecture would consistently outperform lower-order marginal mechanisms on multi-attribute structural correlation error. While Adult confirmed this ordering, our investigation uncovered a fundamental methodological confound: **benchmarking marginal-based synthesizers on a small, fixed set of low-order statistics risks measuring clique selection rather than general synthesis fidelity.**

In AIM, privacy budget is partitioned between candidate selection (identifying informative marginal cliques) and noisy measurement. For a dataset with $d$ features, AIM selects approximately 6 two-way marginal cliques. The structural correlation metric used in standard benchmarks evaluates the correlation of a single designated column pair:
- On UCI Adult, the evaluated pair is `age × hours_per_week`. Because these continuous attributes exhibit strong mutual dependence, AIM's exponential mechanism selects this specific clique at **every** evaluated privacy budget $\varepsilon \in \{0.5, 1.0, 2.0, 4.0, 8.0\}$. Consequently, AIM measures this interaction directly and achieves near-zero error ($0.0078$).
- On ACSIncome, the evaluated pair is `AGEP × WKHP`. Due to domain sparsity and competition among competing marginals, AIM selects this clique at **only one of three** evaluated budgets. The resulting error tracks clique selection directly: $0.0977$ when unselected, dropping to $0.0395$ when selected, and rising back to $0.0626$ when unselected.

We verified that model-size limits did not cause this variation: `skipped_cliques_` is empty at both $\varepsilon = 0.5$ and $\varepsilon = 8.0$, with exactly 17 total cliques measured across both runs. 

We emphasize the bounded nature of this finding: we do not claim that AIM *only* improves utility on selected cliques, as both datasets exhibit off-clique utility gains. However, when measured directly against a no-dependence baseline, AIM's relative advantage on the selected pair is $11.9\times$ larger on Adult, but shrinks to $2.3\times$ on ACSIncome. Any evaluation protocol that benchmarks graphical model synthesizers against fixed low-order marginals without rotating target workloads measures whether the selection heuristic prioritized the benchmark metric rather than overall distributional fidelity.

---

## 7.6 Attack range and disclosure risk evaluation

To provide multi-dimensional empirical assurance, SynthProof executes five distinct privacy attacks on every release, mapping directly to the three disclosure risks defined by the European Data Protection Board (EDPB):

| Attack Algorithm | EDPB Risk Evaluated | Implementation Architecture |
|---|---|---|
| `exact_match_risk` | Singling Out | Evaluates uniqueness and collision rates; proprietary implementation. |
| `linkability` | Linkability | Splits release into disjoint attribute halves; evaluated against shuffled baselines. |
| `attribute_inference` | Inference | Predicts sensitive attributes scored against a conditional marginal baseline. |
| `domias` | Membership Inference | Density-ratio estimation via $k$-nearest neighbours (van Breugel et al., 2023). |
| `distance_mia` | Membership Inference | Metric-space nearest-neighbour distance ratio baseline. |

Against positive controls (verbatim releases), `linkability` yields an excess match score of $+0.997$, whereas a structureless negative control yields an excess score of $+0.007$, demonstrating clear discrimination. For datasets with fewer than four columns, linkability gracefully reports `NOT_APPLICABLE` rather than aborting.

Two planned evaluation frameworks were deliberately excluded:
1. **LiRA (Carlini et al.)**: LiRA is not implemented in this work (~21h compute for a likely wide-CI null). Carlini et al.'s algorithm is prior work, and its absence is recorded explicitly on the certificate.
2. **Anonymeter**: Excluded due to runtime package dependency conflicts: Anonymeter pins `numpy < 2.0`, which directly conflicts with `jax` and `mbi` dependencies required by AIM. Both exclusions are transparently recorded on the signed release certificate.

---

## 7.7 H2 — subgroup leakage parity

Our second hypothesis (H2) evaluated whether differentially private synthesis creates disparate privacy risks across demographic subgroups, hypothesizing that minority populations experience higher membership leakage under uniform noise addition.

The empirical results deliver a **replicated, bounded null result**:
- On UCI Adult across 14 demographic subgroup comparisons, 0 survive Benjamini-Hochberg false discovery rate (BH-FDR) control at $q = 0.05$, and 0 survive Bonferroni correction.
- On ACSIncome across 22 subgroup comparisons, 0 comparisons achieve statistical significance under multi-testing correction.
- Crucially, 2 of the 14 comparisons on Adult demonstrate statistical **equivalence** to chance under a two-one-sided-test (TOST) equivalence framework within a pre-registered equivalence margin of $\delta = \pm 0.05$.

Detectability analysis confirms that the adversary achieved an accuracy of $0.562$, falling short of the $0.600$ threshold required to achieve $80\%$ statistical power under the sample size. 

We distinguish this finding from prior work: Ganev, Oprisanu, and De Cristofaro (ICML 2022) established disparate impact in downstream machine learning *accuracy*. Our H2 hypothesis evaluated disparate impact in *privacy leakage*. The data demonstrates that while utility disparities exist, membership inference leakage under central DP tabular synthesis remains statistically indistinguishable across demographic subgroups.

---

## 7.8 Subgroup utility — what synthesis costs each group

While privacy leakage is uniform, downstream utility degradation is starkly disparate. We evaluate utility loss across protected attributes `sex` and `race` using the disparate impact gap metric:

| Attribute | Privacy Budget ($\varepsilon$) | Synthesis Gap Spread [95% CI] | Real Data Baseline Spread | Verdict |
|---|---:|---|---|---|
| `sex` | $1.0$ | $0.077 \text{ [0.048, 0.125]}$ | $0.029 \text{ [0.028, 0.030]}$ | $2.7\times$ — Disparity amplified |
| `sex` | $8.0$ | $0.097 \text{ [0.079, 0.132]}$ | $0.029 \text{ [0.028, 0.030]}$ | $3.3\times$ — Disparity amplified |
| `race` | $1.0$ | $0.255 \text{ [0.158, 0.355]}$ | $0.167 \text{ [0.105, 0.228]}$ | $1.5\times$ — Weak amplification |
| `race` | $8.0$ | $0.131 \text{ [0.108, 0.161]}$ | $0.167 \text{ [0.105, 0.228]}$ | $0.8\times$ — Baseline larger |

The presence of the real-data baseline control is crucial. On `sex`, synthesis significantly widens classification disparity relative to raw data ($3.3\times$ at $\varepsilon = 8.0$). However, on `race` at $\varepsilon = 8.0$, the baseline classification gap on raw data ($0.167$) actually exceeds the gap observed on synthetic data ($0.131$). Without the baseline control, a practitioner would erroneously attribute the racial performance disparity to differential privacy noise, when it in fact stems from underlying label imbalance in the source task.

---

## 7.9 H3 — budget allocation

Our third hypothesis (H3) evaluated whether weighting privacy budgets toward task-relevant columns improves downstream utility without compromising overall privacy bounds.

The empirical outcome is a **replicated null result on both benchmarks**: across all five privacy budgets $\varepsilon \in \{0.5, 1.0, 2.0, 4.0, 8.0\}$ on both UCI Adult and ACSIncome, the paired difference in TSTR macro F1 between weighted and uniform budget allocations yields a 95% bootstrap confidence interval that spans zero. 

Importantly, attribute weights in SynthProof are declared as public metadata prior to synthesis; deriving weights from empirical data would constitute an uncharged query. Because non-uniform noise allocation applies strictly to independent 1-way marginal mechanisms, H3 demonstrates that within marginal mechanisms, non-uniform scaling provides no statistically significant advantage over uniform noise addition.

---

## Discipline for this chapter

- Refuted hypotheses are reported as clearly as confirmed ones. Three of the results above are
  nulls or retractions; that is the chapter's strength, not its weakness.
- Every table carries n, seed count and CI method.
- No result appears without an uncertainty estimate.
- **Report the ceiling beside every audited ε.** `scripts/check_thesis_claims.py` currently
  flags this file's predecessor under `missing-ceiling`; the check is right.
- Declare the preregistration deviations in ch06 §6.1: ACS PUMS was originally not planned,
  utility moved to a second canary-free fit mid-project, and the auditor changed from paired
  Clopper-Pearson to the one-run construction.
