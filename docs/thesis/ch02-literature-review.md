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
Chapter 8 as a methodological finding, and it is the reason this work delegates all composition
to a reference implementation.

Budget *management* across many analyses is a smaller literature. Sage [Lécuyer et al. 2019]
treats the privacy budget as a systems resource to be scheduled across a stream of queries.
PrivateSQL [Kotsogiannis et al. 2019] allocates budget across a workload to maximise utility.
Both address allocation within a system boundary; neither makes the resulting record
tamper-evident or transferable to an external auditor.


> ⚠️ **SPECIFICATION — added 2026-08-24. This section is missing the literature that kills
> claim 8.** Sage and PrivateSQL allocate budget *within* a system boundary. The line of work
> that manages budget **across releases** is absent, and it is the line that occupies ground
> ch01 §1.4 must therefore concede.
>
> | Add | What it establishes | Why this chapter needs it |
> |---|---|---|
> | **PrivateKube**, OSDI '21 | Privacy budget as a first-class schedulable Kubernetes resource | Earliest of the cluster |
> | **Cohere** | Cross-release budget management | — |
> | **DPack**, EuroSys '25 | Budget allocation across competing pipelines | — |
> | **DPolicy**, [arXiv 2505.06747](https://arxiv.org/abs/2505.06747) | Policy-driven cross-release budget governance | **The system that does properly what our ledger does not.** ch01 §1.4 must name it when conceding no cross-session enforcement |
> | **Cebere et al.**, Feb 2026, [arXiv 2602.17454](https://arxiv.org/abs/2602.17454) | 12 DP libraries audited, 13 guarantee violations | The evidence for §2.4's own argument that composition must be delegated **and cross-checked**. Currently the section argues this from our own bug alone |
> | **Song, Sarathy, Shoemate & Vadhan**, CSCW 2024, [arXiv 2410.09721](https://arxiv.org/abs/2410.09721) | Practitioners do **not** verify DP guarantees; they trust implicitly | **Cited nowhere in this chapter.** It is the premise the whole project rests on and the direct justification for differential accounting |
>
> **Trap.** §2.4 currently forward-references Ch.8 for the hand-rolled-bound story "as a
> methodological finding". Ch.8 §8.2 no longer frames the self-audit as a distinction — Cebere
> et al. showed a defect count is typical of code that was actually audited. Keep the ε
> under-reporting fact; repoint the reference.
>
> `[WRITE: ~200 words added to §2.4.]`

---

## 2.5 Transparency artefacts

A parallel literature asks not how to protect data but how to *describe* it. Datasheets for
Datasets [Gebru et al. 2021] proposed that every dataset ship with a standard document covering
provenance, composition, collection process and recommended uses; Model Cards [Mitchell et al.
2019] did the same for models, and Data Statements [Bender & Friedman 2018] for language
resources.

These have been widely adopted, and they share a limitation: they are **prose written by the
producer, asserting properties of an artefact, with no mechanism for a reader to verify any of
it**. A datasheet records what a dataset is. None of them record, in checkable form, what it
discloses.

Regulation is converging on the same need from the other direction. The EU AI Act creates
documentation obligations for training data in high-risk systems, and India's DPDP Act 2023
constrains processing of personal data. Both make training-data provenance a compliance artefact
rather than a matter of good practice.


> ⚠️ **SPECIFICATION — added 2026-08-24. This section stops at prose datasheets and misses the
> machine-readable generation entirely.** Its closing claim — that these artefacts have "no
> mechanism for a reader to verify any of it" — is **true of Datasheets, Model Cards and Data
> Statements, and false of the standards below.** As written, the section sets up a gap that
> the 2024–2026 literature has partly filled, which is the weakest possible position to be
> caught in.
>
> | Add | What it establishes | Why this chapter needs it |
> |---|---|---|
> | **Croissant**, MLCommons — [docs.mlcommons.org/croissant](https://docs.mlcommons.org/croissant/) | Machine-readable dataset metadata; **a NeurIPS Datasets & Benchmarks submission requirement**. Extensible by external vocabulary; PROV-O provenance. **No signing, no attestation** | **Zero mentions in this chapter.** It is the standard the project now integrates with, and the "no attestation" gap is half the surviving position |
> | **Dibia, Lu, Bhattacharjee, Near & Feng**, 2025, [arXiv 2507.15997](https://arxiv.org/abs/2507.15997) | Expert-elicited nine-category DP privacy label | Currently only in the §2.6 callout. It belongs **here**, in the prose, as the closest prior artefact |
> | **Laminator**, CODASPY '25 | TEE-attested ML property cards | Attests *execution* — the thing our README concedes we cannot. Read beyond abstract level before citing |
> | **MRM3**, MobiSys '25 | Machine-readable model cards | — |
> | **SynthGuard-ReleaseBench**, [arXiv 2608.14753](https://arxiv.org/abs/2608.14753), Jul 2026 | Ships checkable evidence with a release | **Kills "nobody ships checkable evidence."** What survives: it bounds *utility*, not the sensitivity of the privacy measurement. Narrow to that |
> | **SACRO** [preen2024sacro] + **Five Safes** | Automated output checking in UK TREs since 2022 | Mentioned only in the callout. The refusal-gate discussion needs it in prose — and note SACRO **reads output values** and does **not** autonomously refuse |
>
> **The sentence that must survive the rewrite**, because it is what is left after all of the
> above: none of these carries a **signature binding a privacy claim to an issuer**, and none
> proposes a **standard for reporting the operating range of an empirical privacy metric**.
> A SHA-256 checksum binds a file to itself; it does not bind a claim to who made it.
>
> `[WRITE: ~350 words added to §2.5. This is the largest single gap in the chapter.]`

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
