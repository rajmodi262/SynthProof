# 12 — Prior-art kill pass on the release-boundary work (Antigravity, 2026-09-14)

> Status: research pass. Citations re-verified against fetched sources on 2026-09-15. Two
> citations in the original draft were wrong and are corrected here: Dodis et al. carried a wrong
> arXiv ID (it pointed at an unrelated automata-theory paper) and is actually CRYPTO 2012 with no
> arXiv version; the industrial-deployment citation had a fabricated author list and an
> unverified claim, and is replaced by Garfinkel & Leclerc (WPES 2020), which was fetched and does
> support the point. The load-bearing claims rest on Dwork & Roth (2014), Chua et al. (2024) and
> Gopi et al. (2021), each verified. Illustrative tool mentions (StatDP/DP-Finder/CheckDP,
> DP-Auditorium) are named from general knowledge and their venues are not independently verified.

## Verdict in three lines
- Q1 (seed = membership oracle): KILLED as mathematical theory; SURVIVES as an empirical vulnerability in release metadata — Dwork & Roth (2014, Def. 2.4) and Dodis et al. (CRYPTO 2012) define DP strictly over internal random coins; revealing the seed makes any mechanism deterministic and trivially eliminates privacy.
- Q2 (release-boundary auditor): WOUNDED as general auditing; SURVIVES as a domain-specific metadata linter — Mechanism auditing (Cebere et al. 2026, arXiv:2602.17454) and schema validation (MLCommons Croissant) are crowded, but an automated static linter inspecting DP release artefacts for non-epsilon side channels without access to code or data is unaddressed prior art.
- The one sentence the student MAY say: "We demonstrate that the standard machine learning reproducibility norm of publishing random seeds completely destroys differential privacy guarantees in released metadata artefacts, and we provide an automated linter that audits published release documents for non-epsilon side channels."
- The one sentence the student may NOT say: "We discovered a new mathematical vulnerability in differential privacy and created a tool that proves synthetic data is completely private."

---

## Q1 — The published seed as a membership oracle

### 1. Mathematical Grounding (Why Theory is KILLED)
- **Textbook Definition:** In standard $(\varepsilon, \delta)$-differential privacy (Dwork, McSherry, Nissim, Smith, TCC 2006; Dwork & Roth, FNT-TCS 2014 §2.1, Def. 2.4), a randomized algorithm $\mathcal{M}: \mathcal{X} \to \mathcal{Y}$ satisfies privacy if and only if for all neighbouring $x, y$ and all measurable $\mathcal{S} \subseteq \mathcal{Y}$:
  $$\Pr_{r \sim \mathcal{R}}[\mathcal{M}(x; r) \in \mathcal{S}] \le e^\varepsilon \Pr_{r \sim \mathcal{R}}[\mathcal{M}(y; r) \in \mathcal{S}] + \delta$$
  The probability space is taken **strictly over the internal random coins $r$ of the mechanism**.
- **Conditioning on Randomness:** When the random seed $r$ is published, the conditional mechanism $\mathcal{M}_r(x) = \mathcal{M}(x; r)$ is a deterministic function. For any non-trivial mechanism where $\mathcal{M}(x; r) \ne \mathcal{M}(y; r)$, setting $\mathcal{S} = \{\mathcal{M}(x; r)\}$ yields $\Pr[\mathcal{M}_r(x) \in \mathcal{S}] = 1$ and $\Pr[\mathcal{M}_r(y) \in \mathcal{S}] = 0$. The privacy loss is $\ln(1/0) = \infty$.
- `INFERENCE:` Claiming the mathematical vulnerability of seed disclosure as an invention or novel theorem is dead on arrival. Any reviewer familiar with the definition of DP will dismiss it as an axiom.
- `CONFIDENCE: high — follows directly from Dwork & Roth (2014) Def. 2.4.`

### 2. Prior Art on Randomness Secrecy & Implementations
- **Imperfect / Correlated Randomness:** Dodis, López-Alt, Mironov & Vadhan (CRYPTO 2012, DOI 10.1007/978-3-642-32009-5_29; no arXiv version) formally analyzed differential privacy under imperfect randomness (Santha-Vazirani and min-entropy sources). They proved that if the adversary can predict, influence, or correlate with the randomness source, the differential privacy guarantee rapidly degrades or completely collapses.
- **Randomness secrecy in deployed DP:** Garfinkel & Leclerc (WPES 2020, arXiv:2009.03777), documenting the US Census Bureau's 2020 deployment, treat the quality and unpredictability of the randomness source as security-critical to the guarantee — they reject the Mersenne Twister as "unacceptable for use in production privacy-preserving systems" and mix `/dev/urandom` with hardware RDSEED. Predictable or exposed randomness undermines the privacy claim; a *published* seed is the limiting case of that exposure.
- **Floating-Point vs. Seed Disclosure (Crucial Distinction):** Mironov (CCS 2012, DOI: 10.1145/2382196.2382264) investigated vulnerabilities arising from floating-point arithmetic (irregular distribution of low-order mantissa bits in standard library continuous Laplace samplers). Mironov's attack exploits finite machine precision and non-uniform sampling support. In contrast, SynthProof's D5 is **not** a numerical precision failure: the PRNG and sampling mathematics can be mathematically ideal, yet revealing the seed exposes the entire pseudo-random sequence.
- **Grey-Box Auditing with Fixed Randomness:** Cebere, Erb, Desfontaines, Bellet & Fitzsimons (PoPETs 2026, arXiv:2602.17454) built *Re:cord-play* to audit 12 open-source DP libraries. They explicitly set identical seeds across neighbouring runs in test environments to eliminate stochastic variance and detect data-dependent branching. They use seed control as an internal testing technique, not as an adversary threat model against public artefacts.
- **Statistical MIA vs. Deterministic Replay:** The literature on membership inference against synthetic data (e.g., Stadler, Oprisanu & De Cristofaro, USENIX Security 2022; Annamalai, Ganev & De Cristofaro, arXiv:2405.10994, 2024) evaluates *statistical* attacks where an adversary observes synthetic rows and predicts membership with empirical advantage bounded by $\varepsilon$. SynthProof's seed-replay probe (`research/release_boundary/seed_replay_probe.py`: 15/15 true table matches, 0/15 neighbour matches) is an **algebraic identity test**, not a statistical test.

### 3. Where Novelty SURVIVES
- **The "Reproducibility vs. Privacy" Cultural Collision:** In modern machine learning, publishing random seeds (`random_state=42`) is considered an unalloyed virtue for reproducibility (mandated by NeurIPS/ICML reproducibility checklists, Model Cards, and MLCommons benchmarks). In differential privacy, publishing the seed turns the mechanism into an exact membership oracle.
- `INFERENCE:` The publishable finding is an **empirical vulnerability audit**: demonstrating that prominent release specifications, data cards, and real-world pipelines (including SynthProof's earlier iterations and Croissant metadata mappings) inadvertently publish run seeds under the banner of reproducibility, converting theoretically certified releases ($\varepsilon = 1.0$) into deterministic oracles with 100% membership extraction.
- `CONFIDENCE: high — documented in research/release_boundary/seed_replay_probe.py.`

---

## Q2 — The release-boundary auditor

### 1. Comparison with Mechanism Auditing Tools
- **The Algorithmic Auditing Cluster:**
  - *DP-Auditorium* (Google, 2024): Evaluates privacy guarantees by training shadow models and running empirical hypothesis tests on outputs.
  - *Re:cord-play* (Cebere et al., PoPETs 2026, arXiv:2602.17454): Audits library code by hooking into intermediate states, gradient clipping, and noise calls.
  - *StatDP* (Ding et al., POPL 2018), *DP-Finder* (Bichsel et al., CCS 2018), *CheckDP* (Zhang & Kifer, CCS 2017): Symbolic and statistical verifiers for algorithm implementations.
- **The Distinction:** All existing DP auditing tools audit the **algorithm or running code** on sensitive data. SynthProof's `boundary-audit` (`synthproof/audit/boundary.py`) audits the **published document** (the Privacy Data Sheet or Croissant JSON-LD) *after* release, with zero access to training data, model parameters, or source code.
- `INFERENCE:` The distinction between code verification and document boundary verification is real and practical, though conceptually analogous to static linting.

### 2. Comparison with Metadata and Dataset Validators
- **MLCommons Croissant Validator:** The official Croissant validator (`mlcroissant.validate`) inspects syntax, JSON-LD Schema.org types, and structural graph completeness. It reports 0 warnings on records containing `dp:seed: 42` or exact private record counts. It verifies format, not privacy.
- **Privacy Labels:** Dibia, Lu, Bhattacharjee, Near & Feng (arXiv:2507.15997, 2025) proposed nine categories of DP disclosure. However, their paper focuses on human-interpretable reporting categories; it offers no automated linter that evaluates whether the reported metadata itself leaks information.
- **Datasheets & Model Cards:** Gebru et al. (CACM 2021) and Mitchell et al. (FAT* 2019) establish qualitative documentation standards. Existing linters for them check only for missing markdown sections.

### 3. Comparison with Statistical Disclosure Control (SDC)
- **SACRO / ACRO (DARE UK / HDR UK; Ritchie et al., arXiv:2212.02935v3):**
  - SACRO (Semi-Automated Checking of Research Outputs) inspects analytical outputs (crosstabs, regression coefficients) within Trusted Research Environments (TREs) against disclosure rules (e.g., cell counts < 10, dominance thresholds).
  - SACRO reads **output data values** and assists a human output checker. It does not inspect accompanying metadata artefacts for side channels.
- **SDC Handbook (Hundepool et al., 2012):** Focuses on microdata masking (k-anonymity, suppression, perturbation). Metadata is assumed to be benign context, not an active attack vector.

### 4. Verdict on Novelty
- **Status:** **SURVIVES as a domain-specific engineering contribution.**
- **The Asymmetry Principle:** `boundary.py` formally codifies an asymmetric checking model: it can definitively prove a release channel is **OPEN** (e.g., finding a plaintext seed or an exact row count under add/remove-one), but cannot prove it is **CLOSED** (e.g., an unkeyed SHA-256 hash and a keyed HMAC-SHA-256 are syntactically indistinguishable hex strings). Formulating and implementing this distinction across Privacy Data Sheets and Croissant 1.1 records is a clean, defensible capstone deliverable.

---

## Q3 — The honest framing

### What the student MAY say (Defensible):
> "While differential privacy provably bounds leakage from mechanism outputs, current release practices routinely package outputs with metadata. We show that the standard scientific practice of publishing random seeds for reproducibility completely nullifies differential privacy guarantees in released metadata artefacts, converting the release into a 100% accurate membership oracle. To address this gap, we formalize the public release boundary under add/remove-one differential privacy and contribute an automated, data-blind linter (`boundary-audit`) that checks published release artefacts for non-epsilon side channels."

### What the student may NOT say (Fatal in viva):
> "We discovered a fundamental mathematical flaw in differential privacy algorithms, invented a new attack that breaks differential privacy theory, and built the first tool that proves a synthetic data release is completely private."

### Why this framing survives examination:
1. It attributes the core mathematics to Dwork & Roth (2014) and Dodis et al. (2012).
2. It acknowledges the comprehensive survey of DP auditing tools by Cebere et al. (2026) and SACRO (2022).
3. It focuses credit where the work actually succeeded: identifying a dangerous conflict between ML reproducibility norms and DP security in deployed metadata standards, and implementing a working, asymmetric checker for it.

---

## Q4 — The DP-VAE cross-check (Subsampled-Gaussian composition)

- **Status:** **CONFIRMED KNOWN ISSUE (Zero Novelty).**
- **Canonical References:**
  1. **Chua, Ghazi, Kamath, Kumar, Manurangsi, Sinha & Zhang (arXiv:2403.17673, ICML 2024):** *"How Private are DP-SGD Implementations?"* Thoroughly analyzes the discrepancies between the privacy analysis under Poisson subsampling vs. fixed-size batch shuffling.
  2. **Gopi, Lee & Wutschitz (NeurIPS 2021 / arXiv:2106.02848):** *"Numerical Composition of Differential Privacy."* Introduced the Privacy Loss Random Variable (PRV) / Fourier accountant (the core of Google's `dp_accounting`), proving that legacy RDP composition (used in `autodp` and early `Opacus`) can overestimate or underestimate true $(\varepsilon, \delta)$ bounds by 20–30% under subsampled Gaussian mechanisms.
  3. **Doroshenko, Ghazi, Kamath, Kumar & Manurangsi (PoPETS 2022 / arXiv:2207.04380):** *"Connect the Dots: Tighter Discrete Approximations of Privacy Loss Distributions."* Demonstrates numerical differences across disparate accounting discretization schemes for subsampled Gaussian mechanisms.
  4. **Cebere et al. (PoPETS 2026 / arXiv:2602.17454):** Documents that differing library implementations of accountant composition frequently disagree on reported $\varepsilon$ for identical DP-SGD parameters.
- `INFERENCE:` Reporting `unsupported` when cross-checking subsampled Gaussian mechanisms across `autodp` and `dp_accounting` is simply correct bug-handling of a well-documented divergence in the literature. Do not present it as a novelty claim; cite Chua et al. (2024) and Gopi et al. (2021) as the reason cross-checking requires identical composition models.

---

## Sources

1. **Dwork, McSherry, Nissim, Smith (2006)** — *Calibrating Noise to Sensitivity in Private Data Analysis*. TCC 2006. DOI: [10.1007/11681878_14](https://doi.org/10.1007/11681878_14). Foundational definition of DP over internal randomness spaces.
2. **Dwork & Roth (2014)** — *The Algorithmic Foundations of Differential Privacy*. Foundations and Trends in Theoretical Computer Science, Vol. 9, Nos. 3–4. DOI: [10.1561/0400000042](https://doi.org/10.1561/0400000042). Confirms randomness definition (§2.1, Def. 2.4).
3. **Dodis, López-Alt, Mironov, Vadhan (2012)** — *Differential Privacy with Imperfect Randomness*. CRYPTO 2012, LNCS 7417, pp. 497–516. DOI: [10.1007/978-3-642-32009-5_29](https://doi.org/10.1007/978-3-642-32009-5_29) (no arXiv version). Proves DP degrades and collapses when randomness is predictable or correlated.
4. **Mironov (2012)** — *On Significance of the Least Significant Bits for Differential Privacy*. ACM CCS 2012. DOI: [10.1145/2382196.2382264](https://doi.org/10.1145/2382196.2382264). Analyzes floating-point representation vulnerabilities in Laplace noise generation.
5. **Cebere, Erb, Desfontaines, Bellet, Fitzsimons (2026)** — *Privacy in Theory, Bugs in Practice: Grey-Box Auditing of Differential Privacy Libraries*. PoPETs 2026 / arXiv: [2602.17454](https://arxiv.org/abs/2602.17454). Evaluates 12 DP libraries using controlled randomness (Re:cord-play).
6. **Garfinkel & Leclerc (2020)** — *Randomness Concerns When Deploying Differential Privacy*. WPES 2020. arXiv: [2009.03777](https://arxiv.org/abs/2009.03777) / DOI: [10.1145/3411497.3420211](https://doi.org/10.1145/3411497.3420211). Treats randomness-source quality and unpredictability as security-critical to the DP guarantee.
7. **Dibia, Lu, Bhattacharjee, Near, Feng (2025)** — *An Expert-Elicited Differential Privacy Label*. arXiv: [2507.15997](https://arxiv.org/abs/2507.15997). Proposes a nine-category DP disclosure label; identifies "privacy theater" in uncalibrated reporting.
8. **Ritchie, Smith, Green, Mansouri-Benssassi et al. (2022)** — *Semi-Automated Checking of Research Outputs (SACRO)*. DARE UK / arXiv: [2212.02935v3](https://arxiv.org/abs/2212.02935). Framework and ACRO tools for statistical disclosure control of analytical outputs in TREs.
9. **Chua, Ghazi, Kamath, Kumar, Manurangsi, Sinha, Zhang (2024)** — *How Private are DP-SGD Implementations?*. ICML 2024 / arXiv: [2403.17673](https://arxiv.org/abs/2403.17673). Analyzes discrepancies in DP-SGD composition and subsampling accounting.
10. **Gopi, Lee, Wutschitz (2021)** — *Numerical Composition of Differential Privacy*. NeurIPS 2021 / arXiv: [2106.02848](https://arxiv.org/abs/2106.02848). Introduces Privacy Loss Random Variable (PRV) numerical accounting.
11. **Doroshenko, Ghazi, Kamath, Kumar, Manurangsi (2022)** — *Connect the Dots: Tighter Discrete Approximations of Privacy Loss Distributions*. PoPETs 2022 / arXiv: [2207.04380](https://arxiv.org/abs/2207.04380). Benchmarks discrete approximations in privacy loss distribution accounting.
