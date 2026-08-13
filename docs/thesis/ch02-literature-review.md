# Chapter 2 — Literature Review

> **Status: FIRST DRAFT — 1,888 words against a 2,500 target (~75%).** Prose is written; citations are marked `[Author Year]`
> and need converting to the project's BibTeX style. Section 2.6 must be re-checked against
> `results/H1_RESULTS.md` before submission, since it states what this work adds.

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

---

## 2.6 The gap this work addresses

Assembling the picture:

| Approach | Upper bound | Lower bound | Composes | Cross-release | Attached to artefact | Verifiable |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| Formal DP synthesis (AIM, MST) | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| Empirical auditing (LiRA, Steinke) | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Risk assessment (Anonymeter) | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Datasheets / Model Cards | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| **SynthProof** | ✅ | ✅ | ✅ | ✅ | ✅ | partial |

> ⚠️ **Before submission:** set the SynthProof row against what is actually implemented at that
> time. The certificate is not yet signed, so "Verifiable" is *partial*, not a tick. Overstating
> this row would be the same failure this project's own audit was written to catch.

Formal DP supplies an upper bound that nobody verifies against the implementation. Empirical
auditing supplies a lower bound that carries no guarantee, accumulates no budget, and is not
attached to the artefact. Datasheets are attached to the artefact but describe it rather than
bounding what it reveals. **No existing system releases a dataset accompanied by both bounds,
cryptographically bound to a durable record of the organisation's cumulative privacy
expenditure.**

Three narrower gaps follow, each addressed in this work:

1. **Unaccounted preprocessing.** Published DP synthesis pipelines routinely read column ranges
   and category domains directly from the sensitive data before any mechanism runs. This is a
   real leak that invalidates the headline ε, and it is rarely mentioned. Chapter 4 shows how a
   public schema removes the need for it entirely, at zero privacy cost.

2. **Budget interfaces that mislead.** A system can satisfy the DP definition while its
   interface deceives its operator. Before calibration, requesting ε = 8 from this system
   produced a release composing to ε = 70.49. The guarantee was sound at every step; the number
   the operator typed simply did not mean what they thought.

3. **Unverifiable claims.** Privacy claims are asserted by the party with the strongest interest
   in their being believed. A signed data sheet lets a third party check the arithmetic.

---

## Sources to obtain

Search terms covering most of the above: `differential privacy synthetic data survey`,
`privacy auditing one training run`, `AIM adaptive iterative mechanism marginals`,
`membership inference first principles`, `anonymisation groundhog day`.

Prefer arXiv versions for page-stable citation, and maintain `docs/thesis/references.bib` from
the first day — retrofitting citations across 15,000 words is miserable.
