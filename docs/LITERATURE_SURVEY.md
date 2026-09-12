# SynthProof — Deep Literature Survey and Positioning

> **Compiled 22 August 2026.** Every source below was retrieved and read during compilation;
> venue and date are stated for each. This document exists to answer four questions a panel
> asks: *is the problem real, has it been solved already, what exactly is new here, and who
> cares.* It supersedes the "Sources to obtain" note at the end of
> `docs/thesis/ch02-literature-review.md` and should be folded into Ch.2 before submission.
>
> **Read §0 first.** It contains three findings that change how the project's own results must
> be described, including one place where the current wording is too strong and a sharp
> examiner would break it.

---

## 0. What the survey changed about our own claims

### 0.1 The audit-ceiling claim needs one qualifier — and is stronger with it

`results/AUDITOR_COMPARISON.md` currently says:

> "No canary audit at any scale this project can run will certify an ε near its proved bound.
> Switching to the one-run construction does not change that, and neither would a better
> adversary."

That is correct **for auditors that reduce evidence to binary membership guesses**, which is
what Steinke et al. (2023) and our implementation both do. It is not correct as a statement
about auditing in general, and the 2024–2026 literature is precisely the record of people
escaping it:

| Escape route | Paper | What it does |
|---|---|---|
| Audit the whole *f*-DP curve, not one ε | Mahloujifar, Melis & Chaudhuri, **ICML 2025** (arXiv:2410.22235) | Bounds the probability of *exactly i* correct guesses by a recursive relation rather than thresholding, and reports the full trade-off curve. Explicitly outperforms Steinke et al. |
| Keep the canary scores continuous | Agrawal, Wei, Singh, Magdon-Ismail & Zikas, **June 2026** (arXiv:2606.12733) | States the problem in our exact terms: prior one-run methods "threshold training examples or canaries into binary membership guesses, which discards useful information." Models the normalised score sum as asymptotically Gaussian. |
| Sequential / anytime-valid testing | González, Rubio, Ramdas & Ribero, **2025** (arXiv:2509.07055) | e-values + MMD. Cuts detection sample sizes "from 50K to a few hundred." |
| Gaussian-DP tradeoff auditing of AIM specifically | Ganev, Annamalai & Kulynych, **April 2026** (arXiv:2604.18352) | First tight audit of MST and AIM. At (ε,δ)=(1,10⁻²) reaches empirical μ≈0.43 against implied μ=0.45. |

**The corrected claim, which is both defensible and more interesting:**

> The ceiling ε_max(r) ≈ log(r / ln(1/α)) is a property of the *estimator class* that converts
> canary evidence into binary membership guesses — the class that includes Steinke et al.
> (2023) and both of our auditors. Within that class the requirement is ln(1/α)·e^ε canaries,
> exponential in ε, and no adversary strength changes it. Escaping the ceiling requires
> leaving that estimator class, and the three 2025–2026 constructions that do so are the
> field's current frontier. Our measurement establishes where the boundary of the tractable
> class lies; it does not claim auditing is impossible.

Make this change in `AUDITOR_COMPARISON.md`, `DETECTION_FLOOR.md` and `steinke.py`'s docstring.
It costs one paragraph and removes the only claim in the repository that an expert could
falsify with a citation.

Note also the honest limit on the escapes: the sequential paper reports that even its method
degrades above ε≈0.6 because the test statistic and its threshold both approach their maxima.
So the *shape* of our finding — that certifying large ε empirically is qualitatively harder
than certifying small ε — survives all four papers.

### 0.2 Our contribution #1 (charged domain profiling) has been independently published — and we converged on the same answer

This is the most important novelty finding in the survey, and it is good news framed correctly.

**Annamalai, Ganev et al., "Understanding the Impact of Data Domain Extraction on Synthetic
Data Privacy," arXiv:2504.08254, April 2025.** They state the problem in almost our words:

> "Extracting the data domain directly from the input data, which is the common practice,
> breaks the end-to-end DP guarantees of generative models."

Their experiment: place a target record outside the domain of the rest of the data, train 200
shadow models with and without it, run the GroundHog MIA. Result: with un-noised domain
extraction the attack reaches **near-perfect accuracy at every privacy budget**; with a public
domain or a DP-extracted domain, **"the attack success rate is no better than random guessing"**
even at ε=100 for discretisation.

Their recommended hierarchy:

1. **Preferred** — a trusted, externally provided domain (public codebook), costing no budget.
2. **Acceptable** — DP extraction, spending part of the budget.
3. **Avoid** — the common practice of reading it from the sensitive data.

**That is exactly the hierarchy `synthproof/data/profiler.py` implements**, arrived at
independently, and the docstring says so in its own words: *"Numeric ranges come from the
schema's PUBLIC bounds and cost no budget, because a public fact reveals nothing. Only a
column with no declared range falls back to a noisy min/max."*

Corroborated a second time by **Cebere, Erb, Desfontaines, Bellet & Fitzsimons, "Privacy in
Theory, Bugs in Practice: Differential Privacy Library Auditing," PoPETs** (arXiv:2602.17454).
They audited **12 open-source DP libraries and found 13 privacy violations**, and *domain
inference* is one of their named bug classes. In `dpmm` — a 2025 reference library for DP
marginal models — they found AIM and PrivBayes deriving the domain as
`_domain = (df.astype(int).max(axis=0) + 1).to_dict()` "without accounting for it." Their
recommendation is our design:

> "A robust DP implementation should treat the domain as public (provided by the user or a
> safe default), or estimate it through an explicit differentially private primitive."

**How to write this in the thesis.** Do not claim novelty for the idea. Claim three things
that remain ours and are not in either paper:

- **Integration.** Both papers treat domain extraction as a preprocessing question studied in
  isolation. Ours is charged to the *same* accountant as synthesis, inside one `BudgetPlan`,
  so the pipeline's total ε is the number the operator asked for. Neither paper builds that.
- **The refusal path.** `schema_declared=False` makes an unsatisfiable budget *raise* rather
  than fall back to a non-private release — a defect we found ourselves, where a stricter
  suppression threshold made the fallback fire more often and so made the leak *larger*.
  Neither paper reports this failure mode.
- **The downstream consequence,** which is §0.3 and is genuinely new.

Independent convergence with the leading group in the field, arrived at from our own audit,
is a *good* thing to be able to say in a viva. It is evidence the reasoning was sound.

### 0.3 Our ACS finding is a new variant of a known effect — and the variant is the contribution

**Ganev, Annamalai, Mahiou & De Cristofaro, "The Importance of Being Discrete: Measuring the
Impact of Discretization in End-to-End Differentially Private Synthetic Data,"
arXiv:2504.06923, April 2025.** They find:

> Utility "follows an inverted u-shaped trend as the number of bins increases: it initially
> improves but then degrades when too many bins introduce too much noise."

and, on AIM specifically, that it "becomes faster with more bins, possibly because it exhausts
its budget more quickly."

That is the same physics as our ACS diagnosis. **But their inverted-U is in the number of bins,
a hyperparameter the practitioner sets. Ours is in ε itself.** Because our DP domain profiler's
suppression threshold loosens as budget grows, the *effective domain size is a function of the
privacy budget* — `OCCP` goes from 3 categories at ε=0.5 to 23 at ε=8 — so AIM's roughly fixed
clique budget is spread over a domain an order of magnitude larger, and downstream utility
**falls** from 0.704 to 0.581 as ε rises 16×, with non-overlapping endpoint CIs.

The claim to make, precisely:

> In an end-to-end DP pipeline where the domain is itself discovered under DP, increasing the
> privacy budget can *reduce* utility, because the budget increase enlarges the domain faster
> than it improves the measurements taken over it. The inverted-U that Ganev et al. (2025)
> report in the number of bins therefore appears endogenously along the ε axis, where a
> practitioner is least likely to look for it.

Supporting precedent that non-monotonicity in DP graphical models is real and documented:
**Ganev, Xu & De Cristofaro, ACM CCS 2024** (arXiv:2305.10994) report that "more data can hurt
performance" — MST's mutual-information similarity *degrades* past n≈8k — and that very loose
budgets can help through a regularisation effect. Cite it so the finding reads as "a new
instance of a known class" rather than "an anomaly we could not explain."

That paper is also the right citation for our `DEFAULT_SELECTION_FRAC = 0.25`: it documents
that PrivBayes splits roughly 50/50 between structure selection and measurement and MST splits
1/3 to 2/3. Ours is a third data point on the same axis.

### 0.4 H2 is the explicitly declared future work of a paper by the leading group

**Ganev, Oprisanu & De Cristofaro, "Robin Hood and Matthew Effects: Differential Privacy Has
Disparate Impact on Synthetic Data"** (arXiv:2109.11429; ICML-workshop lineage). They show
underrepresented subgroups "suffer bigger and/or more variable drops" in accuracy under DP
synthesis. Critically for us, they measure **utility and fairness only** and state that they
do not consider privacy-specific analysis, leaving it to future work.

**H2 — "under uniform budget allocation, empirical audited privacy loss is significantly higher
for minority subgroups" — is that future work, stated as a preregistered hypothesis.** That is
the single strongest sentence available for justifying H2 to a panel, and it is currently
nowhere in the repository.

Our answer is a *bounded* null on two datasets, and the bound is the useful part: at the canary
counts a single data holder can afford, the per-subgroup instrument ceiling (3.27 on Adult
race, 2.65 on ACS `RAC1P`) is the binding constraint, not the mechanism. Combined with §0.1,
this becomes a methodological result with a clear addressee: *anyone attempting the disparate-
privacy question with a Steinke-class auditor needs to budget canaries per subgroup, and the
requirement is exponential in the ε they hope to resolve.*

Fresh work confirms the area is live: **Angelozzi & Arcolezi, arXiv:2607.07471, July 2026** —
one month old — benchmarks fairness interventions on DP synthetic tabular data using AIM and
MST on Adult, COMPAS and **ACSIncome**, the same two datasets we use, and reports that
intervention rankings shift across metrics and datasets. **"Disparate Impact in Synthetic Data
Generation," arXiv:2606.13105, June 2026**, is a second recent entry.

### 0.5 Our clique-selection confound has a published precedent it explains

On UCI Adult, `results/clique_confound.json` records:

| | correlation error, mean [95% CI] | n |
|---|---|---:|
| AIM on the pair it selected as a clique | **0.0263 [0.0161, 0.0382]** | 25 |
| independent baseline on that same pair | 0.1115 [0.1086, 0.1142] | 25 |
| AIM on pairs it did *not* select | 0.0592 [0.0552, 0.0631] | 125 |
| independent baseline on those pairs | 0.0609 [0.0570, 0.0645] | 125 |

On unselected pairs those two intervals overlap almost entirely. The H1 headline metric was
`age × hours_per_week` — the one pair AIM selected.

**Use the weakened claim from Ch.6 §6.9, not the JSON's blunt `confound_confirmed`.** Running
the same study on ACS showed the strong form is false: each dataset has one unselected pair
where AIM still wins, which is mechanistically expected, since measuring a clique constrains
the joint and a graphical model propagates that constraint outside it. What survives is a
large difference *in degree* that itself does not transfer:

| | largest advantage on a selected pair | largest on an unselected pair | ratio |
|---|---:|---:|---:|
| Adult | +0.0852 | +0.0072 | **11.9×** |
| ACS | +0.0285 | +0.0123 | 2.3× |

The self-correction is worth narrating in the viva: the first version of this study confirmed
a strong confound, the second dataset falsified the strong form, and the thesis states the
weakened version. That is the standing rules working on the project's own most attractive
result.

This is not merely a flaw we caught in our own work. It is the controlled experiment that
explains an anomaly already in the literature. **Rosenblatt et al., "Epistemic Parity:
Reproducibility as an Evaluation Metric for Differential Privacy," PVLDB 16 (2023)**, later a
SIGMOD Record reprint and a **CACM Research Highlight (2025)**, reproduced 105 findings from 8
peer-reviewed social-science papers on DP synthetic data and reported that **PrivBayes
unexpectedly beat MST, "contrary to findings in randomized query workload studies."** Their
explanation is conjectural and is the same shape as ours: the findings "rely on conditional
relationships that PrivBayes explicitly models."

**Our clique-confound study is the isolated, controlled version of that conjecture**, run on a
workload-adaptive mechanism where "what the mechanism models" is observable per run
(`measured_cliques_`). Framed that way it stops being an embarrassment and becomes the
project's cleanest methodological contribution:

> A workload-adaptive DP synthesiser must not be benchmarked on a statistic it was free to
> choose whether to model. Its apparent advantage is conditional on selection, and the
> conditioning is measurable. Report results split by selection state, or the comparison
> measures the selector rather than the mechanism.

Note that **Du & Li, arXiv:2504.14061 (2025)**, benchmarking 8 DP synthesisers on 5 datasets,
uses "predefined 3-way marginals for query error uniformly across all methods, without
analysing workload-specificity." The gap is open and current.

### 0.6 The three findings are one causal chain — present them that way

They are currently three separate documents. They are one story, and the story is what makes
the project look like research rather than a pile of experiments:

1. **The clique confound** says AIM's structural advantage exists only on pairs it selects.
2. **The ACS non-transfer** is exactly what (1) predicts: on ACS, AIM did *not* select
   `AGEP × WKHP` at ε ∈ {0.5, 2, 4, 8} — and at ε = 1.0, the one budget where it *did* select
   it, AIM records its best ACS correlation error (0.0395). The ranking flip is not a mystery;
   it is (1) observed on a second dataset.
3. **The domain-inflation effect** explains *why* it stopped selecting: the DP profiler
   unsuppresses categories as ε grows, the domain inflates, and the fixed clique budget no
   longer reaches the pair being measured.

So: **a DP preprocessing step, priced correctly, changes which marginals an adaptive mechanism
can afford to model, which changes which statistics it is good at, which inverts its ranking
against a baseline — and none of that is visible unless you run two datasets and condition on
selection.** That is a complete, falsifiable, single-sentence research finding derived from
this project's own experiments, and it is defensible in front of any panel.


### 0.7 The framing that makes the whole project coherent: DPBench

**Hay, Machanavajjhala, Miklau, Chen & Zhang, "Principled Evaluation of Differentially Private
Algorithms using DPBench," SIGMOD 2016.** From the Miklau group &mdash; the same lab that wrote
private-PGM and AIM. It sets out **ten principles** for evaluating a DP algorithm honestly.
They map onto this project almost one-to-one, and nobody has audited modern DP synthesisers
against them.

| # | DPBench principle | SynthProof |
|---:|---|---|
| 1 | **&epsilon; diversity** | 5 values, 0.5&ndash;8 |
| 2 | Scale diversity | Partial &mdash; n = 3,000 and 6,000 |
| 3 | **Shape diversity** | Two datasets, protocol held identical |
| 4 | **Domain-size diversity** | The ACS finding *is* a domain-size result &mdash; and ours varies with &epsilon;, a case DPBench does not anticipate |
| 5 | **Private pre- and post-processing** &mdash; "account for all computations on the input dataset" | The charged domain profiler. **Our contribution #1, stated as a principle in 2016** |
| 6 | **No free parameters** &mdash; "a data-independent or differentially private method for setting each required parameter" | Public schema, calibrated noise, schema-only preflight |
| 7 | Knowledge of side information used consistently | Public bounds and the ACS code-book coarsening, applied to every mechanism |
| 8 | **Measurement of variability** | Bootstrapped 95% CIs over 5 seeds, everywhere |
| 9 | Measurement of bias | Partial &mdash; the independent baseline's flatness is a bias check |
| 10 | **Reasonable privacy and utility** | The &epsilon; &ge; 4 separation threshold |

And the sentence that predicts our headline result nine years early:

> "a data dependent algorithm may have lower error than another&hellip; on one dataset, but the
> reverse may be true on another dataset."

**Use this as the thesis's methodological spine.** It reframes everything:

> SynthProof is a faithful implementation of DPBench's ten evaluation principles applied to a
> modern workload-adaptive DP synthesiser and to the auditing pipeline around it. The three
> findings are what those principles predict you find when you actually follow them &mdash; and
> the reason they are not already in the literature is that current DP-synthesis benchmarks do
> not follow principles 4, 5 and 6.

That claim is checkable against the benchmarks: Du & Li (2025) uses one fixed 3-way marginal
workload across all methods; the 2025 domain-extraction and discretisation papers exist
precisely *because* principle 5 is routinely violated; and the PoPETs library audit found
principle-5 violations (domain inference) shipping in production libraries in 2026.

**It also disarms the "you just wrapped libraries" objection completely.** The answer becomes:
*we implemented a 2016 SIGMOD evaluation standard that the field's own benchmarks still do not
meet, and doing so surfaced three results.*

### 0.8 Currency check: AIM is no longer unqualified SOTA

**Tran, Backurs, Lin, Reis, Yekhanin & Xiong, "Differentially Private Synthetic Data via APIs 4:
Tabular Data" (Tab-PE), ICML 2026** (arXiv:2606.08259; Emory + Microsoft Research). Beats AIM by
**up to 10% classification accuracy while running 28&times; faster** &mdash; but only on data with
genuine high-order correlations. They still call AIM "the strongest marginal-based baseline,"
and they report that **the standard benchmarks are "dominated by low-order dependencies,"** where
marginal methods remain effective.

Two consequences:

1. **Qualify the SOTA claim.** Say "the strongest marginal-based mechanism" rather than "the
   state of the art," and cite Tab-PE for the qualification. Currency costs one clause.
2. **Tab-PE independently corroborates our clique finding from the other side.** Their point is
   that Adult/Bank/Census reward mechanisms tuned to low-order dependencies; ours is that a
   single 2-way correlation on Adult rewards precisely the clique AIM chose. Same critique of
   the same benchmark culture, reached by two different routes in the same year.

### 0.9 Two more comparables Ch.2 does not cite and must

**TAPAS: a Toolbox for Adversarial Privacy Auditing of Synthetic Data** (Houssiau, Jordon,
Elliott, Geddes et al.; Alan Turing Institute, ONS, Oxford, Glasgow, Edinburgh;
arXiv:2211.06550, NeurIPS 2022 SyntheticData4ML). **This is the closest existing system to
SynthProof's audit half and its absence from the bibliography is the most conspicuous gap in
Ch.2.** It provides a general threat-model framework and a library of attacks. What it does
*not* provide, per the paper itself: **no &epsilon; lower bound and no privacy accounting** &mdash;
it stops at attack success rates. That is a clean, honest differentiation and it should be a row
in the positioning table.

**Cohen & Nissim, "Towards Formalizing the GDPR's Notion of Singling Out," PNAS 2020**
(arXiv:1904.06009). The formal definition of *predicate singling out* that underpins the
Anonymeter triad and now the EDPB's first technical criterion. Our exact-match singling-out
attack is a weak instance of it; saying so, with the citation, is better than leaving the
attack undefined.

Two smaller ones worth adding:

- **Papernot & Steinke, "Hyperparameter Tuning with R&eacute;nyi Differential Privacy," ICLR 2022
  (Oral)** (arXiv:2110.03620). The canonical result that *choosing* anything from the data costs
  budget. It is the theoretical justification for the schema-only preflight and for charging
  AIM's clique selection.
- **RFC 6962, Certificate Transparency.** Our signed head over `(entry_count, tip_hash)` is
  structurally CT's Signed Tree Head over `(tree_size, root_hash)`, arrived at independently
  after we found the truncation attack. Citing RFC 6962 turns "we added a signed head" into "we
  rediscovered the standard defence for exactly this attack," which is a much better sentence.
  It also names the honest gap: CT gets its strength from *public, gossiped* logs and
  consistency proofs; a single-holder SQLite chain does not, so a key holder can still rewrite
  history. Say that.

### 0.10 One unoccupied design idea worth claiming

`synthproof/data/preflight.py` refuses inputs that cannot be released honestly &mdash; and
**every check reads only the declared schema and the row count. Nothing in the module touches a
cell.** The docstring states the constraint that forces this:

> "A check that reads the data to decide whether the data is safe is the defect it is meant to
> prevent: counting distinct values in a column is a query against sensitive records, and its
> answer &mdash; *column 7 looks like an identifier* &mdash; is exactly the kind of statement DP
> exists to bound."

Targeted searching found no paper stating this as a design principle. It follows directly from
Papernot & Steinke and from DPBench principle 5, but as a *deployed precondition layer* with
named refusal codes it appears to be unoccupied. It is a small contribution, not a headline
&mdash; but it is a real one and it is currently invisible outside the source file. Give it a
subsection in Ch.4 and a paragraph in Ch.8.


### 0.11 The impact case, finally quantified — and a dated disconnect between two literatures

This is the strongest single result of the whole survey, and it belongs at the top of
Chapter 1.

**Kaabachi et al., "A scoping review of privacy and utility metrics in medical synthetic
data," *npj Digital Medicine*, 2025.** Seventy-three studies of medical synthetic data,
published 2018 to July 2024:

- **Only 11% (8 of 73)** used a differentially private generator.
- Of works naming privacy as their *purpose*, only **46% (31 of 67)** performed any privacy
  evaluation whatsoever.
- Their conclusion, in their words: *"most works that use synthetic data for preserving privacy
  do not evaluate residual privacy risks"* and *"many evaluations may offer a false sense of
  security."*
- **No consensus** on a standardised evaluation approach.

Now put that beside what happened in security research **in the same year**:

- **IEEE S&P 2025** — ReconSyn recovers **78–100% of training-set outliers with perfect
  precision** using only the fitted model and its *published privacy metrics*.
- **ESORICS 2025** — Yao, Krčo, Ganev & de Montjoye, *The DCR Delusion*. Membership inference
  performs **equally well against datasets that pass and fail DCR tests**; records reach
  **AUC > 0.8** despite passing; 10% TPR at **0% FPR** on diffusion models. They recommend
  moving to MIAs *"as the rigorous, comprehensive standard"* for legal anonymity claims.

And then the disconnect, dated to the month: a **December 2025 *npj Digital Medicine*** paper
(Marino, Cassidy, Nanni et al.) on clinical synthetic data states that *"DP has not been
adopted in practice, and existing applications are limited to specialized use cases"*, and
evaluates its release with a similarity-style *"privacy protection (0.83)"* score — the exact
class of metric the two papers above broke that year.

> **Write this as the opening of Chapter 1.** It is not a hypothetical audience. It is a
> documented, dated disagreement between the medical-informatics literature and the security
> literature, and nobody has shipped the artefact that would settle it for a given release.
> SynthProof's signed data sheet — ε_proved, ε_audited, *and the instrument's working range* —
> is a concrete proposal for that artefact.

Supporting regulatory evidence, all 2025–26:

- **Pilgram, Ko, Tung & El Emam, *npj Digital Medicine* 2025** — UK, Singapore and South Korea
  all require "very low" residual disclosure risk and all concede *"precise criteria were
  lacking."*
- **Wang, Myles, Foraker, El Emam et al., *npj Digital Medicine*, December 2025** — *"limited
  guidance from privacy regulators"*; synthetic data *"may still be regarded as personal data"*
  depending on the generation method and the identifiability of the output; calls for
  *"consensus standards and country-specific guidance."*
- **Sood et al., *npj Digital Medicine* 2025**, on Indian medical research under the DPDP Act —
  identifies unresolved ambiguity across clinical sharing, research reuse and AI processing,
  and **does not discuss synthetic data or differential privacy at all.** For an MIT-WPU
  submission this is the domestic motivation paragraph, and it is currently missing.
- **Zuo, Kang, Patterson & Seneviratne, WWW 2026** — six financial datasets; DP-TVAE mode
  collapse drops minority-class representation to **0.00–3.09%** from 11.6–23.9%. The financial
  half of the audience, and a second instance of DP harming minority subgroups.

### 0.12 A calibration number for the audit results

**MIDST Challenge, IEEE SaTML 2025** (Shafieinejad et al., Vector Institute) — a community
competition on membership inference over diffusion-generated synthetic tabular data. Winning
results:

| Track | TPR at 10% FPR |
|---|---:|
| white-box, single-table | 46% |
| white-box, multi-table | 35% |
| black-box, single-table | **25%** |
| black-box, multi-table | 23% |

**These are against *non-DP* generators.** Our attacks recover essentially nothing against DP
mechanisms, which is the ordering one should expect and is worth stating explicitly rather than
leaving as an unexplained zero. Their conclusion is also ours: there is an *"urgent need for
better assessments and audits of the privacy risks in the **life cycle** of synthetic tabular
data"* — "life cycle" being exactly the ledger-plus-datasheet framing.

### 0.13 A deadline that is five weeks away

**IEEE SaTML 2027 — paper submission deadline 29 September 2026**, conference early May 2027.
Accepts research papers, **systematization-of-knowledge papers**, and **position papers**;
"privacy in machine learning" is in scope. SaTML hosted the MIDST challenge, so the programme
committee is demonstrably interested in exactly this question.

Finding 1 (the clique-selection confound) is the most submission-ready: one controlled
experiment, committed numbers, a clear addressee in the benchmarking community. An SoK or
position paper on *"DP-synthesis benchmarks do not satisfy DPBench"* is the alternative shape,
and it is arguably a better fit for a first submission.

Other dated options: **TPDP** (~February, 4pp, non-archival); **SynthAI @ SIGMOD** (workshop on
synthetic data generation and management, co-organised from IIT Delhi); **SynthData @ ICLR**
(6pp or a 3pp "tiny paper"); **PETS/PoPETs** (rolling, with artifact evaluation).


---

## 1. Formal differential privacy

Foundations are unchanged from Ch.2 §2.1 and adequately cited there: Dwork et al. (2006);
Dwork & Roth (2014); Mironov (2017) for RDP; Balle et al. (2020) for conversion; Mironov (2012)
for the floating-point attack; Canonne, Kamath & Steinke (2020) for exact discrete samplers.

**Add: NIST SP 800-226, "Guidelines for Evaluating Differential Privacy Guarantees," finalised
6 March 2025.** A US federal publication whose stated purpose is to help practitioners
"understand how to evaluate promises made (and not made) when deploying differential privacy,"
with accompanying Python notebooks. This is the single best citation for the sentence *"the
question of whether a deployed DP guarantee means what it claims is now a standards question,
not only a research one."* Ch.1 §1.1 should cite it in the motivation.

**Add: Dwork, Kohli & Mulligan, "Differential Privacy in Practice: Expose Your Epsilons!",
Journal of Privacy and Confidentiality 9(2), 2019.** The canonical argument that ε values and
deployment parameters should be public. It is the intellectual ancestor of our signed data
sheet and its absence from `references.bib` is conspicuous.

---

## 2. DP synthetic tabular data

Ch.2 §2.2 is sound on AIM (McKenna et al., VLDB 2022), private-PGM (McKenna, Sheldon & Miklau,
2019), the NIST challenges, and DP-GAN / PATE-GAN. Four additions materially strengthen it.

**Cormode, Maddock, Ullah & Gade, "Synthetic Tabular Data: Methods, Attacks and Defenses,"
KDD 2025.** A tutorial-survey at a top venue, published this year. Gives the canonical
taxonomy — marginal-based (PrivBayes → the select-measure-generate paradigm → AIM, RAP/RAP++)
versus deep (CTGAN, TVAE, TabDDPM, TabSyn, GReaT/SynLM) — and names as an open problem that
"SOTA approaches based on diffusion models and LLMs have not been systematically compared to
marginal-based methods." **This is the citation that retroactively justifies dropping tabular
diffusion**: a KDD 2025 survey says the comparison is unsettled and hard, which is a better
reason than "the 4 GB RTX 3050 ran out of VRAM." Use both, in that order.

**Du & Li, "Benchmarking Differentially Private Tabular Data Synthesis," arXiv:2504.14061
(2025).** 8 algorithms, 5 datasets, 37k–135k records, 10–42 attributes. Two findings we need:
AIM and PrivMRF consistently lead on ML efficacy but **"no single algorithm dominates"**, and
AIM's runtime spans **5.8 to 689.6 minutes** depending on preprocessing. The first supports our
cross-dataset non-transfer as normal rather than anomalous; the second is the citation for why
our 75-cell grid takes ~4 hours.

**Ganev et al., "dpmm: Differentially Private Marginal Models," arXiv:2506.00322 (2025).** A
2025 reference library for MST/AIM/PrivBayes. Relevant twice: it is the natural comparison
point for our generator suite, and it is one of the libraries in which the PoPETs audit found
domain-inference bugs (§0.2).

**Angelozzi & Arcolezi, arXiv:2607.07471 (July 2026)** describes AIM as "state-of-the-art
marginal-based DP synthesizer" citing KDD and VLDB 2025 tutorials. Use it whenever the thesis
asserts AIM is SOTA — it is a one-month-old third-party attestation.

The critical literature in Ch.2 §2.2 (Stadler, Oprisanu & Troncoso, "Synthetic Data —
Anonymisation Groundhog Day," USENIX Security 2022) remains correctly the motivating citation.

---

## 3. Empirical privacy auditing

This is the section that most needs rewriting, because it currently stops in 2023 and the field
moved substantially in 2024–2026.

**Foundations (keep):** Shokri et al. (2017) shadow models; Carlini et al. (2022) LiRA and the
argument for TPR at low FPR; van Breugel et al. (2023) DOMIAS; Jagielski, Ullman & Oprea (2020)
for the audit framing; Nasr et al. (2021, 2023); Steinke, Nasr & Jagielski (2023) one-run,
a NeurIPS 2023 Outstanding Paper; Giomi et al. (2023) Anonymeter's singling-out / linkability /
inference triad.

**Add — the tightness frontier:**

| Paper | Venue / date | Why it matters here |
|---|---|---|
| Annamalai & De Cristofaro, "Nearly Tight Black-Box Auditing of DP Machine Learning" (arXiv:2405.14106) | **NeurIPS 2024** | At theoretical ε=10 reaches ε_emp = 7.21 (MNIST 1k), 6.95 (CIFAR-10 1k), **4.96 (full CIFAR-10)**. Prior work managed 3.41 and 0.69. Audit tightness degrades with dataset size and clipping norm. *Nobody closes the gap; a factor of two at industrial compute is the state of the art.* |
| Annamalai, Ganev & De Cristofaro, "What do you want from theory alone?" (arXiv:2405.10994) | **USENIX Security 2024** | The first large-scale audit of DP synthetic data generators. Black-box MIAs "severely limited in power, yielding remarkably loose empirical privacy estimates." At ε=4: MST white-box ε_emp=3.10 vs black-box ≈0.00; PrivBayes 4.62; DPWGAN needs *active* white-box to reach 3.02. 10,000 synthetic datasets per experiment; 3h24m per configuration on 32 cores. **States the Clopper-Pearson cap explicitly.** |
| Ganev, Annamalai & Kulynych, "Tight Auditing of Differential Privacy in MST and AIM" (arXiv:2604.18352) | **April 2026** | First tight audit of AIM. GDP framing over the full FP/FN tradeoff; 10,000 model instances; worst-case 3-attribute datasets. Notes that unstable threshold selection is why prior work reported zero. |
| Mahloujifar, Melis & Chaudhuri, "Auditing *f*-DP in One Run" (arXiv:2410.22235) | **ICML 2025**, FAIR at Meta | Escapes the binary-guess bottleneck via a recursive bound on the count distribution. Outperforms Steinke et al. |
| Agrawal et al., "Let's Ask Gauss" (arXiv:2606.12733) | **June 2026** | Names the thresholding loss directly; Gaussian approximation to the score sum. |
| González, Rubio, Ramdas & Ribero, "Sequentially Auditing DP" (arXiv:2509.07055) | **2025** | e-values, anytime-valid. 50K samples → a few hundred. Still degrades above ε≈0.6. |
| Namatevs et al., "Privacy Auditing in DP Machine Learning: The Current Trends," *Applied Sciences* 15(2):647 | **2025** | Survey. Confirms existing auditing "require[s] thousands or millions of training runs to produce non-trivial statistical estimates." |

**Add — the implementation-bug literature, which is the project's actual premise:**

- **Ganev, Annamalai & De Cristofaro, "The Elusive Pursuit of Reproducing PATE-GAN"
  (arXiv:2406.13985).** Six open-source implementations, three by the original authors.
  **17 privacy violations and 5 further bugs. All six leak more privacy than claimed.** Utility
  results also fail to replicate.
- **Cebere, Erb, Desfontaines, Bellet & Fitzsimons, "Privacy in Theory, Bugs in Practice,"
  PoPETs (arXiv:2602.17454).** Gray-box "Re:cord-play" auditing of **12 libraries, 13 privacy
  violations**: SmartNoise SDK (sensitivity miscalibration), SmartNoise SQL (missing log(1/δ)
  in the accountant), Synthcity (PrivBayes noise miscalibration), diffprivlib (sensitivity
  errors; label-domain inference), **private-PGM (sensitivity underestimation in JAM)**,
  **MOSTLY AI Engine (incorrect budget composition, data-dependent control flow)**, Opacus,
  **dpmm (domain inference in AIM and PrivBayes)**.

Two consequences the thesis should draw explicitly. First, `private-PGM` — which we depend on
for real AIM — has a published sensitivity bug in one of its algorithms; that belongs in Ch.3
§3.5 "out of scope / trusted components" alongside the `dp_accounting` trust assumption, and it
strengthens rather than weakens the differential-testing argument. Second, a PoPETs paper
finding *incorrect budget composition* in a commercial engine is the best available external
justification for Standing Rule 1 ("never write a bound that cannot be cited") and for the
ledger.

**Also add:** Nasr et al. (2023) "Tight Auditing of Differentially Private Machine Learning"
(arXiv:2302.07956), and the NeurIPS 2023 Outstanding Paper commentary at
differentialprivacy.org for the Steinke framing.

---

## 4. Privacy accounting, budget management and deployment records

Ch.2 §2.4 is thin — three citations — and this is where SynthProof's systems contribution
lives, so it should be the most confident section in the chapter.

**Keep:** Sage (Lécuyer et al., 2019); PrivateSQL (Kotsogiannis et al., 2019); Google
`dp_accounting`; `autodp` as the differential-test target.

**Add:**

- **Tumult Analytics (arXiv:2212.04133)** — a production DP framework, now part of OpenDP as of
  October 2025. The right citation for "reference implementations exist and are mature."
- **OpenDP Differential Privacy Deployments Registry**, launched **25 November 2025**
  (registry.opendp.org). A public, curated record of real DP deployments. This is close kin to
  our ledger and must be cited and distinguished: the registry records *organisations' claims
  about deployments*, voluntarily, after the fact. Our ledger records *a single organisation's
  cumulative spend*, mechanically, at the moment of spending, in a tamper-evident chain.
- **Nanayakkara, Ghazi & Vadhan (OpenDP/Harvard), "Practitioners' Perspectives on a
  Differential Privacy Deployment Registry," arXiv:2509.13509 (September 2025).** An interview
  study. Their proposed "deployment card" schema — privacy unit, ε and δ, deployment model and
  trust assumptions, mechanisms, **pre-processing**, composition, and a justification field —
  is a near-match for the fields in our signed data sheet, arrived at independently and from
  the opposite direction (user research rather than threat modelling). And practitioners asked
  for exactly what a signature provides: they wanted "assurance that deployment claims were
  auditable rather than merely self-reported," and one wanted "Wikipedia style referencing
  where pretty much every claim has a pointer to where it came from."

  **This is the strongest single positioning statement available to the project:**

  > Harvard's OpenDP group asked DP practitioners what a deployment record should contain and
  > got back a schema that matches our data sheet, plus a requirement — that claims be
  > auditable rather than self-reported — that a voluntary registry structurally cannot meet.
  > A signature over the record is the mechanism that meets it.

- **Verifiable DP, which Ch.2 does not cite at all and must.** Two lines of work:
  - **Narayan, Feldman, Papadimitriou & Haeberlen, "Verifiable Differential Privacy,"
    EuroSys 2015** (VerDP) — zero-knowledge proofs that an untrusted curator ran the mechanism
    it claimed.
  - **Biswas & Cormode, "Verifiable Differential Privacy," arXiv:2208.09011.**

  These are the correct comparison for the honest limit in Ch.3 §3.5. **Our signature proves
  authorship and integrity of a *claim*; it does not prove the computation was performed
  correctly.** VerDP-style ZK proofs attempt the latter and are orders of magnitude more
  expensive. Stating this distinction before a reviewer raises it converts a weakness into
  evidence of a well-drawn scope. Write it as: *"the data sheet is an integrity-protected
  attestation, not a proof of execution; closing that gap is the VerDP line of work and is
  future work here."*

---

## 5. Transparency artefacts and regulation

Ch.2 §2.5 has Datasheets (Gebru et al., 2021), Model Cards (Mitchell et al., 2019) and Data
Statements (Bender & Friedman, 2018). All correct; all describe rather than bound. The
regulatory half needs to be rebuilt — it currently gestures at "the EU AI Act and DPDP" and the
last twelve months have made the argument far more concrete.

**Regulation, current as of August 2026:**

- **EDPB draft guidelines on anonymisation, published 30 July 2026.** Three weeks old. Two
  assessment approaches (contextual and simplified) against three technical criteria: **no
  singling out, no linkage, no inference.** That triad is Anonymeter's, and it is now a
  regulatory test rather than a research framework. Our attack suite implements singling-out;
  linkability and inference are declared future work — say so against this citation, because it
  turns a gap into a named roadmap item with a regulator's name on it.
- **EDPB Guidelines 01/2025 on Pseudonymisation** (January 2025) and the EDPB stakeholder-event
  report of 12 December 2025, for the direction of travel after the SRB judgment.
- **NIST SP 800-226** (March 2025) — see §1.
- **India's DPDP Act 2023 with the Digital Personal Data Protection Rules 2025** now
  operational, imposing data-fiduciary obligations. This is the domestic hook and belongs in
  Ch.1 §1.1 for an MIT-WPU submission.
- **Pilgram, Ko, Tung & El Emam, "Protecting patient privacy in tabular synthetic health data:
  a regulatory perspective," *npj Digital Medicine*, 2025.** Analyses UK, Singapore and South
  Korean guidance. All three treat synthetic data generation as processing of personal data;
  the ICO requires that synthetic data "must be subjected to" evaluation for residual
  disclosure risk; all three require the risk be "very low." And then the finding that is this
  project's entire justification:

  > "specific thresholds for a sufficiently low disclosure risk level are not (or only to a
  > limited extent) provided" — regulators "acknowledge that ... precise criteria were lacking
  > at the time of writing the guidelines."

  **Regulators in three jurisdictions require a demonstration of low residual disclosure risk
  and do not say what the demonstration is.** A machine-verifiable release record carrying
  ε_proved, ε_audited, the instrument's working range, and what was assumed public is a
  concrete proposal for what that demonstration could be. This is the audience paragraph, and
  it should open Ch.1.

**Why the commercial status quo does not satisfy this:**

- **Ganev & De Cristofaro, "The Inadequacy of Similarity-Based Privacy Metrics: Privacy Attacks
  against 'Truly Anonymous' Synthetic Datasets," IEEE S&P 2025** (arXiv:2312.05114). Their
  ReconSyn attack, using only the fitted model and the *published privacy metrics*, recovers
  **78–100% of training-set outliers with perfect precision**; DifferenceAttack achieves 100%
  membership and attribute inference with few API calls. Evaluated on PrivBayes, MST, DPGAN,
  PATE-GAN and CTGAN over Adult, Census and MNIST. Their recommendation is to "adopt
  established end-to-end DP pipelines," and they warn that combining DP training with
  unperturbed similarity metrics "breaks the end-to-end DP pipeline and ultimately negates its
  privacy guarantees."
- **Ganev, "Synthetic Data, Similarity-based Privacy Metrics, and Regulatory (Non-)Compliance,"
  GenLaw @ ICML 2024** (arXiv:2407.16929). Documents that major vendors — Mostly AI, Syntegra,
  Panfilo & Aindo, Syntho — rely on similarity metrics rather than formal guarantees, and
  argues this cannot satisfy GDPR/ICO. **Its stated limitation is that it "identifies problems
  rather than providing implementable regulatory solutions."** SynthProof is an attempt at the
  implementable artefact that paper says is missing. That is a legitimate, modest, and
  defensible framing of the whole project.
- **Ganev, "When Synthetic Data Met Regulation," ICML 2023 workshop** (arXiv:2307.00359).

**A note on the commercial signal.** `certifieddata.io` markets machine-verifiable certificates
and transparency logs for AI datasets. There is no evidence it carries DP bounds. Worth one
sentence as evidence that the artefact category is forming commercially, and that the DP-bound
version of it is unoccupied.

---

## 6. Evaluation methodology

A section Ch.2 does not currently have, and needs, because two of our three findings are
methodological.

- **Rosenblatt et al., "Epistemic Parity," PVLDB 16 (2023) / SIGMOD Record / CACM Research
  Highlight 2025.** 105 findings from 8 peer-reviewed papers across 4 ICPSR datasets. Five of
  eight papers reached 100% parity; parity was surprisingly flat across ε ∈ {e⁻³ … e²};
  **PrivBayes beat MST "contrary to findings in randomized query workload studies."** Their
  conclusion — that proxy metrics lack demonstrated connection to real analytic practice — is
  the frame for our §0.5.
- **Du & Li (2025)** as above: rankings vary by dataset; no algorithm dominates.
- **Ganev, Xu & De Cristofaro, CCS 2024** as above: non-monotone utility in n and in ε.
- **Stadler et al., USENIX Security 2022** for the negative-control discipline: a privacy metric
  that fires on a release containing no real records is measuring similarity, not disclosure.
  Our shuffled-release negative control is a direct implementation of that critique and should
  cite it at the point of use in Ch.6, not only in Ch.2.

---

## 7. The positioning table, rewritten

Ch.2 §2.6's table is directionally right but overclaims by omission — it does not include the
2025–2026 work that occupies neighbouring cells. Replace it with this.

| System / line of work | Formal upper bound | Empirical lower bound | Composes | Cross-release record | Bound to artefact | Third-party verifiable | Preprocessing charged |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| DP synthesis: AIM, MST, PrivBayes | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ (bug class per PoPETs) |
| One-run auditing (Steinke '23; *f*-DP '25; Gauss '26) | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | n/a |
| Tight audits of MST/AIM (Ganev '26) | ❌ | ✅ (tight, 10⁴ runs) | ❌ | ❌ | ❌ | ❌ | n/a |
| Risk assessment (Anonymeter) | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | n/a |
| DP domain extraction studies ('25) | partial | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Datasheets / Model Cards | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | n/a |
| OpenDP Deployments Registry ('25) | ✅ (self-reported) | ❌ | ❌ | ✅ (org level) | ❌ | ❌ | ❌ |
| Verifiable DP (VerDP '15; Biswas & Cormode '22) | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ (ZK, expensive) | ❌ |
| DP library auditing (PoPETs '26) | ❌ | ✅ (gray-box) | ❌ | ❌ | ❌ | ❌ | ✅ (as a bug finder) |
| **SynthProof** | ✅ | ✅ (with measured range) | ✅ | ✅ | ✅ | **partial — integrity, not execution** | ✅ |

**The honest one-sentence claim this table supports:**

> Every column of this table is occupied by existing work. No existing system occupies more
> than four of them at once, and none combines a charged end-to-end accountant, an audited
> lower bound reported with its own measured instrument range, a cross-release tamper-evident
> ledger, and a signed release record. SynthProof is a systems integration of seven separate
> research lines, and its research contributions are the three measurements that integration
> made possible.

That claim is defensible. "Nothing ships both" — the current Ch.2 phrasing — is not, and a
reviewer with a search engine will say so.

---

## 8. What is genuinely novel, stated at the level a reviewer will accept

Ranked by how well they would survive peer review.

| # | Claim | Strength | Nearest prior work |
|---|---|---|---|
| 1 | A workload-adaptive DP synthesiser's structural advantage is **concentrated on** the cliques it selects — 11.9× on Adult, 2.3× on ACS — so benchmarking it on a single unselected statistic largely measures the selector, and the concentration ratio is itself dataset-dependent | **Strong.** Novel as a controlled result, and honestly weakened by the second dataset | Rosenblatt et al. PVLDB '23 observe a consistent ranking anomaly and conjecture the cause; Du & Li '25 do not condition on it |
| 2 | Under end-to-end DP where the domain is itself discovered privately, downstream utility can *fall* as ε rises, because budget growth inflates the domain faster than it improves measurement | **Strong.** New instance along a new axis | Ganev et al. '25 find the inverted-U in bins; Ganev et al. CCS '24 find non-monotonicity in n |
| 3 | Quantification of the Steinke-class audit ceiling ε_max(r) ≈ log(r/ln(1/α)), with an empirically measured detection floor and ceiling from a controlled leaky generator, and the consequence for subgroup audits | **Moderate.** The cap is stated in USENIX Sec '24; the quantification, the measured floor/ceiling table, and the per-subgroup corollary are ours | Annamalai et al. USENIX '24; the '25–'26 escape constructions |
| 4 | A bounded null on per-subgroup empirical privacy leakage across two datasets, with FDR control, TOST equivalence against an a-priori bound, and a power statement | **Moderate.** Answers explicitly declared future work; the negative result is the honest answer | Ganev et al. '21 leave privacy-specific analysis to future work |
| 5 | An end-to-end pipeline where preprocessing, selection and measurement all draw on one accountant, with a tamper-evident cross-release ledger and a signed release record | **Systems contribution, not a research claim.** Say so | OpenDP registry '25; VerDP '15; deployment cards '25 |
| 6 | Self-audit as method: 12 defects found in our own implementation, each pinned by a named regression test, plus a 10-mutant targeted probe at score 1.0 with 3 verified-equivalent exclusions | **Moderate, and unusually well evidenced** | PATE-GAN '24 (17 violations, 6 impls); PoPETs '26 (13 violations, 12 libraries) |

**A capstone that can defend two Strong and three Moderate claims, with a preregistration, two
datasets, 373 tests and a reproducibility manifest, is not a weak capstone.** It is above the
bar for a 4-page workshop submission.

---

## 9. Venues, with dates

| Venue | Format | Archival | Timing | Fit |
|---|---|---|---|---|
| **TPDP** (Theory and Practice of DP) | 4 pages + appendices, not anonymised | **No** — explicitly does not preclude later publication | TPDP 2026 was 1–2 June, Boston; deadline was 18 Feb 2026. Expect TPDP 2027 on a similar cycle | **Best first target.** Scope explicitly includes implementations, applications and policy |
| **SynthData @ ICLR** (Synthetic Data × Data Access) | 6 pages, or 3-page "tiny paper" | No | ICLR 2025 edition: deadline 6 Feb, workshop 27 Apr | DP synthetic data and evaluation explicitly in scope. The tiny-paper track is well matched to finding #1 alone |
| **PETS / PoPETs** | Full paper | Yes | Rolling cycles; artifact evaluation | The natural home for findings #1–#3 together, once the thesis is written |
| **PPML @ NeurIPS / CCS** | Workshop | No | Autumn cycle | Broad fit |

Finding #1 (the clique confound) is the most submission-ready: it is a single controlled
experiment, the numbers are committed, and it has a clear addressee in the benchmarking
community.

---

## 10. Concrete edits to make

**In the repository, before the viva:**

1. `results/AUDITOR_COMPARISON.md`, `results/DETECTION_FLOOR.md`, `synthproof/audit/steinke.py`
   — qualify the ceiling claim to the binary-guess estimator class (§0.1). One paragraph each.
2. `docs/thesis/ch02-literature-review.md` §2.6 — replace the positioning table with §7 above
   and the "Nothing ships both" sentence with the §7 claim.
3. `docs/thesis/ch02-literature-review.md` §2.3 — extend to 2026 using the §3 table.
4. `docs/thesis/ch02-literature-review.md` — add §4 (accounting/registries/verifiable DP) and a
   new §2.7 on evaluation methodology from §6.
5. `docs/thesis/ch03-threat-model.md` §3.5 — add the private-PGM JAM sensitivity bug to trusted
   components; add the VerDP distinction (integrity of a claim ≠ proof of execution).
6. `docs/thesis/ch01-introduction.md` §1.1 — rebuild the motivation around the *npj Digital
   Medicine* finding and NIST SP 800-226 rather than Sweeney (2000) alone. Sweeney explains why
   de-identification failed; the regulators explain why nobody knows what to demand instead.
7. `docs/preregistration.md` / Ch.6 — cite Ganev et al. (2021) as the origin of H2.
8. Merge the three findings into one narrative section (§0.6) and make it Ch.8's spine.
9. `docs/thesis/references.bib` — 29 entries now; add the ~25 below.
10. Remove the vestigial Postgres service from `docker-compose.yml`.

**New BibTeX keys to add:**

`cormode2025synthsurvey` (KDD'25) · `annamalai2024theoryalone` (USENIX Sec'24) ·
`annamalai2024nearlytight` (NeurIPS'24) · `ganev2026tightmstaim` · `mahloujifar2025fdponerun`
(ICML'25) · `agrawal2026gauss` · `gonzalez2025sequential` · `namatevs2025auditsurvey` ·
`ganev2024pategan` · `cebere2026bugs` (PoPETs) · `annamalai2025domain` ·
`ganev2025discretization` · `ganev2024graphicalvsdeep` (CCS'24) · `ganev2021robinhood` ·
`ganev2025inadequacy` (S&P'25) · `ganev2024regulatory` (GenLaw@ICML'24) ·
`rosenblatt2023epistemic` (PVLDB) · `du2025benchmark` · `ganev2025dpmm` ·
`dwork2019exposeepsilons` (JPC) · `nanayakkara2025registry` · `opendp2025registry` ·
`nist2025sp800226` · `narayan2015verdp` (EuroSys) · `biswas2022verifiabledp` ·
`pilgram2025regulatory` (npj Digital Medicine) · `edpb2026anonymisation` · `berns2022tumult` ·
`angelozzi2026fairness`

---

## Sources

Retrieved 22 August 2026.

- Cormode, Maddock, Ullah & Gade — *Synthetic Tabular Data: Methods, Attacks and Defenses*, KDD 2025 — https://dimacs.rutgers.edu/~graham/pubs/papers/synthsurvey.pdf
- Annamalai, Ganev & De Cristofaro — *"What do you want from theory alone?" Experimenting with Tight Auditing of DP Synthetic Data Generation*, USENIX Security 2024 — https://arxiv.org/html/2405.10994
- Annamalai & De Cristofaro — *Nearly Tight Black-Box Auditing of DP Machine Learning*, NeurIPS 2024 — https://arxiv.org/html/2405.14106v4
- Ganev, Annamalai & Kulynych — *Tight Auditing of Differential Privacy in MST and AIM*, 2026 — https://arxiv.org/html/2604.18352
- Mahloujifar, Melis & Chaudhuri — *Auditing f-Differential Privacy in One Run*, ICML 2025 — https://arxiv.org/html/2410.22235v1
- Agrawal, Wei, Singh, Magdon-Ismail & Zikas — *Let's Ask Gauss: Improved One-Run Privacy Auditing*, 2026 — https://arxiv.org/html/2606.12733
- González, Rubio, Ramdas & Ribero — *Sequentially Auditing Differential Privacy*, 2025 — https://arxiv.org/html/2509.07055
- Steinke, Nasr & Jagielski — *Privacy Auditing with One (1) Training Run*, NeurIPS 2023 — https://proceedings.neurips.cc/paper_files/paper/2023/file/9a6f6e0d6781d1cb8689192408946d73-Paper-Conference.pdf
- Namatevs et al. — *Privacy Auditing in DP Machine Learning: The Current Trends*, Applied Sciences 2025 — https://www.mdpi.com/2076-3417/15/2/647
- Ganev, Annamalai & De Cristofaro — *The Elusive Pursuit of Reproducing PATE-GAN* — https://arxiv.org/html/2406.13985v1
- Cebere, Erb, Desfontaines, Bellet & Fitzsimons — *Privacy in Theory, Bugs in Practice: DP Library Auditing*, PoPETs — https://arxiv.org/pdf/2602.17454
- Annamalai, Ganev et al. — *Understanding the Impact of Data Domain Extraction on Synthetic Data Privacy*, 2025 — https://arxiv.org/html/2504.08254
- Ganev, Annamalai, Mahiou & De Cristofaro — *The Importance of Being Discrete: Discretization in End-to-End DP Synthetic Data*, 2025 — https://arxiv.org/html/2504.06923
- Ganev, Xu & De Cristofaro — *Graphical vs. Deep Generative Models*, ACM CCS 2024 — https://arxiv.org/html/2305.10994v2
- Ganev, Oprisanu & De Cristofaro — *Robin Hood and Matthew Effects: DP Has Disparate Impact on Synthetic Data* — https://ar5iv.labs.arxiv.org/html/2109.11429
- Ganev & De Cristofaro — *The Inadequacy of Similarity-based Privacy Metrics*, IEEE S&P 2025 — https://arxiv.org/html/2312.05114v3
- Ganev — *Synthetic Data, Similarity-based Privacy Metrics, and Regulatory (Non-)Compliance*, GenLaw @ ICML 2024 — https://arxiv.org/html/2407.16929v1
- Rosenblatt et al. — *Epistemic Parity: Reproducibility as an Evaluation Metric for DP*, PVLDB 16, 2023 — https://www.vldb.org/pvldb/vol16/p3178-rosenblatt.pdf
- Du & Li — *Benchmarking Differentially Private Tabular Data Synthesis*, 2025 — https://arxiv.org/pdf/2504.14061
- Ganev et al. — *dpmm: Differentially Private Marginal Models*, 2025 — https://arxiv.org/html/2506.00322v1
- Angelozzi & Arcolezi — *Where to Intervene? Benchmarking Fairness-Aware Learning on DP Synthetic Tabular Data*, July 2026 — https://arxiv.org/html/2607.07471v1
- McKenna et al. — *AIM: An Adaptive and Iterative Mechanism for DP Synthetic Data*, VLDB 2022 — https://www.vldb.org/pvldb/vol15/p2599-mckenna.pdf
- Dwork, Kohli & Mulligan — *Differential Privacy in Practice: Expose Your Epsilons!*, JPC 9(2), 2019 — https://journalprivacyconfidentiality.org/index.php/jpc/article/view/689
- Nanayakkara, Ghazi & Vadhan — *Practitioners' Perspectives on a DP Deployment Registry*, 2025 — https://arxiv.org/html/2509.13509v1
- OpenDP — *Differential Privacy Deployments Registry*, launched Nov 2025 — https://registry.opendp.org/
- NIST — *SP 800-226, Guidelines for Evaluating Differential Privacy Guarantees*, March 2025 — https://www.nist.gov/news-events/news/2025/03/new-nist-publication-guidelines-evaluating-differential-privacy-guarantees
- Narayan, Feldman, Papadimitriou & Haeberlen — *Verifiable Differential Privacy*, EuroSys 2015 — https://haeberlen.cis.upenn.edu/papers/verdp-eurosys2015.pdf
- Biswas & Cormode — *Verifiable Differential Privacy*, 2022 — https://arxiv.org/abs/2208.09011
- Berns et al. — *Tumult Analytics*, 2022 — https://arxiv.org/pdf/2212.04133
- Pilgram, Ko, Tung & El Emam — *Protecting patient privacy in tabular synthetic health data: a regulatory perspective*, npj Digital Medicine 2025 — https://www.nature.com/articles/s41746-025-02112-0
- EDPB — *Draft Guidelines on Anonymisation*, 30 July 2026 — https://datamatters.sidley.com/2026/07/27/edpb-publishes-draft-guidelines-on-anonymisation/
- *How to DP-fy Your Data: A Practical Guide*, Dec 2025 — https://arxiv.org/html/2512.03238v1
- TPDP — https://differentialprivacy.org/tpdp2026/ · SynthData @ ICLR — https://synthetic-data-iclr.github.io/

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

Full attribution: [`docs/MEASUREMENT_CONVENTIONS.md`](MEASUREMENT_CONVENTIONS.md).
