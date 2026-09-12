# Chapter 1 — Introduction & Motivation

**Target: 1,200 words.** Write *after* Ch.2 and Ch.3, and draft it last.

> **REWRITTEN 2026-08-24 as a specification.** The previous §1.4 instructed the writer to list
> as contributions (1) "a dual-sided assurance pipeline" and (2) "budget-charged domain
> profiling". **Both were killed by this project's own novelty protocol** — the first by
> Annamalai, Ganev & De Cristofaro (USENIX Sec 2024), the second by Ganev, Annamalai, Mahiou &
> De Cristofaro (Apr 2025). Drafting to the old file would have opened the thesis with two
> claims an examiner can refute from the literature.
>
> **Nobody outside the four authors writes the prose.**

---

## 1.1 Motivation

The traditional promise of anonymisation—that personal datasets can be stripped of direct identifiers and safely shared—has repeatedly collapsed under rigorous scrutiny. Sweeney (2000) famously proved that 87% of the United States population can be uniquely identified by the combination of 5-digit ZIP code, gender, and date of birth alone. Narayanan and Shmatikov (2008) demonstrated that anonymised movie ratings released in the Netflix Prize competition could be cross-matched against public IMDb profiles to de-anonymise individual subscribers and reveal sensitive viewing histories. In response, data protection regimes worldwide, including the European Union's General Data Protection Regulation (GDPR Art. 9), the US Health Insurance Portability and Accountability Act (HIPAA), and India's Digital Personal Data Protection (DPDP) Act 2023, have established stringent legal requirements for handling personal records.

Differential privacy (DP) emerged as the mathematically rigorous foundation for privacy-preserving data sharing, guaranteeing an upper bound on an adversary's ability to infer individual participation regardless of auxiliary information. Consequently, differentially private synthetic data has been embraced as an attractive mechanism to unlock analytical utility without disclosing raw individual records.

However, modern empirical research reveals that privacy assurance in synthetic data faces a deeper structural crisis. Three recent findings delineate the core problem:
1. **The field agrees on disclosure standards**: Dibia et al. (arXiv:2507.15997, 2025) conducted an expert-elicited study establishing a consensus nine-category privacy label for differentially private releases, formalising the exact metadata necessary for transparency.
2. **Practitioners do not verify guarantees**: Song, Sarathy, Shoemate, and Vadhan (CSCW 2024, arXiv:2410.09721) evaluated real-world deployment practices and found that data practitioners treat mathematical differential privacy claims as trusted black boxes, rarely validating whether software implementations correctly realize the claimed theoretical privacy parameters.
3. **Implementations silently lose their guarantees**: Cebere et al. (arXiv:2602.17454, Feb 2026) conducted an exhaustive adversarial audit of twelve widely deployed differential privacy libraries, discovering thirteen severe guarantee violations that silently voided theoretical bounds in production software.

This establishes the central challenge addressed by this thesis: the primary barrier to trustworthy synthetic data release is not an absence of disclosure guidelines, but **a reliance on unverified declarations resting on software implementations that demonstrably drift from their theoretical guarantees.**

---

## 1.2 Problem statement

Privacy assurance in synthetic data currently divides into two disconnected paradigms, each addressing only half of the verification challenge.

On one side, theoretical differential privacy proves formal worst-case upper bounds ($\varepsilon_{\text{proved}}, \delta$). Yet downstream consumers cannot independently verify whether the code that executed the synthesis was bug-free, whether composition theorems were correctly evaluated, or whether privacy budgets were silently exceeded. On the other side, empirical auditing evaluates empirical lower bounds ($\varepsilon_{\text{emp}}$) using membership inference attacks and canary insertions. However, empirical audits produce point measurements that carry no mathematical guarantee, are rarely cryptographically bound to the release artefact, and are computed using finite sample budgets.

Crucially, we found no proposal that reports the operating range of its own empirical privacy measurement inside the release artefact. In empirical auditing, when an instrument evaluates a mechanism using $m$ canary trials at significance level $\alpha$, there exists an information-theoretic ceiling $\varepsilon_{\text{max}}(m, \alpha)$ beyond which a perfect adversary cannot push the empirical bound. When an underpowered auditor is applied to a mechanism with $\varepsilon_{\text{proved}} > \varepsilon_{\text{max}}$, reporting an audited leakage of zero ($\varepsilon_{\text{emp}} = 0$) does not demonstrate mechanism soundness; it merely reflects the instrument reaching its own detection floor. As warned by domain experts in Dibia et al. (2025), presenting an audited epsilon without declaring the instrument's limit of detection degenerates into "privacy theater."

To resolve this impasse, this thesis adapts the rigorous Limit of Detection (LoD) framework established in analytical chemistry and clinical diagnostics (such as the MIQE 2.0 guidelines for digital and quantitative PCR, Bustin et al. 2025; ISO 11843). In clinical assay reporting, a biological sample in which no target molecules are detected is never recorded as possessing "zero viral concentration"; rather, the diagnostic protocol mandates reporting the result as *"Not Detected, below Limit of Detection (< LoD)"*, explicitly specifying the assay's sensitivity threshold. By incorporating the audit ceiling directly into the release certificate, SynthProof transfers this foundational analytical principle to privacy engineering, ensuring that empirical lower bounds are evaluated strictly within the demonstrable resolution of the auditing instrument.

---

## 1.3 Thesis statement

Differentially private synthetic tabular data can be rendered verifiably accountable through a cryptographically bound, machine-checkable release certificate that couples formal privacy composition with empirical leakage auditing bounded by explicit limits of detection.

Specifically, this thesis demonstrates that neither formal mathematical proofs nor empirical attack audits are sufficient in isolation to guarantee privacy in deployed data-sharing pipelines. Theoretical proofs can be silently compromised by implementation drift, uncalibrated parameter translation, or uncharged auxiliary operations. Conversely, empirical audits are inherently constrained by finite sample budgets, creating an information-theoretic detection ceiling beyond which an auditor is blind to catastrophic privacy leakage. We prove that by embedding verified composition bounds alongside empirical audit limits of detection within a signed, standards-conformant release metadata object, automated verifiers can independently validate end-to-end privacy integrity without requiring trusted access to raw source records.

---

## 1.4 Contributions

This thesis delivers five evaluated and implemented contributions:

1. **The Clique-Selection Confound in Graphical Model Benchmarks** (*evaluated across two datasets*): We show that evaluating marginal-based differentially private tabular synthesizers (such as AIM and MST) on fixed low-order marginals risks measuring whether target column pairs were selected into the model's clique workload rather than true synthesis fidelity. We demonstrate that this effect is pronounced on Adult and inverts on the sparse ACSIncome benchmark due to privacy-budgeted domain expansion.
2. **Operating Range Reporting in Release Artefacts** (*implemented and evaluated*): We introduce the explicit cryptographic reporting of the empirical audit ceiling (`audit_ceiling`) within release certificates, formalising the transfer of Limit of Detection (LoD) principles from analytical chemistry and molecular diagnostics (MIQE 2.0, Bustin et al., Clinical Chemistry 2025;71(6):634-651; ISO 11843). The underlying ceiling is a corollary of Steinke, Nasr & Jagielski (2023) Thm 2.1, corresponding to the "maximum auditable epsilon" identified by Annamalai, Ganev & De Cristofaro (USENIX Security 2024, arXiv:2405.10994 §2.2).
3. **Signed, Standards-Conformant Release Certificates** (*implemented*): We design and implement the Privacy Data Sheet as an Ed25519-signed Croissant 1.1 JSON-LD metadata package extending the MLCommons schema with an official differential privacy vocabulary (`dp:epsilon`, `dp:delta`, `dp:auditCeiling`, `dp:mechanism`), independently validated by the official MLCommons validator.
4. **Data-Blind Pre-Flight Refusal Gating** (*implemented*): We construct an automated pre-flight release gate that inspects solely schema cardinality and row count, refusing synthesis requests that would trigger vacuous bounds or memory exhaustion prior to any data observation.
5. **Empirical Multi-Dataset Evaluation with Transparent Retractions** (*evaluated*): We conduct a comprehensive empirical evaluation of tabular mechanism families (H1), demographic subgroup leakage parity (H2), and weighted privacy allocation (H3) across UCI Adult and ACSIncome. We document the evolution of our findings, demonstrating why null results under Benjamini-Hochberg false discovery rate control and two-one-sided-test (TOST) equivalence testing must be reported with full methodological fidelity.

---

## 1.5 Scope and non-goals

The scope of this investigation is defined by four clear operational boundaries:
1. **Data Modality**: We restrict our evaluation strictly to structured tabular data; image, audio, and unstructured natural language models are excluded.
2. **Privacy Definition**: We operate under record-level differential privacy in the central curator model (`deployment_model: central`), wherein the curator is trusted to observe the raw input table and execute calibrated noise addition.
3. **Threat Model**: Adversaries are assumed to hold arbitrary auxiliary knowledge and observe solely the published synthetic table and its accompanying certificate.
4. **Non-Goals**: We do not implement cross-session or multi-release global budget enforcement; stateful cross-pipeline budget governance is an independent systems problem formally addressed by dedicated policy architectures such as DPolicy (arXiv:2505.06747).

---

## 1.6 Thesis structure

The remainder of this thesis is organised as follows:
- **Chapter 2 (Literature Review)** surveys differential privacy tabular synthesis, empirical auditing estimators, privacy governance standards, and establishes the precise positioning matrix of this work.
- **Chapter 3 (Threat Model and Scope)** defines the trust assumptions, cryptographic attack surfaces, and formal verification requirements for release certificates.
- **Chapter 4 (System Design)** presents the end-to-end architecture of SynthProof, detailing the data-blind profiler, bisection calibrator, execution pipelines, dual accountants, and tamper-evident ledger.
- **Chapter 5 (Implementation)** details the discrete noise sampling mechanisms (CKS'20 and GRS'12), differential accounting validation against `autodp`, shadow-model auditing procedures, and regression defense suites.
- **Chapter 6 (Methodology)** specifies the pre-registered experimental design, hyperparameter grids, baseline configurations, canary placement strategies, and statistical hypothesis testing criteria.
- **Chapter 7 (Results and Analysis)** presents empirical findings across calibration validation, detection floor characterisation, the H1 utility-privacy frontier, H2 subgroup leakage parity, H3 weighted allocation, and empirical ceiling meta-analysis.
- **Chapter 8 (Discussion and Conclusion)** synthesises the methodological lessons learned, details the documented adversarial self-audit, discusses regulatory implications, delineates remaining limitations, and outlines a concrete future research programme.
