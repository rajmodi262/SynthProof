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
