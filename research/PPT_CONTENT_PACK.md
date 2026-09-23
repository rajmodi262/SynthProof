# SynthProof — PPT Content Pack (pre-build gather)

> Everything the guide asked for, drafted and grounded in real results. We assemble the
> deck from this pack. Numbers pulled from `results/full/*.json`, `research/wild_audit/`,
> `research/21_real_dp_registry_case_study.md` on 2026-09-23. Nothing here is fabricated.

Legend of what maps to which guide point is in each section header.

---

## ITEM 1 — Problem-size numbers  (guide §1, §29: "what %, how many datasets/people")
Goes on the **Problem Statement slide (S3)** as a hard-evidence band.

- **290** unique synthetic datasets examined on Hugging Face (310 repos, forks de-duped).
- **0 / 290** disclose *any* DP guarantee — 0 name a mechanism, 0 state an ε, 0 state δ or the
  neighbour relation. The DP-release ecosystem simply does not ship a checkable guarantee.
- **2 / 290** publish the generation **seed** — the reproducibility habit that DP forbids
  (measures how normalised the risky practice is).
- Even among **12 of the most prominent *real* DP deployments** (Apple QuickType/Emoji,
  Google Mobility/Gboard, US Census 2020/OnTheMap, Israel MoH birth data, …):
  - 12/12 document ε and the mechanism (in prose), BUT
  - **0 / 12 are tamper-evident** (no signature), and
  - **0 / 12 are machine-checkable** (no artifact a stranger can verify).

**One-liner for the slide:** *"Across 290 shared synthetic datasets and 12 flagship DP
deployments, not one ships a proof you can check. 100% of the time you must trust the maker."*

---

## ITEM 2 — Objectives slide  (guide §21: NEW — examiner WILL ask; currently missing)
New slide, place **after Problem (S3), before Requirements (S4)**. Each objective is
checkable and tied to a measured outcome.

| # | Objective (what we set out to do) | Measurable outcome (status) |
|---|---|---|
| O1 | **Define the DP "release boundary"** — exactly which shipped fields are / are not covered by ε | Findings D1–D5: seed, row-count n, unkeyed hash, eval-on-real, domain/discretization identified as out-of-ε leaks ✅ |
| O2 | **Ship a signed, machine-readable Privacy Data Sheet** | Croissant 1.1 extension + Ed25519 signature; MLCommons validator passes with 0 warnings ✅ |
| O3 | **Build `boundary-audit` — a static, data-blind linter** that flags leaks from the document alone | **14 checks (RB1–RB14)**, incl. multi-table RB11–RB14; runs with no data and no code ✅ |
| O4 | **Audit the preprocessing (missing-data) step** prior work never checked | 6-arm imputation membership audit, sanity-gated; bounded negative result (no leak above baseline) ✅ |
| O5 | **Validate at full scale across domains** (finance + healthcare + census) | 4 datasets, **every row**: Adult, Bank, ACS, Diabetes-130 ✅ |
| O6 | **Quantify the problem in the wild + benchmark our mechanisms vs literature** | 0/290 & 0/12 (Item 1); utility **at par with AIM** on shared datasets (Item 3) ✅ |

**Framing line:** *"Six objectives; every one has a number attached, and every number is reproducible."*

---

## ITEM 3 — Dataset comparison slide  (guide §3,§4,§26,§27: NEW — her #1 repeated ask)
New slide. "The datasets the field uses — and what OUR mechanism gets on the very same
data, every row." Utility = best TSTR-F1 as a % of the real-data (TRTR) ceiling; fidelity =
best correlation error (lower = closer to real).

| Dataset | Domain | Rows (full) | Used before by | Our best utility (% of real-data ceiling) | Best correlation fidelity |
|---|---|---|---|---|---|
| **Adult** | census/income | 30,162 | Stadler '22 · Annamalai '24 · Ganev '25 · Mohapatra · McKenna (AIM) | **92%** (MST) · 81% (AIM) | 0.007 err (AIM) |
| **Bank** | finance | 45,211 | Mohapatra, VLDB '24 | **90%** (AIM) | 0.0009 err (pairwise) |
| **ACS** | census survey | 195,665 | — *(our modern-census add)* | **89%** (MST) | 0.0017 err (pairwise) |
| **Diabetes-130** | **healthcare** | 99,492 | — *(our healthcare add)* | **99%** (MST/AIM) | 0.118 err (MST) |

**Honest reading (put on slide, do NOT overclaim):**
- On the datasets others already used (**Adult, Bank**) we **match the published SOTA (AIM)** —
  our synthetic data is *as useful as theirs*, we do **not** claim a better generator.
- We **extend** to a modern census at **196k-row full scale (ACS)** and to the **one healthcare
  table (Diabetes)** none of these papers combined — up to **99%** of real-data usefulness.
- The genuine edge is not utility — it's that **every one of our releases carries a signed,
  one-click-checkable safety seal; none of theirs can be checked** (0/290, 0/12).

**Supporting privacy number (optional footnote):** membership snoop ≈ **0.5 AUC** (coin-flip);
empirical GDP μ well below the theoretical bound (AIM μ_emp ≈ 0.18 vs implied 0.53 at ε=1).

---

## ITEM 4 — Healthcare dataset (Diabetes-130)  (guide §26: built, missing from deck)
Add to **Spec (S4)**, **Timeline datasets (S5)**, **Results (S8)**, and Item-3 slide.

- **Diabetes 130-US hospitals** (UCI), **99,492 rows** after cleaning, 10 columns; target =
  readmission (binarised: readmitted-early/YES vs NO). This is the **healthcare** dataset the
  guide expected alongside finance.
- Why it matters: healthcare is the motivating story (hospital sharing patient data); now we
  actually test on hospital records, at full scale, with the best utility of all four (99%).
- Everywhere the deck says "Adult, Bank, ACS" → make it "**Adult, Bank, ACS, Diabetes**".

---

## ITEM 5 — Title candidates  (guide §16,§18: current title too jargon-heavy)
Keep the honest positioning (no new privacy theorem). Catchy main line + clear technical
subtitle. Candidates:

1. **"Does Your Synthetic Data Ship With a Receipt?"**
   *A Machine-Checkable Release Boundary for Differentially Private Synthetic Data*  ← recommended
2. **"Sign the Cake, Not Just the Recipe"**
   *A Signed, Data-Blind Audit for What DP Synthetic-Data Releases Actually Ship*
3. **"Trust, but Verify — for Synthetic Data"**
   *A One-Click-Checkable Privacy Label for DP Synthetic-Data Releases*
4. **"SynthProof: Auditing What Actually Ships"**
   *A Machine-Checkable Release Boundary for DP Synthetic Data*
5. **"Beyond the Mechanism"** *(current)* → demote to subtitle; too abstract to lead with.

Recommendation: **#1** — it's a question a non-expert instantly gets, and the subtitle carries
the method. (The guide explicitly wanted "eye-catching + methodology visible.")

---

## ITEM 6 — Publication slide: ONE paper, not two  (guide §33,§34: deck contradicts her)
Replace S9 "TWO PAPERS" with a **single comprehensive paper**. Reason on the slide: the guide
warned that splitting shared content across two papers = self-plagiarism → debarment.

- **One paper**, comprehensive:
  *"[chosen title]: a machine-checkable release boundary for DP synthetic data — with a
  signed Privacy Data Sheet, a 14-check data-blind linter, a preprocessing-leakage audit, and
  a full-scale evaluation across finance, healthcare and census."*
- **Contents (was split, now merged):** release-boundary definition (D1–D5) · boundary-audit
  RB1–RB14 · signed Croissant sheet · missing-data audit · full-dataset evaluation (Item 3) ·
  wild-audit problem evidence (Item 1).
- **Format:** IEEE conference / workshop, double-column, ~8 pp.
- **Target venue (honest):** SaTML 2027 or a PoPETs / TPDP-style privacy venue. There is **no
  legitimate venue that grants acceptance by 22 Oct**; avoid predatory pay-to-publish "deadlines".
- **Before submit:** Turnitin + AI-plagiarism pass (Item 13 — deferred for now per your call).

---

## ITEM 7 — Architecture relabel + RB1→RB14  (guide §11: rename "Release artifact")
Edits to **Architecture (S6)** and **Module Ownership (S7)**.

- Rename the box **"Release artifact"** → **"Shipped release — synthetic table + SIGNED Privacy
  Data Sheet + Croissant"** (self-explanatory at a glance, as she asked).
- Replace **"RB1–RB7"** → **"RB1–RB14"** everywhere (S6 linter box, S7 linter spoke).
- Generators box: list what actually ran — **AIM · MST · independent · pairwise**; mark
  **DP-VAE as planned control** (not a headline result) to stay honest.
- The 14 checks, for the linter spoke / an appendix slide:

| Single-table (RB1–RB10) | Multi-table (RB11–RB14) |
|---|---|
| RB1 seed · RB2 row-count n · RB3 fingerprint (scheme-aware) · RB4 evaluation-on-real · RB5 accountant · RB6 domain source · RB7 contribution bound · RB8 public invariants · RB9 discretization source · RB10 amplification | RB11 relational unit · RB12 FK-degree · RB13 join cardinality · RB14 cross-table fingerprint |

---

## ITEM 8 — Evaluation parameters list  (guide §14: name them as a set after methodology)
Add a compact **"Evaluation Parameters"** block right after methodology/architecture. These are
the axes every result is measured on:

| Parameter | What it measures | Good direction |
|---|---|---|
| **Correlation error** | fidelity — how close synthetic column-relationships are to real | lower ↓ |
| **TSTR-F1 vs TRTR ceiling** | utility — model trained on synthetic, tested on real, vs real-on-real | higher ↑ (→ ceiling) |
| **Proved ε (δ)** | the DP guarantee charged by the accountant | as claimed |
| **Audited ε** | empirical leakage via Steinke canaries, beside its instrument ceiling | ≈ 0 (below resolution) |
| **GDP μ** | Gaussian-DP membership advantage (Ganev/Koskela estimator) | below theoretical bound |
| **MIA-AUC** | can a snoop tell if you were in the data | ≈ 0.5 (coin flip) |
| **boundary-audit RB1–RB14** | document-level leaks in the shipped release | all pass / declared |

---

## Deck order after changes (10 → 12 slides)
1 Title (new title) · 2 Literature scorecard · 3 Problem (+Item 1 numbers) · **3b Objectives (NEW)**
· 4 Requirements (+Diabetes) · 5 Timeline (+Diabetes, one-paper) · 6 Architecture (relabel, RB14)
· 7 Module ownership (RB14) · **7b Dataset comparison (NEW)** · 8 Results (+Diabetes, +eval-params)
· 9 Publication (ONE paper) · 10 Thank you.
