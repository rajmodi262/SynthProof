# SynthProof — Defence Pack

**Validity · Literature · Authenticity · Research depth**

MIT-WPU · CSE-AIDS Capstone 2026-27 · Panel B ·
Raj Modi · Krishna Renuse · Aaditya Kumar Sinha · Levinesh G R

This document exists to answer four questions a panel asked and every panel will ask: *is the
problem real, do you know the literature, are your numbers genuine, and is there research here
or only engineering?* Every figure below is quoted from a committed result file in the
repository, and the file is named beside it. Nothing here is estimated, rounded for effect, or
carried over from a slide.

<!--contents-->

## 0. Read this first — the four answers in ninety seconds

**Is the problem real?** Yes, and it is documented rather than argued. Sweeney (2000) showed
87% of Americans are uniquely identified by ZIP, date of birth and sex; Narayanan and Shmatikov
(2008) de-anonymised Netflix subscribers against public IMDb reviews; and Stadler, Oprisanu and
Troncoso (USENIX Security 2022) showed that synthetic data — the fix the industry now reaches
for — provides neither the privacy nor the utility routinely claimed for it. The gap we work in
is narrower and sharper than "privacy is hard": **a formal privacy guarantee is a property of a
mechanism, and nobody checks that a given implementation actually has it.**

**Do we know the literature?** 27 works are cited in `docs/thesis/references.bib` and used in
Chapter 2 across six threads: formal DP, implementation pitfalls, DP synthesis, membership
inference, empirical auditing, and transparency artefacts. Section 3 of this document gives a
per-paper account of what each establishes, what we took from it, and what we deliberately did
not take. Section 3.7 lists the works we have identified but not yet cited, with search terms,
because a survey that pretends to be complete is not a survey.

**Are the numbers genuine?** The project's own first self-audit found **fabricated metrics in
four separate modules** — including a class named `AIMGenerator` that ran independent histograms,
and an accuracy figure computed as `auc = accuracy + 0.05`. Twelve such defects have been found
and fixed. Six standing rules were adopted in response, encoded in the PR-review configuration,
and every result file now carries seeds, confidence intervals and a manifest pinning it to a
commit and an environment. The honest framing is not "we made no mistakes"; it is **"we built
the machinery that catches this class of mistake, and it caught twelve."**

**Is there research here?** Three findings, each a negative or corrective result that survived
attempts to make it go away:

1. **The audit ceiling.** The ε a canary audit can certify is bounded by the canary count
   alone — certifying ε costs about `ln(1/α)·e^ε` canaries. Our headline comparison was
   therefore **structurally impossible before any mechanism ran**. We report the ceiling beside
   every audited ε so a zero is never mistaken for evidence of no leakage.
2. **The clique-selection confound.** A second dataset contradicted the first. The diagnosis
   generalises: any DP-synthesis benchmark scoring a marginal-based mechanism on a small fixed
   set of low-order statistics risks **measuring the mechanism's internal clique selection
   rather than its fidelity**.
3. **Measurement contamination.** Planting audit canaries destroyed 89% of the correlation **[SUPERSEDED 2026-09-06 — does not replicate; see `results/CANARY_DOSE_RESPONSE.md`]**
   signal the utility metric was measuring, producing two confidently-wrong published
   conclusions. The instrument was penalising exactly the mechanisms it was built to reward.

None of the three is the result we set out to get. All three are reportable, and the first and
second are the contribution.

---

## 1. What the system is, stated precisely

SynthProof takes a sensitive tabular dataset and a **publicly declared schema**, and produces
two artefacts: a synthetic table, and a signed **Privacy Data Sheet** recording what the release
cost in privacy terms and what our own attacks recovered from it.

Five properties distinguish it from "a DP synthesiser":

| Property | What it means | Where it lives |
|---|---|---|
| **Every data touch is charged** | Column ranges and category domains are read from a public schema, or released under a noisy threshold. Nothing is read from the data for free | `synthproof/data/profiler.py` |
| **Composition is delegated** | We compose no bounds ourselves. Google's `dp_accounting` does it | `synthproof/accounting/` |
| **ε means what the operator typed** | Requesting ε = 8 previously composed to **70.49**. Calibration inverts the composition theorem by bisection; proved/target ≈ 0.92 and never overspends | `accounting/calibrate.py`, CI-gated over 24 configurations |
| **The spend is recorded tamper-evidently** | Ed25519 over a SHA-256 hash chain, plus a signed head committing to `(entry_count, tip_hash)` so truncation is detected too | `synthproof/ledger/`, 12 adversarial tests |
| **The release is attacked before it ships** | Four attacks plus a canary audit, and the **limit of that audit** is printed on the certificate | `synthproof/attacks/`, `synthproof/audit/` |

**The single sentence for a panel:** *we ship the privacy claim as a checkable document
attached to the data, instead of as a sentence in a paper nobody reads.*

### 1.1 Scale of the artefact

| | |
|---|---|
| Python, package | **8,328 lines** across 9 modules |
| Python, tests | **5,543 lines**, 31 files, **373 test functions** |
| Commits on the working branch | 68 |
| Generator families implemented | 4 — `independent`, `pairwise`, `aim` (private-PGM), `copula` |
| Attacks implemented | 4 — distance MIA, exact-match singling-out, DOMIAS, attribute inference |
| Auditors implemented | 2 — paired Clopper-Pearson, one-run (Steinke et al. 2023) |
| Experiment cells run | 75 per dataset per hypothesis grid, on 2 datasets |
| Datasets | UCI Adult (SHA-256 verified) and ACSIncome CA 2018 |

---

## 2. Research design

### 2.1 The research questions

**RQ1.** For a differentially private synthetic-data release, how large is the gap between the
formal privacy bound the mechanism proves and the empirical privacy loss an adversary can
demonstrate — and does that gap differ across mechanism families?

**RQ2.** Is that empirical loss distributed evenly across the population, or do minority
subgroups bear more of it under a uniform budget?

**RQ3.** Does allocating the privacy budget non-uniformly across columns, weighted by declared
utility, buy more downstream accuracy than allocating it uniformly?

**RQ4 (methodological, and the one that produced the contribution).** What can a canary audit
of a synthetic-data release actually establish, and what are the limits of that instrument?

RQ4 was not in the original plan. It exists because RQ1 could not be answered without first
establishing whether the instrument answering it worked — and it did not, in a way that turned
out to be structural rather than fixable.

### 2.2 The hypotheses, as preregistered

Preregistered **2026-08-05**, before the full-scale grid was run, in `docs/preregistration.md`,
with a commitment to report all outcomes regardless of direction.

| | Hypothesis | Outcome |
|---|---|---|
| **H1** | The audited/proved ratio, and the utility bought at fixed ε, differ across generator families | **Split.** Utility and structure: supported on Adult, **did not transfer** to ACS. Privacy half: **disqualified** by the audit ceiling |
| **H2** | Under uniform budget, audited privacy loss is higher for minority subgroups | **Not supported**, on both datasets. A *bounded* null, not merely an absent signal |
| **H3** | Utility-weighted budget allocation beats uniform at fixed total ε | **Not supported**, and the null **replicated** across both datasets |

Preregistering before running is what separates a result from a result-shaped narrative, and it
is the single strongest answer to "how do we know you did not fit the story to the data."

### 2.3 The parameters, fixed in advance

| | |
|---|---|
| Datasets | UCI Adult (n = 48,842; 30,162 complete rows; **6,000-row subsample**) and ACSIncome CA 2018 (**6,000 rows**) |
| ε grid | 0.5, 1.0, 2.0, 4.0, 8.0 |
| δ | 1 × 10⁻⁵ — chosen so δ < 1/n (1.7 × 10⁻⁴), the standard requirement |
| Seeds | 5 per cell |
| Primary utility metric | Downstream macro F1, **TSTR** (train on synthetic, test on real) |
| Primary privacy metric | ε_audited from the one-run construction (Steinke, Nasr & Jagielski 2023) |
| Uncertainty | Bootstrapped 95% CIs, 4,000 resamples |

### 2.4 Deviations from the preregistration, declared

Declaring deviations is not an admission — undeclared deviation is the problem; declared
deviation is method. All five are in `docs/thesis/ch06-methodology.md` §6.8.

| # | Deviation | Why | Direction of effect |
|---|---|---|---|
| **D1** | ACSIncome added | Original plan named it and it was initially skipped; it was then run in full | **Closed.** External validity was tested, and the H1 structure ordering **did not transfer** |
| **D2** | Utility measured on a second, canary-free model fit | Canaries destroyed the correlation signal being measured (§7.3) | Removed a bias that penalised the better mechanisms. Made H1 measurable at all |
| **D3** | Auditor changed to the one-run construction | The paired estimator spends two canaries per comparison and saturates sooner | Slightly raises the bound at fixed budget. **Both are reported and compared** |
| **D4** | Structure metric added alongside TSTR | TSTR alone cannot separate an independent-marginal mechanism from a structured one on this data | Additive, not substitutive. TSTR is still reported |
| **D5** | H3 run on both datasets | Originally unrun | **Closed.** Null on both |

Note the direction of D2 and D4: both make it **harder** to report a clean H1, not easier. D2
in particular corrected a bias that was producing a *confident null in our favour* — we removed
a mistake that flattered the write-up.

---

## 3. Literature survey

### 3.1 How this survey was built, and its honest limits

This is a **targeted survey**, not a systematic review. It was assembled by following citation
chains from four anchor papers — Dwork et al. (2006), McKenna et al. (2022), Stadler et al.
(2022) and Steinke et al. (2023) — and by searching five term clusters recorded at the end of
`ch02-literature-review.md`. It does not claim exhaustive coverage of DP, which is a literature
of thousands of papers; it claims coverage of the six threads the project's claims actually
depend on.

**Selection rule.** A work is cited if the project either (a) implements it, (b) delegates to
it, (c) adopts its methodological argument, or (d) is positioned against it. Works read but not
load-bearing are not cited, per the note at the head of `references.bib`: *every entry here is
cited somewhere; if you drop a citation, drop the entry.*

**arXiv versions are preferred** where they exist, because pagination is stable and a reviewer
can reach them without a subscription.

### 3.2 Thread 1 — Formal differential privacy

**Dwork, McSherry, Nissim & Smith (2006), *Calibrating Noise to Sensitivity in Private Data
Analysis*, TCC.** The founding definition. A randomised mechanism *M* is (ε, δ)-differentially
private if for all neighbouring datasets *D*, *D′* and all output sets *S*,
Pr[*M*(*D*) ∈ *S*] ≤ e^ε · Pr[*M*(*D′*) ∈ *S*] + δ. Its power is that it quantifies over **all**
adversaries and **all** auxiliary knowledge — unlike every syntactic scheme before it.
*What we take:* the definition itself, and the Laplace mechanism. *What we note:* it quantifies
over the **worst case**, and the worst case may be far from what any real adversary achieves.
That gap between worst case and achieved case is exactly what RQ1 tries to measure.

**Dwork & Roth (2014), *The Algorithmic Foundations of Differential Privacy*, FnTTCS.** The
standard monograph: mechanisms, sensitivity, composition, the exponential mechanism.
*What we take:* the exponential mechanism (used in AIM's selection step and required, as our own
audit found, in the profiler's fallback path), and basic/advanced composition as the baseline our
accountant must beat.

**Mironov (2017), *Rényi Differential Privacy*, CSF.** Reformulates the guarantee in terms of
Rényi divergence, giving composition that is simply **additive** in the RDP curve and converts to
(ε, δ) once at the end. This is the accounting standard today.
*What we take:* the accounting model, via `dp_accounting`. *What we explicitly do not do:*
implement it ourselves — see §5.2 for why that decision was forced on us by our own error.

**Balle, Barthe, Gaboardi, Hsu & Sato (2020), *Hypothesis Testing Interpretations and Rényi
DP*, AISTATS.** Tighter RDP→(ε,δ) conversion, and the hypothesis-testing reading of DP.
*What we take:* the hypothesis-testing framing is the conceptual bridge between the formal bound
and the audit — an audit *is* a hypothesis test about membership, which is why an ε lower bound
can be read off a confusion matrix at all.

**Kasiviswanathan & Smith (2014), *On the "Semantics" of Differential Privacy*, JPC.** The
Bayesian reading: DP bounds how much an adversary's posterior about any individual can shift.
*What we take:* the odds interpretation printed on our data sheet.

**Nanayakkara, Smart, Cummings, Kaptchuk & Redmiles (2023), *What Are the Chances? Explaining
the Epsilon Parameter in Differential Privacy*, USENIX Security.** Empirically tests how to
communicate ε to non-experts, and finds odds-based statements outperform alternatives.
*What we take:* the exact form of the plain-language statement in the signed payload —
`e^ε/(1+e^ε)`, rendered as "an adversary who already knows everything else guesses your
membership *n* times in 100". At ε = 1 that is 73; a coin toss is 50.

### 3.3 Thread 2 — Where implementations lose the guarantee

This thread is the intellectual spine of the project. It is short, and it matters more than its
length suggests.

**Mironov (2012), *On Significance of the Least Significant Bits for Differential Privacy*,
CCS.** Naive floating-point Laplace sampling by inverse-CDF leaks through the low-order bits of
the output and **breaks the guarantee entirely** — the proof is correct and the implementation
still fails.
*What we take:* the requirement to sample discretely rather than sample-and-round.
*What we are careful about:* our `noise.py` originally claimed immunity to this attack while
using a float Bernoulli internally. The claim has been **narrowed** to the output-representation
form, which is what the code actually defends. Overclaiming a defence is the same sin the paper
documents.

**Canonne, Kamath & Steinke (2020), *The Discrete Gaussian for Differential Privacy*, NeurIPS.**
Exact samplers for the discrete Gaussian and discrete Laplace — and, crucially, the result that
**rounding a continuous Gaussian does not produce a discrete Gaussian**. A system that rounds is
not running the mechanism its proof describes.
*What we take:* Algorithm 1, implemented directly in `accounting/noise.py` and χ²-tested against
the exact PMF.

**The pattern these two establish, in one line:** *the theory is mature; the gap between the
theory and a given implementation of it is where guarantees are lost.* That sentence is the
project's thesis. Everything else is an attempt to make that gap visible to someone who is not
reading the source.

### 3.4 Thread 3 — Differentially private synthetic data

**McKenna, Sheldon & Miklau (2019), *Graphical-model based estimation and inference for
differential privacy*, ICML (private-PGM).** Given noisy measurements of low-order marginals,
find a distribution consistent with them via graphical-model inference.
*What we take:* the inference engine. Our `aim` generator depends on `mbi` 1.3.0 and therefore
requires Python 3.11.

**McKenna, Miklau, Hay & Machanavajjhala (2021), *Winning the NIST Contest*, JPC.** The
marginal-based approach won the NIST synthetic-data challenges, which is the empirical case for
preferring it on tabular data.
*What we take:* the justification for choosing this family over deep generative models.

**McKenna, Mullins, Sheldon & Miklau (2022), *AIM: An Adaptive and Iterative Mechanism*, VLDB.**
At each round, select whichever marginal is currently worst approximated (via the exponential
mechanism), measure it, re-solve. Adaptivity costs budget — selection is itself a mechanism —
but spends the rest far better. §4 bounds model size.
*What we take:* the mechanism, and the model-size bound (adopted after an unbounded junction
tree exhausted memory mid-grid; ours is capped at 128 MB).
*What we found out about it:* see §7.2. AIM's clique selection interacts with the benchmark
metric in a way that, on our evidence, can dominate the measured result.

**Xie et al. (2018), *DP-GAN*; Jordon, Yoon & van der Schaar (2019), *PATE-GAN*, ICLR.** The deep
generative line.
*Why we do not use them:* on tabular benchmarks they are generally outperformed by
marginal-based methods. This is a stated scope decision, not an oversight — and we have not
benchmarked them ourselves, so we do not assert the comparison as our finding.

**Ding, Hardt, Miller & Schmidt (2021), *Retiring Adult: New Datasets for Fair Machine
Learning*, NeurIPS.** Builds ACSIncome and its siblings from US Census PUMS as a modern
replacement for UCI Adult, explicitly because Adult is small, dated and over-fitted by the
community.
*What we take:* our second dataset, and the argument for why one dataset is not enough. This
paper is the reason the clique-selection confound was findable at all.

### 3.5 Thread 4 — The critical literature, and why the project exists

**Stadler, Oprisanu & Troncoso (2022), *Synthetic Data — Anonymisation Groundhog Day*, USENIX
Security.** Tests a range of synthetic-data generators against linkage and inference attacks and
finds synthetic data provides **neither the privacy nor the utility routinely claimed for it**;
generators without a formal guarantee frequently reproduce outlier records verbatim.
*What we take:* the direct motivation. Two consequences follow and we state both:
(i) *synthetic* describes how data was produced, not what it discloses — **the word carries no
privacy content**; (ii) the mechanisms that do carry a formal guarantee are precisely the ones
whose guarantee nobody independently verifies, because verifying requires reading the
implementation rather than the paper.
*How this shaped the design:* our negative control — a release with perfect marginals and no
real records — must **not** fire the auditor. A metric that fires there is measuring *similarity*
rather than *disclosure*, which is the failure this paper documents across the field.

**Sweeney (2000), *Simple Demographics Often Identify People Uniquely*.** 87% of the US
population uniquely identified by ZIP + date of birth + sex.
*What we take:* the motivating example, and the specific warning that the fields nobody thinks
of as identifying are the ones that identify. We are careful to say the **87% figure is
American** and we do not claim it for India; what transfers is the principle, which a PIN code
plus a full date of birth demonstrates arithmetically.

**Narayanan & Shmatikov (2008), *Robust De-anonymization of Large Sparse Datasets*, IEEE S&P.**
The Netflix Prize de-anonymisation against public IMDb reviews.
*What we take:* the demonstration that auxiliary information an organisation does not control is
the thing that breaks a release — which is exactly the quantifier DP was invented to close.

### 3.6 Thread 5 — Attacks and empirical auditing

**Shokri, Stronati, Song & Shmatikov (2017), *Membership Inference Attacks Against ML Models*,
IEEE S&P.** The shadow-model attack: train many models on same-distribution data to learn the
member/non-member difference.
*What we take:* the framing of membership inference as *the* privacy instrument.

**Carlini, Chien, Nasr, Song, Terzis & Tramèr (2022), *Membership Inference Attacks From First
Principles*, IEEE S&P (LiRA).** Fits per-example Gaussians to IN and OUT score distributions and
runs a calibrated likelihood-ratio test. Their **methodological** argument matters as much as
the attack: average accuracy is the wrong metric, because a violation affecting a few people
with high confidence is far worse than a marginal population-wide improvement. They argue for
**TPR at low FPR**.
*What we take:* the reporting convention, throughout.
*What we deliberately do not do:* implement LiRA. A shadow-model attack at our scale is roughly
21 hours of compute for a likely wide-CI null, and calling anything cheaper "LiRA" would misname
it. The console and API render it as **NOT IMPLEMENTED** rather than omitting the row — see
standing rule 4.

**van Breugel, Sun, Qian & van der Schaar (2023), *Membership Inference Attacks against Synthetic
Data through Overfitting Detection*, AISTATS (DOMIAS).** Scores membership by a density ratio
between the synthetic distribution and a reference population — adapted specifically to
synthetic data rather than to models.
*What we take:* implemented in `attacks/domias.py` with a k-NN density estimator.

**Giomi, Boenisch, Wehmeyer & Tasnim (2023), *A Unified Framework for Quantifying Privacy Risk
in Synthetic Data*, PoPETs (Anonymeter).** Separates **singling out**, **linkability** and
**inference** as three distinct risks with distinct attack simulations.
*What we take:* the refusal to collapse "privacy risk" into one number, and the singling-out
attack shape.
*A defect this framing caught:* our web console once displayed an "Anonymeter Risk 0.040" card
with **no data source** — the data sheet carries no singling-out field. It was fabricated. It is
gone.

**Jagielski, Ullman & Oprea (2020), *Auditing Differentially Private Machine Learning*,
NeurIPS.** Establishes the proved-versus-audited framing: instantiate a strong adversary,
measure its success, convert to an empirical lower bound. A large gap means either the analysis
is loose *or the adversary is weak* — the ambiguity is inherent.
*What we take:* the entire framing of RQ1, and the honesty that the ambiguity imposes.

**Nasr, Song, Thakurta, Papernot & Carlini (2021), *Adversary Instantiation*, IEEE S&P.**
Tighter lower bounds through better adversary instantiation.
*What we take:* the reminder that our own audited numbers are a statement about **our
adversary**, not about the mechanism.

**Steinke, Nasr & Jagielski (2023), *Privacy Auditing with One (1) Training Run*, NeurIPS.**
Include each of *m* canaries independently at random, have the adversary guess a subset, derive
an ε lower bound from the resulting counts via exact binomial confidence intervals. Makes
auditing tractable for expensive mechanisms.
*What we take:* the construction, implemented in `audit/steinke.py`.
*What we derived from it, and this is the project's main finding:* the same construction implies
a **ceiling**. With a perfect adversary the bound solves p^r = α, giving
ε_max(r) = log(a/(1−a)) with a = α^(1/r) ≈ log(r / ln(1/α)) — so certifying ε costs about
ln(1/α)·e^ε canaries, **exponential in ε**. §7.1 works this through. The ceiling is discussed in
§7 of the paper; the consequence for a benchmark like ours is what we report.

**Structural limits of auditing, as the literature and our results jointly establish:** an audit
bounds what *the attacks you ran* achieved. It is not a guarantee, it produces no budget, it
does not compose, and — the practical point — **its results live in a paper, not attached to the
artefact anyone downloads.**

### 3.7 Thread 6 — Budget management and transparency artefacts

**Lécuyer, Spahn, Vodrahalli, Geambasu & Hsu (2019), *Sage*, SOSP.** Treats the privacy budget
as a systems resource scheduled across a stream of queries.
**Kotsogiannis et al. (2019), *PrivateSQL*, VLDB.** Allocates budget across a workload to
maximise utility.
*What both establish:* budget management within a system boundary is a solved-ish systems
problem. *What neither does:* make the resulting record **tamper-evident** or **transferable to
an external auditor**. That is the seam we work in.

**Gebru et al. (2021), *Datasheets for Datasets*, CACM; Mitchell et al. (2019), *Model Cards*,
FAT\*; Bender & Friedman (2018), *Data Statements*, TACL.** The transparency-artefact line:
ship a standard document describing provenance, composition, intended use.
*What we take:* the artefact format, and the name of our own output.
*The limitation we are positioned against, stated plainly:* these are **prose written by the
producer, asserting properties of an artefact, with no mechanism for a reader to verify any of
it**. A datasheet records what a dataset *is*. None of them record, in checkable form, what it
**discloses**. Our data sheet is signed, and `synthproof verify sheet.json --pubkey org.pub` is
runnable by a third party who has neither our code's trust nor our data.

**Regulatory convergence.** The EU AI Act creates documentation obligations for training data in
high-risk systems, and India's DPDP Act 2023 constrains processing of personal data. Both make
training-data provenance a compliance artefact rather than good practice. *We cite these as
context, not as legal analysis — none of us is qualified to give the latter, and we say so.*

### 3.8 The positioning matrix

| Approach | Upper bound | Lower bound | Composes | Cross-release | Attached to artefact | Third-party verifiable |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| Formal DP synthesis (AIM, MST, PrivBayes) | yes | no | yes | no | no | no |
| Empirical auditing (LiRA, Steinke) | no | yes | no | no | no | no |
| Risk assessment (Anonymeter) | no | yes | no | no | no | no |
| Datasheets / Model Cards | no | no | no | no | yes | no |
| Budget systems (Sage, PrivateSQL) | yes | no | yes | yes | no | no |
| **SynthProof** | yes | yes | yes | within a session | yes | yes, for the sheet |

Read the last row carefully, because an inflated version of it is the easiest thing for a panel
to catch. **Cross-release is "within a session", not "yes"** — there is no cross-session budget
enforcement. **Third-party verifiable applies to the data sheet's signature and arithmetic**, not
to a proof that the pipeline behaved; a verifier checks what we signed, not that we ran what we
said.

### 3.9 The gap, in one paragraph

Formal DP supplies an upper bound that nobody verifies against the implementation. Empirical
auditing supplies a lower bound that carries no guarantee, accumulates no budget, and is not
attached to the artefact. Datasheets are attached to the artefact but describe it rather than
bounding what it reveals. **No existing system releases a dataset accompanied by both bounds,
cryptographically bound to a durable record of the cumulative privacy expenditure.**

Three narrower gaps follow, and each is addressed:

1. **Unaccounted preprocessing.** Published DP synthesis pipelines routinely read column ranges
   and category domains directly from the sensitive data before any mechanism runs. That is a
   real leak which invalidates the headline ε, and it is rarely mentioned. A public schema
   removes the need for it **at zero privacy cost**; where a schema is absent, the domain is
   released under a noisy threshold and charged. The data sheet records which of the two
   happened, in a field called `domain_source`, inside the signed payload so it cannot be
   stripped.

2. **Budget interfaces that mislead.** A system can satisfy the DP definition while its
   interface deceives its operator. Before calibration, requesting ε = 8 from this system
   produced a release composing to **ε = 70.49**. Every step was sound; the number the operator
   typed simply did not mean what they thought it meant.

3. **Unverifiable claims.** Privacy claims are asserted by the party with the strongest interest
   in their being believed. A signed data sheet lets a third party check the arithmetic.

### 3.10 Works identified but not yet cited — the honest gap in the survey

A survey that presents itself as complete is the least credible kind. These are known to us,
not yet load-bearing, and flagged for the final bibliography. **Verify venue and year before
citing any of them** — they are listed from reading notes, not from the `.bib`.

| Area | Work to add | Why it belongs |
|---|---|---|
| Foundations | Dinur & Nissim (2003), reconstruction attacks | The impossibility result that motivates DP at all |
| Syntactic anonymity | k-anonymity (Sweeney 2002), l-diversity, t-closeness | The line DP replaced; a panel may ask why not k-anonymity |
| Composition | Mironov, Talwar & Zhang (2019), subsampled Gaussian RDP | The subsampling bound our own hand-rolled version got wrong |
| DP in ML | Abadi et al. (2016), DP-SGD | The most-deployed DP mechanism; useful contrast |
| Deployment | Abowd (2018), US Census; RAPPOR; Apple/Microsoft telemetry | Evidence DP is production technology, not theory |
| Synthesis | PrivBayes (Zhang et al. 2017) | The other major marginal-based family we do not implement |
| Benchmarking | DPBench (Hay et al. 2016); Tao et al. (2021) DP synthetic benchmarking | Directly relevant to the clique-selection finding |
| Auditing tools | TAPAS (Houssiau et al.) | A practitioner toolbox in exactly our space |
| Tight auditing | Recent work on tight auditing of DP synthetic data generation | Would sharpen or challenge §7.1 |

**Say this out loud if asked about completeness:** *the survey covers what the claims depend on;
these nine are the identified gaps and here is why each matters.* That answer is stronger than a
longer list would be.

---

## 4. Validity — the four kinds, and what threatens each

Panels ask "is this valid?" as one question. It is four, and answering it as four is itself
evidence of research training.

### 4.1 Construct validity — are we measuring what we claim?

| Construct | How it is operationalised | Threat | What we did |
|---|---|---|---|
| Formal privacy loss | ε composed by `dp_accounting` over every charged operation | A hand-rolled bound could be wrong | **We do not write bounds.** Composition is delegated. Our own hand-rolled version under-reported ε by ~2× (0.485 vs 0.956 at q = 0.01) before we removed it |
| Empirical privacy loss | ε_audited from the one-run construction | A weak adversary produces a flattering number | We report the **ceiling** and the **detection floor** beside every audited ε, so a 0 is never read as "no leakage" |
| Utility | TSTR macro F1 against a real held-out split | In-sample evaluation inflates it | TRTR was once a bogus 0.971 measured in-sample; on a shared held-out split it fell to chance for random labels. Real TRTR baseline on Adult: **0.660 [0.646, 0.674]** |
| Structural fidelity | Mean absolute correlation error on one column pair | **A single pair may not represent the joint** | This turned out to be a real defect in the construct — see §7.2. It is now our headline methodological finding rather than a hidden weakness |

The fourth row is the one to volunteer. A construct-validity threat that you found yourself,
diagnosed, and converted into a contribution is worth more than a construct with no known
threats.

### 4.2 Internal validity — is the causal story inside each experiment sound?

| Threat | Status |
|---|---|
| **Measurement contamination** — the audit's canaries altering the thing the utility metric measures | **Found and fixed.** Canaries measurably cut corr(age, hours); the size we first reported is
retracted and does **not** replicate. `run_cell` now fits **twice**: once on the augmented split for the audit, once on the clean split for utility and structure (`separate_utility_fit=True`) | **[SUPERSEDED 2026-09-06 — does not replicate; see `results/CANARY_DOSE_RESPONSE.md`]**
| **Seed artefacts** | 5 seeds per cell; bootstrapped CIs over 4,000 resamples; a detection-floor cell counts only on a **majority** of seeds |
| **Engineering confound in AIM** — the model-size cap suppressing cliques | **Ruled out before the finding was written.** `skipped_cliques_` is empty at both ε = 0.5 and ε = 8, with 17 cliques measured at each |
| **Instrument not working at all** | Positive control (verbatim release, detected at m = 10, TPR 1.00, FPR 0.00, p < 0.001) and negative control (perfect marginals, no real records — never detected) both hold, and CI enforces them |
| **Researcher degrees of freedom** | Preregistered 2026-08-05; all five deviations declared with direction of effect |

### 4.3 External validity — does it generalise?

This is where most capstones are weakest and where we have the most to show, because we
**tested** it rather than listing it as a limitation.

The full preregistered protocol was re-run on ACSIncome (California, 2018), holding identical
everything the protocol controls: n = 6,000, seeds 0–4, the same ε grid, and the analogous
structure column pair (`AGEP`×`WKHP` for `age`×`hours_per_week`). A difference is therefore
attributable to the **data**, not the procedure — and that is enforced by a test:
`tests/test_experiment_scripts.py::test_the_two_datasets_share_the_protocol_that_makes_them_comparable`.

**What transferred:**

- **H2's null replicated**, and for the same reason. Adult: 0 of 14 comparisons survive BH-FDR
  or Bonferroni. ACS: 0 of 22. The conclusion is now dataset-independent.
- **H3's null replicated.** No ε value on either dataset gives a weighted-minus-uniform gap
  whose bootstrap CI excludes zero.
- **The TSTR ordering reproduced**: aim > pairwise > independent on both.

**What did not transfer:**

- **H1's structure ordering inverted.** Adult at ε = 8: aim (0.0078) < pairwise (0.0283) <
  independent (0.0947), all CIs mutually non-overlapping. ACS: pairwise (0.0202) < independent
  (0.0535) ≈ aim (0.0626), with **independent and aim not separating at all**.

Two things could not be held identical, and both are reported rather than corrected away:

1. **True correlation differs** (Adult 0.1034, ACS 0.0721), so *absolute* correlation error is
   not comparable across datasets. Only the **ordering** transfers.
2. **The per-subgroup audit ceiling differs.** A fixed 400-canary budget split across 5 Adult
   race levels gives 80 each (ceiling 3.27); across 9 ACS `RAC1P` levels it gives 44 each
   (ceiling 2.65). ACS's race instrument is **genuinely weaker before any mechanism runs**.
   Equalising the ceilings by raising ACS's budget would have confounded group count with total
   canary count instead.

**Remaining external-validity limits, stated first:** two datasets, both US census-derived,
both single-table, both with a binary income target, at n = 6,000. We do not claim behaviour on
healthcare records, time series, or multi-table schemas, and the system does not support the
last of those at all.

### 4.4 Statistical conclusion validity — are the inferences sound?

| Practice | What we do |
|---|---|
| Uncertainty on every number | Bootstrapped 95% CIs, 4,000 resamples |
| Multiplicity | H2 runs 14 comparisons on Adult and 22 on ACS. Both **Benjamini–Hochberg FDR and Bonferroni** are applied. Nothing survives either |
| Distinguishing "no effect" from "no power" | **TOST equivalence testing.** 2 of 14 Adult comparisons are statistically *equivalent* to chance within a pre-specified margin — that is a **bound on the effect**, not merely absence of evidence |
| Stating detectability | H2's adversary needed accuracy **0.600** to reach significance and reached **0.562**. We publish the number it needed |
| Not over-reading small differences | The auditor comparison states plainly that differences under ~0.2 at 3 seeds are inside noise, and that at budget 120 the *older* auditor is fractionally ahead |
| Reporting anomalies | At m = 100, one seed of five fires at leak 0.00/0.01/0.05 — a false positive. Expected: at α = 0.05 over 5 seeds, P(≥1 FP) ≈ 23%. It is the **same seed** each time, so it is one event replicated, not three. It is why the majority rule exists |

That last row is the single best answer to "did you report everything." We had a false positive
in a negative control, we published it, we explained why it is consistent with the nominal error
rate, and we showed the design decision it justifies.

---

## 5. Authenticity — why the numbers should be believed

### 5.1 The uncomfortable part, said first

The project's first self-audit found **fabricated metrics in four separate modules**. Not bugs —
numbers that looked like measurements and were not:

- `auc = accuracy + 0.05` — a metric derived as an affine function of another and presented as
  independent.
- A class named `AIMGenerator` that ran **independent histograms**.
- A profiler that **charged ε and then published `df.unique()`** — the exact category domain,
  released with no noise.
- A web console displaying four hardcoded `PASSED` attack verdicts with invented figures,
  including a pass for **attribute reconstruction, which did not exist in the codebase**.

**Twelve such defects have been found and fixed.** Volunteering this is not self-harm; it is the
strongest available evidence that the surviving numbers were checked. A project that reports zero
defects has either done no auditing or is not telling you about it.

**Two of the twelve were caught by controls rather than by reading code**, which is why every
new measurement now ships with a positive and a negative control.

### 5.2 The six standing rules

Adopted in response, encoded in `.coderabbit.yaml` so PR review enforces them, and recorded in
`docs/AUDIT_AND_ROADMAP.md` §7.

1. **Never write a bound that cannot be cited.** Composition is delegated to `dp_accounting`.
2. **Never report a number that was not computed.** No hardcoded fallbacks, no derived stand-ins,
   no metric that is an affine function of another presented as independent.
3. **A mechanism that is charged must be applied.** Paying ε and skipping the noise is *worse*
   than not paying: the budget is spent **and** the data leaks deterministically.
4. **Name things what they are.** A nearest-neighbour heuristic is not LiRA.
5. **Illustrative values must be labelled where they are displayed**, not only in a commit
   message.
6. **A null result is a result.** Reframe honestly rather than manufacturing a signal.

Rule 4 is why the console renders LiRA and attribute reconstruction as **NOT IMPLEMENTED**
rather than omitting them. An absent capability is named as absent.

### 5.3 The two defects found by an adversarial audit run against external anchors

Scored against OpenDP / TAPAS / PETS-standard expectations rather than against other capstones:

**Un-noised mode leak in the DP profiler (critical).** The categorical profiler's empty-domain
fallback returned `max(observed, key=counts.get)` — the **exact mode of a sensitive column**,
released with no noise and no charge. Under DP that argmax needs the exponential mechanism.
Measured: at `eps_budget = 0.001` it returned the true mode in **196 of 200 seeds (98%)**, where
a correct mechanism must approach data-independence as ε → 0. The exploitable band is
`profile_eps ≤ 0.01`, and it is **0% at target ε ≥ 0.2** — so **no committed result was
affected**, verified by re-running a committed grid cell and getting all 11 metrics
bit-identical. Fixed by falling back to the schema's **public** domain, else raising
`InsufficientBudgetError` with the fix in the message. Never guess.

**Ledger truncation undetected (high).** Hash chaining detects modification, insertion and
reordering but **not truncation** — a shortened chain is internally consistent. Deleting the
last two entries left `verify()` returning `True`, so an operator could delete exactly the
entries recording a budget overspend. Fixed with a `ledger_head` table committing to
`(entry_count, tip_hash)`, signed. **9 attacks now stopped where 8 were before**, and
`verify_with_reason()` names the failure mode.

Both fixes carry a named regression test, and **each test was verified by reintroducing the
bug**, not by reading it. Both defects had sat behind confident, well-written comments claiming
the opposite — which is the argument for believing measurements over docstrings.

### 5.4 Traceability — how any number in this document can be checked

| Mechanism | What it gives you |
|---|---|
| `results/MANIFEST.json` | Pins results to git commit `{MANIFEST_COMMIT}…`, branch, dirty flag, Python 3.11.4, and exact versions of numpy / pandas / scipy / scikit-learn / dp-accounting 0.6.0 / mbi 1.3.0 / autodp |
| Dataset hashing | UCI Adult verified against committed SHA-256 `7537312d…` on every load |
| Recorded seeds | Every result file carries its seed list |
| `make reproduce` | Re-runs the grid and compares against the manifest |
| `make figures` | All 8 thesis figures regenerate from `results/*.json`, so no figure can go stale |
| `ARTIFACT.md` | Written to the USENIX artifact-evaluation format: every thesis claim mapped to the command that reproduces it, with expected output and runtime |
| PDF build gates | The explainer and simple-guide PDF builders **refuse to build** if the prose disagrees with the committed JSON |

That last one is worth demonstrating live. While writing the plain-language guide, the build
**refused** because the prose said "exactly zero on the negative control" and the data showed 34
of 35 — one false positive at r = 100, ε = 0.070. **The prose was fixed, not the check.**

### 5.5 Testing

| | |
|---|---|
| Test functions | **373**, across 31 files, 5,543 lines |
| Adversarial ledger tests | 12, each an attack run against **live SQLite** by an adversary with file access but no key |
| Property-based tests | Hypothesis, present in the suite |
| Noise correctness | Discrete Gaussian χ²-tested against the exact PMF |
| Calibration gate | CI-enforced across 24 configurations; proved/target ≈ 0.92 and **never overspends** |
| Console tests | 10 vitest tests covering the hand-rolled SSE parser, including a frame split across two network chunks — a case that previously dropped a pipeline stage silently |
| Findings pinned by test | `tests/test_acs_h1_findings.py` pins the clique-selection result so it cannot be quietly edited |

---

## 6. Results, including the ones that did not go our way

### 6.1 H1 — mechanism families, UCI Adult (75 cells: 3 × 5 ε × 5 seeds)

| Mechanism | target ε | proved ε | Correlation error [95% CI] | TSTR F1 [95% CI] |
|---|---:|---:|---|---|
| independent | 0.5 | 0.456 | 0.0934 [0.0802, 0.1063] | 0.472 [0.417, 0.525] |
| independent | 8.0 | 7.356 | 0.0947 [0.0817, 0.1071] | 0.406 [0.297, 0.515] |
| pairwise | 4.0 | 3.664 | **0.0197** [0.0048, 0.0464] | 0.427 [0.362, 0.477] |
| pairwise | 8.0 | 7.356 | 0.0283 [0.0132, 0.0517] | 0.432 [0.368, 0.478] |
| aim | 1.0 | 0.778 | 0.0424 [0.0142, 0.0708] | **0.540** [0.515, 0.565] |
| aim | 8.0 | 6.543 | **0.0078** [0.0031, 0.0125] | 0.505 [0.468, 0.544] |

**TRTR baseline (real → held-out real): 0.660 [0.646, 0.674].**

Two things a panel should be told without being asked. First, `independent` is **flat in ε** —
0.0934 at ε = 0.5 and 0.0947 at ε = 8. That is correct and is the control working: a mechanism
that models no dependence cannot get better at reproducing dependence no matter how much budget
it is given. Second, **every synthetic TSTR is far below the 0.660 real baseline.** We do not
claim synthetic data matches real data here.

### 6.2 H1 on ACSIncome — the ordering inverts

| mechanism | ε = 8 correlation error, Adult | ε = 8 correlation error, ACS |
|---|---|---|
| independent | 0.0947 [0.0817, 0.1071] | 0.0535 [0.0471, 0.0604] |
| pairwise | 0.0283 [0.0132, 0.0517] | **0.0202** [0.0076, 0.0383] |
| aim | **0.0078** [0.0031, 0.0125] | 0.0626 [0.0432, 0.0753] |

On Adult all three separate with non-overlapping CIs. On ACS, **independent and aim do not
separate**. Reported as measured; §7.2 is the diagnosis.

### 6.3 H2 — subgroup disparity: a *bounded* null

`race`, ε = 8.0 (proved ε 7.356), 80 canaries per subgroup, per-subgroup ceiling **3.27**:

| subgroup | population share | attack accuracy | ε audited | p |
|---|---:|---:|---:|---:|
| Other | 0.008 | **0.562** | 0.036 | 0.224 |
| Amer-Indian-Eskimo | 0.010 | 0.533 | 0.000 | 0.340 |
| Asian-Pac-Islander | 0.030 | 0.521 | 0.000 | 0.445 |
| Black | 0.095 | 0.529 | 0.036 | 0.438 |
| White | 0.857 | 0.542 | 0.000 | 0.268 |

The **direction is consistent with H2** — the rarest subgroup has the highest attack accuracy at
both ε settings, and the largest sits at or near exactly chance. **It is not significant.** The
largest audited ε is 0.036 against a ceiling of 3.27 — about **1% of the instrument's range**.

Equal canary allocation across subgroups is deliberate: proportional allocation would give
`Other` (0.8% of rows) about 3 canaries and `White` (85.7%) about 343, and since the ceiling
falls with the guess count, **the rare groups H2 is about would get the weakest instrument.**

### 6.4 H3 — budget allocation: null, replicated

Utility-weighted versus uniform allocation at fixed total ε, 5 ε × 5 seeds × 2 arms, both
datasets. At **no** ε value on **either** dataset does the paired weighted-minus-uniform gap in
TSTR macro F1 have a bootstrap CI excluding zero. Example at ε = 8: +0.0051 [−0.0266, +0.0486].

One design point worth stating: the weights are **declared public metadata**, never measured
from the table. Deriving them from the data would be an uncharged query — the exact leak the
project exists to close.

---

## 7. The three findings

### 7.1 Finding 1 — the audit ceiling is information-theoretic

`ε_audited = log(TPR_lower / FPR_upper)` from binomial confidence intervals. With *r* guesses
those intervals cannot be arbitrarily tight, so there is a **maximum ε the instrument can
report** — even against a release that is 100% verbatim training data. With a perfect adversary
the bound solves p^r = α:

```
eps_max(r) = log( a / (1 - a) ),    a = alpha^(1/r)     ~=  log( r / ln(1/alpha) )
```

Certifying a given ε therefore costs about **ln(1/α)·e^ε** canaries — exponential in ε:

| ε to certify | canaries needed, perfect adversary |
|---:|---:|
| 1.0 | 10 |
| 2.0 | 24 |
| 4.0 | 166 |
| **7.36** | **4,711** |
| 8.0 | 8,932 |

Two auditors, two ceilings, and they must not be quoted interchangeably. The measured row is
the **paired Clopper-Pearson** auditor from `results/detection_floor.json`, which spends two
canaries per comparison; the formula row is the **one-run** construction, which uses all *r*
guesses:

| canaries | 10 | 25 | 50 | 100 | 200 | 400 | 800 |
|---|---:|---:|---:|---:|---:|---:|---:|
| paired, measured at leak = 1.0 | 0.81 | 1.84 | 2.57 | 3.28 | 3.98 | 4.68 | **5.38** |
| one-run, from the formula above | 1.05 | 2.06 | 2.79 | 3.49 | 4.19 | 4.89 | **5.59** |

At every one of the measured points, TPR = 1.00 and FPR = 0.00 — **the adversary is perfect**.
The number is bounded by sample size alone.

**The consequence for our own headline.** H1 ran at m = 60, ceiling ≈ **2.97**, against a proved
ε of **7.36**. The instrument could not have reported above 2.97 *even against a release that
was 100% training data*. **The proved-versus-audited gap was structurally guaranteed before any
mechanism ran.** Nothing about it is evidence concerning the mechanisms.

We checked whether this was our implementation. It is not: moving to the Steinke one-run
construction improved a verbatim release at m = 60 only from 2.034 to **2.168**, and a stronger
adversary would not change the ceiling either. Raising the canary count to 800 lifts the
ceiling only to 5.38 (paired) or 5.59 (one-run) — still below 7.36.

**Attribution first, because this is the question that decides how the finding lands.** The
inequality is **not ours**. It is a one-line corollary of Steinke, Nasr & Jagielski (2023),
Theorem 2.1 / Eq. (3) — the paper we implement: set `v = r` (a perfect adversary) and their
bound reduces to `p(ε)^r ≤ β`. We verified our `max_provable_epsilon` is **bit-identical** to
that derivation at r = 10, 60, 100, 400 and 800. We re-derived a consequence of our own cited
source, and Ganev, Annamalai & Kulynych (2026) then obtained *tight* audits of MST and AIM with
a Gaussian-DP estimator — so the ceiling we hit belongs to the single-threshold estimator we
chose, not to auditing. **What is ours is the measurement**: the detection floor, the ceiling at
the counts we actually ran, and the demonstration that a published proved-vs-audited gap was
structurally guaranteed before any mechanism ran.

**The defensible framing:** *this estimator catches broken implementations; it does not confirm
tight ones.* It found a verbatim release at m = 10. It will never confirm that
ε = 7.36 is tight. We therefore report the ceiling **beside every audited ε, inside the signed
payload**, so a zero can never be read as "no leakage was found".

### 7.2 Finding 2 — the clique-selection confound

The ACS grid contradicted Adult. The diagnosis is the most publishable thing in the project.

The structure metric is the correlation of a **single column pair**. AIM selects roughly six
two-way cliques, and its score on that metric is largely decided by **whether the measured pair
is one of them**. On Adult, AIM selects `age`×`hours_per_week` at *every* ε tested. On ACS it
selects `AGEP`×`WKHP` at one of three, and the ACS error tracks that selection exactly:

```
0.0977  (pair not selected)  ->  0.0395  (selected)  ->  0.0626  (not selected)
```

So the Adult headline is partly a coincidence between the metric's chosen pair and the
mechanism's internal selection — not a claim about structure preservation. It generalises:
**any DP-synthesis benchmark scoring a marginal-based mechanism on a small fixed set of
low-order statistics risks measuring clique selection rather than fidelity.**

**We then tested the claim instead of leaving it as an inference from one pair**, recording
AIM's error and its clique selection for **every** numeric pair across the grid
(`scripts/run_clique_confound.py`). **The test weakened the claim, and the weakened version is
what we state.** It is *not* true that AIM beats the no-dependence baseline only on pairs it
selects — each dataset has a counterexample, which is mechanistically expected, since measuring
a clique constrains the joint and a graphical model propagates that constraint outside the
clique. What is true is a large **difference in degree** that itself does not transfer: AIM's
advantage is **11.9× larger on the selected pair on Adult, but only 2.3× on ACS**.

A secondary result, verified before being written down: on ACS, AIM's TSTR F1 **falls** with ε —
0.704 [0.695, 0.713] at ε = 0.5 down to 0.581 [0.539, 0.629] at ε = 8, CIs disjoint. Cause: the
DP profiler suppresses fewer rare categories at higher ε (OCCP 3 → 23 levels, RELP 3 → 14), so a
fixed clique allowance covers proportionally less domain and fewer cliques touch the target
column.

**Why this matters as research:** it was invisible from one dataset. It is the concrete argument
for why the second dataset was worth the compute, and it converts a weak "our mechanism ranks
best" claim into a **methodological contribution about benchmark design**.

### 7.3 Finding 3 — the instrument was penalising the mechanisms it measured

`run_cell` originally fitted **one** model on the canary-augmented split and used it for
everything. Canaries are extreme by construction, and enough of them move the joint
distribution:

```
corr(age, hours_per_week)    on the fit split        0.1014
                             + 60 canaries           [figure retracted 2026-09-06]
```

The generator trained on a table with almost no correlation, then got scored against one that
had it. Mechanisms that model dependence faithfully **reproduced the flattened structure and
were penalised for it**; the independent baseline, which reports no correlation either way, was
unaffected. **The better a mechanism was, the worse it scored.**

This produced **two separate published conclusions that were both wrong** — "H1 not supported",
and pairwise apparently getting *worse* with more budget — both reported in good faith. An
earlier partial fix (randomising canary direction) changed the **sign** of the bias but not its
size, which made it look solved.

Fixed by fitting twice: once on the augmented split for the audit, once on the clean split for
utility and structure. After the fix, pairwise correlation error at ε = 8 improved **58%**
(0.1098 → 0.0459) while independent was **unchanged** — the control working exactly as a control
should.

**The transferable lesson:** a measurement instrument that systematically penalises the thing it
is trying to detect produces a **confident null**, and nothing about that null looks wrong from
outside.

---

## 8. Limitations — say these before the panel finds them

Volunteering the risk list is the single most credible thing available at the end of a review,
and it removes the panel's best questions before they are asked.

| Limitation | Precise statement |
|---|---|
| **Not deployment-ready** | Single-table CSV only. **One shared API key**, so the ledger's `actor` cannot say *who* spent the budget, and rotation invalidates everyone at once. No cross-session budget enforcement. No multi-table support |
| **The audit half of H1 is disqualified** | By our own instrument's working range, not by a mechanism result |
| **One adversary** | Both auditors use the same nearest-neighbour similarity score. A stronger, mechanism-aware adversary would raise every audited number and could change the ordering |
| **LiRA is not implemented** | Deliberately. ~21 hours of compute for a likely wide-CI null, and naming something cheaper "LiRA" would be false |
| **`LeakyGenerator` is coarse** | Verbatim copying is the *easiest* leak to detect. Real mechanisms leak in subtler ways that may be harder or easier to see |
| **Two datasets, both US census-derived** | n = 6,000 each, single table, binary target. No healthcare, no time series |
| **δ handled by a union bound** | Conservative rather than exact. At δ = 1e-5 the correction is negligible, but it is not the paper's tighter treatment |
| **Detection floor measured at one n** | n = 3,000, 5 seeds. Enough to reject one-seed artefacts; not enough to estimate the false-positive rate precisely |
| **Verification is of the sheet, not the run** | A third party can verify the signature and the arithmetic. They cannot verify that we ran the pipeline we say we ran |
| **Thesis incomplete** | The binding constraint on the project is the write-up, not the code |

---

## 9. Questions a panel will ask, with answers

### On validity and framing

**1. Is this a real problem or a manufactured one?**
Documented, not argued. Sweeney showed three ordinary fields identify 87% of Americans;
Narayanan and Shmatikov de-anonymised Netflix subscribers from public film reviews; Stadler et
al. (USENIX Security 2022) showed the *fix* — synthetic data — provides neither the privacy nor
the utility claimed for it. The specific gap we work in is that a formal guarantee is a property
of a mechanism and nobody checks a given implementation has it.

**2. Isn't differential privacy already solved?**
The *theory* is mature. Two results show the theory is not the hard part: Mironov (2012)
demonstrated that naive floating-point Laplace sampling breaks the guarantee entirely with a
correct proof in place, and Canonne et al. (2020) showed that rounding a continuous Gaussian
does **not** give a discrete Gaussian, so a system that rounds is not running the mechanism its
proof describes. Our own code contributed a third example: a hand-rolled subsampling bound that
under-reported ε by roughly 2×.

**3. What is genuinely novel here, in one sentence?**
**Eight of our candidate claims are dead, and we killed them ourselves.** The adversarial
protocol in `research/` ran all eight query families and issued a verdict
(`research/08_novelty_verdict.md`). Occupied: dual-sided assurance (USENIX Sec 2024),
budget-charged domain profiling (2025), the ceiling corollary (Steinke's own theorem),
defect-finding by self-audit (12 libraries, 13 violations, Feb 2026), **shipping a structured
privacy label** (Dibia et al. 2025), **automated release gating** (Five Safes + SACRO, in UK
Trusted Research Environments since 2022), **machine-checkable release artefacts** (Croissant is
a NeurIPS submission requirement), and cross-release budget management (OSDI'21 onward).

**The position we can defend is integration, not invention**, and it rests on one paper.
Dibia, Lu, Bhattacharjee, Near & Feng (arXiv 2507.15997, 2025) elicited a nine-category DP
privacy label from experts. Its categories overlap our Privacy Data Sheet almost field for
field — including `unit_of_privacy` and empirical privacy metrics — which is validation, not
defeat: a panel of DP experts converged on what we built. **What they explicitly do not propose
is any signing mechanism, or any standard for reporting the limits of an empirical privacy
metric** — an omission one of their own experts called *"privacy theater"*, warning that
empirical numbers emphasise average-case performance without showing worst-case. That is
precisely the hazard we hit: our H1 reported ε_audited = 0.000 against a ceiling of 2.97.

So: the field has converged on *what* a DP release should disclose, and not on making those
disclosures **checkable**. We sign the claim, and we ship the audit ceiling beside the number it
qualifies. Both are narrow. Say them narrowly.

**4a. Isn't your refusal gate novel?**
No — say so before they do. Automated release gating is production practice under the Five Safes
framework, and SACRO has automated it since 2022. Two differences are real and visible in our
code: SACRO reads the actual output values and does **not** autonomously refuse (its own docs say
a "pass" is not a certification, and human checkers hold final authority); ours reads only the
declared schema and row count, and refuses. **We state that as unrefuted, not as novel** — the
primary SDC Handbook was unreachable and that literature predates arXiv, so our search is
genuinely incomplete there.

**4. Is this just a wrapper around existing libraries?**
Composition, the graphical-model inference and the AIM mechanism are existing work — deliberately,
per standing rule 1. What is ours: the pre-flight refusal gate, the charged-and-applied
discipline across the whole pipeline, the signed data sheet with the ceiling inside the signed
payload, the ledger head that makes truncation detectable, and the audit-ceiling analysis in §7.1.

**5. How do we know you did not fit the story to the data?**
Preregistration dated 2026-08-05, before the full grid, with an explicit commitment to report
all outcomes. Two of three hypotheses came back **not supported** and are published that way.
All five deviations are declared with their direction of effect, and two of them made the
write-up **harder**, not easier.

**6. Your main result is negative. Is that a finding?**
Yes, and it is a stronger one than the positive result we were aiming for. Reporting
"ε_proved = 7.36, ε_audited = 0" as a fact about a mechanism would have been **wrong** — the
instrument's ceiling at that canary count was 2.97, so it could not have reported otherwise even
against a release that was 100% training data. Discovering that a measurement cannot answer the
question, proving why, and reporting the limit alongside every future number is a result.

**7. Why not just raise the canary count?**
Because the cost is exponential in ε. Certifying ε = 7.36 needs about 4,711 canaries **every one
of which the adversary identifies correctly**; with a real adversary, far more. Going from 60 to
800 canaries lifts the one-run ceiling only from 2.97 to 5.59 — still below 7.36.

**8. Would a stronger attacker change your conclusions?**
It would change the *audited* numbers and could change the mechanism ordering — we state that as
an open threat. It would **not** change the ceiling, which depends on the canary count and α
alone. That separation is precisely why the ceiling is worth reporting.

**9. What would falsify your central claim?**
An auditing construction whose certifiable ε is not bounded by the guess count — for example one
that extracts a bound from a continuous score rather than binary guesses. We would want to know
about it, and it is the first thing we would look for in the extended survey (§3.10).

### On the literature

**10. How many papers, and how did you choose them?**
27 in the bibliography, across six threads, selected by a stated rule: cited if the project
implements it, delegates to it, adopts its methodological argument, or is positioned against it.
It is a targeted survey, not a systematic review, and we say so.

**11. What is the single most important paper for this project?**
Stadler, Oprisanu & Troncoso (2022). It is why the project exists: it shows synthetic data has
recreated the false confidence de-identification once offered. Everything we build is an attempt
to make the difference checkable rather than asserted.

**12. Which paper does your main finding extend?**
Steinke, Nasr & Jagielski (2023). We implement their one-run construction and then work out the
consequence of its confidence-interval structure for a benchmark at our scale — the exponential
canary cost of certifying a given ε.

**13. Why AIM and not a GAN or a diffusion model?**
Marginal-based methods won the NIST synthetic-data challenges (McKenna et al. 2021) and generally
outperform DP-GAN and PATE-GAN on tabular data. That is a scope decision citing the literature —
we have **not** benchmarked GANs ourselves and do not assert the comparison as our own finding.

**14. Why not k-anonymity?**
It is syntactic: it constrains the *shape* of the released table rather than bounding what any
adversary can learn, so its guarantee depends on assumptions about auxiliary knowledge. DP was
introduced because those assumptions fail. It is on our list to cite explicitly (§3.10).

**15. What is missing from your survey?**
Nine identified areas, listed in §3.10 with reasons — reconstruction attacks (Dinur & Nissim),
the syntactic-anonymity line, subsampled RDP, DP-SGD, real deployments, PrivBayes, DP
benchmarking work, and recent tight-auditing results. The last of these could sharpen or
challenge our §7.1, which is exactly why it is named.

**16. Has anyone done this before?**
The two halves exist separately, in different research communities: formal DP synthesis, and
empirical auditing. Transparency artefacts exist in a third. We found no system shipping both
bounds on one release with the measurement's own limit printed beside it. That is a
literature-search claim, not a proof of novelty, and we state it that way.

### On authenticity

**17. How do we know these numbers are real?**
Every result file records its seeds and carries bootstrapped CIs; `results/MANIFEST.json` pins
them to a commit hash, a Python version and exact dependency versions; UCI Adult is verified
against a committed SHA-256 on every load; `make reproduce` re-runs and compares; and both PDF
builders **refuse to build** if the prose disagrees with the committed JSON.

**18. Give an example of that check firing.**
It fired while writing the plain-language guide. The prose said "exactly zero on the negative
control"; the data showed 34 of 35, with one false positive at r = 100, ε = 0.070. **The prose
was corrected, not the check.**

**19. Did you find mistakes in your own work?**
Twelve, including fabricated metrics in four modules — an AUC computed as accuracy + 0.05, a
class named `AIMGenerator` running independent histograms, a profiler charging ε and publishing
`df.unique()`, and a console showing hardcoded PASS verdicts for an attack that did not exist.
All fixed. Six standing rules were adopted in response and are enforced in PR review.

**20. Isn't admitting that damaging?**
The alternative is worse. Two of the twelve were caught by **controls**, not by reading code, so
a project with no reported defects has either not audited or is not saying. What we can show is
the machinery that catches this class of error, and evidence it works.

**21. Were any published results affected by the bugs you found?**
The critical profiler leak: **no**, and we verified it rather than asserting it — the exploitable
band is profile_eps ≤ 0.01 and it is 0% at target ε ≥ 0.2, confirmed by re-running a committed
grid cell and getting all 11 metrics bit-identical. The canary contamination bug: **yes** — it
produced two wrong conclusions, both of which were retracted and corrected in place, with the
reason documented.

**22. How do you test a privacy guarantee?**
Four ways. Distributionally — the discrete Gaussian sampler is χ²-tested against the exact PMF.
Adversarially — 12 attacks against a live SQLite ledger by an adversary with file access but no
key. By calibration — a CI gate over 24 configurations checks proved ≤ target, always. And by
controls — every measurement has a positive and a negative control, and CI enforces them.

**23. Do you verify your regression tests actually catch anything?**
Yes, by **reintroducing the bug** and confirming the test fails. Reading a test is not evidence
it works; both of the defects in §5.3 sat behind confident comments claiming the opposite.

**24. Can a third party check a release without trusting you?**
They can check the data sheet: `synthproof verify sheet.json --pubkey org.pub` validates the
Ed25519 signature and the arithmetic, with nothing but the file and a public key. They **cannot**
verify that we ran the pipeline we claim — that would need attestation, and we do not claim it.

### On method and results

**25. Why ε from 0.5 to 8? Isn't 8 too weak?**
It is weak, and deliberately so: at ε = 8 an adversary who knows everything else guesses your
membership essentially every time. It is included as the *permissive* end so the curve spans the
range practitioners actually argue about. The US Census used values in a comparable range,
which is part of why the argument is live.

**26. Why δ = 1e-5?**
Because δ must be below 1/n, and n = 6,000 gives 1.7e-4. It is the standard requirement and it
is checked.

**27. Why only 6,000 rows?**
Compute. The full H1 grid is about four hours and it is resumable. n is held **identical across
both datasets**, so it is a constant rather than a confound for the cross-dataset comparison.

**28. Why 5 seeds?**
Preregistered, and sufficient to reject one-seed artefacts with bootstrapped CIs. It is **not**
enough to estimate a false-positive rate precisely — at 5 seeds, 1/5 and 0.05 are not
distinguishable, and we say so where it matters.

**29. Your TSTR numbers are much worse than real data. Isn't that a failure?**
The real baseline is 0.660 and the best synthetic is 0.540. We report the gap rather than hiding
it. That gap **is** the honest state of DP tabular synthesis at these ε values, and pretending
otherwise would be the Groundhog Day failure Stadler et al. document.

**30. Your independent baseline does not improve with ε at all. Is it broken?**
No — it is the control working. 0.0934 at ε = 0.5 and 0.0947 at ε = 8. A mechanism that models
no dependence cannot get better at reproducing dependence however much budget it gets. If it
*had* improved, the metric would be wrong.

**31. H2 found nothing. How is that different from not measuring?**
Three ways, and this is the difference between a null and a *bounded* null. We applied
multiplicity correction (0 of 14 survive BH-FDR or Bonferroni on Adult; 0 of 22 on ACS). We ran
**TOST equivalence tests**, and 2 of 14 are statistically equivalent to chance within a
pre-specified margin — a bound on the effect size. And we state detectability: the adversary
needed accuracy 0.600 and reached 0.562.

**32. Why equal canary allocation across subgroups instead of proportional?**
Because the audit ceiling falls with the guess count. Proportional allocation would give the
0.8% subgroup about 3 canaries and the 85.7% subgroup about 343 — **the rare groups H2 is about
would get the weakest instrument.** Equal allocation measures every subgroup at the same ceiling.

**33. Why did the two datasets disagree, and did you tune anything to fix it?**
Nothing was tuned. Per the analysis plan a contradicting result is diagnosed, not adjusted. The
diagnosis is §7.2: the metric measures one column pair, and AIM's score on it depends largely on
whether that pair is among its selected cliques. We then **tested** that inference over every
numeric pair, the test **weakened** the claim, and the weakened version is what we state.

**34. Could the model-size cap explain the ACS result?**
Ruled out first. `skipped_cliques_` is empty at both ε = 0.5 and ε = 8, with 17 cliques measured
at each.

**35. Why does AIM get *worse* with more budget on ACS?**
Verified, not hand-waved: the DP profiler suppresses fewer rare categories at higher ε (OCCP goes
3 → 23 levels, RELP 3 → 14), so a fixed clique allowance covers proportionally less of the domain
and fewer cliques touch the target column. TSTR F1 falls from 0.704 [0.695, 0.713] to
0.581 [0.539, 0.629], CIs disjoint.

**36. What is a canary, in one sentence?**
A deliberately extreme record we insert so we can ask afterwards whether the release reveals that
it was there — the audit's test subject.

**37. Doesn't inserting canaries change the data you are measuring?**
Yes, and that is finding 3. The size of the effect we originally reported did **not** replicate
and is retracted; report the shape instead — contamination scales with the canary FRACTION m/(n+m) and is significant only above ~3%; at m=60 on Adult (n=6,000) it is not significant (t=1.85). See `results/CANARY_DOSE_RESPONSE.md`.
The two-fit decision stands on its own regardless, and Mitchell et al. (arXiv:2606.10481 §3)
recommend it independently: we fit twice, once on the augmented split for the audit and once on
the clean split for utility and structure.

**38. What does ε_audited = 0 mean?**
That our adversary recovered nothing above the instrument's floor. It does **not** mean no
leakage, and this is why the ceiling is printed beside it: at m = 60 the instrument cannot detect
below roughly 25% verbatim copying, so a 0 is consistent with a perfectly private mechanism and
with a fairly leaky one.

### On engineering and scope

**39. What is the hardest engineering problem you solved?**
Making a requested ε mean what the operator typed. Before calibration, requesting ε = 8 produced
a release composing to **70.49** — every step sound, the interface deceiving. Calibration now
inverts the composition theorem by bisection; proved/target ≈ 0.92, never over, gated in CI
across 24 configurations.

**40. What does the pre-flight refusal gate do, and why is it interesting?**
It refuses inputs that cannot be released honestly — too few rows, a near-unique identifier
column, free text, no categorical target, a two-way domain blow-up — using **only the declared
schema and the row count, never the data**. A gate that read the data to decide would itself be
an uncharged query.

**Say the prior art before the panel does.** Automated release gating is production practice in
UK Trusted Research Environments under the **Five Safes** framework, where "Safe Outputs"
requires disclosure checking of everything leaving the environment, and **SACRO**
(arXiv 2212.02935) has automated it since 2022. Two differences are real and verifiable in our
code: SACRO **reads the actual output values** — cell frequencies against thresholds, the
p%-rule, the NK-rule, regression degrees of freedom — where our gate reads no cell at all; and
SACRO **does not autonomously refuse** (its own documentation states that a "pass" is not a
certification that an output is safe, and human checkers retain final authority) where ours
does. Whether a *data-blind* gate is genuinely unoccupied has **not** been established — the SDC
literature is large and poorly indexed, and our search made one pass. See
`research/PHASE2_COMPLETE.md` §6.

**41. Why is `domain_source` on the certificate?**
Because it records whether column domains came from a public schema (free, leaks nothing) or
were read from the data (a real leak that invalidates the headline ε). Published pipelines
routinely do the latter without mentioning it. It sits **inside the signed payload** so it cannot
be stripped.

**42. Why did the ledger need a signed head?**
Hash chaining detects modification, insertion and reordering but **not truncation** — a shortened
chain is internally consistent. Deleting the last two entries left `verify()` returning `True`,
so an operator could delete exactly the records of a budget overspend. The head commits to
`(entry_count, tip_hash)` and is signed. 9 attacks stopped, up from 8.

**43. Can the ledger stop someone who has the signing key?**
No, and we say so in the README rather than leaving it implied. Key custody is out of scope.

**44. Could a hospital use this tomorrow?**
No, and the limitations table says why: single-table CSV, one shared key so the ledger cannot say
*who* spent the budget, and no cross-session budget enforcement. It is an instrument for checking
releases, not a production pipeline.

**45. What would you do with six more months?**
Three things, in order. Replace the nearest-neighbour adversary with a proper shadow-model attack
so the audited numbers reflect a strong adversary rather than a convenient one. Test the
clique-selection finding on a third and fourth dataset, and on a second marginal-based mechanism
such as MST or PrivBayes, to establish whether it is a property of AIM or of the benchmark
design. And replace the shared key with real identity so the ledger can attribute spend.

---

## 10. What to hand the panel, and in what order

1. **This document** — the validity, literature and authenticity answers.
2. **`results/DETECTION_FLOOR.md` and `results/AUDITOR_COMPARISON.md`** — the two files behind
   finding 1. If a panel reads one thing beyond this pack, make it these.
3. **`docs/preregistration.md`** with its date, and **`ch06-methodology.md` §6.8** with the five
   declared deviations.
4. **`results/acs/CROSS_DATASET.md`** — the external-validity test, including the disagreement.
5. **`ARTIFACT.md`** — every claim mapped to the command that reproduces it.
6. **`docs/AUDIT_AND_ROADMAP.md`** — the twelve defects and the six standing rules.

**The line to close on:** *we did not get the result we planned. We got a better one, we can show
exactly why it is better, and every number in it traces to a committed experiment with a recorded
seed.*

---

### Measurement convention — the ceiling is borrowed, and attributed

The audit ceiling reported beside every ε_audited is `log(r / ln(1/α))`, a one-line corollary
of Steinke, Nasr & Jagielski (NeurIPS 2023, arXiv:2305.08846) Thm 2.1 — **not a result of
ours** — and the same quantity is already named *maximum auditable epsilon* by Annamalai,
Ganev & De Cristofaro (USENIX Sec 2024, arXiv:2405.10994) §2.2.

Reporting it alongside the measurement is a transfer of **limit-of-detection (LoD) reporting**
from analytical chemistry, where **MIQE 2.0** (Bustin et al., *Clinical Chemistry*
2025;71(6):634–651) mandates LoD/LLOQ disclosure and a laboratory reports *"Not Detected,
< LOD"* rather than zero. The transfer is the claim; the convention is not our invention.

Full attribution: [`docs/MEASUREMENT_CONVENTIONS.md`](../MEASUREMENT_CONVENTIONS.md).
