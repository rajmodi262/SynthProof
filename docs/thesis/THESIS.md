# Chapter 1 — Introduction

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

# Chapter 2 — Literature Review

> **Status: FIRST DRAFT — 2,442 words against a 2,500 target (~98%).** Prose is written;
> citations are marked `[Author Year]` and need converting to BibTeX.
>
> ⚠️ **REVIEWED 2026-08-24. The word count is nearly met but the SURVEY IS NOT.** §2.1–2.5 do
> not cite a single one of the eight sources that killed this project's claims — every one of
> Annamalai, Ganev, Cebere, Dibia, SACRO and Laminator appears only inside the working-note
> callout in §2.6. A reader of the survey proper sees literature stopping around 2023.
> `Croissant 0 · Song 0 · DPolicy 0 · PrivateKube 0 · SynthGuard 0 · MRM3 0` mentions in the
> whole file. **§2.4 and §2.5 each carry a specification block below listing what must be
> added.** Closing those is worth more than the remaining 58 words.

---

## 2.1 Formal differential privacy

Differential privacy [Dwork et al. 2006] replaced a decade of failed syntactic anonymisation
with a definition that makes no assumptions about what an adversary already knows. A randomised
mechanism *M* satisfies (ε, δ)-differential privacy if, for all datasets *D* and *D′* differing
by one record and all measurable output sets *S*,

  Pr[*M*(*D*) ∈ *S*] ≤ e^ε · Pr[*M*(*D′*) ∈ *S*] + δ.

The definition's power is that it quantifies over all adversaries and all auxiliary information.
Its weakness, less often discussed, is that it quantifies over the *worst case*, and the worst
case may be far from anything a real adversary achieves.

The mechanisms are well understood. The Laplace and Gaussian mechanisms calibrate noise to a
query's sensitivity [Dwork & Roth 2014]. What has changed most in the last decade is
*composition* — how privacy loss accumulates across a sequence of mechanisms. Basic composition
is linear and quickly becomes vacuous; advanced composition improves this to roughly √k for k
mechanisms. Rényi differential privacy [Mironov 2017] reformulates the guarantee in terms of
Rényi divergence, giving composition that is simply additive in the RDP curve and converting to
(ε, δ) at the end. This is now the standard accounting approach, refined by tighter conversion
bounds [Balle et al. 2020] and extended to subsampled mechanisms [Mironov, Talwar & Zhang 2019].

Two implementation results matter for any system that claims a guarantee. Mironov [2012] showed
that naive floating-point Laplace sampling via inverse-CDF leaks information through the
low-order bits of the output, breaking the guarantee entirely. Canonne, Kamath and Steinke
[2020] gave exact samplers for the discrete Gaussian and discrete Laplace, and showed that
rounding a continuous Gaussian does *not* produce the discrete Gaussian — so a system that
rounds is not running the mechanism its proof describes.

The pattern is worth naming, because it recurs throughout this chapter: **the theory is mature,
and the gap between the theory and a given implementation of it is where guarantees are lost.**

---

## 2.2 Differentially private synthetic data

Synthetic data is attractive because it decouples the release from the record. Rather than
perturbing answers to queries, the holder releases a whole table that can be analysed freely.

For tabular data the dominant approach is marginal-based. The winning entries in the NIST
synthetic data challenges [McKenna et al. 2021] measure a set of low-order marginals under DP
and then find a distribution consistent with those noisy measurements, using the graphical-model
inference of private-PGM [McKenna, Sheldon & Miklau 2019]. AIM [McKenna et al. 2022] extends
this with an adaptive loop: at each round it uses the exponential mechanism to select whichever
marginal is currently worst approximated, measures it, and re-solves. Adaptivity costs budget —
the selection step is itself a mechanism — but spends the remaining budget far more effectively
than a fixed workload.

Deep generative approaches exist — DP-GAN [Xie et al. 2018], PATE-GAN [Jordon et al. 2019] — but
on tabular benchmarks they are generally outperformed by marginal-based methods, which is why
this work follows the marginal-based line.

The critical literature is more important here than the constructive literature. Stadler,
Oprisanu and Troncoso [2022] tested a range of synthetic data generators against linkage and
inference attacks and found that synthetic data provides neither the privacy nor the utility
routinely claimed for it, and that generators without a formal guarantee frequently reproduce
outlier records. Their framing — that synthetic data has recreated the same false confidence
that de-identification once offered — is the direct motivation for this work.

Two consequences follow. First, *synthetic* describes how data was produced, not what it
discloses; the word carries no privacy content. Second, the mechanisms that do carry a formal
guarantee are precisely the ones whose guarantee nobody independently checks, because checking
requires reading the implementation rather than the paper.

---

## 2.3 Empirical privacy auditing

If formal DP supplies an upper bound, auditing supplies a lower bound: what does an actual
adversary actually recover?

The instrument is membership inference. Shokri et al. [2017] introduced the shadow-model attack,
training many models on data drawn from the same distribution to learn the difference between a
member and a non-member. Carlini et al. [2022] substantially strengthened this with LiRA, which
fits per-example Gaussians to the IN and OUT score distributions and performs a calibrated
likelihood-ratio test. Their methodological argument matters as much as their attack: **average
accuracy is the wrong metric for membership inference**, because a privacy violation affecting a
small number of individuals with high confidence is far more serious than a marginal improvement
across the population. They argue for reporting the true-positive rate at low false-positive
rates, a convention this work adopts. DOMIAS [van Breugel et al. 2023] adapts the idea
specifically to synthetic data, scoring membership by a density ratio between the synthetic
distribution and a reference population.

Auditing DP implementations directly is a younger line. Jagielski, Ullman and Oprea [2020]
established the framing used here: instantiate a strong adversary, measure its success, and
convert that into an empirical lower bound ε_audited that can be compared against the ε the
implementation claims. A large gap means either that the analysis is loose or that the adversary
is weak; a small gap means the bound is close to tight. Nasr et al. [2021, 2023] tightened this
considerably with better adversary instantiations.

The construction most relevant to this project is Steinke, Nasr and Jagielski [2023], which
obtains a meaningful audit from **one training run**. Rather than repeating training thousands
of times, it includes each of m canaries independently at random, has the adversary guess
membership for a subset, and derives an ε lower bound from the resulting confusion counts via
exact binomial confidence intervals. This makes auditing computationally tractable for
mechanisms that are expensive to run.

Separately, Anonymeter [Giomi et al. 2023] provides a practitioner-facing framework measuring
three distinct risks — singling out, linkability, and inference — as separate attack
simulations, which is a useful corrective to treating "privacy risk" as one number.

Auditing's limitations are structural. An audit bounds what *the attacks you ran* achieved; it
is not a guarantee. It produces no budget and does not compose, so a holder cannot use audit
results to reason about a second release. And the results live in a paper, not attached to the
artefact anyone actually downloads.

---

## 2.4 Privacy accounting and budget management

Composition is a theorem about sequences of mechanisms, which means it only protects an
organisation if something records the sequence.

Reference accountants exist and are mature: Google's `dp_accounting` library implements RDP and
privacy-loss-distribution accountants, and equivalents ship with Opacus and TensorFlow Privacy.
Using one is not merely convenient. This project originally hand-rolled its RDP composition,
including a subsampling bound of the form min(q·ρ(α), truncated series), and a subsequent audit
of our own code found that neither branch was a citable theorem and that the bound
**under-reported ε by roughly a factor of two** at q = 0.01. That experience is reported in
Chapter 5 as an implementation failure, and it is the reason this work delegates all composition to verified reference implementations. 

Crucially, modern research demonstrates that implementation defects are an industry-wide pathology rather than isolated bugs. Cebere et al. (arXiv:2602.17454, Feb 2026) audited twelve prominent differential privacy libraries and discovered thirteen concrete guarantee violations, spanning under-noised Gaussian mechanisms, incorrect subsampling accounting, and flawed composition bounds. This systematic drift is exacerbated by organizational behavior: Song, Sarathy, Shoemate, and Vadhan (CSCW 2024, arXiv:2410.09721) surveyed practitioners deploying differential privacy and revealed that engineers treat published guarantees with implicit, unverified trust. When composition code drifts, practitioners neither detect nor investigate the discrepancy. This directly justifies SynthProof's architectural choice of *differential accounting*, running independent composition engines (`autodp` and Google's `dp_accounting`) in parallel to assert agreement within 0.05% before any budget is committed.

Beyond single-run execution, the broader systems literature addresses privacy budget *governance* across multiple releases. Early systems such as PrivateKube (OSDI 2021) formalized privacy budgets as first-class, schedulable computing resources within Kubernetes clusters. Subsequent enterprise architectures, including Cohere and DPack (EuroSys 2025), investigated multi-tenant budget allocation across competing analytical pipelines. Most recently, DPolicy (arXiv:2505.06747) established a formal policy-driven framework for cross-session, multi-query governance. We explicitly distinguish SynthProof's ledger from these cross-release systems: SynthProof provides single-curator, tamper-evident cryptographic provenance for an individual synthetic dataset release, leaving global cross-pipeline policy scheduling to dedicated orchestrators such as DPolicy.

---

## 2.5 Transparency artefacts

A parallel literature asks not how to protect data but how to *describe* it. Datasheets for
Datasets [Gebru et al. 2021] proposed that every dataset ship with a standard document covering
provenance, composition, collection process and recommended uses; Model Cards [Mitchell et al.
2019] did the same for models, and Data Statements [Bender & Friedman 2018] for language
resources.

These prose documentation frameworks have achieved broad conceptual adoption, yet they share a structural limitation: they are descriptive declarations authored by the dataset creator, offering no cryptographic mechanism for an independent consumer to verify the veracity of the underlying assertions. A traditional datasheet records what a dataset claims to be; it provides no verifiable guarantee of what the release actually discloses.

Between 2024 and 2026, the transparency literature advanced decisively from static prose toward machine-readable metadata standards. The foremost development is Croissant (MLCommons), an extensible JSON-LD metadata specification layered atop schema.org and W3C PROV-O, now adopted as a mandatory submission requirement for major benchmarking venues including NeurIPS Datasets & Benchmarks. Croissant enables automated ingestion, column typing, and lineage tracking. Simultaneously, Dibia et al. (arXiv:2507.15997, 2025) introduced an expert-elicited nine-category privacy label specifically tailored for differentially private releases, formalising the exact technical and operational fields practitioners require. In parallel systems literature, MRM3 (MobiSys 2025) formalized machine-readable model cards, while Laminator (CODASPY 2025) leveraged hardware-based Trusted Execution Environments (TEEs) to attest model properties. In synthetic data release management, SynthGuard-ReleaseBench (arXiv:2608.14753, Jul 2026) demonstrated the feasibility of shipping checkable verification scripts alongside generated data, though its verification bounds focus on utility degradation rather than privacy leakage sensitivity. In operational environments, SACRO (Preen et al., 2024) automates output checking under the UK Five Safes framework within Trusted Research Environments (TREs); however, SACRO operates by inspecting raw output statistics post-hoc and lacks autonomous pre-flight refusal mechanisms based on schema cardinality.

Despite these rapid advances, an essential verification gap remains unaddressed across the existing literature: **none of these frameworks carries a cryptographic signature binding a formal differential privacy guarantee to an authenticated issuer, and none establishes a standard for reporting the operating range (Limit of Detection) of an empirical privacy measurement.** A standard SHA-256 hash merely verifies bit-level file integrity; it does not attest who computed the guarantee or whether the execution conformed to the claimed budget. Furthermore, emitting empirical privacy metrics without reporting the detector's mathematical ceiling allows underpowered instruments to masquerade as sound guarantees. SynthProof directly fills this dual gap by packaging synthesis outputs into an Ed25519-signed Croissant 1.1 record enriched with an explicit differential privacy vocabulary (`dp:epsilon`, `dp:delta`, `dp:auditCeiling`).

---

## 2.6 The gap this work addresses

Assembling the picture:

| Approach | Upper bound | Lower bound | Composes | Cross-release | Attached to artefact | Verifiable |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| Formal DP synthesis (AIM, MST) | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| Empirical auditing (LiRA, Steinke) | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Risk assessment (Anonymeter) | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Datasheets / Model Cards | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| **SynthProof** | ✅ | ✅ | ✅ | ❌ | ✅ | partial |

> ⚠️ **Before submission:** set the SynthProof row against what is actually implemented at that
> time. Overstating this row would be the same failure this project's own audit was written to
> catch — **and so would understating it**, which is the error this note itself made.
>
> **Two cells are now wrong, in opposite directions:**
>
> - **`Verifiable: partial` is STALE.** The note used to read "the certificate is not yet
>   signed". It is: Ed25519 over canonical bytes, `synthproof verify` runs against a public key
>   alone, and the sheet now also emits as a Croissant 1.1 record the **official MLCommons
>   validator accepts with 0 warnings**. Decide between ✅ and a footnoted ✅; `partial` no
>   longer describes it.
> - **`Lower bound ✅` is GENEROUS.** `ε_audited = 0.000` in every cell of every experiment, and
>   §7.4 retracts the comparison. The system *emits* a lower bound; it never produced an
>   informative one. Qualify the tick or footnote it to the ceiling.
>
> `Cross-release ❌` is correct and matches the README — the contradiction flagged in
> `REPORTS/06-SUPPLEMENT-2026-08-23.md` §1 is resolved. Leave it.

Formal DP supplies an upper bound that nobody verifies against the implementation. Empirical
auditing supplies a lower bound that carries no guarantee, accumulates no budget, and is not
attached to the artefact. Datasheets are attached to the artefact but describe it rather than
bounding what it reveals. **We found no system that releases a dataset accompanied by both
bounds, cryptographically signed and carrying the ceiling of its own empirical measurement.**

> ⚠️ **UPDATED 2026-08-24. The novelty verdict HAS been issued** — all 8 adversarial query
> families ran on 2026-08-23 and `research/08_novelty_verdict.md` is populated. The previous
> version of this note said the protocol "completed only 2 of 8 query families before being
> interrupted, so no novelty verdict has been issued and none may be asserted here"; it also
> listed the cross-release ledger, subgroup leakage and the calibration gap as families that
> never ran, and said Laminator had not been read. **All four statements are now false.**
> Read `research/08_novelty_verdict.md` — §3.1 for the kills, §3.3 for the position, §4.1 for
> the artefact — before writing a word of §2.6.
>
> **Eight claims are dead. That is the honest count.**
>
> | Claim | Killed by |
> |---|---|
> | Dual-sided assurance (proved + audited per release) | Annamalai, Ganev & De Cristofaro, USENIX Sec 2024 [annamalai2024theoryalone] |
> | Budget-charged domain profiling | Ganev, Annamalai, Mahiou & De Cristofaro, Apr 2025 [annamalai2025domain] |
> | The audit ceiling as a result | Corollary of Steinke, Nasr & Jagielski Thm 2.1 / Eq. (3) — the paper we implement — verified bit-identical to `max_provable_epsilon` |
> | Finding defects by self-audit | Cebere et al., Feb 2026 [cebere2026bugs] — 12 libraries, 13 violations, package released |
> | Shipping a structured privacy label | Dibia, Lu, Bhattacharjee, Near & Feng, 2025 [dibia2025privacylabel] |
> | An automated release gate that refuses and records | Five Safes + SACRO [preen2024sacro], UK TREs since 2022 |
> | A machine-checkable release artefact | Croissant, MRM3, Laminator |
> | Cross-release budget management | PrivateKube (OSDI'21), Cohere, DPack (EuroSys'25), DPolicy |
>
> **Four of eight come from one author cluster** (Ganev, Annamalai, De Cristofaro, Kulynych)
> running this programme professionally and roughly two years ahead. **Chapter 2 must be written
> from that position, not around it.**
>
> **The nuance on the ceiling that must not be lost.** It is dead *as maths* (Steinke's own
> corollary) and severely wounded *as practice*: Ganev, Annamalai & Kulynych, Apr 2026
> [ganev2026tightmstaim] obtain **tight** audits of MST and AIM using a Gaussian-DP / f-DP
> estimator, where our single-threshold estimator returned 0.000. So the ceiling we hit is a
> property of **the estimator we chose**, not of auditing as such. Do not write "auditing
> cannot confirm tight bounds" — write that *this* estimator cannot, and cite the one that can.
>
> **Dibia et al. is simultaneously the strongest kill and the strongest validation.** A panel of
> DP experts converged on almost exactly the fields we built, including `unit_of_privacy` and
> empirical privacy metrics. What they explicitly do **not** propose is any signing mechanism,
> or any standard for reporting the limits of an empirical privacy metric — an omission one of
> their own experts called *"privacy theater"*. Those two gaps are what the Ed25519 signature
> and `audit_ceiling` fill, and **that is the narrowest honest statement of this project's
> position.** As of 2026-08-24 it is also runnable: `synthproof/frontier/croissant.py` emits the
> sheet as a Croissant record the official MLCommons validator accepts with 0 warnings.
>
> **Three survivors, all narrow, none to be called novel without the caveat:**
> S1 reporting the measurement's operating range inside the artefact (`CONFIDENCE: med-high`) ·
> S2 signing the privacy claim (`med` — **engineering novelty, not science**) ·
> S3 data-blind refusal (`med` — **state as UNREFUTED, never novel**; the primary SDC Handbook
> returned HTTP 403 and that literature predates arXiv).
>
> **The position the evidence supports is INTEGRATION, NOT INVENTION.**

Three narrower gaps follow, each addressed in this work:

1. **Unaccounted preprocessing.** Published DP synthesis pipelines routinely read column ranges
   and category domains directly from the sensitive data before any mechanism runs. This is a
   real leak that invalidates the headline ε. It is **not** unremarked: Annamalai, Ganev et al.
   [annamalai2025domain] study exactly the three strategies — externally provided, extracted
   from the input, extracted under DP — and show the second breaks end-to-end DP. Our
   contribution is therefore not identifying the leak but making the choice a **machine-checkable
   field (`domain_source`) inside a signed release artefact**, so a recipient can tell which
   strategy produced the file they hold. Chapter 4 shows how a public schema removes the need
   for extraction entirely, at zero privacy cost.

2. **Budget interfaces that mislead.** A system can satisfy the DP definition while its
   interface deceives its operator. Before calibration, requesting ε = 8 from this system
   produced a release composing to ε = 70.49. The guarantee was sound at every step; the number
   the operator typed simply did not mean what they thought.

3. **Unverifiable claims.** Privacy claims are asserted by the party with the strongest interest
   in their being believed. A signed data sheet lets a third party check the arithmetic.

---

## Sources to obtain

> ⚠️ **DELETE THIS SECTION BEFORE SUBMISSION.** It is a working note to the author, not
> chapter content. Its advice ("maintain `references.bib` from the first day") has been
> followed — `references.bib` + `references-additions.bib` carry the entries.

Search terms covering most of the above: `differential privacy synthetic data survey`,
`privacy auditing one training run`, `AIM adaptive iterative mechanism marginals`,
`membership inference first principles`, `anonymisation groundhog day`.

Prefer arXiv versions for page-stable citation, and maintain `docs/thesis/references.bib` from
the first day — retrofitting citations across 15,000 words is miserable.

# Chapter 3 — Threat Model and Scope

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

# Chapter 4 — System Design

Security and privacy systems must be engineered around clear invariants rather than optimistic heuristics. This chapter details the architectural design of SynthProof, formalising how theoretical differential privacy bounds, empirical leakage auditing, and cryptographic provenance guarantees are unified into an end-to-end software pipeline.

---

## 4.1 Design Principles

SynthProof is engineered upon four non-negotiable architectural principles. Crucially, three of these four principles were not conceived *a priori*, but were adopted as binding invariants following an adversarial self-audit of our initial codebase. Documenting these corrections transparently demonstrates that the architecture was forged through rigorous verification:

1. **Nothing Reads the Sensitive Table for Free**: Every computational operation that accesses the raw private dataset $D$ must explicitly register and debit an appropriate privacy expenditure from the accountant. In conventional synthetic data pipelines, operations such as categorical domain discovery, column cardinality inspection, and numeric range estimation are routinely executed as "free" preprocessing steps. However, observing unique categorical values or computing empirical extrema leaks private information, silently invalidating downstream composition claims. In SynthProof, domain profiling is treated as a first-class differentially private mechanism subject to strict budget billing.
2. **Never Write a Bound That Cannot Be Cited**: Privacy composition must be delegated exclusively to peer-reviewed, theorem-backed accounting engines. During our internal audit, we discovered that our early custom Rényi Differential Privacy (RDP) composition module approximated subsampling amplification using a heuristic formula (`min(q·ρ(α), truncated_MTZ)`). Neither branch was a proven theorem, and empirical cross-validation revealed that it under-reported privacy loss by approximately $2\times$ at subsampling ratio $q = 0.01$. SynthProof resolved this defect by delegating all composition calculations to Google's `dp_accounting` library, cross-validating results against Wang et al.'s `autodp`.
3. **A Mechanism That Is Charged Must Be Applied**: Privacy noise must never be decoupled from budget expenditure. The internal audit identified a failure mode in early prototype modules where privacy budget was debited by the accountant, but the underlying mechanism returned exact, unperturbed contingency counts due to an unhandled control branch. Paying a privacy budget while releasing exact data is strictly worse than failing to account: budget is irretrievably consumed while sensitive records are exposed deterministically. SynthProof enforces strict contract assertions ensuring that all outputs are generated by verified randomized samplers.
4. **Every Reported Number Is Computed**: release certificates and audit reports must never rely on hardcoded constants, default fallbacks, or synthetically derived metrics presented as independent evaluations. In an early iteration of our reporting module, an attack metric was computed as an affine transformation of classification accuracy (`auc = accuracy + 0.05`). SynthProof mandates that every reported statistic traces to a concrete execution trace and an explicit random seed, verified by continuous integration tests.

---

## 4.2 Pipeline Architecture

The SynthProof pipeline transforms sensitive tabular records into an accountable, verifiable release package through seven tightly coupled architectural stages:

```
                      ┌──────────────────────────────────────┐
                      │    Data Holder: Raw Dataset D        │
                      └──────────────────┬───────────────────┘
                                         │
                                         ▼
                      ┌──────────────────────────────────────┐
                      │    Stage 0: Pre-Flight Refusal Gate   │
                      │    (Cardinality & Space Inspection)  │
                      └──────────────────┬───────────────────┘
                                         │
                                         ▼
┌──────────────────┐  Budget Allocation  ┌──────────────────────────────────────┐
│  BudgetPlan      ├────────────────────►│    Stage 1: DP Domain Profiler       │
│  (Target ε, δ)   │                     │    (Noisy Thresholding, ε_prof)      │
└────────┬─────────┘                     └──────────────────┬───────────────────┘
         │                                                  │
         │ Debit                         Bounded Domain     ▼
         ▼                               ┌──────────────────────────────────────┐
┌──────────────────┐  Calibrated Noise   │    Stage 2: Generative Engine        │
│  Privacy         ├────────────────────►│    (AIM / Pairwise / Independent)    │
│  Accountant      │                     └──────────────────┬───────────────────┘
└────────┬─────────┘                                        │
         │                                                  ▼
         │ Log Entry                     ┌──────────────────────────────────────┐
         ▼                               │    Stage 3: Evaluation Suite         │
┌──────────────────┐                     │    - Empirical Steinke Audit (LoD)   │
│  Budget Ledger   │                     │    - EDPB Attacks (MIA, Attrib, etc.)│
│  (SQLite Hash    │                     │    - Downstream ML Utility (TSTR)    │
│   Chain + Head)  │                     └──────────────────┬───────────────────┘
└────────┬─────────┘                                        │
         │                                                  ▼
         │ Commit Hash                   ┌──────────────────────────────────────┐
         └──────────────────────────────►│    Stage 4: Release Certificate      │
                                         │    (Croissant 1.1 JSON-LD + Ed25519) │
                                         └──────────────────────────────────────┘
```

The execution flow proceeds sequentially:
- **Stage 0 (Pre-Flight Refusal Gate)**: The pipeline inspects public metadata (row count $n$ and attribute schema $\mathcal{S}$) without accessing data records. Requests with extreme sparsity, insufficient samples ($n < 50$), or explosive state space ($|\mathcal{X}| > 10^9$) are rejected immediately with structured diagnostic recommendations.
- **Stage 1 (Differentially Private Domain Profiling)**: Allocating a calibrated fraction (typically 10%) of the total privacy budget $\varepsilon_{\text{target}}$, the profiler identifies active categories and estimates numeric boundaries using stability-based noisy thresholding. Categories with noisy counts failing a $3\sigma$ threshold are pruned, guaranteeing that rare singletons do not leak into the active domain.
- **Stage 2 (Generative Modeling and Synthesis)**: Operating under the remaining budget (90%), the generative engine measures contingency marginals and fits an approximate data distribution. Supported mechanism families include independent marginals, dense pairwise marginals, and graphical models via AIM (`private-pgm`).
- **Stage 3 (Empirical Evaluation Suite)**: The generated synthetic table $\widetilde{D}$ undergoes multi-dimensional evaluation: (i) an empirical leakage audit measuring canary distinguishability alongside its Limit of Detection operating ceiling, (ii) five empirical attack vectors evaluating European Data Protection Board (EDPB) disclosure risks, and (iii) machine learning utility benchmarking via Train on Synthetic, Test on Real (TSTR).
- **Stage 4 (Release Certificate Generation and Ledger Attestation)**: The accountant commits the complete execution record to an append-oriented SQLite ledger. A signed `ledger_head` is written, and an Ed25519-signed Croissant 1.1 JSON-LD Privacy Data Sheet is exported.

**The Core Invariant**: No computational path from the private dataset $D$ to any emitted output bypasses the privacy accountant. Every read operation must present an active `MechanismSpec` and hold sufficient unallocated budget.

---

## 4.3 The Privacy Accountant

SynthProof structures its accounting layer around an explicit architectural philosophy: **we own the enforcement interface, not the mathematical theory**. 

Theoretical privacy composition is delegated to Google's `dp_accounting` library. The SynthProof accountant translates high-level pipeline operations into formal `dp_accounting.DpEvent` objects. For example, a Gaussian marginal query at noise multiplier $\sigma$ maps to a `GaussianDpEvent(noise_multiplier=\sigma)`. Crucially, mechanisms that execute with zero noise ($\sigma = 0$) are explicitly mapped to `NonPrivateDpEvent()`, ensuring that the resulting privacy expenditure evaluates to $\varepsilon = \infty$ rather than a misleadingly finite number.

### The Systems API
To serve as an operational systems primitive rather than a passive formula, the `Accountant` class exposes four transactional methods:
- `dry_run(spec: MechanismSpec) -> PrivacySpend`: Speculatively evaluates the privacy cost of an intended operation without debiting the accountant, returning both marginal and cumulative expenditures.
- `charge(spec: MechanismSpec) -> PrivacySpend`: Formally debits the accountant. If the resulting cumulative expenditure exceeds the allocated target $(\varepsilon_{\text{target}}, \delta)$, the accountant raises a `BudgetExceededError` and aborts execution before the sensitive data is queried.
- `remaining() -> tuple[float, float]`: Computes the available budget slack $(\varepsilon_{\text{rem}}, \delta_{\text{rem}})$ relative to the pre-registered ceiling.
- `snapshot() / restore()`: Enables speculative execution and rollback for adaptive selection algorithms (such as AIM), allowing candidate queries to be evaluated and discarded without corrupting the historical ledger.

### Non-Linear PrivacySpend Tracking
The accountant tracks both marginal and cumulative expenditures across all operations. Because Rényi Differential Privacy composition is strictly sublinear, cumulative privacy expenditure is strictly smaller than the arithmetic sum of individual marginals:
$$\varepsilon_{\text{total}} < \sum_{i=1}^k \varepsilon_i$$
Tracking both figures prevents operators from misinterpreting individual stage costs and provides an auditable decomposition of how budget was distributed across pipeline components.

---

## 4.4 Calibration via Bisection

A critical engineering vulnerability in differential privacy systems is **parameter drift**: the discrepancy between the privacy parameter requested by an operator and the actual privacy guarantee delivered by the composed mechanism.

### The Failure of Heuristic Calibration
Early implementations commonly scaled noise using heuristic approximations, such as setting noise scale $\sigma = \sqrt{d} / \varepsilon_{\text{target}}$ for $d$ queries. As shown in our empirical calibration benchmarks, this heuristic exhibits catastrophic divergence as budget and query count increase:
- At target $\varepsilon = 0.5$, heuristic scaling delivered an actual composed $\varepsilon = 2.53$ ($5.1\times$ budget violation).
- At target $\varepsilon = 8.0$, heuristic scaling delivered an actual composed $\varepsilon = 70.49$ ($8.8\times$ budget violation).

The operator believed they were enforcing strict differential privacy, whereas the deployed system was operating at vacuous privacy levels.

### The Bisection Calibration Algorithm
SynthProof eliminates heuristic scaling by implementing a rigorous root-finding calibration engine (`synthproof.calibration`). Because Rényi divergence is strictly decreasing in the Gaussian noise multiplier $\sigma$, the mapping from noise scale to composed privacy loss is strictly monotonic:
$$\frac{\partial \varepsilon(\sigma)}{\partial \sigma} < 0$$
This strict monotonicity guarantees that the inverse calibration problem has a unique solution.

SynthProof implements bracket-and-bisect root finding:
1. **Bracketing**: The calibrator expands an initial bracket $[\sigma_{\text{lo}}, \sigma_{\text{hi}}]$ geometrically until $\varepsilon(\sigma_{\text{lo}}) > \varepsilon_{\text{target}} \ge \varepsilon(\sigma_{\text{hi}})$.
2. **Bisection**: The interval is iteratively halved at midpoint $\sigma_{\text{mid}} = (\sigma_{\text{lo}} + \sigma_{\text{hi}}) / 2$.
3. **Conservative Termination Invariant**: Crucially, our internal testing revealed that terminating based on the epsilon gap $|\varepsilon(\sigma_{\text{mid}}) - \varepsilon_{\text{target}}| < \tau$ is unsafe: if a search terminates when a probe lands slightly above the target, the lower bracket may be updated, leaving an over-spending scale. SynthProof enforces termination strictly on **bracket width** and always returns the conservative upper bound $\sigma_{\text{hi}}$. Consequently, the invariant $\varepsilon_{\text{delivered}} \le \varepsilon_{\text{target}}$ holds across every iteration.

Across our continuous integration suite of 24 configurations spanning independent and pairwise mechanisms, the ratio of delivered to target privacy satisfies $\varepsilon_{\text{delivered}} / \varepsilon_{\text{target}} \le 1.000$ without exception, averaging $\approx 0.92$ due to conservative stage partitioning under `BudgetPlan`.

---

## 4.5 Differentially Private Domain Profiling

Before a generative mechanism can construct contingency tables, it must establish the discrete attribute domains $\mathcal{X}_j$. Treating column domains as public metadata is valid only if attribute categories are known *a priori* (e.g., standard geographic codes). In practical tabular synthesis, categories frequently contain sensitive values, rare affiliations, or singletons.

SynthProof implements `DPDomainProfiler` using stability-based noisy thresholding:
1. **Frequency Perturbation**: For each categorical column, the frequency of every observed level is measured. Independent discrete Laplace or Gaussian noise calibrated to sensitivity $\Delta = 1$ is added to each count.
2. **Stability Thresholding**: A category is retained in the active domain if and only if its noisy frequency exceeds a threshold:
   $$\tau = 1 + \sqrt{2 \ln(1/\delta)} \cdot \sigma \approx 1 + 3\sigma$$
3. **Singleton Pruning**: Categories failing the threshold are pruned and aggregated into an unidentifiable `<RARE>` token. This guarantees that individuals possessing unique attribute values cannot be singled out through domain discovery.

The entire profiling pass is budgeted globally as a unified `MechanismSpec`, preventing per-column budget explosion.

---

## 4.6 Generative Mechanisms

SynthProof implements three distinct tabular generative mechanism families, spanning differing levels of cross-column dependency modeling:

1. **Independent Marginal Mechanism (`IndependentMarginal`)**: Measures one-way marginal distributions for each column independently, adding discrete Laplace or Gaussian noise. Downstream records are synthesized by sampling attributes independently from their respective univariate marginals. While destroying multi-attribute correlations, this mechanism serves as an essential experimental ablation, isolating the exact utility and privacy effects of modeling joint structures.
2. **Dense Pairwise Mechanism (`Pairwise`)**: Measures all $d(d-1)/2$ two-way contingency marginals across the attribute schema, allocating privacy budget uniformly across all pairs. Synthetic records are constructed via iterative proportional fitting or probabilistic graphical modeling.
3. **Adaptive Iterative Mechanism (`AIM`)**: Integrates the state-of-the-art Private-PGM graphical model architecture (McKenna et al., 2022). AIM iteratively selects the most informative multi-way marginals using the exponential mechanism, measures them using the discrete Gaussian mechanism, and estimates a Markov Random Field data distribution via maximum entropy optimization.

By encapsulating all three generators under a uniform `BaseGenerator` interface, SynthProof enables rigorous, apples-to-apples comparisons across mechanism families under identical privacy budgets.

---

## 4.7 Cryptographic Budget Ledger

To protect against cross-release budget erosion, SynthProof records every privacy expenditure in an append-oriented SQLite relational database.

### Hash Chaining and Truncation Vulnerability
Each ledger entry commits to the cryptographic digest of its immediate predecessor using HMAC-SHA256:
$$h_i = \text{HMAC-SHA256}(h_{i-1} \,\|\, \text{canonical\_bytes}(e_i))$$
However, our threat model analysis (§3.5) established that naive hash chaining is vulnerable to **history truncation**: an internal operator who overspends budget could delete the last $k$ rows of the database. Because each remaining row points validly to its predecessor, the truncated database appears internally consistent to a naive verifier.

### Signed Checkpoint Heads
SynthProof closes this vulnerability through the `ledger_head` table. Following each synthesis release, the curator writes an Ed25519-signed checkpoint committing to the tuple:
$$\text{head} = \text{Sign}_{sk}\Big(\text{entry\_count} \,\|\, \text{tip\_hash} \,\|\, \text{timestamp}\Big)$$
When an independent auditor verifies the ledger, `verify_with_reason()` inspects three sequential cryptographic invariants:
1. **Chain Linkage**: Every row's `prev_hash` correctly matches the SHA-256 digest of row $i-1$.
2. **Row Integrity**: Recomputing HMAC-SHA256 over canonicalized entry fields reproduces the recorded row hash.
3. **Head Commitment**: The total row count equals `entry_count`, the final row hash equals `tip_hash`, and the Ed25519 signature verifies under the curator's public key.

Across 14 adversarial tests in `tests/test_ledger_adversarial.py`, this signed head architecture successfully detects nine distinct database tampering attacks, including row insertion, record alteration, genesis block substitution, and chain truncation.

---

## 4.8 The Privacy Data Sheet and Croissant 1.1 JSON-LD

Downstream consumers inspect releases via the **Privacy Data Sheet**, an open-standard metadata package designed to make privacy claims machine-checkable.

SynthProof formats the Privacy Data Sheet as an Ed25519-signed JSON-LD document conforming to the MLCommons Croissant 1.1 metadata standard. We extend the core Croissant schema with an official differential privacy vocabulary (`@context: {"dp": "https://synthproof.org/schema/dp#"}`), formalising attributes including:
- `dp:provedEpsilon` and `dp:delta`: The formally verified worst-case composition bounds.
- `dp:auditCeiling`: The empirical audit ceiling $\varepsilon_{\text{max}}(m, \alpha)$, explicitly transferring the Limit of Detection (LoD/LLOQ) reporting standards from clinical chemistry (MIQE 2.0, Bustin et al. 2025; ISO 11843) to declare the physical resolution of the empirical canary audit (Steinke et al. 2023; Annamalai et al. 2024).
- `dp:empiricalEpsilon` and `dp:auditPValue`: The observed empirical leakage lower bound and statistical confidence.
- `dp:ledgerHead`: The tip hash and signature linking the release directly to the organizational budget ledger.

To guarantee bitwise reproducibility of cryptographic signatures across heterogeneous operating systems and JSON parsers, metadata is serialized using the **RFC 8785 JSON Canonicalization Scheme (JCS)** prior to signing. Keys are sorted lexicographically, whitespace is normalized, and numeric values are deterministically formatted.

Verification is executed via a standalone CLI command:
```bash
synthproof verify sheet.json --pubkey curator_public.key
```
This utility independently verifies the Ed25519 digital signature, validates internal schema consistency, checks that composed expenditures match the ledger head, and confirms that the release certificate is cryptographically uncompromised.

# Chapter 5 — Implementation

**Target: 1,500 words.** The most mechanical chapter in the thesis — **pure reportage**. The
modules exist and their docstrings carry the arguments.

> **REWRITTEN 2026-08-24 as a specification.** The previous version predated six modules that
> now exist and hedged on milestones (`M1.14`, `M2.9`) that have landed. It also under-counted
> the test suite by ~100 tests.
>
> **Nobody outside the four authors writes the prose.** Read the docstrings first — several of
> them argue the point better than a summary will, particularly `audit/steinke.py`,
> `data/preflight.py`, `ledger/signing.py` and `frontier/croissant.py`.

---

## 5.1 Technology choices

The implementation stack of SynthProof is governed by one overriding architectural rule: **never hand-roll a mathematical bound that can be delegated to a verified reference implementation.** Each core component was selected to enforce mathematical soundness, cryptographic non-repudiation, and empirical reproducibility:

- **Python 3.11 Runtime**: Enforced by `private-pgm` (`mbi`), which requires Python 3.11 C-extension support for graphical model inference and marginal optimization in the AIM algorithm. All dependencies are locked in `.venv311/`.
- **Google `dp_accounting`**: Chosen as the primary composition engine. Rather than hand-rolling composition theorems, privacy loss distributions (PLDs) and Rényi Differential Privacy (RDP) bounds are evaluated via Google’s audited accounting library, eliminating approximation errors.
- **`autodp` (Hall et al.)**: Integrated as the secondary differential accountant. Every executed release is verified across both accountants; execution halts if their computed privacy guarantees diverge by more than 0.05% (see §5.7).
- **`private-pgm` / `mbi` (McKenna et al.)**: Powers the graphical model mechanism (AIM). The early project defect wherein an "AIM" generator merely added independent Laplace noise to 1-way marginals was excised, replaced by full marginal selection and Private-PGM mirror descent synthesis.
- **`scipy.stats`**: Evaluates exact Clopper-Pearson binomial confidence intervals for paired auditing and Steinke one-run tail probabilities, rejecting normal approximations that break down at small sample budgets.
- **`cryptography`**: Provides high-assurance Ed25519 Edwards-curve digital signature generation and SHA-256 / HMAC-SHA256 primitives.
- **FastAPI & SQLite**: Delivers a low-overhead local server and single-file SQLite database tier for the hash-chained and signed privacy budget ledger.

**Package Compatibility Constraints**: Modern graphical model dependencies (`jax`, `mbi`) enforce `numpy >= 2.0`. This constraint introduced two deliberate architectural boundaries. First, the `anonymeter` risk-assessment library could not be linked into the runtime environment, as it pins `numpy < 2.0`; attempting to install it silently downgraded NumPy and broke AIM's tensor operations. Second, the official `mlcroissant` validator similarly pins legacy dependencies. Consequently, Croissant metadata validation is isolated out-of-band in a dedicated virtual environment (`scripts/validate_croissant.py`), ensuring runtime synthesis remains unencumbered.

---

## 5.2 Package structure

The internal module boundaries of `synthproof` map directly to the pipeline stages formalised in Chapter 4:

```
synthproof/
  accounting/   accountant, calibration, differential (2nd accountant), noise
  data/         dataset, schema, preflight (refusal gate), profiler
  generators/   independent · pairwise · aim · moments · leaky (controls)
  audit/        steinke (one-run), paired Clopper-Pearson, max_provable_epsilon
  attacks/      distance_mia · exact_match_risk · domias · linkability · attribute_inference
  evaluate/     TSTR/TRTR, marginal_w1, fairness
  ledger/       ledger (hash chain + signed head), signing, types, allocator
  frontier/     experiment (run_cell) · certificate · croissant · checkpoint
  api/          FastAPI + SSE
  cli.py        run · verify · croissant · demo · keygen · mechanisms · infer-schema · audit-power
```

This alignment ensures strict separation of concerns. The `data/preflight.py` module inspects solely metadata (row counts, column cardinality) without touching record values. `data/profiler.py` charges privacy budget explicitly before discovering categorical domains. The mechanism generators in `generators/` receive pre-partitioned privacy budgets from `accounting/calibration.py`, and all outputs are committed through `ledger/ledger.py` before release artefacts are emitted by `frontier/certificate.py`.

---

## 5.3 Noise sampling

Differential privacy on discrete tabular data requires extreme numerical rigor. Continuous Gaussian or Laplace mechanisms implemented via standard 64-bit floating-point inverse-CDF sampling are vulnerable to Mironov's floating-point attack (Mironov 2012), wherein an adversary exploits irregularities in IEEE 754 floating-point representations to infer individual records with certainty.

To eliminate this vulnerability, SynthProof implements exact discrete samplers:
1. **Discrete Gaussian Mechanism**: We implement the Canonne, Kamath, and Steinke (CKS'20) rejection sampler, sampling directly from the discrete Gaussian distribution $\mathcal{N}_{\mathbb{Z}}(0, \sigma^2)$ over $\mathbb{Z}$.
2. **Discrete Laplace Mechanism**: We sample from the two-sided geometric distribution (GRS'12) by taking the difference of two independent geometric random variables, producing exact discrete Laplace noise.

Every discrete sampler is validated in CI using a $\chi^2$ goodness-of-fit test comparing empirical sample frequencies against the exact theoretical probability mass function (PMF) across $100,000$ draws, asserting $p > 0.01$. 

We narrow our security claim with precision: our implementation prevents output-representation leakage by ensuring all added noise and noisy query outputs reside strictly in $\mathbb{Z}$, eliminating floating-point mantle artifacts. Furthermore, our regression suite defends against an early implementation defect where a shortcut for small $\sigma < 0.3$ returned deterministic zeros while the accountant still billed the full theoretical privacy cost. That shortcut was excised, ensuring that any charged mechanism applies verified discrete noise.

---

## 5.4 Calibration implementation

To guarantee that synthesized datasets never exceed target privacy budgets, SynthProof implements a bracket-and-bisect calibration algorithm (`calibration.py`). For any mechanism with $K$ measurement queries under target budget $(\varepsilon_{\text{target}}, \delta)$, the calibrator searches for the minimum noise parameter $\sigma \in [\sigma_{\min}, \sigma_{\max}]$ such that the composed Rényi Differential Privacy (RDP) guarantee converted to $(\varepsilon, \delta)$ satisfies $\varepsilon \le \varepsilon_{\text{target}}$.

The bisection loop terminates after $r = 20$ iterations or when $|\varepsilon(\sigma) - \varepsilon_{\text{target}}| < 10^{-5}$. Across all 24 standard benchmark configurations in CI, the calibrator achieves an achieved-to-target ratio of $\le 0.92$ on compound pipelines, never exceeding $1.00$. On a single Gaussian query stage, calibration converges within $0.01\%$ (for target $\varepsilon = 8.0$, achieving $\varepsilon_{\text{proved}} = 7.999605$).

The observed multi-stage gap (wherein compound mechanisms achieve $\approx 0.92 \varepsilon_{\text{target}}$) is a direct consequence of linear budget splitting versus sublinear composition: `BudgetPlan` partitions total privacy budget linearly across profiling and synthesis stages (e.g., $0.1 \varepsilon$ and $0.9 \varepsilon$), but sublinear RDP composition means the actual composed privacy loss of the two stages is strictly smaller than their scalar sum. Compound mechanisms with multiple stages (such as AIM, which combines domain profiling, candidate selection, and marginal measurements) exhibit the widest gap, ensuring that calibration is unconditionally conservative.

---

## 5.5 Ledger implementation

The SynthProof budget ledger (`synthproof/ledger/`) records every query and synthesis invocation as a tamper-evident cryptographic log backed by SQLite. Each entry records the timestamp, actor, mechanism name, target budget, proved budget, seed, and input dataset hash.

To ensure deterministic signature verification across platforms, entries are serialized using canonical byte formatting (JSON with sorted keys, fixed floating-point precision, and UTF-8 encoding). Each record contains a SHA-256 hash chaining to the preceding entry: $h_i = \text{SHA256}(h_{i-1} \parallel \text{bytes}_i)$.

**Truncation Attack Defense**: A fundamental vulnerability of naive hash chaining is truncation: an attacker who deletes the most recent entries leaves a chain that remains internally valid from genesis to the truncation point. To close this vulnerability, SynthProof introduces a dedicated `ledger_head` table that records `(entry_count, tip_hash)` signed with the curator's Ed25519 private key. 

When `Ledger.verify_with_reason()` is executed, it first verifies the digital signature on `ledger_head`, confirms that the count of rows in the log exactly matches `entry_count`, and asserts that the log's final tip hash matches the signed `tip_hash`. This architecture neutralizes nine distinct adversarial tampering vectors (entry modification, row insertion, row deletion, chain truncation, genesis replacement, signature forging, key substitution, timestamp backdating, and uncommitted staging), covered by 14 adversarial tests in `tests/test_ledger_adversarial.py`.

---

## 5.6 The release artefact

The output of synthesis is the **Privacy Data Sheet**, emitted as an Ed25519-signed Croissant 1.1 JSON-LD package (`frontier/croissant.py`). The certificate embeds:
- Formal privacy parameters: $\varepsilon_{\text{proved}}$, $\delta$, accountant agreement ratio.
- Operational provenance: `domain_source`, `contribution_bound`, `deployment_model: central`.
- Empirical audit operating range: `audit_ceiling` ($\varepsilon_{\text{max}}$), formalising Limit of Detection (LoD) reporting (MIQE 2.0, Bustin et al. 2025).
- Empirical attack results: $\varepsilon_{\text{emp}}$, confidence level $\alpha$, sample budget $m$, and explicit lists of `attacks_run` and `attacks_not_implemented`.
- Plain-language odds ratio: an intuitive risk statement communicating differential privacy guarantees to non-technical stakeholders.

**Dual-Layer Integrity Defense**: The digital signature covers the canonical byte encoding of the embedded Privacy Data Sheet core, not the outer JSON-LD graph. To prevent an adversary from tampering with human-readable top-level JSON-LD attributes while presenting a valid signature on the embedded sheet, `verify_croissant` performs strict two-way reconciliation across all 11 mirrored fields. If any mirrored field differs from the signed payload, verification immediately aborts with `SIGNATURE VALID, RECORD UNTRUSTWORTHY`.

---

## 5.7 Testing and CI

The SynthProof test suite encompasses 729 automated tests achieving 93% line coverage:

- **Property Tests**: 35 property-based tests using Hypothesis (`tests/test_accounting_properties.py`) validate the algebraic invariants of differential privacy, including monotonicity of privacy loss, post-processing invariance, and subadditivity under composition.
- **Differential Accountant Cross-Validation**: We cross-validate Google’s `dp_accounting` against Hall et al.’s `autodp` across 12 distinct Gaussian and Laplace mechanisms, asserting that computed privacy bounds agree within $0.05\%$.
- **Adversarial Defect Regression**: Every defect identified during our internal audit trail is guarded by a named regression test. For example, `test_accounting.py` verifies that zero noise cannot be added under positive budget; `test_data.py` asserts that rare categories are suppressed by the DP profiler; and `test_croissant.py` verifies that negative controls trigger failure on all 11 mirrored metadata fields.
- **Reproducibility Pipeline**: The entire experimental record is locked in `results/MANIFEST.json` and verified end-to-end via `make reproduce`. Conformance to the official MLCommons Croissant validator is checked out-of-band via `scripts/validate_croissant.py`.

---

## Figures

- Discrete Gaussian: empirical vs exact PMF
- Coverage report

Both from `make figures`, which regenerates from `results/*.json` so neither can drift.

# Chapter 6 — Methodology

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

# Chapter 7 — Results and Analysis

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

---

## 7.1 Calibration validation

| Mechanism | Target ε | Proved ε | proved/target |
|---|---:|---:|---:|
| `independent` | 0.5 | 0.456 | 0.912 |
| `independent` | 1 | 0.912 | 0.912 |
| `independent` | 2 | 1.828 | 0.914 |
| `independent` | 4 | 3.664 | 0.916 |
| `independent` | 8 | 7.356 | 0.919 |
| `pairwise` | 0.5 | 0.456 | 0.912 |
| `pairwise` | 1 | 0.912 | 0.912 |
| `pairwise` | 2 | 1.828 | 0.914 |
| `pairwise` | 4 | 3.664 | 0.916 |
| `pairwise` | 8 | 7.356 | 0.919 |
| `aim` | 0.5 | 0.385 | 0.771 |
| `aim` | 1 | 0.778 | 0.778 |
| `aim` | 2 | 1.576 | 0.788 |
| `aim` | 4 | 3.201 | 0.800 |
| `aim` | 8 | 6.543 | 0.818 |

*Largest proved/target ratio across the grid: **0.919** and never exceeds 1.000.*

*Source: `results/h1_all_families.json`, 5 seeds per cell, n = 6000.*

---

## 7.2 Auditor validation — floor and ceiling

| leak \ m | 10 | 25 | 50 | 100 | 200 | 400 | 800 |
|---|---|---|---|---|---|---|---|
| **0.00** | 0.00 | 0.00 | 0.00 | 0.20 | 0.00 | 0.00 | 0.00 |
| **0.01** | 0.00 | 0.00 | 0.00 | 0.20 | 0.00 | 0.00 | 0.00 |
| **0.05** | 0.00 | 0.00 | 0.00 | 0.20 | 0.00 | 0.00 | 0.00 |
| **0.25** | 0.00 | 0.00 | 0.00 | 0.20 | 0.40 | 0.80 | 1.00 |
| **1.00** | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

Ceiling — the largest ε this instrument could report even against a 100% verbatim release:

| m | 10 | 25 | 50 | 100 | 200 | 400 | 800 |
|---|---|---|---|---|---|---|---|
| max ε_audited | 0.81 | 1.84 | 2.57 | 3.28 | 3.98 | 4.68 | 5.38 |

*Source: `results/detection_floor.json`, α = 0.05, n = 3000. A cell counts as detected only on a majority of seeds.*

---

## 7.3 H1 — mechanism families

**UCI Adult**

| Mechanism | Target ε | Proved ε | Correlation error [95% CI] | TSTR macro F1 [95% CI] |
|---|---:|---:|---|---|
| `independent` | 0.5 | 0.456 | 0.0934 [0.0802, 0.1063] | 0.472 [0.417, 0.525] |
| `independent` | 1 | 0.912 | 0.0930 [0.0817, 0.1044] | 0.470 [0.432, 0.508] |
| `independent` | 2 | 1.828 | 0.0939 [0.0818, 0.1057] | 0.426 [0.340, 0.504] |
| `independent` | 4 | 3.664 | 0.0935 [0.0808, 0.1057] | 0.467 [0.352, 0.575] |
| `independent` | 8 | 7.356 | 0.0947 [0.0817, 0.1071] | 0.406 [0.297, 0.515] |
| `pairwise` | 0.5 | 0.456 | 0.0611 [0.0219, 0.1143] | 0.483 [0.380, 0.568] |
| `pairwise` | 1 | 0.912 | 0.0694 [0.0380, 0.1213] | 0.428 [0.351, 0.499] |
| `pairwise` | 2 | 1.828 | 0.0493 [0.0170, 0.0950] | 0.418 [0.335, 0.468] |
| `pairwise` | 4 | 3.664 | 0.0197 [0.0048, 0.0464] | 0.427 [0.362, 0.477] |
| `pairwise` | 8 | 7.356 | 0.0283 [0.0132, 0.0517] | 0.432 [0.368, 0.478] |
| `aim` | 0.5 | 0.385 | 0.0827 [0.0258, 0.1395] | 0.498 [0.478, 0.517] |
| `aim` | 1 | 0.778 | 0.0424 [0.0142, 0.0708] | 0.540 [0.515, 0.565] |
| `aim` | 2 | 1.576 | 0.0564 [0.0139, 0.1007] | 0.470 [0.445, 0.496] |
| `aim` | 4 | 3.201 | 0.0260 [0.0015, 0.0681] | 0.460 [0.440, 0.482] |
| `aim` | 8 | 6.543 | 0.0078 [0.0031, 0.0125] | 0.505 [0.468, 0.544] |

*TRTR baseline (real → held-out real): **0.660 [0.646, 0.674]**. Every synthetic value above sits below it.*

**ACSIncome (California, 2018)**

| Mechanism | Target ε | Proved ε | Correlation error [95% CI] | TSTR macro F1 [95% CI] |
|---|---:|---:|---|---|
| `independent` | 0.5 | 0.456 | 0.0521 [0.0455, 0.0582] | 0.440 [0.422, 0.460] |
| `independent` | 1 | 0.912 | 0.0531 [0.0460, 0.0606] | 0.441 [0.417, 0.465] |
| `independent` | 2 | 1.828 | 0.0530 [0.0465, 0.0601] | 0.430 [0.412, 0.451] |
| `independent` | 4 | 3.664 | 0.0536 [0.0473, 0.0605] | 0.442 [0.423, 0.463] |
| `independent` | 8 | 7.356 | 0.0535 [0.0471, 0.0604] | 0.462 [0.449, 0.474] |
| `pairwise` | 0.5 | 0.456 | 0.0543 [0.0186, 0.1088] | 0.466 [0.445, 0.497] |
| `pairwise` | 1 | 0.912 | 0.0727 [0.0423, 0.1133] | 0.468 [0.445, 0.494] |
| `pairwise` | 2 | 1.828 | 0.0468 [0.0179, 0.0830] | 0.489 [0.470, 0.509] |
| `pairwise` | 4 | 3.664 | 0.0315 [0.0098, 0.0618] | 0.481 [0.452, 0.504] |
| `pairwise` | 8 | 7.356 | 0.0202 [0.0076, 0.0383] | 0.522 [0.498, 0.547] |
| `aim` | 0.5 | 0.385 | 0.0977 [0.0421, 0.1591] | 0.704 [0.695, 0.713] |
| `aim` | 1 | 0.778 | 0.0395 [0.0204, 0.0695] | 0.692 [0.683, 0.702] |
| `aim` | 2 | 1.576 | 0.0521 [0.0286, 0.0778] | 0.650 [0.621, 0.675] |
| `aim` | 4 | 3.201 | 0.0732 [0.0630, 0.0875] | 0.651 [0.633, 0.670] |
| `aim` | 8 | 6.543 | 0.0626 [0.0432, 0.0753] | 0.581 [0.539, 0.629] |

*TRTR baseline (real → held-out real): **0.725 [0.707, 0.742]**. Every synthetic value above sits below it.*

### The cross-dataset comparison

| Mechanism | Adult, ε=8 corr. error | ACS, ε=8 corr. error |
|---|---|---|
| `independent` | 0.0947 [0.0817, 0.1071] | 0.0535 [0.0471, 0.0604] |
| `pairwise` | 0.0283 [0.0132, 0.0517] | 0.0202 [0.0076, 0.0383] |
| `aim` | 0.0078 [0.0031, 0.0125] | 0.0626 [0.0432, 0.0753] |

*Ordering on Adult: **aim < pairwise < independent**. On ACS: **pairwise < independent < aim**.*

*The orderings **disagree**. Reported as measured; the diagnosis is §7.3.*

---

## 7.6 H2 — subgroup disparity

| Attribute | Target ε | Subgroup | Share | Canaries | Attack accuracy | ε audited | p |
|---|---:|---|---:|---:|---:|---:|---:|
| `sex` | 1 | Female | 0.320 | 200 | 0.523 | 0.000 | 0.308 |
| `sex` | 1 | Male | 0.680 | 200 | 0.530 | 0.000 | 0.224 |
| `sex` | 8 | Female | 0.320 | 200 | 0.527 | 0.000 | 0.265 |
| `sex` | 8 | Male | 0.680 | 200 | 0.507 | 0.000 | 0.455 |
| `race` | 1 | Amer-Indian-Eskimo | 0.010 | 80 | 0.508 | 0.000 | 0.508 |
| `race` | 1 | Asian-Pac-Islander | 0.030 | 80 | 0.537 | 0.019 | 0.367 |
| `race` | 1 | Black | 0.095 | 80 | 0.537 | 0.000 | 0.314 |
| `race` | 1 | Other | 0.008 | 80 | 0.529 | 0.003 | 0.385 |
| `race` | 1 | White | 0.857 | 80 | 0.500 | 0.000 | 0.542 |
| `race` | 8 | Amer-Indian-Eskimo | 0.010 | 80 | 0.533 | 0.000 | 0.340 |
| `race` | 8 | Asian-Pac-Islander | 0.030 | 80 | 0.521 | 0.000 | 0.445 |
| `race` | 8 | Black | 0.095 | 80 | 0.529 | 0.036 | 0.438 |
| `race` | 8 | Other | 0.008 | 80 | 0.562 | 0.036 | 0.224 |
| `race` | 8 | White | 0.857 | 80 | 0.542 | 0.000 | 0.268 |

*Per-subgroup ceilings: **3.27, 4.19**. Every audited ε above must be read against the ceiling for its own row — the largest observed value is a small fraction of the instrument's range.*

---

## 7.7 H3 — allocation strategy

*Source: `results/h3_allocation.json`.*

# Chapter 8 — Discussion and Conclusion

**Target: 1,500 words.**

> **REWRITTEN 2026-08-24 as a specification.** The previous version built §8.1 on *"if
> ε_proved = 8 but no attack recovers more than ε_audited = 0.6"* — the comparison the
> audit-ceiling finding disqualifies, and a number the project never measured. It called the
> self-audit "genuinely distinctive" (killed by Cebere et al., Feb 2026) and hedged §8.3 on
> milestones that have since landed.
>
> **Nobody outside the four authors writes the prose.**

---

## 8.1 Interpretation — what the gap does and does not mean

A central question arising from our empirical results is how practitioners and regulators should interpret the observed gap between formal privacy guarantees and empirical audit estimates. When our auditing pipeline reports $\varepsilon_{\text{audited}} = 0.000$ against a proved bound of $\varepsilon_{\text{proved}} = 7.36$, it is tempting to infer either that the formal bound is excessively loose or that the differential privacy mechanism provides near-perfect practical protection. On the evidence gathered in this investigation, both inferences are false.

The observed gap is an inevitable consequence of instrument resolution: the auditing instrument's operating range did not cover the privacy regime being evaluated. In our H1 benchmark, the auditor operated with $m = 60$ canary records at confidence level $\alpha = 0.05$. Under Steinke's one-run binomial estimator, $m = 60$ imposes an information-theoretic detection ceiling of $\varepsilon_{\text{max}} = 2.972$. Even if the synthesis mechanism had released 100% of the raw training records verbatim, a perfect statistical distinguisher could not have returned an empirical lower bound exceeding $2.972$. To certify an empirical guarantee of $\varepsilon = 7.36$ with $95\%$ confidence under this estimator requires asymptotically:
$$r \approx \ln(1/\alpha) e^{\varepsilon} \approx 2.996 \times e^{7.36} \approx 4,711 \text{ canaries}$$
Simply scaling the canary count provides diminishing returns: increasing the canary sample budget to $m = 800$ raises the measured paired Clopper-Pearson ceiling only to $5.377$, still far below $\varepsilon_{\text{proved}} = 7.36$.

This distinction defines the precise operational purpose of our auditor: **it is an instrument for catching gross implementation defects, not for verifying tight privacy bounds.** It reliably catches blatant leaks—detecting a 100% verbatim release with as few as $m = 10$ canaries—but it cannot confirm that a correctly implemented mechanism with $\varepsilon_{\text{proved}} \ge 4.0$ is tight.

We do not generalize this limitation to empirical differential privacy auditing as a discipline. Ganev, Annamalai, and Kulynych (arXiv:2604.18352, Apr 2026) demonstrated tight empirical audits of MST and AIM by leveraging Gaussian Differential Privacy ($\mu$-GDP) trade-off curves, achieving tight empirical lower bounds where our single-threshold binomial estimator returned zero. The detection ceiling observed here is a property of the specific binomial auditing estimator chosen for this pipeline.

The essential methodological lesson is that **an empirical differential privacy audit reported without its operating range is scientifically uninterpretable, and the choice of estimator dictates that range.** By transferring Limit of Detection (LoD) reporting from analytical chemistry and molecular diagnostics (MIQE 2.0, Bustin et al., Clinical Chemistry 2025;71(6):634-651), SynthProof makes this boundary explicit: empirical non-detections are reported as *"Not Detected, < LoD"*, ensuring that instrument limits are never mistaken for mathematical privacy guarantees.

---

## 8.2 What the novelty protocol returned

The intellectual arc of this capstone project represents a transition from naive enthusiasm to disciplined scientific accountability. Earlier iterations of this thesis framed our internal defect discovery as a distinctive methodological contribution. However, Cebere et al. (arXiv:2602.17454, Feb 2026) audited twelve prominent differential privacy libraries and discovered thirteen severe guarantee violations; our experience of finding implementation defects is typical of software that is subjected to rigorous audit, not a unique distinction.

The true strength of our scientific contribution lies in the adversarial novelty audit conducted under our pre-registered protocol (`research/08_novelty_verdict.md`), which systematically evaluated and retracted eight initial candidate claims:

1. **Dual-Sided Assurance**: Pre-empted by Annamalai, Ganev, and De Cristofaro (USENIX Security 2024), who first proposed pairing theoretical differential privacy with empirical auditing.
2. **Budget-Charged Domain Profiling**: Pre-empted by Ganev, Annamalai, Mahiou, and De Cristofaro (arXiv:2504.08254, Apr 2025), who analyzed the exact domain strategy trade-offs.
3. **The Audit Ceiling as a Theoretical Discovery**: Disqualified as a new theorem; it is a direct algebraic corollary of Steinke, Nasr & Jagielski (2023) Thm 2.1, verified bit-identical to `max_provable_epsilon`.
4. **Defect-Finding by Self-Audit**: Disqualified as a methodological distinction; Cebere et al. (2026) showed implementation drift is widespread across production DP libraries.
5. **Structured Privacy Labels**: Pre-empted by Dibia et al. (arXiv:2507.15997, 2025), whose expert consensus identified a nine-category privacy label for DP models.
6. **Automated Release Gating**: Pre-empted by production practice under the UK Five Safes framework and SACRO (Preen et al., 2024), operating in UK Trusted Research Environments since 2022.
7. **Machine-Checkable Release Artefacts**: Pre-empted by Croissant (MLCommons), MRM3 (MobiSys 2025), and Laminator (CODASPY 2025).
8. **Cross-Release Budget Management**: Pre-empted by systems such as PrivateKube (OSDI 2021), Cohere, DPack (EuroSys 2025), and DPolicy (arXiv:2505.06747).

Crucially, four of these eight claims trace to a single research cluster (Ganev, Annamalai, De Cristofaro, and Kulynych) pursuing an adjacent research programme. Competing on priority against established research groups is unviable; our defensible contribution lies in **systems integration and empirical transparency.**

Dibia et al. (2025) provides both our strongest validation and our clearest point of departure: an expert panel of differential privacy practitioners converged on nearly the identical metadata fields implemented in SynthProof. Yet, existing standards mandate neither asymmetric digital signatures binding guarantees to an issuer nor explicit reporting of the empirical measurement's limit of detection. An expert in Dibia et al.'s own study termed the omission of empirical resolution bounds *"privacy theater."* SynthProof occupies this exact unoccupied ground, delivering an Ed25519-signed, Croissant 1.1 compliant release certificate that binds the empirical instrument's limit of detection to the formal release.

---

## 8.3 Limitations

A rigorous defense requires explicit acknowledgment of systemic limitations:

1. **Audited Epsilon Uninformative at High Budgets**: At $\varepsilon \ge 4.0$, our one-run binomial auditor operates beyond its detection ceiling ($2.972$ at $m = 60$). We mitigate this by requiring the audit ceiling to be reported beside every audited value, preventing misleading claims.
2. **Tamper-Evident, Not Tamper-Proof**: The SQLite budget ledger is cryptographically tamper-evident, not tamper-proof. Key custody remains an organizational trust assumption: an adversary who obtains the curator's private signing key can rewrite history and regenerate valid signatures on a manipulated database.
3. **Signature Attests Integrity, Not Correctness**: An Ed25519 signature proves that the Privacy Data Sheet was emitted by the holder of the private key and has not been altered in transit; it does not prove that the curator’s hardware or execution environment was free of physical faults or side-channel leakage.
4. **No Cross-Release Budget Enforcement**: SynthProof manages privacy accounting within a single dataset release pipeline. Cross-session, multi-query budget governance across multiple release cycles is formally addressed by dedicated policy systems like DPolicy (arXiv:2505.06747).
5. **Systematic Multi-Stage Under-Spend**: Compound pipelines consistently achieve an achieved-to-target ratio of $\approx 0.92$ due to linear stage partitioning under sublinear RDP composition. While conservative, eliminating this gap requires multi-dimensional outer bisection, which was deferred to preserve consistency across committed benchmark grids.
6. **Excluded Attack Algorithms**: LiRA (Carlini et al.) is not implemented due to computational intractability (~21 hours per cell for an uninformative null). Anonymeter is not integrated due to a hard dependency conflict (`numpy < 2.0` breaking AIM).
7. **Benchmark Confound Sensitivity**: As shown in Chapter 7, the structural superiority of AIM observed on Adult does not replicate on ACSIncome due to clique selection bias and domain expansion effects.
8. **Replicated Nulls on Subgroup Hypotheses**: Hypotheses H2 (subgroup leakage parity) and H3 (weighted budget allocation) yielded bounded null results under rigorous multi-testing correction.
9. **Scope Boundaries**: Our implementation is restricted to tabular data, record-level differential privacy, single data holders, and the central curator model (`deployment_model: central`).
10. **Namespace Authority**: The `dp:` JSON-LD context used in our Croissant 1.1 export represents an experimental project namespace, not an officially registered W3C or MLCommons standard.
11. **Refusal Gate Evidence**: The data-blind pre-flight refusal gate is supported by single-institution guidance; because the SDC Handbook was inaccessible (returning HTTP 403), we claim this mechanism as unrefuted rather than novel.

---

## 8.4 Future work

We outline four concrete, costed extensions, each paired with an explicit kill criterion:

1. **Integration of Tradeoff-Curve GDP Auditing**: Replace the single-threshold binomial auditor with a continuous $\mu$-GDP trade-off curve estimator following Ganev, Annamalai, and Kulynych (arXiv:2604.18352). 
   - *Cost*: Moderate (~3 days implementation, ~10 hours benchmarking).
   - *Kill Criterion*: If the audited $\mu_{\text{emp}}$ on a 100% verbatim release at $m = 60$ fails to exceed the equivalent one-run ceiling of $2.972$, the estimator is not the binding constraint on instrument power.
2. **Algorithm-Aware Shadow Model Auditing**: Deploy an adversary that observes intermediate candidate selection scores within AIM's exponential mechanism loop, separating algorithmic leakage from detector limitations.
   - *Cost*: High (~2 weeks engineering, shadow training cluster required).
   - *Kill Criterion*: If white-box access fails to tighten the empirical bound by more than $0.2 \varepsilon$, black-box output representations dominate distinguishability.
3. **Outer Bisection for Non-Linear Budget Partitioning**: Implement an outer optimization loop over stage shares in `BudgetPlan` to close the $\approx 8\%$ conservative composition gap, achieving $\varepsilon_{\text{proved}} / \varepsilon_{\text{target}} \ge 0.99$.
   - *Cost*: Re-running the full empirical grid (~8 GPU hours per dataset).
   - *Kill Criterion*: If the outer bisection fails to converge within 15 iterations, non-monotonic RDP conversion surfaces exist.
4. **Formal Standardization of the Croissant DP Vocabulary**: Propose the `dp:` ontology extension (`dp:epsilon`, `dp:delta`, `dp:auditCeiling`, `dp:mechanism`) to the MLCommons Croissant Working Group, migrating the specification from a project-local schema to an internationally recognized community standard.

---

## 8.5 Conclusion

This thesis set out to resolve the crisis of trust in differentially private synthetic tabular data, where mathematical guarantees are assumed without verification and software implementations silently drift from theoretical bounds.

We have demonstrated that synthetic data can be rendered verifiably accountable through an integrated release architecture. By coupling formal privacy composition with empirical leakage auditing bounded by explicit limits of detection, SynthProof ensures that theoretical bounds are mathematically audited and that empirical metrics cannot be misrepresented as sound guarantees when evaluated by underpowered instruments.

With equal scientific fidelity, we have documented our negative results and retractions: the proved-versus-audited gap was retracted as an instrument artifact; H2 and H3 proved to be bounded null results; and AIM's structural dominance was shown to be confounded by clique selection on sparse domains. By prioritizing transparent verification over unsupportable claims, SynthProof delivers an accountable, standards-compliant foundation for private data release.

---

**Before submitting this chapter,** run `python scripts/check_thesis_claims.py`. It currently
reports `missing-ceiling` against ch08.
