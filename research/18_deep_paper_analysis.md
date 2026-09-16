# 18 — Deep per-paper analysis of the literature survey (2026-09-17)

> Purpose: the team's deepest understanding of each surveyed paper — what they did, how, the
> techniques, the datasets and exactly how they were used/modified, the novelty, and (most
> important) how each relates to SynthProof. Read against the actual PDFs in
> `research/litsurvey/literature surveys/`. Standing honesty rules apply: quotes are from the paper;
> where a number is the paper's, it is marked; inferences are labelled `INFERENCE:`.
>
> **Status: COMPLETE — all 11 papers (P1–P11) are Claude-verified deep-reads** (read from the PDFs,
> §0 schema, verbatim evidence). The earlier Antigravity batch (`research/deep_analysis/*.md`) is
> superseded — it fabricated P3 and got P1/P2 wrong. This file is authoritative.

---

## MASTER SYNTHESIS — the survey at a glance

| # | Paper (short) | Type | Datasets (overlap ✅) | What they did NOT do → OUR opening |
|---|---|---|---|---|
| P1 | Stadler, *Groundhog Day* (USENIX'22) | attack + framework | Adult✅, Texas | proved synth leaks + DP-impls read domain from data; no signed/checkable artifact → **precursor to D1** |
| P2 | Annamalai, *Tight Auditing* (USENIX'24) | mechanism audit | Adult✅, SF Fire, worst-case | audits the mechanism (needs code/worst-case); no document audit → **grounds our ceiling; black-box audits read ε≈0** |
| P3 | Cebere, *Grey-Box Auditing* (PoPETs'26) | library audit | none (synthetic probes) | audits library code, not the shipped release → **same "neighbours+fixed randomness" as our seed-replay** |
| P4 | Ganev, *Domain Extraction* (ICLR'25) | preprocessing audit | Wine✅ | domain-from-data breaks DP; no artifact field for it → **validates our domain-source rule (=D1)** |
| P5 | Ganev, *Discretization* (CCS'25) | preprocessing audit | Adult✅, Gas✅, Wine✅ | audits discretization; no checkable release → **maps preprocessing subfield we slot into** |
| P6 | Ganev, *SMOTE and Mirrors* (ICLR'26) | attack on oversampling | 8 imbalanced✅ + cardio/higgs/… | naive metrics miss leaks (need MIA) → **validates our sanity-gate; our kNN arm is SMOTE-like** |
| P7 | Mohapatra, *Missing Data* (VLDB'24) | mechanism + privacy analysis | **Adult✅ + Bank✅**, BR2000, National | asks "does missingness hurt utility/help privacy"; never audits membership → **THE base for our imputation audit** |
| P8 | McKenna, *AIM* (VLDB'22) | mechanism (we USE it) | Adult✅, salary, msnbc, fire, nltcs, titanic | ships a model, no signed/boundary check → **our generator; where D1 lives** |
| P9 | Abowd, *Census TopDown* (HDSR'22) | production deployment | Census (restricted) | ships invariants outside ε, documented in prose only → **real case study; we make it machine-checkable** |
| P10 | Dibia, *DP Privacy Label* (PoPETs'26) | interview + standard | none (12 experts) | label has no signing, no measurement-limit reporting ("privacy theater") → **★ LEAD: we sign it + report the ceiling** |
| P11 | Song, *Mental Models* (CSCW'24) | interview study | none (5 devs+17 analysts) | diagnoses blind trust, builds no tool → **★ PREMISE: why an automatic checker is needed** |

**Cross-cutting themes (the spine of your literature survey + gaps):**
1. **"Reading structure from the private data breaks DP"** appears in **P1, P2, P4, P5, P11** — a whole
   cluster of the exact bug your **D1 fix + domain-source rule** address. This is your single strongest
   "what they missed, we do" thread.
2. **Preprocessing is a leak surface** — P4 (domain), P5 (discretization), P6 (SMOTE) audit three
   steps; **missing-data handling is the unaudited one = your imputation audit.**
3. **Naive privacy metrics / black-box audits underestimate leakage** (P2, P6) — justifies your
   **sanity-gated** auditor and your honesty that audited ε=0.000 is *loose*, not "safe."
4. **The field converged on WHAT to disclose (P10) but not on making it CHECKABLE** — no signing (P10),
   no operating-range reporting (P10), documented only in prose (P9), and practitioners don't verify
   (P11). **That gap — signed + machine-checkable + limit-reporting — is SynthProof.**

---

## §0 — The extraction schema (the "parameters" to fill for EVERY paper)

For each paper, fill all of these:

**A. Identity & framing** — full citation, venue, year, arXiv, authors + lab/cluster; paper type
(attack / empirical-audit / DP-mechanism / preprocessing-audit / standard-proposal / interview);
one-line thesis; the gap it targets.
**B. What they did** — stated contributions (verbatim); the core novelty; threat model / adversary
assumptions; DP definition + neighbouring relation (add/remove vs replace one).
**C. How they did it** — core method/algorithm (2–4 sentences); DP mechanism(s) used; attack/audit
technique; privacy-accounting method (RDP/zCDP/PLD/GDP, library); key hyperparameters (ε grid, δ,
#trials, #seeds); evaluation metrics.
**D. Datasets — deep** — each dataset: exact rows, #numerical / #categorical, target column; how
they PRE-PROCESSED it (discretisation/binning/one-hot/scaling/subsample size/missingness injection/
splits); what they MODIFIED vs used as-is; the role each plays (train SDG / attack target /
benchmark); any dataset-specific finding.
**E. Results & findings** — headline numbers; what worked / failed; surprising findings; the
limitations the authors themselves admit.
**F. Relevance to SynthProof** — overlap (what they also do); what they did NOT do → our opening;
is a same-dataset comparison possible (which dataset, which metric); a technique of theirs we can
borrow/cite; how to position (complementary / builds-on / differs); a one-line viva soundbite.
**G. Citations to chase** — key references we should also read.

---

## P7 — Mohapatra, Zong, Kerschbaum & He, *Differentially Private Data Generation with Missing Data* (VLDB 2024, arXiv:2310.11548) — CLAUDE VERIFIED

**A. Identity & framing.** U. Waterloo (He/Kerschbaum group). Type: **DP-mechanism + privacy-analysis**
paper (not an attack/audit). One-line thesis: *existing DP synthesizers degrade badly when the input
has missing values; propose adaptive strategies that handle missingness inside the generator, and
analyse how privacy for the incomplete data relates to privacy for the ground-truth data.* Gap
targeted: prior DP-synthesis work "only look at a simple scenario where the input data has no
missing values."

**B. What they did (contributions, ~verbatim).**
1. *"first to formalize and study the problems of DP synthetic data with missing data"* — existing
   algorithms lose **5–23% utility at ≤5% missing** and **10–190% at ≤20% missing.**
2. Three **adaptive-recourse** approaches (one per DP-mechanism family) that fold missing-data
   handling into learning, using **no extra privacy budget**, improving utility **15–72%.**
3. Differentiate privacy for **incomplete** vs **ground-truth** data; sufficient conditions
   (Thm 5.2) under which an incomplete-data DP mechanism also protects the ground truth.
4. First to use **missingness as a sampling-amplification** source: ground-truth ε is
   **0.1–0.65× the incomplete-data ε** at 10–50% missing.
   Threat model / DP: (ε,δ)-DP, neighbours *"differ in one row."* Two privacy targets: the
   incomplete table D the curator holds, and the true table D̄ behind the missing mechanism.

**C. How they did it.**
- **Vanilla baselines:** (i) *complete-row-only* (drop incomplete rows) — biased under MAR/MNAR, and
  collapses the sample (Adult 32k → ~5k at 20% MAR, ~1k at 20% MCAR/MNAR); (ii) *imputation-first* —
  and they prove DP imputation is **expensive**: imputing an attribute has **stability c = m_A+1**
  (Lemma 4.2), so worst-case `M∘T` on n rows is **nε-DP** (Thm 4.3). This is the key theoretical
  reason uncharged cross-record imputation is dangerous.
- **Adaptive recourse (the novelty):** **DP-MisGAN** (privatised MisGAN — two generator/discriminator
  pairs, one for data one for the missing-mask; gradient-sanitises only the generators, WGAN,
  **RDP** accounting via the sampled-Gaussian mechanism); **PrivBayesE** (partial-marginal
  observation — drop a row only if it's missing in the *queried* attributes, extends PrivBayes, no
  extra budget); **KaminoI** (column-wise — extends Kamino, imputes each attribute with the same
  intermediate model it already trains, no extra budget).
- **Ground-truth privacy:** Thm 5.2 (independent-row missingness ⇒ `M∘MΦ` is (ε̄,δ̄)-DP, ε̄≤ε);
  MCAR gives a tighter bound; Algorithm 4 computes the optimal amplified cost; **MAR/MNAR
  amplification left as future work.**
- Accounting: RDP (DP-MisGAN), pure-DP for PrivBayes (δ=0).

**D. Datasets — deep (Table 1).**
| Dataset | Rows | #Num | #Cat | Overlap w/ ours |
|---|---|---|---|---|
| **Adult** | 32,561 | 5 | 10 | ✅ same |
| **Bank** | 45,211 | 3 | 14 | ✅ same |
| BR2000 | 38,000 | 3 | 11 | mirror only |
| National (NIST) | 15,012 | 6 | 14 | (we have the 27k parent excerpt) |
- **Preprocessing:** numerical attributes **discretised into 10 uniform bins or scaled 0–1**;
  categoricals **one-hot or ordinal** — per each generator's own paper.
- **Missingness injected** with the **Muzellec et al. [65]** pipeline: MCAR = Bernoulli mask to an
  exact count; MAR = uses 50% of attributes as features to drive missingness; MNAR = value-dependent.
  Levels: ≤5%, ≤20% (utility), 10–50% (amplification).
- Role: all four are *inputs to the DP synthesizer*; no attack target (this is not an audit paper).

**C-bis. Settings.** Baselines: **PrivBayes, AIM** (statistical), **DPCTGAN, DPautoGAN** (deep),
**Kamino** (mixed). Imputation baselines: **random, mean, Kamino-impute**. ε: PrivBayes/Kamino **ε=1**,
GANs **ε=3**; PrivBayes pure-DP (δ=0), others δ ≈ one order below 1/|D|. Metrics: **1-way & 2-way TVD**
(marginal distance, ↓) and **downstream F1-score** (↑).

**E. Results & findings.** Complete-row collapses under MAR/MNAR; imputation-first is privacy-costly;
adaptive methods win (15–72% utility gain, sometimes matching the no-missing baseline). Missingness
*amplifies* ground-truth privacy (ε̄ = 0.1–0.65× the incomplete ε). Admitted limits: MAR/MNAR
amplification unsolved; identifying the missing type without domain knowledge is unreliable.

**F. Relevance to SynthProof — THE most important comparison base.**
- **Same problem area, opposite question.** They ask *"does missing data hurt utility, and can
  missingness be turned into a privacy amplifier?"* We ask *"does the missing-data HANDLING step leak
  membership above the DP baseline?"* They treat missingness as a **utility problem / privacy
  benefit**; we test it as a **privacy risk**. This is the cleanest "what they didn't do" in the
  whole survey.
- **They give us our theory.** Thm 4.1–4.3 (imputation stability = nε) is exactly why our *uncharged*
  cross-record imputation arms (A2/A4) are a candidate boundary leak and why the *charged* arms
  (A3/A4_CHARGED) cost budget. Cite it as the theoretical grounding of our audit design.
- **They never run a membership-inference audit** of the handling step → our bounded-negative result
  is the empirical privacy check their paper leaves open.
- **Same-dataset comparison feasible on Adult + Bank** (they report 2-way TVD and F1; we can place
  our arms' utility/leakage next to theirs).
- **Borrow & cite:** the **Muzellec et al. [65]** MCAR/MAR/MNAR injection pipeline — align our
  injection methodology to theirs and cite it (strengthens our method section for the guide).
- **Position:** *complementary and building-on* — never "we beat them."
- **Viva soundbite:** *"Mohapatra et al. is the one prior paper on DP synthesis with missing data —
  but they ask whether missingness hurts utility and helps privacy; we ask whether the missing-data
  handling leaks membership, which they never test."*

**G. Citations to chase:** Muzellec et al. [65] (missingness generation), Kamino [35], PrivBayes [97],
AIM [58], McSherry stability [60], MisGAN [53].

---

## P8 — McKenna, Mullins, Sheldon & Miklau, *AIM: An Adaptive and Iterative Mechanism for DP Synthetic Data* (VLDB 2022, arXiv:2201.12677) — CLAUDE VERIFIED (datasets/metric confirmed against PDF)

**A. Identity & framing.** UMass/Miklau group + private-PGM authors. Type: **DP-mechanism**. Thesis:
a workload-adaptive, iterative *select→measure→estimate* marginal mechanism that beats prior
marginal-based synthesizers across privacy budgets. **This is the strong generator SynthProof itself
uses**, so P8 is our foundation, not a competitor.

**B. What they did.** AIM adaptively **selects** which marginals to measure (guided by the target
workload and current model error), **measures** them with the Gaussian mechanism, and **estimates** a
consistent distribution via **Private-PGM** (a graphical model). Novelty: adaptive marginal selection
+ a principled budget/quality trade-off. DP: (ε,δ) via **zCDP/RDP** composition; neighbours differ by
one record.

**C. How they did it.** Iterative rounds; each round picks the highest-value marginal, spends a slice
of budget measuring it under Gaussian noise, refits the PGM. Accounting: zCDP. **ε grid [0.01, 10]**,
**δ = 1e-9**, **5 trials**, metric = **average workload error** (error over a workload of 3-way /
target / skewed marginals; TVD-style, ↓). Baselines: **MST, PrivBayes+PGM, GEM, MWEM+PGM**.

**D. Datasets — deep (Table 3).**
| Dataset | Rows | Dims | Target (if any) |
|---|---|---|---|
| **adult** | 48,842 | 15 | income>50K |
| salary | 135,727 | — | — |
| msnbc | 989,818 | — | — |
| fire | 305,119 | — | — |
| nltcs | 21,574 | — | — |
| titanic | 1,304 | Survived |
- Verbatim: *"For the adult and titanic datasets, these are the income>50K attribute and the Survived
  attribute, as those correspond to the attributes we are trying to predict."* Preprocessing:
  attributes discretised; a subset of attributes kept for some datasets. Role: all are inputs to the
  generator; utility measured as workload error (no attack).

**E. Results & findings.** AIM achieves competitive/best workload error across ε on most datasets;
Fig 1 shows workload error vs ε for AIM vs MST/PrivBayes/GEM. (These are utility numbers, not
privacy attacks.)

**F. Relevance to SynthProof.**
- **We use AIM as our main mechanism** — so cite it as our generator, not a rival. Same benchmark
  (**Adult**) as our H1.
- **Our D1 finding lives here:** AIM/Private-PGM was consuming the exact private row count
  (`known_total=n`) uncharged — our fix (`known_total=None`) makes AIM's stated ε honest. Great viva
  material: we found and fixed a real accounting leak *in the mechanism we depend on.*
- **What AIM does NOT do:** it ships a model/synthetic table with a utility guarantee — **no signed
  release artifact, no boundary audit, no report of the empirical audit's operating range.** That's
  our whole contribution layer.
- **Same-dataset comparison:** Adult, and we reproduce AIM's ~9× utility edge over `independent` at
  ε=8 on Adult (our verified `results/h1_all_families.json`).
- **Viva soundbite:** *"AIM is the state-of-the-art marginal mechanism we build on; our job isn't a
  better generator, it's making AIM's release checkable — and we caught it charging the wrong ε for
  the private row count."*

**G. Citations to chase:** Private-PGM (McKenna et al. 2019), MST, MWEM, GEM.

---

## P3 — Cebere, Erb, Desfontaines, Bellet & Fitzsimons, *Privacy in Theory, Bugs in Practice: Grey-Box Auditing of Differential Privacy Libraries* (arXiv:2602.17454) — CLAUDE VERIFIED

**A. Identity & framing.** Inria/TUM/Oblivious. Type: **empirical audit of DP software**. Thesis:
*DP implementations are buggy; a grey-box audit that inspects a mechanism's internal state can
catch violations that black-box statistical auditing misses.* Gap: formal tools are too
restrictive, black-box auditing is intractable and can't localise the bug.

**B. What they did.** Introduce **Re:cord-play** — run an *instrumented* algorithm on **neighbouring
datasets with identical randomness** and check for **data-dependent control flow**, falsifying
sensitivity violations by comparing *declared* sensitivity to the *empirically measured* distance
between internal inputs. Generalise to **Re:cord-play-sample** (a full statistical audit per
component). **Audited 12 open-source libraries** (SmartNoise SDK, Opacus, Diffprivlib, …) and
**found 13 privacy violations** (from "subtle preprocessing flaws to misapplication of parameters").

**C. How they did it.** Grey-box instrumentation of the internal state; neighbouring-dataset +
fixed-randomness replay to expose data-dependent branches; per-component statistical testing.

**D. Datasets.** **No real ML benchmark** — uses controlled/synthetic inputs to trigger the
libraries' code paths (the "data" is a probe, not a dataset). Role: adversarial test harness.

**E. Results & findings.** 13 real violations across 12 shipped libraries — concrete evidence that
"DP in theory" ≠ "DP in practice." Localises the buggy component (black-box can't).

**F. Relevance to SynthProof.**
- **Direct methodological cousin of our seed-replay attack.** Their core trick — *run on
  neighbouring datasets with identical randomness and see what differs* — is exactly our D5
  seed-replay probe. Cite it as precedent for our attack methodology.
- **Motivates our differential-accountant cross-check:** if 13 violations hide in 12 libraries, a
  release resting on one library's unexamined accounting deserves a second accountant (our fix).
- **What they did NOT do:** audit the *released artifact/document*; theirs is a code/library audit,
  ours is a data-blind document audit (`boundary-audit`). Complementary layers.
- **Same-dataset comparison:** N/A (no dataset).
- **Viva soundbite:** *"Cebere et al. found 13 privacy bugs in 12 DP libraries using the same
  neighbouring-datasets-with-fixed-randomness idea our seed-replay attack uses — which is exactly
  why a release can't be trusted on one library's word, and why we add a second accountant and a
  document-level check."*

**G. Citations to chase:** SmartNoise/OpenDP, Opacus, Diffprivlib docs; prior DP-auditing (Jagielski,
Nasr, Steinke).

---

## P1 — Stadler, Oprisanu & Troncoso, *Synthetic Data – Anonymisation Groundhog Day* (USENIX Security 2022, arXiv:2011.07018) — CLAUDE VERIFIED

**A. Identity & framing.** EPFL/UCL. Type: **empirical privacy attack + evaluation framework**.
Thesis: *synthetic data is NOT a privacy silver bullet — it either fails to stop inference attacks or
destroys utility, and its privacy-utility tradeoff is unpredictable.* Gap: prior work measured
synthetic-data privacy with naive similarity tests and average-case metrics that **underestimate**
the risk.

**B. What they did (contributions I–IV, ~verbatim).** (I) Non-private generative models do **not**
protect **outlier** records from linkage; a strategic adversary infers a target's presence with high
confidence. (II) DP synthetic data protects targets **but at large, unpredictable utility cost**, with
no transparency about what is preserved/suppressed. (III) **Existing implementations of two DP
generators (PrivBay, PATEGAN) violate their own formal guarantees** — they patch them. (IV) Release an
open-source evaluation framework with two attacks. Threat model: adversary sees **only the published
synthetic dataset** (black-box, no model query) + a reference dataset from the same distribution and
knows n, m, GM(·). Neighbours: raw dataset with vs. without the target record (a membership game à la
Yeom).

**C. How they did it.** A **membership/linkability privacy game** (Fig 1) → measure **privacy gain
PG = Adv(R) − Adv(S)**. Attack = **black-box shadow-model MIA**: train many shadow generators on
reference sets with/without the target, extract features from the synthetic output, train a
**Random-Forest** distinguisher. Three feature sets: **F_Naive** (summary stats), **F_Hist**
(1-way marginals), **F_Corr** (pairwise correlations). Also an **attribute-inference** game
(regression/RF to predict a hidden sensitive attribute). Generators studied: IndHist, BayNet,
CTGAN (no DP); **PrivBay, PATEGAN** (DP).

**D. Datasets — deep.** **Adult** and **Texas Hospital Discharge** (inpatient records; they built a
2013 train / 2014 test split). Both mixed numeric+categorical. Experiment sizes: raw/synthetic
**n = m = 1000**, adversary reference **l = 10,000**, **10 shadow models**; DP models tested at
**ε = 0.1** (and ε = 1, 10 in the tradeoff study). Outliers hand-picked (rare categories or values
outside the 95% quantile). *(Note: their Adult is described as ~45,222 records in the appendix — NOT
48,842; Antigravity got this wrong.)*

**E. Results & findings.** Privacy gain is **disparate** (outliers stay vulnerable, PG far below 1)
and **unpredictable** (which records leak varies by model and feature set). Headline: **PrivBay &
PATEGAN at ε=0.1 gave some outliers PG < 0.1, violating Yeom's bound PG ≥ 0.89 for ε=0.1.** Root
cause: their implementations **learned attribute metadata (numeric ranges, categorical domains)
directly from the raw data** — outside the DP guarantee — so a target's rare value shifted the output
detectably. After patching (metadata supplied as an independent public input), most outliers were
back within the DP bound. Utility: DP synthetic data cost ~10 accuracy points vs raw even at ε=10.

**F. Relevance to SynthProof — a direct precursor to D1 and to your threat model.**
- **Their DP-violation IS your D1/domain problem.** "Implementations learn the domain/ranges from
  private data, breaking DP" is exactly what you found in AIM (`known_total=n`) and what the
  release-boundary's domain-source rule addresses. Cite P1 as the empirical precedent; your
  `boundary-audit` + domain-source field is the *systematic* fix they applied ad hoc.
- **Same threat model:** adversary sees only the shipped synthetic dataset — identical to yours.
- **Same benchmark (Adult)** → comparison feasible (their MIA advantage vs your MIA-AUC / audited ε).
- **What they did NOT do:** no signed artifact, no document-only checker, no operating-range report;
  their fix required a disjoint public dataset most curators don't have — your data-blind boundary
  approach sidesteps that.
- **Borrow/cite:** their shadow-model MIA + F_Hist/F_Corr feature sets underpin our membership
  auditor; their "outliers leak most" motivates canary design.
- **Viva soundbite:** *"Stadler et al. proved synthetic data leaks membership for outliers and that DP
  generators silently broke DP by reading the data domain — the exact class of bug our release
  boundary and D1 fix are built to catch and certify."*

**G. Citations to chase:** Yeom et al. (membership bound), Shokri et al. (shadow models), PrivBayes
[71], PATE-GAN [32], DataSynthesizer [50].

---

## P2 — Annamalai, Ganev & De Cristofaro, *"What do you want from theory alone?" Experimenting with Tight Auditing of DP Synthetic Data Generation* (USENIX Security 2024, arXiv:2405.10994) — CLAUDE VERIFIED

**A. Identity & framing.** UCL / Hazy / UC Riverside (the Ganev cluster). Type: **empirical DP
auditing of mechanisms/implementations**. Thesis: *bugs make real DP-SDG leakage higher than the
theory; audit them by a distinguishing game + MIA, and see how tightly empirical ε can match
theoretical ε.* Gap: prior black-box, average-case audits give **loose** estimates.

**B. What they did.** First large-scale audit of **6 DP-SDG implementations** — PrivBayes×2
(DataSynthesizer, Hazy), MST (SmartNoise), DPWGAN×2 (NIST, Synthcity). Craft **implementation-specific
worst-case datasets**; introduce the **first white-box MIAs against PrivBayes and MST**. DP defined
both **add/remove (unbounded)** and **edit (bounded)**; audit via the (ε,δ) privacy region and
**µ-GDP**, with **Clopper-Pearson** CIs.

**C. How they did it.** Distinguishing game on fixed neighbours D/D′; MIA outputs a score; false-pos/
false-neg rates → empirical **ε_emp** (Eq. 1) or via **µ-GDP** (Eq. 2–3). Threat models escalate:
**black-box → passive white-box → active white-box** (canary gradients). Key concept: **"maximum
auditable ε"** — even a perfect adversary is capped by the CI, so a fixed number of trials bounds the
largest ε you can measure.

**D. Datasets.** **Adult** and **SF Fire** (both overlap our set); plus **hand-crafted worst-case
tables** designed to maximise leakage. Metric: **ε_emp vs theoretical ε**.

**E. Results & findings.** (1) **Black-box MIAs are severely underpowered** — e.g. **MST at ε=4:
black-box ε_emp = 0.00 (meaningless) vs white-box ε_emp = 3.10.** (2) Tightness is
implementation-dependent (PrivBayes/MST need passive white-box; DPWGAN needs active). (3) **DP
violations in 4 of 6 implementations** (Table 1) — mostly **"learning metadata directly from the
input"**; plus a **new violation in the NIST DPWGAN (early stopping)** and **PRNG reuse in Synthcity
DPWGAN**.

**F. Relevance to SynthProof — grounds two of our pillars AND our honesty caveat.**
- **"Maximum auditable ε" IS our audit ceiling.** This paper is the citation for why we report a
  ceiling beside ε_audited (also named "maximum auditable epsilon" here). Use it in §IX.
- **Explains why our audited ε = 0.000 is LOOSE, not "safe".** Our canary auditor is a *black-box*
  MIA — exactly the class they show yields ε_emp ≈ 0.00 even when true ε = 4. So our bounded-negative
  and 0.000 must be stated as *black-box-loose*; P2 is the honest citation for that limitation.
- **Their "metadata learned from input" violations (4/6)** reinforce your D1/domain thesis — a whole
  cluster of shipped DP tools break DP the same way.
- **Their DPWGAN "PRNG reuse" violation** rhymes with your D5 seed-replay finding (randomness
  handling breaks releases).
- **What they did NOT do:** they audit the *mechanism/implementation* (need code, model internals,
  worst-case data); you audit the *shipped document* (no data, no code). Complementary layers — cite
  them as the mechanism-side audit that your artifact-side audit sits beside.
- **Same benchmark (Adult).** **Viva soundbite:** *"Annamalai et al. show black-box audits of DP
  synthesizers read ε≈0 even when the true ε is 4 — which is exactly why we report our audited 0.000
  next to its 2.97 ceiling instead of calling it private, and why we don't overclaim our null."*

**G. Citations to chase:** Nasr et al. (auditing/GDP), Houssiau (threat models), Jagielski/Steinke
(one-run auditing), MST [43], PrivBayes [75].

---

## P4 — Ganev, Annamalai, Mahiou & De Cristofaro, *Understanding the Impact of Data Domain Extraction on Synthetic Data Privacy* (ICLR 2025 SynthData workshop, arXiv:2504.08254) — CLAUDE VERIFIED

**A. Identity & framing.** UCL / SAS / UC Riverside (Ganev cluster). Type: **preprocessing privacy
audit**. Thesis: *how you define the data DOMAIN (column min/max, categories) decides whether a
DP synthesizer is actually private* — and the common practice of reading the domain from the input
data silently breaks end-to-end DP.

**B. What they did.** Compare **three domain strategies**: (1) **provided** (from public data), (2)
**extracted directly from input** (no DP — what many libraries do), (3) **extracted with DP**. Across
2 generators (PrivBayes, MST) and 4 DP discretizers (uniform, quantile, k-means, PrivTree). Threat:
GroundHog MIA on a worst-case outlier that sits outside the others' domain.

**C. How they did it.** GroundHog shadow-model MIA (Stadler): pick the furthest outlier target,
train **200 shadow models** with/without it, extract F_naive statistical features from the synthetic
output, classify, report **AUC**. Settings: ε=1 preprocessing (split domain+discretization), ε=1
model (δ=1e-5 for MST), 20 bins. Domain-DP via Desfontaines/OpenDP noisy-histogram bounds.

**D. Datasets.** **Wine Quality** (4,898 rows, 11 continuous attributes) — we have it. Role: MIA
target substrate. (Small on purpose — this is a mechanism/preprocessing probe, not a benchmark sweep.)

**E. Results & findings.** **Extracting the domain from the input → MIA AUC ≈ 1.0 (near-perfect
attack), regardless of discretizer or model — end-to-end DP is broken.** Provided or DP-extracted
domain → AUC ≈ random, even at ε up to 100. Striking secondary finding: **GroundHog's success is
mostly due to domain extraction, not the model itself** (an in-domain outlier stays safe). DP domain
extraction "could address many previously identified DP vulnerabilities in open-source libraries."

**F. Relevance to SynthProof — the external proof that your domain-source rule matters.**
- **This is exactly D1 generalised.** Your D1 was AIM using the private row count uncharged; P4 shows
  the *whole domain* (ranges, categories) read from private data breaks DP across libraries and is
  often the *dominant* leak. Your **`domain_source` field + release-boundary rule** ("domain must be a
  public declaration, a charged output, or labelled") is the artifact-level fix P4 argues for.
- **boundary-audit can check it:** a sheet whose `domain_source` = "extracted from data (uncharged)"
  is a flaggable leak — a concrete RB check motivated directly by P4.
- **Same cluster runs P2/P5/P6** — position as complementary: they prove the leak in the mechanism;
  we make the domain provenance a checkable field in the shipped document.
- **Dataset:** Wine (we have it); metric MIA AUC → comparison feasible.
- **Viva soundbite:** *"Ganev et al. show that reading a column's min/max from the private data — which
  most libraries do — breaks DP and lets an attacker win with AUC≈1; our release boundary forces the
  domain to be declared or charged, and our linter flags it when it isn't."*

**G. Citations to chase:** GroundHog/Stadler [P1], PrivBayes, MST/Private-PGM [P8], Desfontaines
domain-DP, Meeus et al. (vulnerable-record identification).

---

## P5 — Ganev, Annamalai, Mahiou & De Cristofaro, *The Importance of Being Discrete: Measuring the Impact of Discretization in End-to-End DP Synthetic Data* (ACM CCS 2025, arXiv:2504.06923) — CLAUDE VERIFIED

**A. Identity & framing.** UCL / SAS / UC Riverside (Ganev cluster). Type: **preprocessing measurement
study (utility + privacy)**. Thesis: *discretization (binning continuous columns) is an overlooked
step that strongly affects both utility and end-to-end DP; the domain/bins are usually inferred from
the data, which can break DP.*

**B. What they did.** Build DP versions of 3 discretizers (uniform, quantile, k-means) + reimplement
**PrivTree**; measure across **6 marginal models** (dp-synthpop, PrivBayes, MST, RAP, GEM, **AIM**) on
**3 datasets + 5 controlled 1-D distributions**; study the optimal bin count; and (RQ4) how domain
extraction affects privacy. Massive scale: **~300,000 discretizers, ~200,000 models fit.**

**C. How they did it.** Integrate each discretizer into an end-to-end DP pipeline; DP domain bounds via
Desfontaines/OpenDP; sweep bin counts; utility = how well marginals/distributions are captured;
privacy via MIAs (incl. GroundHog). DP defined as differing in a single record; ε=1 default.

**D. Datasets.** **Adult (48,842), Gas (36,733), Wine (4,898)** — we have all three — plus **5
controlled synthetic 1-D distributions** (varying modality/skew). Preprocessing: the paper's whole
subject — binning strategies + DP domain extraction.

**E. Results & findings.** Utility follows an **inverted-U in #bins**; optimizing discretizer+bins
improves utility **9.28–43.54%** (≈30% avg) over the default (uniform, 20 bins); **PrivTree best**.
Crucially (RQ4): **non-private domain/discretization → MIA success ≈ 100%; DP discretization drops it
to ≈50% (near-random) at ≈4% utility cost.**

**F. Relevance to SynthProof — completes the "preprocessing audit" map you slot into.**
- **The Ganev cluster has now audited two preprocessing steps — domain extraction (P4) and
  discretization (P5) — for DP leakage. The missing-data handling step is the one they leave
  unaudited; that is exactly your imputation audit's contribution.** This is the cleanest way to
  position your negative result: same subfield, the next unexamined step.
- Reinforces the boundary thesis: uncharged preprocessing (reading domain/bins from data) breaks DP;
  your release boundary makes preprocessing provenance a charged/declared/labelled requirement.
- **Same datasets (Adult/Gas/Wine) and includes AIM** — direct comparability.
- **What they did NOT do:** ship a signed, checkable artifact; theirs is a utility+leak measurement.
- **Viva soundbite:** *"Ganev et al. audited discretization and domain extraction as DP-breaking
  preprocessing steps; we audit the one they didn't — missing-data handling — and put all of it inside
  a checkable release boundary."*

**G. Citations to chase:** PrivTree [Zhang 2016], AIM/MST/PrivBayes/RAP/GEM, Desfontaines domain-DP,
their own P4 (domain) and P2 (auditing).

---

## P6 — Ganev, Nazari, Davison, … & De Cristofaro, *SMOTE and Mirrors: Exposing Privacy Leakage from Synthetic Minority Oversampling* (ICLR 2026, arXiv:2510.15083) — CLAUDE VERIFIED

**A. Identity & framing.** SAS / UCL / UC Riverside (Ganev cluster). Type: **privacy attack on a
preprocessing/oversampling technique**. Thesis: *SMOTE — the near-ubiquitous class-imbalance fix — is
inherently non-private; standard privacy checks miss the leak, and geometric attacks recover minority
records almost perfectly.*

**B. What they did.** First systematic privacy study of SMOTE. Show naive checks (distinguishing,
distance-to-closest-record/DCR) detect nothing; instantiate a real MIA (first time on SMOTE); then
build two **novel geometric attacks — DistinSMOTE** (real-vs-synthetic in augmented data) and
**ReconSMOTE** (reconstruct real minority records from synthetic data) — with theoretical guarantees.

**C. How they did it.** Exploit SMOTE's interpolation geometry (a synthetic point lies on a segment
between two real minority neighbours). Assumptions: access to a single augmented/synthetic dataset +
knowledge that SMOTE made it. Complexity O(n²d + n(kr)²). Metrics: precision/recall, MIA AUC.

**D. Datasets.** **8 standard imbalanced sets** (ecoli, abalone, car-eval, solar-flare, yeast,
mammography, …) plus **cardio, churn, higgs, creditcard, miniboone** — we have all of them now.
Imbalance ratio r and #neighbours k are the key knobs.

**E. Results & findings (Table 1).** Naive distinguish precision **0.01**, naive DCR **0.16** — both
miss the leak entirely. MIA AUC **0.68** (augmented) / **0.93** (synthetic). **DistinSMOTE precision/
recall = 1.00**; **ReconSMOTE perfect precision, recall → 1 at imbalance ratio r ≥ 20**. Training a
classifier on augmented (vs real) data raises MIA AUC by **17%**. Conclusion: SMOTE is fundamentally
non-private; minority records are most exposed; **DCR is an unreliable privacy metric.**

**F. Relevance to SynthProof — validates your audit methodology and your kNN-imputation risk.**
- **Direct support for your sanity-gate design.** P6's headline is that *naive privacy metrics
  underestimate leakage; you need a real MIA and must verify it can see a leak.* That is exactly why
  your imputation audit **sanity-gates** the auditor (plant a leak, confirm it's caught) before
  trusting a null. Cite P6 as the reason a bare "no leak" is untrustworthy.
- **Your kNN imputation arm (A4) is geometrically SMOTE-like** (interpolate/borrow from nearest
  neighbours). P6 proves that family can leak badly — so your finding that A4 did *not* leak above the
  charged baseline is a genuine, non-trivial negative (you tested a real, demonstrated risk).
- **Preprocessing-audit map:** P4 domain, P5 discretization, **P6 oversampling** — your **missing-data
  handling** is the remaining unaudited step. Together they define the subfield you contribute to.
- **What they did NOT do:** audit missing-data imputation; no artifact/document-level check.
- **Datasets:** all present; metric MIA AUC / reconstruction precision.
- **Viva soundbite:** *"Ganev et al. show SMOTE leaks minority records almost perfectly and that DCR
  misses it — which is why our imputation audit uses a sanity-gated MIA, not a naive metric, and why a
  clean result on our SMOTE-like kNN arm actually means something."*

**G. Citations to chase:** SMOTE [Chawla 2002], DCR critiques, Kotelnikov TabDDPM, Shokri MIAs.

---

## P10 — Dibia, Lu, Bhattacharjee, Near & Feng, *"We Need a Standard": Toward an Expert-Informed Privacy Label for Differential Privacy* (PoPETs 2026, arXiv:2507.15997) — CLAUDE VERIFIED — **★ LEAD POSITIONING PAPER**

**A. Identity & framing.** University of Vermont (Joseph Near's group). Type: **qualitative interview
study + standards proposal**. Thesis: *real DP deployments under-disclose their guarantees, causing
misunderstanding even among experts; the field needs a standardized "privacy label for DP."*

**B. What they did.** Semi-structured interviews with **12 DP experts (P01–P12)**; RQ1 = which
parameters to disclose, RQ2 = how to present them. Output: an **expert-informed prototype DP label**
(aimed at technical users, not end-users).

**C. How they did it.** Purposive expert sampling across academia/industry/government; qualitative
coding of interviews to build consensus; a two-layer prototype label.

**D. Datasets.** **None** — it's an interview study. "Data" = the 12 experts' transcripts.

**E. Results & findings.** **Nine key parameter categories (Table 1):** (1) privacy parameters (ε,δ),
(2) **unit of privacy**, (3) utility information, (4) mechanism used, (5) algorithm hyperparameters,
(6) deployment model, (7) **empirical privacy metrics**, (8) privacy interpretation/semantics,
(9) other parameters. Strong consensus on ε/δ/unit-of-privacy; limited consensus on "normal ranges."
**The "privacy theater" finding (verbatim):** expert **P11** warned that empirical metrics "focus on
average-case performance, potentially downplaying worst-case attack scenarios" — *"Even if all of your
per-attribute privacy budgets are big, every theoretical guarantee you can provide is almost trivial.
Then you need empirical attacks to show that you did something useful."*

**F. Relevance to SynthProof — this is the paper you LEAD with; you fill its two open gaps.**
- **Field-for-field overlap with your Privacy Data Sheet:** their 9 categories ≈ your PDS fields
  (ε/δ, unit_of_privacy/contribution_bound, evaluation, mechanism, hyperparameters, deployment model,
  audited ε/attacks, plain-statement/membership-odds, domain/fingerprint). This is your strongest
  external validation that you built the right artifact — an expert panel converged on your field set.
- **Gap 1 they leave open — NO signing/attestation.** Their label is a human-facing prototype; verified
  no cryptographic signing is proposed. **You add Ed25519 signing + machine-checkability
  (`boundary-audit`, Croissant).**
- **Gap 2 they leave open — NO way to report an empirical metric's LIMITS.** Their own expert (P11)
  names this hazard as "privacy theater," but the proposal has no mechanism. **Your `audit_ceiling` /
  operating-range reporting is exactly that mechanism** — you found it the hard way (audited ε=0.000
  vs ceiling 2.97). Quote P11 directly in your intro.
- **One category to make sure you carry: "deployment model"** (Dibia 4.1.6) — confirm your PDS has it.
- **What they did NOT do:** sign, make machine-checkable, or report measurement limits — your three
  contributions map onto exactly these.
- **Viva soundbite:** *"Dibia et al. asked 12 experts what a DP release should disclose and got almost
  exactly our Privacy Data Sheet — but their label isn't signed, isn't machine-checkable, and, as their
  own expert warned, has no way to flag 'privacy theater'. We sign it, make a linter check it, and
  report the audit's operating range."*

**G. Citations to chase:** Dwork et al. Epsilon Registry, Desfontaines deployments list, Oblivious/
OpenDP registry, Cummings et al. (DP communication), Kelley et al. (privacy nutrition labels).

---

## P11 — Song, Sarathy, Shoemate & Vadhan, *"I inherently just trust that it works": Investigating Mental Models of Open-Source Libraries for DP* (CSCW 2024, arXiv:2410.09721) — CLAUDE VERIFIED — **★ THE PREMISE**

**A. Identity & framing.** Harvard / Northeastern (the **OpenDP** team). Type: **qualitative HCI /
mental-models study**. Thesis: *there is a gap between how DP-library developers think and how users
think; users trust the libraries implicitly, so the libraries struggle to keep implementations
rigorous while staying usable.*

**B. What they did.** Two-stage study: **formative interviews with 5 DP-library developers** +
**user studies with 17 data analysts** (little DP-programming experience), on **Diffprivlib** and
**OpenDP**. Analyse developer conceptual models vs user mental models; give library-design
recommendations.

**C. How they did it.** Qualitative coding of interviews + task-based user studies (analysts asked to
compute DP statistics and reason about the results).

**D. Datasets.** **None** — interview/user study; "data" = 5 developers + 17 analysts.

**E. Results & findings.** The title says it: analysts **"inherently just trust that it works"** — they
do **not verify** DP guarantees. Two concrete implementation traps they surface: (1) **bounds** — a DP
mean without user-specified bounds: Diffprivlib emits a *privacy warning* (and uses data-derived
bounds → a leak), while OpenDP throws a *type error* forcing the user to supply them (Fig 1);
(2) a **`nanmean` sensitivity flaw** — Diffprivlib's DP nanmean ignores nulls when averaging but uses
the **total count including nulls** for sensitivity, so the noise is miscalibrated.

**F. Relevance to SynthProof — the missing premise under your whole project.**
- **This is the citation that justifies the project's existence.** If practitioners don't verify and
  trust implicitly, then a release resting on one library rests on its unexamined bugs → you need an
  automatic, data-blind checker (`boundary-audit`) and a second accountant (differential accounting).
  Use P11 in your intro's motivation (pairs with P2/P3 which show the bugs are real).
- **Their "bounds from data" trap = the domain problem again** (D1/P4) — a fourth independent sighting
  of "reading structure from the private data breaks DP."
- **Their `nanmean`/null-handling bug ties to YOUR missing-data audit.** A DP statistic that mishandles
  nulls miscalibrates sensitivity — the preprocessing-boundary hazard your imputation work audits.
  Nice, concrete bridge between P11 and your Section on imputation.
- **What they did NOT do:** build any tool — it's a diagnosis of blind trust. Your signed sheet +
  linter is the response.
- **Viva soundbite:** *"Song et al. found data analysts 'inherently just trust that it works' and never
  verify DP — that blind trust, plus the real library bugs others document, is exactly why we ship a
  signed, machine-checkable Privacy Data Sheet instead of asking anyone to take the release on faith."*

**G. Citations to chase:** OpenDP, Diffprivlib, Tumult Analytics; Cummings et al. (DP communication);
Dwork Epsilon Registry.

---

## P9 — Abowd et al., *The 2020 Census Disclosure Avoidance System TopDown Algorithm* (Harvard Data Science Review 2022, arXiv:2204.08986) — CLAUDE VERIFIED — **★ REAL-DEPLOYMENT CASE STUDY**

**A. Identity & framing.** U.S. Census Bureau + Duke / Penn State / Tumult Labs. Type: **production DP
systems paper** (a real, nationwide deployment). Thesis: describe the maths + testing of the TopDown
Algorithm (TDA) that applied DP to the entire 2020 US Census.

**B. What they did.** TDA ingests the edited 2020 Census, produces **noisy "measurements"** under
**zero-Concentrated DP (zCDP)** with **discrete Gaussian** noise, then **post-processes the
measurements together with "invariants"** to output a Microdata Detail File (one record per person and
housing unit) → the redistricting summary file. Replaces the pre-2020 record-swapping method.

**C. How they did it.** zCDP accounting (Bun-Steinke; implies (ε,δ)-DP) + discrete Gaussian (Canonne
et al.); noisy measurements over a nationwide geographic spine; post-processing (NNLS / integer
programming) to nonnegative, consistent microdata. Neighbours differ on a single entry. Justify DP
over suppression: non-degradation under post-processing, bounded composition, resistance to
Dinur–Nissim reconstruction.

**D. Datasets.** The confidential **2020 Census Edited File** (~331M records) and 2010 CEF/HDF
demonstration data; **Title-13 restricted — not obtainable** (our litsurvey marks P9 RESTRICTED).
Role: the sensitive input; not reproducible outside a federal RDC.

**E. Results & findings.** **Invariants** are "statistics that the Census Bureau has determined, as a
matter of policy, to **exclude from the privacy-loss accounting**" — e.g. **state population totals**
(aggregation only, *no noise*), plus housing/MAF operational constraints, edit constraints and
structural zeros, all "passed to post-processing without noise injection." So a real, high-stakes
deployment deliberately ships quantities that are **outside ε (effectively ε=∞)**.

**F. Relevance to SynthProof — your canonical case study, with an honest nuance.**
- **Invariants ARE the release boundary in production.** The Census ships exact state totals + structural
  constraints outside the DP budget — the textbook real example of "the released artifact contains
  quantities ε doesn't cover." Lead your case-study section (research/16) with it.
- **Honest nuance (keep it):** the Census *declares* its invariants in prose/policy — so they are a
  *declared* out-of-ε quantity (rule #2 of your boundary), **not a hidden leak.** Your contribution is
  that this disclosure is **prose, not a machine-checkable field** — no standard expresses "which
  fields are outside ε" so a validator can enforce it. That's precisely the P5–P11 gap in your
  standards table (§15) and what `boundary-audit` + the PDS add.
- **No same-dataset comparison** (data is Title-13 restricted) — qualitative case study only; do not
  claim to have run on Census data.
- zCDP/discrete-Gaussian is the same accounting family your AIM path uses.
- **Viva soundbite:** *"The 2020 Census is the proof this matters at scale: it publishes state totals
  and structural constraints outside the privacy budget. They document that in prose as policy — we
  make 'which fields are outside ε' a signed, machine-checkable field instead."*

**G. Citations to chase:** Bun & Steinke (zCDP), Canonne et al. (discrete Gaussian), Dinur & Nissim
(reconstruction), JASON report, Ashmead/Kifer TDA papers.

---

## ✅ Verification status — ALL 11 papers now Claude-verified
Every paper P1–P11 has been read from its PDF and written up above with the §0 schema and verbatim
evidence. **The Antigravity batch in `research/deep_analysis/*.md` is superseded and should not be
used** — it contained a full fabrication (P3), a wrong dataset count (P1), and a mischaracterisation
(P2). This file (`18_deep_paper_analysis.md`) is the authoritative deep analysis.

## ⚠️ (historical) Antigravity batch errors found during verification (`research/deep_analysis/*.md`)
Antigravity produced P1–P11 files, but a spot-check found **fabrication and errors — do NOT merge
them unverified**:
- **P3 — FABRICATED** (Antigravity described a nonexistent "multi-table relational DP" paper; the
  real P3 is the grey-box library audit above). Antigravity's `deep_analysis/P3.md` is discarded.
- **P1 — wrong Adult row count** (Antigravity 48,842; paper says **45,222**).
- **P2 — mischaracterised** as "GroundHog MIA"; it is a **tight-auditing** paper (GDP/canaries;
  "tight" ×49, GroundHog ×1).
- **Others (P4,P5,P6,P9,P10,P11) — treat as UNVERIFIED drafts** until Claude reads the PDF and
  checks quotes. P9 also over-claims a "same-dataset comparison on ACS" (Census ≠ ACS).

**Verified by Claude so far (trust these):** P7, P8, P3. **Still to verify/redo by Claude:** P1, P2,
P4, P5, P6, P9, P10, P11 — I will read each PDF and rewrite, rather than trust the batch.
