# 18 — Deep per-paper analysis of the literature survey (2026-09-17)

> Purpose: the team's deepest understanding of each surveyed paper — what they did, how, the
> techniques, the datasets and exactly how they were used/modified, the novelty, and (most
> important) how each relates to SynthProof. Read against the actual PDFs in
> `research/litsurvey/literature surveys/`. Standing honesty rules apply: quotes are from the paper;
> where a number is the paper's, it is marked; inferences are labelled `INFERENCE:`.
>
> **Status:** P7 and P8 done here as Claude's verified deep-reads (the quality bar + cross-check
> anchor). P1, P2, P4, P5, P6, P9, P10, P11 are being produced by Antigravity with the schema in
> §0; Claude verifies and merges them into this file. **Never trust an Antigravity row until a
> quote is checked against the PDF.**

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

## ⚠️ Verification status of the Antigravity batch (`research/deep_analysis/*.md`)
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
