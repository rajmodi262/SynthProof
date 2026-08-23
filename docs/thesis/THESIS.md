# Chapter 1 — Introduction

**Target: 1,200 words.** Write *after* Ch.2 and Ch.3 — an introduction is far easier once you
know exactly what you are introducing.

## 1.1 Motivation (~350 words)

- Open with the concrete bind: data that could train genuinely useful models sits in compliance
  review instead.
- De-identification does not work. Sweeney (2000): 87% of the US population uniquely identified
  by ZIP + date of birth + sex. Narayanan & Shmatikov (2008): the Netflix Prize dataset
  re-identified from public IMDb ratings. AOL's "anonymised" search logs named users within days.
- Regulation now binds: GDPR Art. 9, HIPAA, and India's DPDP Act 2023.
- Synthetic data is the escape hatch teams reach for — and almost none of it ships with any
  statement of how private it actually is.

## 1.2 Problem statement (~250 words)

Two research communities, each solving half the problem. Formal DP proves an upper bound that
nobody verifies against the implementation. Empirical auditing measures a lower bound that
carries no guarantee, accumulates no budget across releases, and is not attached to the artefact
it describes. Nothing ships both.

## 1.3 Thesis statement (~100 words)

Use the statement from [`../thesis.md`](../thesis.md), tightened.

## 1.4 Contributions (~300 words)

Number them, and mark each honestly against what exists at submission:

1. A dual-sided assurance pipeline reporting ε_proved and ε_audited for the same artefact.
2. Budget-charged domain profiling — schema and range discovery priced rather than taken free.
3. A hash-chained, Ed25519-signed budget ledger whose head commits to
   `(entry_count, tip_hash)`, so truncation is detectable as well as modification.
   **Not** cross-release: there is no cross-session budget enforcement (see the README),
   and DPolicy [kuchler2025dpolicy] is the system that does that properly.
4. An empirical study of the proved-vs-audited gap across mechanism families (H1), and of its
   variation across demographic subgroups (H2).

Be precise about which are *implemented* and which are *evaluated*. A reviewer will separate
these whether or not you do.

## 1.5 Scope and non-goals (~100 words)

Tabular data only. Single data holder. Record-level privacy. Forward-pointer to Ch.3 §3.5.

## 1.6 Thesis structure (~100 words)

One sentence per chapter.

## Writing note

The introduction is the most-read and least-carefully-written chapter in most theses. Draft it
last, then cut it by a third.

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
| **SynthProof** | ✅ | ✅ | ✅ | ❌ | ✅ | partial |

> ⚠️ **Before submission:** set the SynthProof row against what is actually implemented at that
> time. The certificate is not yet signed, so "Verifiable" is *partial*, not a tick. Overstating
> this row would be the same failure this project's own audit was written to catch.

Formal DP supplies an upper bound that nobody verifies against the implementation. Empirical
auditing supplies a lower bound that carries no guarantee, accumulates no budget, and is not
attached to the artefact. Datasheets are attached to the artefact but describe it rather than
bounding what it reveals. **We found no system that releases a dataset accompanied by both
bounds, cryptographically signed and carrying the ceiling of its own empirical measurement.**

> ⚠️ **This claim was narrowed on 2026-08-23. Do not widen it, and do not restate it until
> `research/08_novelty_verdict.md` is populated** — the adversarial protocol in `research/`
> completed only 2 of 8 query families before being interrupted, so no novelty verdict has been
> issued and none may be asserted here. What that partial run *did* verify, and it is
> unforgiving:
>
> - **Dual-sided assurance (proved + audited per release) is occupied.** Annamalai, Ganev &
>   De Cristofaro [annamalai2024theoryalone] compute empirical leakage against the theoretical
>   bound for DP-SDGs and flag both violations and loose audits. That is this framing.
> - **Budget-charged domain profiling is occupied** by [annamalai2025domain].
> - **The audit ceiling is not a contribution.** It is a one-line corollary of Steinke, Nasr &
>   Jagielski's Theorem 2.1 / Eq. (3) — the paper this project implements — verified
>   bit-identical to our `max_provable_epsilon`. Ganev, Annamalai & Kulynych
>   [ganev2026tightmstaim] then obtain *tight* audits of MST and AIM with a Gaussian-DP
>   estimator, so the ceiling we hit is a property of the single-threshold estimator we chose,
>   not of auditing.
> - **Finding defects by self-audit is occupied** by [cebere2026bugs]: 12 libraries, 13
>   violations, method and package released.
> - **Shipping a structured privacy label with a DP release is occupied** by
>   [dibia2025privacylabel] — an expert-elicited nine-category label whose categories overlap
>   this sheet almost field for field, including `unit_of_privacy` and empirical privacy
>   metrics. Treat that as validation, not defeat: a panel of DP experts converged on the fields
>   we built. **What they explicitly do not propose is any signing mechanism, or any standard
>   for reporting the limits of an empirical privacy metric** — an omission one of their own
>   experts called *"privacy theater"*. Those two gaps are what the Ed25519 signature and
>   `audit_ceiling` fill, and they are the narrowest honest statement of this project's
>   position.
> - **Automated release gating is occupied** by the Five Safes framework and SACRO
>   [preen2024sacro], production practice in UK Trusted Research Environments since 2022.
>   SACRO reads output values and does not autonomously refuse; our gate reads only the schema
>   and the row count and does. **State that difference as unrefuted, never as novel** — the
>   primary SDC Handbook could not be retrieved and that literature predates arXiv.
>
> Four of those kills come from one author cluster (Ganev, Annamalai, De Cristofaro, Kulynych)
> running this programme professionally and roughly two years ahead. **Chapter 2 must be written
> from that position, not around it.** Candidates still unresolved because their query families
> never ran: the signed cross-release ledger, subgroup leakage disparity, and the calibration
> gap. `research/PHASE2_INTERIM.md` §5 lists what to check first — Laminator (verifiable ML
> property cards via hardware attestation) is structurally the closest thing to a Privacy Data
> Sheet and has not been read.

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

Search terms covering most of the above: `differential privacy synthetic data survey`,
`privacy auditing one training run`, `AIM adaptive iterative mechanism marginals`,
`membership inference first principles`, `anonymisation groundhog day`.

Prefer arXiv versions for page-stable citation, and maintain `docs/thesis/references.bib` from
the first day — retrofitting citations across 15,000 words is miserable.

# Chapter 3 — Threat Model and Scope

**Target: 1,500 words.** Depends on nothing. **Write this second.**

This chapter is where most capstones are vague and most reviewers push hardest. Being precise
here is cheap and buys a great deal of credibility. The existing
[`docs/threat_model.md`](../threat_model.md) is 177 words and is a starting skeleton, not a
chapter.

---

## 3.1 Setting (~250 words)

Name the actors explicitly.

| Actor | Holds | Wants |
|---|---|---|
| **Data holder** | The sensitive table *D* | To release something useful without disclosing individuals |
| **Analyst** | The released synthetic table *D̃* and its data sheet | To do useful work; to know how far to trust the release |
| **Adversary** | *D̃*, the data sheet, auxiliary knowledge | To learn whether a target record was in *D*, or to reconstruct its attributes |
| **Verifier** | The data sheet and a public key | To check the release's claims without trusting the data holder |

The **verifier** is the actor most systems omit, and introducing it is part of the contribution.
State that explicitly.

---

## 3.2 Adversary model (~400 words)

### Capabilities — be exact
- **Black-box access to the release.** The adversary receives *D̃* in full and the signed data
  sheet, including ε_proved, ε_audited, the mechanism name, and all hyperparameters.
- **Full knowledge of the algorithm.** Kerckhoffs's principle: the mechanism, the code, and the
  seed policy are public. Only the private randomness and *D* are secret.
- **Auxiliary distributional knowledge.** The adversary can sample from the population
  distribution and holds an independent reference set *D_holdout*.
- **Partial record knowledge.** For attribute inference, the adversary knows all but one
  attribute of the target.

### Explicitly NOT assumed
- No access to intermediate state — noisy histograms, model parameters, or the accountant's
  internals are never released.
- No repeated queries. Each release is a one-shot artefact.
- No influence over *D* before ingestion (poisoning is out of scope; see §3.5).

### Goals
1. **Membership inference** — decide whether target *x\** ∈ *D*.
2. **Attribute inference** — recover a sensitive attribute of *x\** given the rest.
3. **Singling out** — produce a predicate matching exactly one record in *D*.
4. **Linkability** — match records across two releases to the same individual.

### Writing note
Tie each goal to the specific attack that measures it in Chapter 7. A threat model that names
threats nothing measures is decoration.

---

## 3.3 Unit of privacy (~200 words)

State plainly: **add/remove-one-record, (ε, δ)-differential privacy**, with δ < 1/n.

Then address the honest subtleties, because a reviewer will:

- **Why record-level and not user-level?** If one individual contributes multiple rows, the
  guarantee degrades by their contribution count. UCI Adult is one row per person, so
  record-level is user-level there. Say so, and say that a multi-row dataset would need group
  privacy or a bounded-contribution preprocessing step.
- **Add/remove vs replace-one.** These differ by a factor of two in sensitivity. State which
  `dp_accounting` neighbouring relation is configured (`ADD_OR_REMOVE_ONE`) and stay consistent.
- **What δ means.** Not "a small probability of failure" hand-waved — the standard
  interpretation, and why δ < 1/n matters (otherwise releasing a few records verbatim
  technically satisfies the definition).

---

## 3.4 What the system must guarantee (~350 words)

Turn the threat model into checkable requirements. This is the bridge to Chapter 4.

| # | Requirement | Enforced by |
|---|---|---|
| R1 | Every operation reading *D* charges the accountant | Accountant + `MechanismSpec`; no generator touches *D* without a charge |
| R2 | Composed ε across a release does not exceed the declared budget | `BudgetPlan` + `charge()` raising `BudgetExceededError` |
| R3 | A requested ε is the ε delivered | `calibrate_noise_scale`, CI-gated across 24 configurations |
| R4 | Schema and domain discovery are not free | DP domain profiler with a noisy-threshold category release |
| R5 | Composition bounds are citable, not derived in-house | Delegated to `dp_accounting` |
| R6 | Cumulative organisational spend is tamper-evident | Ed25519-signed SHA-256 hash chain |
| R7 | Release claims are verifiable without trusting the holder | Signed data sheet + standalone verifier (M3) |
| R8 | Empirical leakage is measured, with uncertainty quantified | Canary auditor, Clopper-Pearson, Fisher exact |

**R3 deserves its own paragraph.** Before calibration, requesting ε = 8 produced a release
composing to ε = 70.49 — the budget interface was decorative. This is a good, concrete
illustration that a DP system can satisfy the *definition* while its *interface* misleads the
operator, and it is the kind of specific, self-critical detail that reads as rigour.

---

## 3.5 Out of scope

Naming what we do not defend is a strength, so this list is deliberately generous.

- **Hardware side channels** — timing, power, EM, cache.
- **Exact-arithmetic noise sampling.** We sample the discrete Gaussian and discrete Laplace
  directly (Canonne–Kamath–Steinke 2020), which avoids Mironov's (2012) attack in its usual
  form: leakage through the *output* representation when a continuous sample is rounded. We
  do **not** implement CKS'20's exact-arithmetic Bernoulli — the acceptance step uses a
  floating-point comparison, as do the underlying geometric draws. The sampled distributions
  are correct (χ² against the exact PMF; empirical variance within 0.3% of theory at
  σ ∈ {0.5, 1, 3, 10}), but an adversary who can observe the sampler at bit level or through
  timing is out of scope. `synthproof/accounting/noise.py` states this at the call site.
- **Upstream poisoning** of *D* before ingestion.
- **Compromise of the signing key.** The ledger is tamper-*evident*, not tamper-*proof*; an
  adversary holding the private key can rewrite history and re-sign. Key custody is an
  organisational control, not a cryptographic one. This is the honest limitation of the
  design and a reviewer will find it, so it is stated rather than buried.

  Within that boundary the adversary we *do* defend against is a **malicious operator with
  full write access to the ledger database and knowledge of the source, but no key** — not
  merely a careless one. Nine attacks in that model are executed against live SQLite in
  `tests/test_ledger_adversarial.py`: field modification, modification with the stored hash
  recomputed, middle-entry deletion, reordering, replay under a fresh entry id, appending a
  forged entry with the head rewritten, tail truncation, and truncation combined with
  deleting the head row. All nine are detected.

  Truncation deserves specific mention because hash chaining alone does **not** catch it: a
  shortened chain is internally consistent, so before the signed head existed, deleting the
  final two entries left `verify()` returning `True`. An operator could therefore have
  deleted the entries recording a budget overspend. The head commits to
  `(entry_count, tip_hash)` and is signed, so shortening the chain now requires forging a
  signature over the new length.
- **Multi-party or federated settings.** Single data holder only.
- **Correctness of `dp_accounting`.** We treat it as trusted, mitigated by a differential
  test against the independent `autodp` implementation — agreement between two libraries is
  evidence; agreement of our code with itself is not.

---

## 3.6 Formal statement (~100 words)

Close with the definition, stated once, properly:

> A randomised mechanism *M* satisfies (ε, δ)-differential privacy if for all neighbouring
> datasets *D*, *D′* differing in the addition or removal of a single record, and all
> measurable *S* ⊆ Range(*M*):
>
> Pr[*M*(*D*) ∈ *S*] ≤ e^ε · Pr[*M*(*D′*) ∈ *S*] + δ

Then the sentence that motivates the whole thesis:

> This bounds the *worst case over all adversaries*. It says nothing about what any *particular*
> adversary achieves. The distance between those two quantities — ε_proved and ε_audited — is
> the object this work measures.

# Chapter 4 — System Design

**Target: 2,000 words.** M0 is complete, so the architecture is settled. **Write this third.**

---

## 4.1 Design principles (~300 words)

State the four rules the system is built on, and note that three of them were adopted *after*
a self-audit found violations. That the project audited itself and changed its own design is a
methodological point worth making, not hiding.

1. **Nothing reads the sensitive table for free.** Schema discovery, range estimation, and
   category-domain discovery all charge the accountant. Most pipelines take these for free,
   which silently invalidates the headline ε.
2. **Never write a bound that cannot be cited.** Composition is delegated to `dp_accounting`.
   Motivation: our own RDP implementation used `min(q·ρ(α), truncated_MTZ)` for subsampling —
   neither branch a theorem — and it under-reported ε by ~2× at q = 0.01.
3. **A mechanism that is charged must be applied.** Two modules were found charging ε and then
   releasing exact values. Paying budget and skipping the noise is strictly worse than not
   paying: budget is consumed *and* the data leaks deterministically.
4. **Every reported number is computed.** No hardcoded fallbacks, no metric derived as an
   affine function of another and presented as independent.

---

## 4.2 Pipeline architecture (~500 words)

Reuse the diagram from `docs/deck/`. Walk the stages in order:

```
SENSITIVE ──► DP PROFILER ──► GENERATOR ──► SYNTHETIC
                  │               │              │
                  └── charges ────┴──────────────┤
                          ▼                      ▼
                  PRIVACY ACCOUNTANT      CANARY AUDIT
                          │               ATTACK RANGE
                          │               UTILITY EVAL
                          ▼                      │
                     LEDGER ◄──────► PRIVACY DATA SHEET
```

Cover per stage: what it reads, what it charges, what it emits.

**The invariant to emphasise:** no path from the sensitive table to the output bypasses the
accountant. Every arrow that touches *D* has a charge attached.

---

## 4.3 The privacy accountant (~350 words)

The design argument: **we own the interface, not the theory.**

- `MechanismSpec` → `dp_accounting.DpEvent` translation, including the deliberate mapping of
  zero noise to `NonPrivateDpEvent` so ε is ∞ rather than a misleadingly finite number.
- The API that makes it usable as a *system* rather than a formula: `dry_run` (what would this
  cost?), `charge` (spend it, or raise), `remaining`, `snapshot`/`restore` (speculative
  execution and rollback).
- Why unknown mechanism names now raise rather than defaulting to Gaussian.
- `PrivacySpend` records both cumulative and marginal ε, because composition is sublinear and
  the running total is not the sum of the marginals — a point worth a sentence, since it
  surprises people.

Contribution framing: the RDP mathematics is not novel and we do not claim it. The **budget
enforcement interface** is the systems contribution.

---

## 4.4 ε-calibration (~350 words)

This section carries a concrete, measurable result — lead with it.

- **The problem.** `noise_scale = √d / target_eps` is a heuristic, not an inversion of the
  composition theorem. Measured drift on the toy sweep: target 0.5 → 2.53 (5.1×), target
  8.0 → 70.49 (**8.8×**), and the error grew with ε.
- **The method.** ε is strictly decreasing in the noise scale, so the inverse is well-posed.
  Bracket, then bisect on **bracket width** rather than on |ε(mid) − target|.
- **The bug worth reporting.** Terminating on the epsilon gap is unsafe: if the final probe
  lands just above the target it updates the lower bracket, leaving the upper bracket stale.
  Laplace at 5 steps with target 2.0 returned a scale achieving ε = 1.25. The invariant
  ε(hi) ≤ target < ε(lo) holds every iteration, so shrinking the bracket and returning `hi` is
  both correct and conservative. **Including this in the thesis is a strength** — it shows the
  implementation was validated rather than assumed.
- **The result.** proved/target = 0.92 across the grid, never exceeding 1.0.
- **`BudgetPlan`.** One release budget split across stages (10% profiling, 90% synthesis) so
  the composed total approximates the request instead of exceeding it by whatever earlier
  stages happened to spend.
- **Known residual.** ~8% under-spend, because RDP composition across the two stages is
  sublinear. Safe, but leaves utility unclaimed. Report it; do not hide it.

**Figure:** target vs achieved ε across mechanisms and step counts.

---

## 4.5 DP domain profiler (~250 words)

- Public vs sensitive: column *names* and coarse types are treated as public schema metadata;
  column *contents* are sensitive. State this assumption explicitly — it is load-bearing.
- Calibrated so the whole profiling pass costs its allotted ε regardless of column count.
  (The previous `eps_per_col` design meant total cost grew with the schema and no caller could
  predict a release's ε.)
- **The category-domain leak and its fix.** The profiler charged ε and then published
  `df[col].unique()` — the exact domain including values occurring once. Now categories survive
  only if their noisy count clears a threshold at 3σ.
- **Open limitation.** min/max over an unbounded column has unbounded sensitivity, so the
  declared `sensitivity = 1.0` for range queries is not yet justified. The fix is
  caller-declared public bounds (M1.7). State this as open.

---

## 4.6 Generators (~200 words)

Be scrupulous here.

- What is implemented at submission: name it accurately.
- If real AIM (`private-pgm`) has landed, describe it and keep the independent-marginal
  generator as a **deliberate ablation** — it isolates the value of modelling cross-column
  structure, which is a legitimate experimental role.
- If it has not landed, say the generator bank contains two independent-marginal baselines and
  that H1's mechanism-family comparison is correspondingly limited. **Do not call it AIM.**

---

## 4.7 The budget ledger (~250 words)

- Hash-chained SQLite; each entry commits to its predecessor's SHA-256; Ed25519 over canonical
  bytes. Canonicalisation matters — fixed-precision float formatting and sorted keys, or
  signatures are not reproducible.
- **Chaining alone is not enough, and this is the point worth making.** A hash chain detects
  modification, insertion and reordering, but **not truncation** — a shortened chain is
  internally consistent. Deleting the last two entries left `verify()` returning `True`, so an
  operator could remove exactly the records of a budget overspend. A signed `ledger_head`
  committing to `(entry_count, tip_hash)` closes it: 9 distinct attacks are now stopped where 8
  were before (`tests/test_ledger_adversarial.py`, 14 tests). Do not call this ledger
  "append-only" — nothing prevents an append; what is detectable is that one happened.
- Threat addressed: **cross-release budget erosion.** Nothing in standard practice stops a
  second team re-releasing the same table at full budget.
- Verification: chain linkage, per-entry hash, and signature, checked in order.
- **Honest limitation.** Tamper-*evident*, not tamper-*proof*. An adversary with the private key
  rewrites and re-signs freely. Key custody is an organisational control. Also state the current
  implementation gap: the key is generated in memory per instance and not yet persisted, so
  file-backed ledgers cannot be verified after restart (M3.1).

---

## 4.8 The Privacy Data Sheet (~200 words)

- Contents: both ε values, δ, per-stage budget breakdown, mechanism and hyperparameters, canary
  counts and audit p-value, attack results, utility, ledger head, seed.
- Lineage from Gebru et al.'s datasheets; the difference is that the central claim is
  **machine-checkable**.
- Verification flow: `synthproof verify sheet.json --pubkey org.pub`.
- **State the current gap plainly** if M3.2 has not landed: the ledger head is real, the
  signature is not yet implemented.

---

## Figures for this chapter

| Figure | Source |
|---|---|
| Pipeline architecture | `docs/deck/pitch-interactive.html` diagram |
| Ledger hash-chain schematic | new |
| Target vs achieved ε (calibration) | measurable today |
| Data sheet example | `synthproof demo` output |

# Chapter 5 — Implementation

**Target: 1,500 words.** Depends on M1.

## 5.1 Technology choices (~250 words)

Python 3.11; `dp_accounting` for composition; `private-pgm` for AIM; `scipy.stats` for exact
binomial intervals; `cryptography` for Ed25519; FastAPI; SQLite. One sentence each on *why* —
especially why composition is delegated rather than implemented in-house.

## 5.2 Package structure (~200 words)

Module-by-module table with responsibilities. Emphasise that module boundaries match the
pipeline stages in Ch.4, so the architecture diagram and the package tree are the same picture.

## 5.3 Noise sampling (~300 words)

- CKS'20 discrete Gaussian rejection sampler; discrete Laplace as a difference of geometrics.
- Why discrete at all: Mironov (2012) floating-point attack on inverse-CDF sampling.
- **Include the χ² goodness-of-fit test against the exact PMF.** A validated sampler is a
  different claim from an asserted one, and this is cheap evidence.
- Report the removed σ < 0.3 shortcut that returned deterministic zeros while the accountant
  still charged ε — a one-line defect that voided the guarantee silently.

## 5.4 Calibration implementation (~250 words)

Bracket-and-bisect, the convergence criterion, and the CI guard across 24 configurations.
Cross-reference Ch.4 §4.4 for the result rather than repeating it.

## 5.5 Ledger implementation (~250 words)

Canonical byte serialisation (fixed-precision floats, sorted keys — otherwise signatures are not
reproducible), chain construction, and verification order. Include the tamper tests that mutate
and delete rows directly in SQLite rather than going through the API.

## 5.6 Testing and CI (~250 words)

Test count, coverage, and what each regression test defends against. Note that every defect the
self-audit found now has a named test. List the property tests (M1.14) and the differential test
against `autodp` (M2.9).

## Figures

- Discrete Gaussian: empirical vs exact PMF
- Coverage report

# Chapter 6 — Methodology

**Target: 1,200 words.** Depends on M1.11.
**This chapter must honour [`../preregistration.md`](../preregistration.md) exactly.**

## 6.1 Preregistration (~200 words)

State that hypotheses were registered before any sweep ran, with the commit hash and tag.
State the commitment to report results regardless of direction — and then honour it in Ch.7.

## 6.2 Datasets (~250 words)

UCI Adult (n = 48,842, 14 columns) and ACS PUMS via `folktables`. Provenance, licence,
preprocessing, and SHA-256 checksums. Name the subgroup variables used for H2 and justify the
choice.

## 6.3 Experimental design (~350 words)

- ε grid {0.5, 1, 2, 4, 8}; δ = 1e-5 (justify δ < 1/n).
- 5 seeds per cell; state what varies per seed and what is held fixed.
- Train/test protocol: TSTR and TRTR scored on the **same** held-out real split. Explain why —
  the earlier in-sample TRTR produced a constant 0.971 and a meaningless utility gap.
- Which mechanisms are compared and what genuinely distinguishes them.

## 6.4 Metrics (~250 words)

- **Privacy:** ε_proved (RDP composition), ε_audited (Clopper-Pearson lower bound), audit
  p-value (Fisher exact).
- **Attacks:** AUC and **TPR at 0.1% FPR**. Justify via Carlini et al. (2022) — average-case
  accuracy is the wrong metric for membership inference.
- **Utility:** macro F1 (TSTR/TRTR), Wasserstein-1 marginal distance, correlation preservation.

## 6.5 Statistical analysis (~150 words)

Bootstrapped confidence intervals, multiple-comparison handling, and the significance threshold
— fixed in advance, not selected after seeing results.

## 6.6 Reproducibility (~150 words)

Seed policy, environment capture, `make reproduce`, and the emitted manifest hash.

---

## 6.7 The preregistration tag — what it does and does not establish

`docs/preregistration.md` is tagged `prereg-v1`. State the following in the chapter, in these
terms, because a reviewer will check it and a stronger claim is not supportable.

**What is verifiable.** The tag points at commit `8a8e21d` (2026-08-07), the repository's
first commit, which is where `preregistration.md` first appears. **No result file in this
repository predates that commit** — `git log --reverse -- results/` confirms the earliest
result artefacts are in the same commit or later. The hypotheses, ε grid, δ, seed count and
primary metrics were therefore fixed in version control before any committed experiment ran.

**What is NOT verifiable, and must be said.** Three qualifications:

1. **The tag was applied retroactively**, on 2026-08-15, pointing at the historical commit. It
   was not created at the time. Git tags carry their own creation date, so this is discoverable
   and should be declared rather than left for a reviewer to notice.
2. **The document is dated 2026-08-05, two days before its first commit.** There is no
   independent timestamp for that earlier date. The earliest *verifiable* existence of the
   preregistration is 2026-08-07.
3. **This is not a third-party registration.** An OSF or AsPredicted entry is timestamped by a
   party with no interest in the outcome. A git tag is timestamped by us, and we control the
   repository. The correct description is a **version-controlled commitment**, not a
   preregistration in the clinical-trials sense.

**Why it is still worth having.** The commitment predates every committed result, the
deviations below are declared rather than discovered, and both H1's partial refutation and
H2's null are reported. That is the substance preregistration exists to protect. Overstating
its formal status would undermine exactly the credibility it is meant to supply.

## 6.8 Deviations from the preregistration

Every deviation, its reason, and its likely direction of effect on inference.

| # | Deviation | Reason | Effect on inference |
|---|---|---|---|
| ~~D1~~ | ~~**ACSIncome not run.** UCI Adult only~~ **CLOSED.** Both hypotheses now run on ACSIncome (CA 2018, n=6,000) under the identical protocol — same seeds, epsilon grid, and structure column pair | — | See §6.9. External validity was **tested**, and the H1 structure ordering **did not transfer**. That is now a reported finding rather than an unexamined limitation |
| D2 | **Utility measured on a second, canary-free fit** | Measuring it on the canary-trained model destroyed the signal being measured — 60 canaries cut corr(age, hours) from 0.1014 to 0.0109 | Removes a bias that had been penalising exactly the mechanisms that model dependence. Direction: made H1 *measurable*; without it H1 was falsely null |
| D3 | **Auditor changed** from paired Clopper-Pearson to the one-run construction | The paired estimator spends two canaries per comparison and saturates sooner | Slightly raises the audited bound at fixed canary budget. Both are reported and compared |
| D4 | **H1 primary metric supplemented.** Preregistration named TSTR macro F1; correlation error was added as a structure metric | TSTR alone cannot distinguish an independent-marginal mechanism from a structured one on this data | Additive, not substitutive — TSTR is still reported. The structure metric is what separates the families |
| ~~D5~~ | ~~**H3 not run**~~ **CLOSED.** H3 now run on both datasets, 5 epsilon values x 5 seeds x 2 arms | — | See §6.10. H3 is **not supported** on either dataset, and the null replicates |

## 6.9 External validity: what the second dataset changed

D1 was closed by running the full preregistered protocol on **ACSIncome (California, 2018)**
via `folktables` — the dataset Ding et al. (NeurIPS 2021) built as UCI Adult's modern
replacement. Everything the protocol controls was held identical: n = 6,000, seeds 0-4,
ε ∈ {0.5, 1, 2, 4, 8}, and the same structure-metric column pair by analogy (`AGEP`×`WKHP`
for `age`×`hours_per_week`). A difference between the datasets is therefore attributable to
the data, not the procedure. This is enforced by
`tests/test_experiment_scripts.py::test_the_two_datasets_share_the_protocol_that_makes_them_comparable`.

Two things could not be held identical, and both are reported rather than corrected away:

1. **The true correlation differs** (Adult 0.1034, ACS 0.0721), so *absolute* correlation
   error is not comparable across the datasets. Only the mechanism **ordering** transfers.
2. **The per-subgroup audit ceiling differs.** H2 allocates a fixed 400-canary budget equally
   across an attribute's levels; `race` has 5 levels on Adult and `RAC1P` has 9 on ACS, giving
   80 vs 44 canaries per group and ceilings of 3.27 vs 2.65. ACS's race instrument is
   genuinely weaker *before any mechanism runs*. Raising ACS's budget to equalise the ceilings
   would have confounded group count with total canary count instead.

### What transferred, and what did not

**H2 replicated.** The null holds on both datasets and for the same reason. On Adult, 0 of 14
comparisons survive BH-FDR or Bonferroni; on ACS, 0 of 22. On ACS the largest observed bound
was 0.096 at adversary accuracy 0.591, against a ceiling of 2.65 — 3.6% of the instrument's
range. The conclusion is unchanged and is now dataset-independent: at this canary budget the
instrument cannot resolve subgroup differences, which bounds the effect rather than
establishing its absence.

**H1's structure ordering did not.** At ε = 8 on Adult the three families separate with
mutually non-overlapping CIs, `aim` (0.0078) < `pairwise` (0.0283) < `independent` (0.0947).
On ACS the ordering inverts — `pairwise` (0.0202) < `independent` (0.0535) ≈ `aim` (0.0626) —
and AIM is **not statistically distinguishable** from the independent-marginals baseline.

Per the analysis plan, a contradicting result is diagnosed, not adjusted. The diagnosis:

- The engineering model-size bound is **not** responsible — `skipped_cliques_` is empty at
  both ε = 0.5 and ε = 8, with 17 cliques measured at each.
- The structure metric is the correlation of a **single column pair**, and AIM's score on it
  is largely determined by whether that pair is among the ~6 two-way cliques AIM selects. On
  Adult, AIM selects `age`×`hours_per_week` at *every* ε tested. On ACS it selects
  `AGEP`×`WKHP` at one of three, and the ACS correlation error tracks that selection exactly:
  0.0977 (not selected) → 0.0395 (selected) → 0.0626 (not selected).

This was later tested directly rather than left as an inference from one pair, by recording
AIM's error and its clique selection for EVERY numeric pair across the grid
(`scripts/run_clique_confound.py`). The test weakened the claim, and the weakened version is
what this thesis states.

It is **not** true that AIM beats the no-dependence baseline only on pairs it selects — each
dataset has one unselected pair where it still wins, which is mechanistically expected, since
measuring a clique constrains the joint and a graphical model propagates that constraint
outside the clique. What is true is a large difference in degree, which itself does not
transfer:

| | largest advantage on a selected pair | largest on an unselected pair | ratio |
|---|---:|---:|---:|
| Adult | +0.0852 | +0.0072 | 11.9x |
| ACS | +0.0285 | +0.0123 | 2.3x |

On Adult, AIM's advantage on the pair it selects is nearly twelve times its best advantage
anywhere else, and `age x hours_per_week` — the pair the H1 headline measured — is that pair,
selected in 22 of 25 cells. On ACS the effect is roughly five times weaker and the run's own
verdict is inconclusive.

The defensible claim is therefore narrower than a first reading of the single-pair evidence
suggested: **the structure metric's choice of column pair materially affects the measured
ranking, and on Adult it happened to fall on AIM's strongest pair by an order of magnitude.**
That still carries a generalisable warning — a benchmark scoring a marginal-based mechanism on
a small fixed set of low-order statistics may be measuring which statistics the mechanism
chose to spend budget on — but it does not support the stronger reading that AIM's advantage
is entirely an artefact of selection. The cross-dataset pattern is the same one H1 itself
showed: an effect on Adult that does not carry to ACS.

A secondary observation, reported because it is counter-intuitive and was verified before
being written down: on ACS, AIM's downstream utility **falls** as ε rises (TSTR F1 0.704
[0.695, 0.713] at ε = 0.5 against 0.581 [0.539, 0.629] at ε = 8; the endpoint CIs do not
overlap). The cause is the same mechanism — the DP profiler suppresses far fewer rare
categories at a larger budget (OCCP 3 → 23 categories, RELP 3 → 14), so a roughly fixed clique
allowance covers proportionally less of the domain and fewer cliques land on the target
column. AIM optimises global marginal approximation, not a downstream task.

These observations are pinned by `tests/test_acs_h1_findings.py`, so the prose above cannot
drift from the committed results without a test failing.

---

## 6.10 H3: utility-weighted budget allocation

D5 was closed by running H3 on both datasets under the same protocol as H1: 5 epsilon values,
5 seeds, and a paired design in which the two arms differ **only** in how a fixed total budget
is split across columns.

**Where the weights come from, because that is the whole design question.** They are
*declared*, not measured. The analyst names the columns they care about — for Adult,
`income`, `education`, `hours_per_week`, `occupation` — and those columns receive weight 4
while every other column keeps weight 1. That declaration is public metadata, exactly like the
schema's numeric bounds, and so costs nothing.

Deriving the weights from the data instead — mutual information with the target, a
feature-importance run, anything measured — would be a data-dependent parameter choice made
with an uncharged query, and every epsilon reported here would be a false statement. That
version of H3 is not testable at any budget and was not run.

**How the split is priced.** `calibrate_weighted_scales` fixes the *shape* of the allocation
analytically (for Gaussian mechanisms under RDP the per-query cost goes as `1/scale^2`, so a
column of weight `w` takes `scale ∝ 1/sqrt(w)`) and then finds its *size* by bisecting against
the accountant, exactly as the scalar calibration does. No epsilon in this section is computed
by hand. Two properties are asserted by test rather than assumed: a uniform weight vector
reproduces the scalar calibration to within tolerance, and the weighted arm never composes to
more than the uniform arm. The second matters most — a weighted arm that quietly overspent
would manufacture a utility gain out of extra privacy loss.

### Result: not supported, on either dataset

**UCI Adult** — TSTR macro F1, paired weighted-minus-uniform gap with 95% bootstrap CI:

| eps | uniform | weighted | gap [95% CI] | supports H3 |
|---:|---:|---:|---|---|
| 0.5 | 0.4314 | 0.4493 | +0.0179 [-0.1142, +0.1145] | no |
| 1 | 0.4160 | 0.4333 | +0.0173 [-0.0268, +0.0519] | no |
| 2 | 0.3983 | 0.4289 | +0.0305 [-0.0136, +0.0857] | no |
| 4 | 0.4663 | 0.4427 | -0.0236 [-0.0549, +0.0076] | no |
| 8 | 0.4698 | 0.4749 | +0.0051 [-0.0266, +0.0486] | no |

**ACSIncome (CA 2018)**:

| eps | uniform | weighted | gap [95% CI] | supports H3 |
|---:|---:|---:|---|---|
| 0.5 | 0.4753 | 0.4796 | +0.0043 [-0.0070, +0.0149] | no |
| 1 | 0.4850 | 0.4828 | -0.0023 [-0.0115, +0.0073] | no |
| 2 | 0.4829 | 0.4869 | +0.0040 [-0.0184, +0.0265] | no |
| 4 | 0.4871 | 0.4854 | -0.0016 [-0.0148, +0.0147] | no |
| 8 | 0.4893 | 0.4873 | -0.0021 [-0.0142, +0.0076] | no |

At none of the ten dataset-epsilon combinations does the paired gap have an interval excluding
zero. On Adult the point estimates are mixed in sign (three positive, two negative) and the
intervals are wide; on ACS the gaps are smaller still (|gap| <= 0.004) with tighter intervals,
which is the stronger null of the two.

**Reading it honestly.** This is a null about *this mechanism*, not about budget allocation in
general. The independent-marginal generator measures one 1-way marginal per column and samples
each column independently, so a better-measured marginal on the target improves that column's
own distribution and nothing else — there is no cross-column structure for the extra budget to
sharpen. The result is therefore consistent with the mechanism's design, and the interesting
version of H3 would repeat it on `pairwise` or `aim`, where budget could be steered toward
*cliques* rather than columns. That is stated as future work rather than claimed here.

The same caveat that governs H2 applies: a null bounds the effect at this scale, it does not
establish that no effect exists.

---

D2 is the deviation most likely to be challenged, because changing a measurement mid-study can
look like fishing. The defence is that the change was made for a diagnosed measurement defect,
the diagnosis is quantified and reproducible, and the fix moved the result *away* from the
direction that would have been convenient to report — the earlier contaminated analysis
supported "no difference between mechanism families", which is a weaker and less interesting
claim than the one the corrected analysis supports.

# Chapter 7 — Results and Analysis

**Target: 2,500 words.** Depends on M1.13 and M2.8. The core empirical chapter.

> **Every number here traces to a committed experiment with a recorded seed.**
> If it cannot be regenerated by `make reproduce`, it does not appear.

## 7.1 Calibration validation (~250 words)

Target vs achieved ε across mechanisms and step counts. This establishes that every ε reported
downstream means what it says — the rest of the chapter depends on it, so it goes first.

## 7.2 Auditor validation (~300 words)

**Before trusting any audit result, show the instrument works.** Run it against a deliberately
broken mechanism and show detection; run it against a correct one and show the null. Report the
detection floor at each canary count.

Without this section, ε_audited ≈ 0 is indistinguishable from a broken auditor — which is
exactly the failure the first self-audit found.

## 7.3 H1 — the proved-vs-audited gap (~600 words)

The primary result. ε_audited / ε_proved by mechanism family and by ε, with confidence
intervals. Report the direction honestly, including the case where the gap does *not* differ
across families.

**Figure:** ε_proved vs ε_audited with CI bands.

## 7.4 Privacy–utility frontier (~400 words)

TSTR and TRTR against ε per mechanism, bootstrapped. Where does usable utility end? That
threshold is the practically useful contribution for a data holder.

## 7.5 Attack range (~400 words)

LiRA, DOMIAS, anonymeter, attribute inference. AUC and TPR@0.1%FPR. Relate measured attack
success back to ε_audited.

## 7.6 H2 — subgroup disparity (~400 words)

Per-subgroup ε_audited by race and sex under uniform allocation, with confidence intervals.

**The most publishable result in the project if the effect is real — and a genuinely useful
negative result if it is not.**

## 7.7 H3 — allocation strategy (~150 words)

Weighted vs uniform allocation at equal total ε. This is stretch scope; report it as such if
incomplete rather than omitting the hypothesis.

## Discipline for this chapter

- Refuted hypotheses are reported as clearly as confirmed ones.
- Every table carries n, seed count, and the CI method.
- No result appears without an uncertainty estimate.

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

[WRITE: ~250 words. State that this establishes every ε downstream means what it says, and that calibration never overspends. The pre-calibration failure — ε=8 requested, 70.49 composed — belongs here as the motivation.]

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

[WRITE: ~300 words. The instrument works — positive control detected at m=10, negative control never fires. Then the ceiling, and the consequence: H1 ran at m=60 where the ceiling is 2.97 against a proved ε of 7.36, so the gap was structurally guaranteed. Attribute the ceiling to Steinke et al. Thm 2.1 / Eq. (3) — it is not ours.]

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

[WRITE: ~600 words. The structure ordering does NOT transfer; the TSTR ordering does. Diagnose: the metric scores a single column pair, and AIM's score on it depends largely on whether that pair is among its selected cliques. State the weakened version — each dataset has a counterexample — and the 11.9x vs 2.3x difference in degree.]

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

[WRITE: ~400 words. A BOUNDED null, not a bare one: multiplicity correction (0 of 14 survive BH-FDR on Adult, 0 of 22 on ACS), TOST equivalence (2 of 14 equivalent to chance within a pre-specified margin), and stated detectability (the adversary needed 0.600 and reached 0.562). Explain why canaries were allocated equally, not proportionally.]

---

## 7.7 H3 — allocation strategy

[WRITE: ~150 words. Not supported on either dataset: at no ε does the paired weighted-minus-uniform gap in TSTR macro F1 have a bootstrap CI excluding zero. The null replicates. Note that the weights are declared public metadata — deriving them from the table would be an uncharged query. Source: `results/h3_allocation.json`.]

# Chapter 8 — Discussion and Conclusion

**Target: 1,500 words.** Depends on M2.

## 8.1 Interpretation (~400 words)

What does the proved-vs-audited gap mean for a practitioner? If ε_proved = 8 but no attack
recovers more than ε_audited = 0.6, what should a data holder actually do?

There are two readings — the bounds are loose, or the attacks are weak — and the chapter should
say how to tell them apart. Be careful not to overclaim: **a failed attack is not proof of
safety**, and the audit only lower-bounds what *these* adversaries achieved.

## 8.2 The self-audit as method (~250 words)

A genuinely distinctive section, and one most theses cannot write.

This project audited its own codebase adversarially and found: fabricated metrics in four
modules, an unsound subsampling bound that under-reported ε by roughly 2×, a zero-noise shortcut
that voided the guarantee while still charging budget, mechanisms charged but never applied, and
a mechanism-dispatch bug that meant two "different" generators were secretly the same one. Each
defect is now defended by a named regression test.

The general argument: **DP implementations need adversarial code review as standard practice**,
because a privacy claim is only as strong as its least-checked line. Most published DP systems
have never had this done to them, and the failures found here were not exotic — they were
ordinary software defects with extraordinary consequences.

## 8.3 Limitations (~450 words)

Be thorough. A reviewer trusts a paper that finds its own holes.

- Unbounded min/max sensitivity in the profiler, if M1.7 did not land.
- Simplified canary audit versus the full Steinke construction.
- The ledger is tamper-*evident*, not tamper-*proof*; key custody is an organisational control,
  not a cryptographic one.
- `dp_accounting` is treated as trusted (mitigated by the differential test, if M2.9 landed).
- Tabular data only; record-level privacy only; single data holder.
- Any hypothesis not fully tested — state it plainly rather than letting it go unmentioned.

## 8.4 Future work (~250 words)

User-level privacy for multi-row individuals; multi-party and federated settings; a formal proof
of the pipeline invariant (no read without a charge); a deployment study with a real data holder;
and extending the Privacy Data Sheet format toward a community standard.

## 8.5 Conclusion (~150 words)

Return to the thesis statement. State what was demonstrated — and, with equal clarity, what
was not.
