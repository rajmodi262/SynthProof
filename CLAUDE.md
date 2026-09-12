# SynthProof — running research context

Working memory for the novelty-assessment protocol. Decisions, open questions, current phase.
Kept short on purpose; detail belongs in `research/`.

## Current phase

**Phases 1–3 COMPLETE as of 2026-08-23.** Families B and D: `research/PHASE2_INTERIM.md`.
Families A, C, E, F, G, H: `research/PHASE2_COMPLETE.md`. **The verdict is issued** in
`research/08_novelty_verdict.md` — read that first; it supersedes the interim kill tables.

**Verdict in one line: eight claims dead, three narrow survivors, and the position is
INTEGRATION not invention.**

**The integration MVP is BUILT as of 2026-08-23** — `synthproof/frontier/croissant.py`, 43
tests, and the **official MLCommons validator accepts our record with 0 warnings**. See
`research/08_novelty_verdict.md` §4.1. This is the one thing that turns "integration" from a
paragraph into something an examiner can run, and the three defects found while building it
(a correctly-signed record that can still show a false epsilon · Croissant's mandatory
FileObject checksum · the validator recursing on an empty JSON object) are better viva
material than the feature itself. **Do not describe Croissant as future work anywhere** —
`docs/thesis/ch08-evidence.md` line 81 still does, and is now stale.

**The single most important citation is Dibia, Lu, Bhattacharjee, Near & Feng, arXiv 2507.15997
(2025)** — an expert-elicited nine-category privacy label for DP that overlaps the Privacy Data
Sheet almost field for field. It kills "we invented the concept" AND is the strongest external
validation the project has. Critically it proposes **no signing** and **no standard for
reporting the limits of an empirical privacy metric** — an omission one of their own experts
called **"privacy theater"**. Those two gaps are exactly what our Ed25519 signature and
`audit_ceiling` fill. Lead with this. (The ceiling-in-the-artefact convention is a transfer
of limit-of-detection reporting from analytical chemistry — MIQE 2.0, Bustin et al.,
*Clinical Chemistry* 2025;71(6):634–651 — not our invention. See
`docs/MEASUREMENT_CONVENTIONS.md`.)

**Second: Song, Sarathy, Shoemate & Vadhan, CSCW 2024 (arXiv 2410.09721)** — practitioners do
NOT verify DP guarantees, they trust implicitly. That is the missing premise under the whole
project and the direct justification for differential accounting.

**Survivors, all narrow, none to be called novel without the caveat:**
S1 reporting the measurement's operating range in the artefact (`CONFIDENCE: med-high`) ·
S2 signing the privacy claim (`med`, and it is engineering novelty not science) ·
S3 data-blind refusal (`med` — **state as UNREFUTED, never novel**; the SDC Handbook 403'd and
family G is the weak point).

## Standing rules for this protocol

1. **No citation without a fetched URL/DOI/arXiv ID.** Anything recalled from memory is marked
   `[UNVERIFIED]` and no argument may rest on it.
2. **No fabricated numbers.** Copy from source or write `[NOT REPORTED]`.
3. Prefix reasoning with `INFERENCE:` and uncertainty with `CONFIDENCE: low/med/high + why`.
4. Adversarial by default — try to kill each idea before recommending it.
5. Checkpoint findings to files before context runs short.
6. Stop at each phase boundary.
7. If a search tool is unavailable, say so. Never simulate a result.

## Key state (observed 2026-08-21, from the repo not from memory)

- **H1**: supported on structure/utility (AIM corr-err 0.0078 vs independent 0.0947 at eps=8,
  non-overlapping CIs). **Privacy half disqualified** — auditor ceiling ~2.7 at m=60 vs
  eps_proved 7.36.
- **H2**: not supported at this scale; direction weakly consistent; instrument-limited.
- **H3**: run (uniform vs utility-weighted allocation).
- **Detection floor measured**: verbatim leak detected at m=10; 25% leak needs m=400; 5% and 1%
  undetected at m<=800; 0% control correctly silent.
- **Auditor ceiling measured**: max reportable eps_audited is bounded by canary count alone —
  5.38 at m=800 even with a perfect adversary.
- Five self-audit defects found and fixed; two result documents retracted in-repo.

## Novelty status — VERIFIED kills as of partial Phase 2

- **C1 dual-sided assurance — KILLED** by Annamalai/Ganev/De Cristofaro, USENIX Sec 2024
  (arXiv:2405.10994).
- **C2 budget-charged profiling — KILLED** by Ganev et al. Apr 2025 (arXiv:2504.08254).
- **F2 auditor ceiling — KILLED as maths** (one-line corollary of Steinke et al. Thm 2.1), and
  **severely wounded as practice** by Ganev/Annamalai/Kulynych Apr 2026 (arXiv:2604.18352), who
  get TIGHT audits on MST and AIM with a GDP/f-DP estimator where SynthProof got 0.000.
- **F3 self-audit defects — KILLED** by Cebere et al. Feb 2026 (arXiv:2602.17454): 12 libraries,
  13 violations, released package.
- **C3 signed cross-release ledger — HEAVILY CROWDED.** PrivateKube (OSDI'21), Cohere, DPack
  (EuroSys'25), DPolicy. Blockchain DP-cost ledgers exist. The signing gap is UNVERIFIED —
  fetch 2006.04693 before claiming it.
- **C4/H2 subgroup — ADJACENT PRIOR WORK.** Ganev, Oprisanu & De Cristofaro, ICML 2022
  ("Robin Hood and Matthew Effects") is disparate impact on *accuracy*; H2 asks about *leakage*.
  That distinction is the only thing separating H2 from a 2022 ICML paper — state it precisely.
- **F1 calibration — QUALIFIED.** The phenomenon is documented (Ngong et al., SOUPS 2024;
  SoK 2412.16825). The specific quantified instance was not found, on ONE pass. Weak negative.
- **NEW — release-gating is CROWDED.** Five Safes + SACRO (arXiv 2212.02935v3) is production
  practice in UK TREs since 2022. But SACRO **reads output values** and **does not autonomously
  refuse**; our preflight reads only schema + row count and does refuse. That difference is the
  claim, and it is much stronger stated against SACRO than in a vacuum.
- **NEW — machine-checkable release artefacts are CROWDED.** Croissant (MLCommons, a NeurIPS
  submission requirement), MRM3 (MobiSys'25), Laminator (CODASPY'25, TEE-attested property
  cards — which attests *execution*, the thing our README concedes we cannot).

**The recommended reframing (auditing working range) did not survive.** Do not build on it.

**The ceiling is now attributed in the code.** `audit/steinke.py`, `results/AUDITOR_COMPARISON.md`
and `results/DETECTION_FLOOR.md` name it a corollary of Steinke Thm 2.1 / Eq. (3), verified
bit-identical to `max_provable_epsilon` at r = 10/60/100/400/800 and pinned by
`tests/test_audit_power.py`.

**Three narrow differences survived every family** — candidates for Phase 3 to TEST, not claims:
data-blind refusal · cryptographic signing of the privacy claim · reporting the measurement's
own operating range inside the artefact.

**The direction the evidence actually supports: integration, not invention.** Emit the Privacy
Data Sheet as a **Croissant extension** and adopt SACRO's refusal vocabulary. Nobody has
connected DP accounting to the standards the field uses, and no author cluster is racing us
there.

**Strategic fact:** four of six kills come from one author cluster (Ganev, Annamalai,
De Cristofaro, Kulynych) that is running this exact programme ~2 years ahead.

## Blocking questions (asked, unanswered)

Q1 target outcome/venue · Q2 deadline · Q3 is novelty required or desired · Q4 are the four
synopsis contributions locked · Q5 compute ceiling · Q6 ACS availability · Q7 reframe appetite.

## Open questions — updated 2026-08-23

**Resolved:**
- *Is the ceiling inequality stated as a reporting standard anywhere?* **No standard found.**
  Dibia et al. (2507.15997) propose empirical privacy metrics and explicitly do NOT propose any
  way to report their limits. That is S1.
- *Does SDC already have the certificate concept?* **Partly.** SACRO + Five Safes gate releases
  and produce auditable records since 2022 — but SACRO reads output values and does not
  autonomously refuse. That is what leaves S3 standing.

**Still open, and they are the risks to the verdict:**
- The SDC Handbook returned **HTTP 403**. S3 rests on one practice guide and one toolkit paper.
  Read the Handbook before claiming S3 anywhere it matters.
- F1 (calibration gap) was searched via a web index, not the actual issue trackers. **Do not
  claim F1.**
- Saturation was not reached in any family run on 2026-08-23. A second pass on G or E could
  kill S1 or S3.
