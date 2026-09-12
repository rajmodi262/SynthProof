# Chapter 3 — Threat Model & Problem Formulation

In privacy-preserving systems engineering, security guarantees are only as meaningful as the threat model that defines them. This chapter formalizes the operational environment, the capabilities and objectives of potential adversaries, the exact mathematical unit of privacy enforced, and the formal verification requirements that govern SynthProof.

---

## 3.1 Setting and Operational Actors

We consider a data-sharing ecosystem comprising four distinct operational entities:

1. **The Data Holder (Curator)**: Custodian of a sensitive private tabular dataset $D \in \mathcal{X}^n$, containing $n$ individual records over attribute schema $\mathcal{S}$. The data holder seeks to enable downstream analytical utility by releasing a synthetic counterpart $\widetilde{D}$, while ensuring that the release satisfies rigorous differential privacy guarantees and complies with regulatory standards. The curator operates the synthesis pipeline and possesses an Ed25519 private signing key used to attest execution certificates.
2. **The Data Analyst (Consumer)**: A legitimate downstream practitioner who ingests the released synthetic table $\widetilde{D}$ to perform exploratory data analysis, train predictive machine learning models, or evaluate statistical hypotheses. The analyst requires transparent metadata regarding data provenance, utility metrics, and privacy bounds to determine the evidentiary weight of downstream findings.
3. **The Adversary**: A malicious observer who obtains the released synthetic dataset $\widetilde{D}$ and its public release certificate. The adversary seeks to compromise the privacy of individual participants in $D$, attempting to infer record membership, reconstruct sensitive attributes, or establish linkage with external databases.
4. **The Independent Verifier**: An external oversight authority, compliance auditor, or downstream user who inspects the release package. Unlike conventional architectures that require blind trust in the curator's claims, the verifier possesses solely the curator's public key and independently validates that the release certificate is internally consistent, cryptographically authentic, and compliant with claimed privacy budgets.

The explicit formalization of the **independent verifier** represents a fundamental architectural departure from traditional synthetic data workflows. Conventional frameworks treat the curator and analyst as the sole participants, forcing consumers to rely on unverified assertions. SynthProof introduces machine-checkable verification as a first-class operational primitive.

---

## 3.2 Adversary Model and Attack Vectors

### Adversary Capabilities
In accordance with Kerckhoffs's principle, we assume that the adversary has complete knowledge of the system architecture and synthesis mechanisms. The adversary's capabilities are formally specified as follows:
- **Black-Box Release Access**: The adversary observes the released synthetic dataset $\widetilde{D}$ in its entirety, accompanied by its signed Privacy Data Sheet. This metadata explicitly informs the adversary of the mechanism family (e.g., AIM or Pairwise), the proved privacy parameters $(\varepsilon_{\text{proved}}, \delta)$, the empirical audit results $(\varepsilon_{\text{emp}}, \alpha, m)$, the audit ceiling ($\varepsilon_{\text{max}}$), and all hyperparameter choices.
- **Algorithmic and Implementation Transparency**: The source code, dependency versions, random number generator algorithms, and parameter calibration logic are fully public. Only the specific runtime cryptographic seed and the sensitive dataset $D$ remain secret.
- **Auxiliary Distributional Knowledge**: The adversary possesses auxiliary data drawn from the same underlying population distribution, formalized as an independent holdout dataset $D_{\text{holdout}} \sim \mathcal{D}_{\mathcal{X}}$. This reflects realistic threat scenarios where adversaries acquire historical or geographically related public datasets.
- **Partial Record Knowledge**: When executing attribute reconstruction attacks, the adversary is assumed to know all non-sensitive attributes for a targeted individual $x^* \in D$, attempting to infer the remaining sensitive feature value.

### Excluded Capabilities
To maintain a well-defined security boundary, certain threat vectors are explicitly placed out of scope:
- **No Intermediate State Observation**: The adversary observes solely the finalized release package. Internal mechanism states, intermediate noisy contingency tables, Private-PGM marginal optimization traces, and transient memory structures are inaccessible.
- **No Interactive Query Oracle**: Synthesis is executed as a non-interactive batch release. The adversary cannot submit adaptive query sequences to the curator.
- **No Pre-Ingestion Data Poisoning**: The raw dataset $D$ is assumed to be curated prior to synthesis; active poisoning attacks on $D$ before pipeline execution are not defended against.

### Adversarial Objectives
The adversary pursues four concrete disclosure goals, which map directly to the empirical attacks implemented and evaluated in Chapter 7:
1. **Membership Inference**: Determining whether a specific target record $x^*$ was included in the private training set $D$ ($x^* \in D$). Evaluated via metric-space nearest-neighbour distance attacks (`distance_mia`) and density-ratio estimation (`domias`, van Breugel et al., 2023).
2. **Attribute Inference**: Reconstructing the sensitive attribute of a targeted record $x^*$ given knowledge of its quasi-identifiers. Evaluated via supervised classifiers scored against conditional baselines (`attribute_inference`).
3. **Singling Out**: Constructing an attribute predicate that isolates exactly one individual within the underlying population. Evaluated via exact match collision metrics (`exact_match_risk`).
4. **Linkability**: Correlating records across two disjoint synthetic releases or external datasets to determine if they correspond to the same identity. Evaluated via split-attribute bipartite matching (`linkability`).

---

## 3.3 Unit of Privacy

SynthProof formalizes differential privacy under the **add/remove-one-record** neighbouring relation. 

Two datasets $D, D' \in \mathcal{X}^*$ are defined as neighbours, denoted $D \sim D'$, if and only if one can be obtained from the other by the addition or deletion of a single record: $|D \triangle D'| = 1$. A randomized synthesis mechanism $\mathcal{M}$ satisfies $(\varepsilon, \delta)$-differential privacy if, for all neighbouring datasets $D \sim D'$ and all measurable output subsets $\mathcal{S} \subseteq \text{Range}(\mathcal{M})$:
$$\Pr[\mathcal{M}(D) \in \mathcal{S}] \le e^\varepsilon \Pr[\mathcal{M}(D') \in \mathcal{S}] + \delta$$

### Technical Specifics of the Formulation
1. **Record-Level vs. User-Level Scope**: In datasets where each individual contributes exactly one row (such as the UCI Adult benchmark), record-level differential privacy is mathematically identical to user-level privacy. On multi-record datasets where individuals contribute up to $k$ rows, record-level guarantees degrade by a factor of $k$ under group privacy; adapting to multi-record scenarios requires contribution-bounding preprocessing.
2. **Neighbouring Definition**: We configure Google’s `dp_accounting` library under the `ADD_OR_REMOVE_ONE` relation rather than the `REPLACE_ONE` relation. This distinction is critical: replacement-based neighbouring yields an $L_1$ query sensitivity of $\Delta = 2$, whereas add/remove neighbouring yields $\Delta = 1$, altering the required noise calibration scale by a factor of two.
3. **Operational Interpretation of $\delta$**: The parameter $\delta$ represents the probability that the pure $\varepsilon$-DP guarantee is breached. Following standard cryptographic practice, we enforce $\delta \ll 1/n$ across all experiments (specifically fixing $\delta = 10^{-5}$ for benchmarks with $n \ge 30,000$). Setting $\delta \ge 1/n$ would render the definition vacuous, as a mechanism that releases $n\delta$ records verbatim would technically satisfy the formal inequality.

---

## 3.4 Verification Requirements (R1–R8)

To translate these theoretical boundaries into an actionable engineering architecture, SynthProof enforces eight explicit verification requirements:

| # | Requirement | Description | Enforcement Architecture |
|---|---|---|---|
| **R1** | Strict Budget Billing | Every operation that reads raw data $D$ must debit the accountant. | `Accountant` + `MechanismSpec`; execution hooks block raw access without active budget. |
| **R2** | Non-Exceedance Guarantee | Total composed expenditure across all stages must not exceed target $(\varepsilon_{\text{target}}, \delta)$. | `BudgetPlan` and accountant raise `BudgetExceededError` upon over-spend. |
| **R3** | Faithful Delivered Budget | The requested privacy parameter must match the delivered parameter. | Bracket-and-bisect calibrator (`calibration.py`), CI-gated across 24 configurations. |
| **R4** | Privacy-Charged Profiling | Categorical domain discovery and cardinality estimation must not be free. | `DPDomainProfiler` with stability-based noisy frequency thresholding. |
| **R5** | Audited Composition | Privacy composition must rely on verified mathematical theorems, not heuristics. | Composition delegated to Google’s `dp_accounting` and cross-validated via `autodp`. |
| **R6** | Tamper-Evident Ledger | Cumulative organizational budget expenditure must be cryptographically auditable. | SQLite database with HMAC-SHA256 hash chaining and Ed25519-signed tip heads. |
| **R7** | Zero-Trust Verifiability | Release integrity must be verifiable using public metadata without trusted curator access. | Ed25519-signed Privacy Data Sheet and standalone `synthproof verify` CLI. |
| **R8** | Bound-Auditing Parity | Empirical leakage audits must quantify uncertainty and declare their detection limits. | Steinke one-run binomial auditor reporting audit ceilings alongside empirical estimates. |

### The Criticality of Requirement R3 (Delivered Calibration)
Requirement R3 reflects an essential lesson in differential privacy systems design. During early project development, requesting a synthesis budget of $\varepsilon = 8.0$ under an uncalibrated pipeline silently resulted in releases whose actual composition totaled $\varepsilon = 70.49$. The software interface accepted the parameter $\varepsilon = 8.0$, but applied noise scaled for an isolated query while evaluating multiple multi-way marginals. A system can strictly implement differential privacy mechanisms while its configuration interface misleads the operator. By integrating automated bisection calibration, SynthProof ensures that the requested budget equals the verified delivered guarantee.

### Requirement R8: Limit of Detection (LoD) Transfer and Audit Ceilings
Requirement R8 addresses the fundamental epistemic asymmetry between formal mathematical proof and empirical statistical estimation. When an empirical audit algorithm (such as the Clopper-Pearson binomial inversion on canary guess success rates developed by Steinke et al., 2023) evaluates a synthetic dataset release, its statistical power is strictly bounded by sample size $m$ and test significance $\alpha$. Under the maximum possible canary success rate ($k = m$), the maximum auditable epsilon that the statistical test is mathematically capable of reporting is:
$$\varepsilon_{\text{max}} = \ln\left(\frac{1 - \alpha^{1/m}}{\alpha^{1/m}}\right)$$
As formally defined by Annamalai, Ganev & De Cristofaro (arXiv:2405.10994 §2.2), this operating range boundary—which we designate the **audit ceiling** $\varepsilon_{\text{max}}$—represents an intrinsic physical limit of the measurement instrument.

In analytical chemistry, molecular diagnostics, and clinical pathology, measuring an analyte below the detector's physical sensitivity threshold without declaring that threshold constitutes scientific malpractice. The MIQE 2.0 guidelines (Bustin et al., *Clinical Chemistry* 2025;71(6):634–651) mandate the explicit reporting of the Limit of Detection (LoD) and Lower Limit of Quantification (LLOQ); diagnostic laboratories never report an analyte concentration as "zero," but rather as "Not Detected, < LoD." SynthProof explicitly transfers this standardized laboratory reporting convention (codified in ISO 11843) into differential privacy engineering. Reporting an empirical leakage estimate of $\varepsilon_{\text{audited}} = 0.0$ when the audit ceiling is $\varepsilon_{\text{max}} = 2.45$ against a proved guarantee of $\varepsilon_{\text{proved}} = 8.0$ conveys zero information about whether privacy is preserved or whether the detector was simply blind. Requirement R8 mandates that every empirical audit report must declare its audit ceiling $\varepsilon_{\text{max}}$ alongside its observed point estimate.

### Requirements R6 & R7: Cryptographic Canonicalization and Verification
Requirements R6 and R7 decouple verification from trusted pipeline access. Conventional privacy tools require downstream analysts to execute proprietary verification scripts within the curator's internal enclave. SynthProof achieves zero-trust verifiability by coupling two cryptographic structures:
1. **The Hash-Chained Budget Ledger (R6)**: The cumulative history of organizational budget debits is recorded in an append-oriented SQLite relational database where each entry commits to the cryptographic hash of its predecessor via HMAC-SHA256. To defend against ledger rollback and history truncation, the system periodically writes a signed checkpoint to the `ledger_head` table, committing to the pair `(entry_count, tip_hash)` under the curator's Ed25519 private key.
2. **Canonical JSON Serialization (R7)**: Release certificates and Privacy Data Sheets are serialized using deterministic RFC 8785 JSON Canonicalization Scheme (JCS) semantics prior to signing. Field keys are lexicographically sorted, whitespace is stripped, and floating-point coordinates are cast to normalized string representations. As a result, an external verifier possessing only the curator's public key can recompute the certificate hash and verify the Ed25519 digital signature across arbitrary compute platforms without round-trip floating-point serialization drift.

---

## 3.5 Out of Scope Boundaries and Operator Threat Model

To maintain scientific integrity, we explicitly delineate the boundaries that SynthProof does not defend:

- **Physical and Cache Side Channels**: Timing variations, CPU cache contention, power consumption analysis, and electromagnetic emanations are excluded.
- **Floating-Point Bit-Level Adversaries**: While our discrete Gaussian and discrete Laplace samplers reside strictly in $\mathbb{Z}$ to defeat Mironov's (2012) output-representation attacks, the underlying rejection steps rely on 64-bit IEEE 754 floating-point operations. An adversary with hardware-level inspection access to execution registers is out of scope.
- **Curator Key Compromise**: The budget ledger is cryptographically tamper-evident, not tamper-proof. An attacker who obtains the curator’s Ed25519 private key can rewrite database history and forge valid signatures over manipulated tables. Key protection is an organizational security control.

### The Malicious Operator Threat Model
Within these boundaries, SynthProof defends against a **malicious internal operator who holds full file-system read and write access to the SQLite ledger database, but does not possess the curator's private signing key.** 

Under naive hash chaining, an attacker who overspends budget could simply truncate the last $k$ rows of the database; because each row points only to its predecessor, the truncated log remains internally consistent. SynthProof defeats this attack through the `ledger_head` table, which commits to `(entry_count, tip_hash)` under an Ed25519 signature. Across 14 live adversarial test suites in `tests/test_ledger_adversarial.py`, we verify that nine distinct database manipulation attacks—including entry modification, row deletion, chain truncation, genesis tampering, and head substitution—are unambiguously detected by `verify_with_reason()`.

---

## 3.6 Formal Problem Statement

We conclude with the formal definition that anchors the entire thesis:

> **Definition (Differential Privacy)**: A randomized algorithm $\mathcal{M}$ satisfies $(\varepsilon, \delta)$-differential privacy if for all neighbouring datasets $D, D' \in \mathcal{X}^*$ differing by at most one record ($|D \triangle D'| = 1$) and all measurable output subsets $\mathcal{S} \subseteq \text{Range}(\mathcal{M})$:
> $$\Pr[\mathcal{M}(D) \in \mathcal{S}] \le e^\varepsilon \Pr[\mathcal{M}(D') \in \mathcal{S}] + \delta$$

This inequality defines a mathematical bound over the **worst-case adversary across all possible auxiliary knowledge**. It does not, however, reveal how much privacy a specific, computationally bounded adversary can compromise when observing a particular released table $\widetilde{D}$. The operational tension between the proved formal bound ($\varepsilon_{\text{proved}}$) and the empirically measured audit resolution ($\varepsilon_{\text{audited}}$ constrained by the audit ceiling $\varepsilon_{\text{max}}$) constitutes the core scientific phenomenon evaluated in this work.

