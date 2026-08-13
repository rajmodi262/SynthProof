# Chapter 2 — Literature Review

**Target: 2,500 words.** Depends on nothing. **Write this first.**

The job of this chapter is to establish that two mature research communities exist, that each
solves half the problem, and that nothing in the literature ships both halves attached to a
released artefact. That gap is the thesis.

---

## 2.1 Formal differential privacy (~700 words)

### Foundations
- **Dwork et al. (2006)**, *Calibrating Noise to Sensitivity in Private Data Analysis* — the
  (ε, δ) definition; Laplace mechanism; sensitivity.
- **Dwork & Roth (2014)**, *The Algorithmic Foundations of Differential Privacy* — the standard
  reference. Use for the Gaussian mechanism and basic/advanced composition.
- **Mironov (2017)**, *Rényi Differential Privacy* — RDP, and why it composes more tightly than
  advanced composition.
- **Mironov, Talwar & Zhang (2019)** — subsampled RDP. Cite when explaining why our first
  hand-rolled bound was invalid.
- **Balle et al. (2020)** — improved RDP→(ε,δ) conversion.
- **Canonne, Kamath & Steinke (2020)** — the discrete Gaussian, and why rounding a continuous
  Gaussian does not produce it.
- **Mironov (2012)**, *On Significance of the Least Significant Bits* — the floating-point
  attack that motivates discrete sampling at all.

### Point to make
Formal DP gives a **worst-case upper bound**. Released values of ε in deployed systems are
frequently large enough to be close to vacuous — the US Census 2020 redistricting data used
ε ≈ 19.61 in aggregate. An upper bound that permits e^19 relative change in output probability
is a guarantee in name.

### Writing note
Do not over-explain the definition. One paragraph of formalism, then move to what it fails to
deliver in practice. The reader is a supervisor, not a student of DP.

---

## 2.2 DP synthetic data generation (~600 words)

### Marginal-based
- **McKenna et al. (2021)**, *Winning the NIST Contest* — MST.
- **McKenna et al. (2022)**, *AIM: An Adaptive and Iterative Mechanism* — the state of the art
  for tabular DP synthesis. Adaptive marginal selection via the exponential mechanism, plus
  private-PGM inference.
- **McKenna, Sheldon & Miklau (2019)**, *Graphical-model based estimation and inference* —
  private-PGM itself.

### Deep generative
- **Xie et al. (2018)** DP-GAN; **Jordon et al. (2019)** PATE-GAN — cite briefly, then explain
  why marginal-based methods dominate on tabular benchmarks and why we follow that line.

### Critical literature
- **Stadler, Oprisanu & Troncoso (2022)**, *Synthetic Data — Anonymisation Groundhog Day* —
  **essential.** Shows synthetic data does not automatically provide privacy and that many
  claimed protections fail under linkage attacks. This paper is a large part of your motivation.
- **Ganev & De Cristofaro (2023)** — on the gap between claimed and actual protection.

### Point to make
Two things follow. First, "synthetic" is a statement about provenance, not about disclosure
risk. Second, the mechanisms that *do* carry a formal guarantee are exactly the ones whose
guarantee nobody independently checks.

---

## 2.3 Empirical privacy auditing (~700 words)

### Membership inference
- **Shokri et al. (2017)** — the original shadow-model MIA.
- **Carlini et al. (2022)**, *Membership Inference Attacks From First Principles* — LiRA, and
  the methodological argument that **average-case accuracy is the wrong metric**; report
  TPR at low FPR. Our attack reporting follows this.
- **van Breugel et al. (2023)**, *DOMIAS* — density-ratio MIA specifically for synthetic data.

### Auditing DP implementations
- **Jagielski, Ullman & Oprea (2020)**, *Auditing Differentially Private Machine Learning* —
  establishes ε_audited as an empirical lower bound and the proved-vs-audited gap as an object
  of study. **This is the closest ancestor of our H1.**
- **Nasr et al. (2021, 2023)** — tight auditing; adversary instantiations.
- **Steinke, Nasr & Jagielski (2023)**, *Privacy Auditing with One (1) Training Run* — the
  construction we implement. Randomised inclusion vector, guesses on a subset, Clopper-Pearson.
- **Tramèr et al. (2022)** — auditing via poisoning / canaries.

### Risk frameworks
- **Giomi et al. (2023)**, *Anonymeter* — singling-out, linkability, inference as three
  separate, measurable risks.

### Point to make
Auditing gives a **lower bound from an actual adversary**. But an audit is a statement about
the attacks you ran, produces no budget, does not compose across releases, and lives in a paper
rather than attached to the released data.

---

## 2.4 Privacy accounting and budget management (~300 words)

- **Google `dp_accounting`** — the reference implementation (RDP and PLD accountants). State
  explicitly that we delegate composition to it rather than re-deriving theory, and cite the
  audit finding that motivated the switch: our hand-rolled subsampled-RDP bound under-reported
  ε by roughly a factor of two at q = 0.01.
- **Opacus / TensorFlow Privacy** accountants — for comparison.
- **Lécuyer et al. (2019)**, *Sage* — DP budget management as a systems problem across many
  queries and releases. Closest prior work to our ledger.
- **Kotsogiannis et al. (2019)**, *PrivateSQL* — budget allocation across a workload.

### Point to make
Composition is a theorem about a *sequence* of mechanisms. It only protects an organisation if
something durably records that sequence. Almost nothing in the literature addresses the
cross-release accounting problem, and no system we are aware of makes that record
tamper-evident.

---

## 2.5 Transparency artefacts (~200 words)

- **Gebru et al. (2021)**, *Datasheets for Datasets* — direct ancestor of the Privacy Data Sheet.
- **Mitchell et al. (2019)**, *Model Cards* — same lineage.
- **Bender & Friedman (2018)**, *Data Statements* — NLP variant.
- **EU AI Act (2024)** and **India's DPDP Act (2023)** — regulatory pressure making
  training-data provenance a compliance artefact rather than good practice.

### Point to make
Datasheets record *what a dataset is*. None of them record *what it discloses*, and none are
machine-verifiable. A signed Privacy Data Sheet is a datasheet whose central claim can be
checked by a third party.

---

## 2.6 The gap (~200 words)

The synthesis paragraph. Something close to:

> Formal DP supplies an upper bound that nobody verifies against the implementation.
> Empirical auditing supplies a lower bound that carries no guarantee, accumulates no budget,
> and is not attached to the artefact it describes. Datasheets describe datasets but say
> nothing about disclosure. **No existing system releases a dataset accompanied by both
> bounds, cryptographically bound to a durable record of the organisation's cumulative privacy
> expenditure.** SynthProof is an attempt to build exactly that, and to measure — across real
> mechanisms and real data — how far apart the two bounds actually are.

---

## Table to include

| Approach | Upper bound | Lower bound | Composes | Cross-release | Attached to artefact | Verifiable |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| Formal DP (AIM, MST) | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| Empirical auditing (LiRA, Steinke) | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Anonymeter risk assessment | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Datasheets / Model Cards | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| **SynthProof** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (M3) |

Mark the SynthProof row honestly against what is actually built at submission time. If the
signature is not implemented, that cell is not a tick.

---

## Sources to obtain

Search terms that surface most of the above: `differential privacy synthetic data survey 2024`,
`privacy auditing one training run`, `AIM adaptive iterative mechanism marginals`,
`membership inference first principles`, `anonymisation groundhog day`.

Prefer the arXiv version for page-stable citation. Keep a BibTeX file at
`docs/thesis/references.bib` from the first day — retrofitting citations is miserable.
