# Reproducibility at the Cost of Secrecy: How Machine Learning Metadata Compromises Differential Privacy in Synthetic Data Releases

**Target Venue:** Proceedings on Privacy Enhancing Technologies (PoPETs) / ACM Conference on Computer and Communications Security (CCS)  
**Authors:** SynthProof Research Team  
**Date:** September 2026  
**Artifact Codebase:** `https://github.com/capstone-synthproof/SynthProof`

---

## Abstract

Differential Privacy (DP) mathematically bounds information leakage by injecting calibrated randomness over an algorithm's internal coin flips. Concurrently, modern machine learning (ML) governance demands complete deterministic reproducibility, codifying the publication of pseudo-random generator (PRNG) seeds, exact record counts, and execution parameters in dataset documentation standards such as MLCommons Croissant and Model Cards. In this paper, we uncover a fundamental socio-technical collision between these paradigms: the **Metadata Boundary Paradox**.

We demonstrate that publishing the PRNG seed in release metadata converts a randomized differential privacy mechanism into a deterministic function, allowing an adversary with candidate records to execute an algebraic replay attack that achieves a 100% accurate membership oracle—completely nullifying theoretical $(\varepsilon, \delta)$ guarantees. We examine established machine learning dataset documentation formats (MLCommons Croissant, Model Cards, Datasheets) and find that none of them account for this vulnerability or provide mechanisms to lint release metadata for non-epsilon side channels.

To reconcile reproducibility with privacy without requiring data consumers to access proprietary training code or private raw data, we present **SynthProof**: an asymmetric static release-boundary auditor and cryptographic verification framework. SynthProof formalizes the *Asymmetry Principle* for post-release inspection, detects non-epsilon side channels in published JSON-LD manifests in under 50ms, and cryptographically binds claims via Ed25519 signatures paired with MIQE 2.0-adapted Limit-of-Detection (LoD) operating ceilings. Our work provides the missing gatekeeper between theoretical privacy mechanisms and real-world metadata dissemination.

---

## 1. Introduction

Differential Privacy (DP) [Dwork et al. 2006, Dwork & Roth 2014] has emerged as the mathematical gold standard for sharing synthetic tabular data derived from sensitive records. By bounding the privacy loss parameter $\varepsilon$, data custodians guarantee that no individual record disproportionately affects the output distribution.

Simultaneously, the machine learning community has undergone a reproducibility revolution. Leading conferences (NeurIPS, ICML), regulatory bodies, and industry consortia (MLCommons) mandate rigorous reproducibility standards. Frameworks like **Croissant** [Akhtar et al. 2024], **Datasheets for Datasets** [Gebru et al. 2021], and **Model Cards** [Mitchell et al. 2019] urge practitioners to publish complete execution environments, hyperparameters, and random seeds (`random_state=42`) to enable exact verification of results.

### The Core Vulnerability: The Metadata Paradox
These two well-intentioned disciplines are operating on a direct collision course:
1. **Differential Privacy requires randomness secrecy:** The privacy guarantee holds *if and only if* the internal random coins $r \sim \mathcal{R}$ remain unobserved by the adversary [Dwork & Roth 2014, Def. 2.4; Dodis et al., CRYPTO 2012].
2. **ML Metadata standards encourage randomness disclosure:** Publishing execution manifests containing PRNG seeds is considered best practice.

When a synthetic data release publishes both the dataset and the generator's random seed, the mechanism ceases to be a randomized mapping. It collapses into a **deterministic identity function**. An adversary armed with candidate data does not need complex statistical machine learning or shadow models [Carlini et al. 2021, Stadler et al. 2022]; they simply replay the generator with the published seed. If the candidate record yields the released synthetic artifact, membership is confirmed with **100% precision**.

### Our Contributions:
1. **The Metadata Boundary Paradox:** We identify the inherent conflict between machine learning reproducibility standards (mandating seed disclosure) and differential privacy (mandating randomness secrecy). We formalize the algebraic collapse under seed disclosure and validate it empirically, achieving 15/15 exact matches and 0/15 false positives on benchmark releases certified at $\varepsilon = 1.0$.
2. **Metadata Specification Case Study:** We analyze prominent machine learning dataset documentation specifications (MLCommons Croissant, Google Model Cards, Hugging Face dataset cards), demonstrating that none of these specifications define constraints or linters against random seed publication or row-count side channels.
3. **The SynthProof System:** We design and implement `boundary-audit`, an asymmetric static release-boundary linter operating under the formal *Asymmetry Principle*, combined with Ed25519 cryptographic tamper-proofing and clinical metrology-inspired (MIQE 2.0) Limit of Detection (LoD) operating ceilings.

---

## 2. Threat Model & Mathematical Formulation

### 2.1 Standard Differential Privacy
Let $\mathcal{X}$ denote the universe of data records, and $\mathcal{D} = \mathcal{X}^n$ denote a dataset. Two datasets $D, D' \in \mathcal{D}$ are *neighbours* ($D \sim D'$) if they differ by at most one individual record.

**Definition 1 (Differential Privacy, Dwork & Roth 2014).** A randomized algorithm $\mathcal{M}: \mathcal{D} \times \mathcal{R} \to \mathcal{Y}$ with internal randomness space $(\mathcal{R}, \mu)$ satisfies $(\varepsilon, \delta)$-differential privacy if for all neighbouring $D \sim D'$ and all measurable subsets $\mathcal{S} \subseteq \mathcal{Y}$:
$$\Pr_{r \sim \mu}[\mathcal{M}(D; r) \in \mathcal{S}] \le e^\varepsilon \Pr_{r \sim \mu}[\mathcal{M}(D'; r) \in \mathcal{S}] + \delta$$

Crucially, the probability measure $\Pr$ is evaluated **exclusively over the internal coin tosses $r \in \mathcal{R}$**.

### 2.2 The Conditional Collapse
Consider an adversary $\mathcal{A}$ who observes the released synthetic data $Y = \mathcal{M}(D; r)$ and the published metadata $\Phi$. Suppose $\Phi$ contains the PRNG seed $r^*$.

**Observation 1 (Conditional Determinism).** *Let $\mathcal{M}$ be a deterministic function conditioned on fixed randomness $r^*$: $\mathcal{M}_{r^*}(D) = \mathcal{M}(D; r^*)$. For any candidate dataset $D$ and neighbour $D' \ne D$ where $\mathcal{M}(D; r^*) \ne \mathcal{M}(D'; r^*)$, setting $\mathcal{S} = \{\mathcal{M}(D; r^*)\}$ yields:*
$$\Pr[\mathcal{M}_{r^*}(D) \in \mathcal{S}] = 1, \quad \Pr[\mathcal{M}_{r^*}(D') \in \mathcal{S}] = 0$$
*The empirical privacy loss evaluates to $\ln(1/0) = \infty$, reducing differential privacy to a deterministic lookup.*

While this consequence follows directly from Definition 1, standard machine learning pipelines routinely serialize random state parameters alongside data artifacts without recognizing this vulnerability.

---

## 3. Empirical Exploit Validation: Algebraic Replay

To validate that seed disclosure translates into an empirical vulnerability, we implemented an algebraic seed replay probe on standard tabular synthesis pipelines.

### Experimental Setup:
- **Baseline Dataset:** US Census Adult and Bank Marketing benchmarks ($N = 1,000$ to $N = 30,000$).
- **Theoretical Guarantee:** $\varepsilon = 1.0, \delta = 10^{-5}$ via Gaussian noise.
- **Attack Implementation:** The adversary receives candidate records and the published metadata card containing `random_state: 42`. The adversary simulates synthesis under candidate subsets and computes exact string-matching hashes against the published synthetic table.

### Results:
| Evaluation Metric | Statistical MIA (Shadow Models) | SynthProof Algebraic Replay Attack |
|---|:---:|:---:|
| **Adversary Computation Time** | 45.2 seconds (training 10 shadow models) | **0.018 seconds (deterministic replay)** |
| **True Member Identification** | 58.4% ROC-AUC | **100.0% Exact Match (15/15)** |
| **False Positive Neighbour Rate** | 12.1% | **0.0% (0/15)** |
| **Bypassed $\varepsilon = 1.0$ Guarantee?** | No (bounded by $e^\varepsilon$) | **YES ($\varepsilon_{empirical} = \infty$)** |

**Takeaway:** Statistical membership inference attacks (MIA) are bounded by $\varepsilon$, but seed disclosure renders statistical bounds irrelevant: membership testing becomes an exact equality lookup.

---

## 4. Analysis of Metadata Specifications

We analyzed prominent machine learning dataset documentation specifications to evaluate whether release-boundary side channels are addressed:

1. **MLCommons Croissant (Akhtar et al., SIGMOD 2024):** The official Croissant validator (`mlcroissant.validate`) inspects JSON-LD graph structure and Schema.org syntax. It contains no rules flagging PRNG seed attributes (`seed`, `random_state`) or exact record counts in dataset descriptions.
2. **Datasheets for Datasets (Gebru et al., CACM 2021):** Focuses on qualitative socio-technical context (collection motivation, demographic representation), with no automated technical linter for cryptographic leakage.
3. **Model Cards (Mitchell et al., FAT* 2019):** Encourages reporting hyperparameters and random seeds for reproducibility, directly incentivizing the practice that compromises DP releases.

---

## 5. The SynthProof System Architecture

SynthProof addresses this vulnerability by acting as a **static release-boundary gatekeeper**. Crucially, SynthProof operates **asymmetrically**: it requires zero access to private training data, model parameters, or source code.

```
┌───────────────────────────────┐
│     Published Data Package    │
│  (Synthetic CSV + Metadata)   │
└──────────────┬────────────────┘
               ▼
┌───────────────────────────────┐
│         boundary-audit        │  <-- Static Data-Blind Linter
│   (Checks 5 Side Channels)    │      Runs in < 50ms
└──────────────┬────────────────┘
               │
      [Passes All Checks?]
         │              │
        YES             NO ──► [EMIT FATAL ALERT] (Reject Release)
         ▼
┌───────────────────────────────┐
│   Ed25519 Signature Engine    │  <-- Cryptographic Tamper-Proofing
│   (Binds Data Hash to Claims) │
└──────────────┬────────────────┘
               ▼
┌───────────────────────────────┐
│   MIQE 2.0 Metrology Gauge    │  <-- Limit of Detection (LoD)
│   (Calculates Audit Ceiling)  │      Flags "Privacy Theater"
└───────────────────────────────┘
```

### 5.1 The Asymmetry Principle
We formalize the theoretical limitation and capability of static release auditing:
- **Proposition 1 (Provable Leakage):** A static boundary linter can *prove* a release is insecure by exhibiting an open side channel $\kappa \in \{\text{PRNG Seed}, \text{Exact } N, \text{Unkeyed Hash}\}$.
- **Proposition 2 (Unverifiable Privacy):** A static boundary linter *cannot prove* a release is differentially private solely from documentation. A clean manifest could theoretically accompany an unperturbed raw table.

SynthProof surfaces this asymmetry explicitly, preventing data custodians from misinterpreting a successful lint as a mathematical privacy certificate.

### 5.2 Cryptographically Signed Claims
Unlike static JSON privacy labels, SynthProof binds the release metadata, boundary audit report, and dataset SHA-256 hash into an Ed25519 asymmetric signature. Any post-release alteration of claimed $\varepsilon$ immediately invalidates the signature.

### 5.3 MIQE 2.0 Limit-of-Detection (LoD) Metrology
Borrowing from molecular diagnostics [Bustin et al., Clinical Chemistry 2009, 2025; Forootan et al. 2017], SynthProof computes the minimum detectable privacy leak given empirical sample size $N_{audit}$:
$$\varepsilon_{LoD} = \frac{z_{1-\alpha} + z_{1-\beta}}{\sqrt{N_{audit}}}$$
If an auditor tests synthetic data with $N=100$ and claims $\varepsilon_{empirical} = 0.05$, SynthProof flags the claim as uncalibrated because the assay operates below its statistical detection limit.

---

## 6. Benchmarks & System Performance

We evaluated the performance of SynthProof on standard commodity hardware (Intel Core i7, 16GB RAM):
- **Linter Latency:** Average execution time across 100 metadata manifests is **14.2 milliseconds** (standard deviation: 2.1ms).
- **Cryptographic Signing Overhead:** Ed25519 signature generation and verification takes **1.8 milliseconds**.
- **Test Coverage:** All 13 core boundary-audit unit tests pass with 95% code coverage.

---

## 7. Related Work

- **DP Tabular Synthesis:** PrivBayes [Zhang 2017], PATE-GAN [Jordon 2018], AIM [McKenna 2021], CTAB-GAN+ [Zhao 2024], and TabDDPM [Kotelnikov 2022] optimize fidelity and noise mechanisms, but assume external release boundaries are secured.
- **Algorithmic Auditing:** StatDP [Ding 2018], DP-Finder [Bichsel 2018], and Cebere et al. [2026] audit library implementations using dynamic execution tracing. SynthProof is complementary: it audits release artifacts data-blind.
- **Output Checking:** SACRO / ACRO [Ritchie 2023, Preen 2025] monitors interactive statistical queries in Trusted Research Environments. SynthProof extends disclosure control to bulk static dataset releases.
- **Documentation Standards:** Croissant [Akhtar 2024], Model Cards [Mitchell 2019], and DP Labels [Dibia 2026] define metadata taxonomy, but lack automated side-channel verification rules.

---

## 8. Conclusion

Machine learning reproducibility and differential privacy are both essential pillars of trustworthy AI, but without deliberate boundary engineering, reproducibility mandates directly subvert privacy guarantees. SynthProof resolves this paradox through automated static linting, cryptographic signatures, and metrology-calibrated privacy reporting.

---

## References

1. M. Akhtar et al., "Croissant: A Metadata Format for ML-Ready Datasets," *ACM SIGMOD*, 2024.
2. S. A. Bustin et al., "MIQE 2.0: Revision of the Minimum Information for Publication of Quantitative Real-Time PCR Experiments Guidelines," *Clinical Chemistry*, vol. 71, no. 1, 2025.
3. N. Carlini et al., "Membership Inference Attacks From First Principles," *IEEE S&P*, 2022.
4. B. Cebere, B. Erb, D. Desfontaines, A. Bellet, and M. Fitzsimons, "Privacy in Theory, Bugs in Practice: Systematic Grey-Box Auditing of Differential Privacy Libraries," *Proceedings on Privacy Enhancing Technologies (PoPETs)*, 2026.
5. O. Dibia, M. Lu, P. Bhattacharjee, J. P. Near, and X. Feng, "‘We Need a Standard’: Toward an Expert-Informed Privacy Label for Differential Privacy," *Proceedings on Privacy Enhancing Technologies (PoPETs)*, 2026.
6. Y. Dodis, A. López-Alt, I. Mironov, and S. Vadhan, "Differential Privacy with Imperfect Randomness," *CRYPTO*, LNCS vol. 7417, pp. 497–514, 2012.
7. C. Dwork and A. Roth, "The Algorithmic Foundations of Differential Privacy," *Foundations and Trends in Theoretical Computer Science*, 2014.
8. S. L. Garfinkel and P. Leclerc, "Randomness Concerns when Deploying Differential Privacy," *WPES*, 2020.
9. T. Gebru et al., "Datasheets for Datasets," *Communications of the ACM*, 2021.
10. M. Mitchell et al., "Model Cards for Model Reporting," *ACM FAT\**, 2019.
11. R. J. Preen et al., "A Multi-Language Toolkit for the Semi-Automated Checking of Research Outputs," *IEEE Transactions on Privacy*, 2025.
12. F. Ritchie et al., "Machine Learning Models in Trusted Research Environments," *IJPDS*, 2023.
13. T. Stadler, B. Oprisanu, and E. De Cristofaro, "Synthetic Data – Anonymisation Groundhog Day," *USENIX Security*, 2022.
14. Z. Zhao et al., "CTAB-GAN+: Enhancing Tabular Data Synthesis," *Frontiers in Big Data*, 2024.
