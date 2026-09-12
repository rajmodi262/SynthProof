# Phase 2 — COMPLETE

> **Status: all 8 query families have now run.** Families B and D completed on 2026-08-21 and are
> reported in `PHASE2_INTERIM.md`. Families **A, C, E, F, G, H** ran on 2026-08-23 and are
> reported here.
>
> **Ground rules observed.** Every source below was reached by a fetch or a search that returned
> its venue and identifier; none is recalled from memory. Where only an abstract or a search
> result was read, the entry says so. No number appears that was not copied from a source.
>
> **Per rule 6 this document stops at the phase boundary. It does NOT issue a novelty verdict.**
> `08_novelty_verdict.md` remains for the phase that owns it.

---

## 1. What ran

| Family | Guards | Interim status | Now |
|---|---|---|---|
| A — auditing limits | F2 | NEVER RAN | **ran** — §2 |
| B — DP synthetic tabular | C1, H1 | completed | unchanged |
| C — budget accounting | C3 | NEVER RAN | **ran** — §3 |
| D — verifiable DP | C3, R4 | completed | extended — §4 |
| E — transparency artefacts | C1 | NEVER RAN | **ran** — §4 |
| F — subgroup disparity | C4 | NEVER RAN | **ran** — §5 |
| G — SDC / official statistics | C1, C2 | NEVER RAN | **ran** — §6 |
| H — DP implementation correctness | F1, F3 | NEVER RAN | **ran** — §7 |

---

## 2. Family A — auditing limits (guards F2)

**F2 remains KILLED as mathematics, and this run closed it independently.**

The interim report derived the ceiling as a corollary of Steinke, Nasr & Jagielski (2023)
Theorem 2.1 / Eq. (3). On 2026-08-23 that derivation was **executed against our own code**:
setting `v = r` gives `ε_max = log(β^(1/r) / (1 − β^(1/r)))`, and this is **bit-identical** to
`synthproof.audit.steinke.max_provable_epsilon` at r = 10, 60, 100, 400 and 800.

That check is now pinned by `tests/test_audit_power.py::test_the_ceiling_is_the_steinke_corollary_not_our_own_theorem`,
and the attribution is written into `audit/steinke.py`, `results/AUDITOR_COMPARISON.md` and
`results/DETECTION_FLOOR.md`. **The repository no longer presents the ceiling as its own result.**

`CONFIDENCE: high` — this is arithmetic, executed, not argued.

---

## 3. Family C — budget accounting (guards C3)

**C3 (signed cross-release budget ledger) moves from UNRESOLVED to HEAVILY CROWDED.** Budget
management across releases and workloads is a mature systems literature.

| Work | Identifier | What it does |
|---|---|---|
| **PrivateKube** — *Privacy Budget Scheduling* | OSDI '21, [arXiv 2106.15335](https://arxiv.org/abs/2106.15335) | Adds privacy as a **native Kubernetes resource** alongside CPU/GPU/RAM. Introduces Dominant Privacy Fairness (DPF), a DRF variant designed for a **non-replenishable** resource |
| **Cohere** — *Managing Differential Privacy in Large Scale Systems* | [arXiv 2301.08517](https://arxiv.org/pdf/2301.08517) | Benchmarks against PrivateKube as "the state-of-the-art solution for DP resource management across multiple workloads" |
| **DPack** — *Efficiency-Oriented Privacy Budget Scheduling* | EuroSys 2025, [doi 10.1145/3689031.3696096](https://doi.org/10.1145/3689031.3696096) | Budget scheduling optimised for efficiency |
| **DPolicy** | [arXiv 2505.06747](https://arxiv.org/pdf/2505.06747) | Risk management across multiple releases; sequential composition, allocation, risk aggregation |

Separately, **tamper-evident privacy-budget ledgers already exist in the blockchain
literature** — `append-only` hash-chained structures where "each block contains a hash of the
previous block, as well as information about which queries were processed and perturbed results
released", with budget decremented by iterating the ledger.

**What appears to survive:** none of the four systems above was found to **cryptographically
sign** its budget record for verification by a party outside the operator's trust boundary.
`CONFIDENCE: low-med` — the blockchain-based DP cost-management work was seen only in search
results and **has not been fetched**. Anyone claiming the signing gap must read it first.

**What does not survive:** any claim that managing or recording budget across releases is novel.
It is a systems research area with an OSDI paper and a EuroSys paper in it. SynthProof does not
do cross-session enforcement at all — the `ch02` matrix cell was corrected to ✗ on 2026-08-23.

---

## 4. Families D + E — verifiable artefacts and transparency metadata (guards C1)

**This is the second unpleasant surprise, and it is a standards problem rather than a paper.**

| Work | Identifier | Bearing |
|---|---|---|
| **Laminator** — *Verifiable ML Property Cards using Hardware-assisted Attestations* | Duddu, Järvinen, Gunn & Asokan, **CODASPY 2025**, [arXiv 2406.17548](https://arxiv.org/abs/2406.17548) | Makes model cards, datasheets and a novel "inference card" **verifiable via TEE attestation** across training and inference. **Does not address DP or privacy budgets** (checked at abstract/metadata level) |
| **Croissant** | MLCommons; [1.1 released Feb 2026](https://mlcommons.org/2026/02/croissant-1-1-standard/) | JSON-LD metadata standard for ML datasets. Adopted across **hundreds of thousands of datasets** on Hugging Face, Kaggle, OpenML, Google Dataset Search, and a **submission requirement at NeurIPS**. 1.1 adds machine-actionable provenance, structured usage policies for automated enforcement, PROV-O / DUO grounding |
| **MRM3** — *Machine Readable ML Model Metadata* | MobiSys 2025, [arXiv 2505.13343](https://arxiv.org/html/2505.13343v1) | Machine-readable model metadata |

**Two consequences, and the second is actionable.**

1. **"A machine-checkable release artefact" is not novel.** It is a standardised, widely adopted
   space. Laminator additionally does the thing SynthProof's README explicitly concedes it
   cannot: **attest execution**, not merely sign a claim. That is the honest route across our
   own stated boundary, and it now has a citation.

2. **The Privacy Data Sheet is a bespoke JSON format in a field that has converged on
   Croissant.** `INFERENCE:` emitting the sheet as a Croissant extension — reusing its
   provenance vocabulary and adding DP-specific fields — would cost little and would place the
   artefact inside the ecosystem instead of beside it. `CONFIDENCE: med` on the effort estimate;
   the Croissant extension mechanism was read from the 1.1 announcement, not from the spec.

---

## 5. Family F — subgroup disparity (guards C4 / H2)

**H2's parent paper is confirmed and is by the same cluster.**

**Ganev, Oprisanu & De Cristofaro — "Robin Hood and Matthew Effects: Differential Privacy Has
Disparate Impact on Synthetic Data", ICML 2022**
([PMLR v162](https://proceedings.mlr.press/v162/ganev22a.html), [arXiv 2109.11429](https://arxiv.org/abs/2109.11429)).

Studies DP's effect on underrepresented subgroups across PrivBayes, DP-WGAN and PATE-GAN, on
(1) subgroup size in the synthetic data and (2) downstream classification accuracy. Finds DP
produces **opposite** size distributions depending on setting — shrinking the majority/minority
gap ("Robin Hood") in some cases and widening it ("Matthew") in others — with disparate impact
on accuracy either way.

**Bearing on H2.** H2 asks the adjacent question — not disparate impact on *accuracy* but
disparate *leakage*. That distinction is real and worth stating precisely, because it is the
one thing separating H2 from a 2022 ICML paper. Also relevant: *Risk-Equalized DP Synthetic
Data* ([arXiv 2602.10232](https://www.arxiv.org/pdf/2602.10232)) assumes the leakage effect and
builds a mechanism to equalise it.

`CONFIDENCE: high` on the paper's existence, venue and findings; `med` on the claim that no one
has measured per-subgroup *leakage* specifically — family F ran one pass.

---

## 6. Family G — SDC / official statistics (guards C1, C2) — **the predicted surprise**

`00_problem_framing.md` §7 flagged this family as the most likely source of an unpleasant
surprise. **It was right.**

Automated release gating for confidential data is **production practice in UK Trusted Research
Environments**, under the **Five Safes** framework, where "Safe Outputs" is one of the five and
requires explicit disclosure checking of every output before it leaves the environment.

| Work | Identifier |
|---|---|
| **SACRO** — *A Multi-Language Toolkit for the Semi-Automated Checking of Research Outputs* | Preen, Albashir, Davy & Smith, [arXiv 2212.02935v3](https://arxiv.org/html/2212.02935v3) (Nov 2024) |
| **SACRO-ML** — *Safe machine learning model release from Trusted Research Environments* | [arXiv 2212.01233](https://arxiv.org/pdf/2212.01233) |
| *Handbook on Statistical Disclosure Control for Outputs* | [securedatagroup.org](https://securedatagroup.org/wp-content/uploads/2019/09/thf_datareport_aw_web.pdf) |
| *Principles- vs Rules-Based Output SDC in Remote Access Environments* | ResearchGate 273725328 |

**What SACRO does** (fetched and read): applies disclosure tests to research outputs — cell
frequencies against minimum thresholds, dominance via the p%-rule and NK-rule, regression
degrees of freedom — optionally applies suppression or rounding, and emits **structured JSON or
Excel reports** recording which checks passed, failed or need review, with a GUI for checkers to
record approval/rejection and commentary, creating "auditable records". It generates **SHA-256
checksums** alongside outputs.

**Three verified differences that are the only things standing between SynthProof's preflight
gate and prior art:**

| | SACRO / output checking | SynthProof preflight |
|---|---|---|
| **What it reads** | **The actual output values** — cell counts, regression internals | **Only the declared schema and the row count. Never a cell.** |
| **Who decides** | Flags and mitigates; **does not autonomously refuse**. "A status of 'pass' does not indicate that the tool has certified that an output is safe for publication." Human checkers retain final authority | **Refuses autonomously**, with a code, a reason and a remedy |
| **Record** | SHA-256 checksums and decision logs; **no cryptographic signing described** | Ed25519-signed, third-party verifiable |

`INFERENCE:` the *concept* of an automated gate producing an auditable release record is
occupied, in production, since at least 2022. What is not occupied, on this evidence, is a
**data-blind** gate — one whose refusal reads no sensitive value at all. That is exactly the
argument `data/preflight.py`'s own docstring already makes, and it is far stronger stated
against SACRO than stated in a vacuum. `CONFIDENCE: med-high` on the difference being real;
`med` on it being unoccupied, since family G ran one pass and the SDC literature is large and
poorly indexed by arXiv search.

**C2 is further reinforced as killed**: the SDC field has treated "does this check itself leak?"
as a first-class question for decades.

---

## 7. Family H — DP implementation correctness (guards F1, F3)

**F3 (finding defects by self-audit) stays KILLED** — Cebere et al., [arXiv 2602.17454](https://arxiv.org/html/2602.17454).

**F1 (the calibration gap: ε = 8 requested, 70.49 delivered) is now qualified rather than
unresolved.** The general phenomenon is well documented:

| Work | Identifier | Bearing on F1 |
|---|---|---|
| **Ngong et al.** — *Evaluating the Usability of Differential Privacy Tools with Data Practitioners* | **SOUPS 2024**, [arXiv 2309.13506](https://ar5iv.labs.arxiv.org/html/2309.13506) | 24 US practitioners across DiffPrivLib, Tumult Analytics, PipelineDP and OpenDP. Finds API design and documentation are decisive for correct DP implementation |
| **SoK: Usability Studies in Differential Privacy** | [arXiv 2412.16825](https://arxiv.org/pdf/2412.16825) | Systematises the usability literature |
| *Detecting Violations of Differential Privacy* | [arXiv 1805.10277](https://arxiv.org/pdf/1805.10277) | Detecting DP violations |
| *Guidelines for Implementing and Auditing Differentially Private Systems* | [arXiv 2002.04049](https://arxiv.org/pdf/2002.04049) | Practice guidance |

The literature states the enabling condition plainly: errors in DP implementation are close to
undetectable, and users are unlikely to notice when a released result is less private than the
level they asked for.

**What was NOT found:** a published instance of the *specific* failure — a tool whose
target-epsilon control does not compose to the epsilon requested, quantified end to end
(ratio 70.49/8 ≈ 8.8×, corrected to 0.92). `CONFIDENCE: low-med`. Family H ran a single pass and
the negative is weak evidence. Anyone building on F1 must search DP tooling issue trackers and
the usability literature properly before claiming it.

---

## 8. Consolidated kill table after Phase 2

| Claim | Verdict | Basis |
|---|---|---|
| **C1** dual-sided assurance | **KILLED** | Annamalai, Ganev & De Cristofaro, USENIX Sec 2024 (2405.10994) |
| **C2** budget-charged domain profiling | **KILLED** | Ganev, Annamalai, Mahiou & De Cristofaro, Apr 2025 (2504.08254); reinforced by SDC practice |
| **C3** signed cross-release budget ledger | **HEAVILY CROWDED** | PrivateKube (OSDI'21), Cohere, DPack (EuroSys'25), DPolicy; blockchain DP-cost ledgers. Signing gap unverified |
| **C4 / H2** subgroup leakage disparity | **ADJACENT PRIOR WORK** | Ganev et al., ICML 2022 — disparate impact on *accuracy*; leakage is the adjacent question |
| **F1** calibration gap | **QUALIFIED** | Phenomenon documented (SOUPS 2024, SoK 2412.16825); the specific quantified instance not found |
| **F2** auditor ceiling | **KILLED as mathematics** | Steinke Thm 2.1 corollary, verified bit-identical against our own code and pinned by a test |
| **F3** self-audit defects | **KILLED** | Cebere et al., Feb 2026 (2602.17454) |
| **Release-gate / refusal** | **CROWDED — new** | Five Safes + SACRO, production practice in UK TREs since 2022 |
| **Machine-checkable release artefact** | **CROWDED — new** | Croissant (NeurIPS submission requirement), MRM3, Laminator (CODASPY 2025) |

### The three narrow differences that survived every family

Stated as candidates for Phase 3 to test, **not** as claims:

1. **Data-blind refusal.** SACRO reads output values; `preflight.py` reads only the declared
   schema and row count. No counterexample found.
2. **Cryptographic signing of the privacy claim.** SACRO checksums; PrivateKube/Cohere/DPack
   were not found to sign; Laminator attests execution via TEE but does not address DP budgets.
3. **Reporting the measurement's own operating range inside the artefact.** SynthGuard bounds
   utility; nothing found reports what the privacy measurement could not have seen.

Each is narrow. Each is stated here as *not yet refuted*, which is a different thing from novel.

---

## 9. Strategic assessment, unchanged and reinforced

The interim report's §4 conclusion survives Phase 2 completion and is strengthened by it: the
**Ganev / Annamalai / De Cristofaro / Kulynych** cluster is running this research programme
professionally and is roughly two years ahead. Families A, B, C and F all terminate at their
work. Family G shows that the applied-statistics community solved the release-gating problem
before that.

**Two directions this evidence supports, neither of which competes on their axis:**

- **Integration rather than invention.** Emit the Privacy Data Sheet as a **Croissant
  extension**; adopt the SACRO vocabulary for refusal codes. This is honest, cheap, and reframes
  the contribution as *connecting DP accounting to the standards the field actually uses* —
  which nobody has done and which no author cluster is racing us to.
- **The data-blind gate as the sharp claim.** It is one sentence, it is verifiable in the code,
  it is defensible against SACRO, and it is the one thing here that a domain expert would not
  expect.

---

## 10. What Phase 3 must do before any verdict

1. **Fetch the blockchain DP cost-management work** (2006.04693 and neighbours) and settle
   whether any budget ledger is signed for external verification. C3 turns on this.
2. **Read the SDC output-checking literature properly**, not via arXiv search. The Handbook and
   the principles-vs-rules paper are the entry points. Confirm nobody does a data-blind
   pre-check.
3. **Search DP tooling issue trackers** for the F1 failure mode before claiming it.
4. **Read the Croissant 1.1 extension mechanism** and cost the integration.
5. Only then populate `08_novelty_verdict.md`.

**Sources reached in this run.** Laminator (CODASPY 2025) · Croissant 1.1 (MLCommons, Feb 2026) ·
MRM3 (MobiSys 2025) · PrivateKube (OSDI '21) · Cohere · DPack (EuroSys 2025) · DPolicy ·
SACRO (arXiv 2212.02935v3) · SACRO-ML (arXiv 2212.01233) · Five Safes (Dundee TRE) ·
Handbook on SDC for Outputs · Ganev et al. ICML 2022 · Risk-Equalized DP Synthetic Data ·
Ngong et al. SOUPS 2024 · SoK Usability in DP (2412.16825) · Detecting Violations of DP
(1805.10277) · Guidelines for Implementing and Auditing DP Systems (2002.04049).

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

Full attribution: [`docs/MEASUREMENT_CONVENTIONS.md`](docs/MEASUREMENT_CONVENTIONS.md).
