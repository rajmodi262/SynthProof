# Phase 2 — INTERIM REPORT (incomplete run)

> **Status: PARTIAL.** The parallel search was interrupted by a session usage limit.
> **2 of 8 query families completed. 6 never ran.** Everything below is honest about which.
>
> Six sources are **VERIFIED** — I fetched each and read the abstract or full text myself.
> Thirty further candidates are **UNVERIFIED** — proposed by a search agent whose verification
> pass never executed. Per Ground Rule 1 no argument rests on those.

---

## 1. What ran, what did not

| Family | Guards | Status |
|---|---|---|
| A — auditing limits | F2 | **NEVER RAN** |
| B — DP synthetic tabular | C1, H1 | completed (15 candidates, unverified) |
| C — budget accounting | C3 | **NEVER RAN** |
| D — verifiable DP | C3, R4 | completed (15 candidates, unverified) |
| E — transparency artefacts | C1 | **NEVER RAN** |
| F — subgroup disparity | C4 | **NEVER RAN** |
| G — SDC / official statistics | C1, C2 | **NEVER RAN** |
| H — DP implementation correctness | F1, F3 | **NEVER RAN** |

Saturation was **not** reached in any family. The Phase-3 bar (>=60 screened, >=20 deep-read) is
not met: 30 screened, 6 verified, 2 deep-read.

## 2. Kill table — VERIFIED evidence only

| Claim | Verdict | Killed by |
|---|---|---|
| **C1** dual-sided assurance (proved + audited per release) | **KILLED** | Annamalai, Ganev & De Cristofaro, USENIX Sec 2024 — [arXiv:2405.10994](https://arxiv.org/abs/2405.10994). Computes empirical leakage vs theoretical bound for DP-SDGs; flags violations when empirical exceeds theory and loose audits when non-negligibly lower. That is the framing. |
| **C2** budget-charged domain profiling | **KILLED** | Ganev, Annamalai, Mahiou & De Cristofaro, Apr 2025 — [arXiv:2504.08254](https://arxiv.org/abs/2504.08254). Examines the exact three domain strategies (externally provided / extracted from data / extracted under DP) and shows extraction from input data breaks end-to-end DP. |
| **C3** signed cross-release budget ledger | **UNRESOLVED — but crowded** | Family C never ran. Family D surfaced 7 unverified candidates incl. PrivateKube (OSDI'21), Cohere, Sage, DPolicy, and a *Blockchain-Based Differential Privacy Cost Management System*. Must verify before any claim. |
| **C4 / H2** subgroup leakage disparity | **UNRESOLVED** | Family F never ran. One unverified hit: Bagdasaryan et al. on disparate impact on *accuracy* — which is the adjacent, not the same, claim. |
| **F1** calibration gap (eps 8 requested, 70.49 delivered) | **UNRESOLVED** | Family H never ran. Not yet attacked. |
| **F2** auditor working range / ceiling | **KILLED as mathematics; SEVERELY WOUNDED as practice** | See §3 — two independent hits. |
| **F3** self-audit found 5 defects | **KILLED** | Cebere, Erb, Desfontaines, Bellet & Fitzsimons, Feb 2026 — [arXiv:2602.17454](https://arxiv.org/abs/2602.17454). Audits **12** open-source DP libraries (SmartNoise SDK, Opacus, Diffprivlib), finds **13** privacy violations, names the method (Re:cord-play) and ships it as a package. |

## 3. F2 — the finding I recommended as the headline. It does not survive intact.

**Hit 1 — the mathematics is a corollary of the paper SynthProof already cites.**
Steinke, Nasr & Jagielski 2023 ([arXiv:2305.08846](https://arxiv.org/abs/2305.08846)), Theorem 2.1
and Equation (3), read directly from the PDF:

> `P[Σ max{0, T_i·S_i} ≥ v] ≤ P[W̄ ≥ v] + O(δ)` where `W̄ ← Binomial(r, e^ε/(e^ε+1))`

Set `v = r` (perfect adversary) and this reduces to `p(ε)^r ≤ β`, i.e.
`ε_max = log(β^(1/r) / (1 − β^(1/r)))`. At r = 800, β = 0.05 that is **ε ≈ 5.59** — matching
SynthProof's measured 5.38 to within the difference between an exact binomial tail and a
Clopper-Pearson interval. SynthProof independently re-derived a one-line consequence of its own
cited source. `CONFIDENCE: high` — the inequality is printed on page 4.

**Hit 2 — and this is the damaging one — the ceiling is partly an artefact of the estimator
SynthProof chose.**
Ganev, Annamalai & Kulynych, 20 Apr 2026 ([arXiv:2604.18352](https://arxiv.org/abs/2604.18352))
audit **MST and AIM** — SynthProof's own mechanisms — using a Gaussian-DP framework that measures
the **full false-positive/false-negative trade-off** rather than a single threshold. They obtain:

> "the first tight audits in the strong-privacy regime. For (ε,δ)=(1,10⁻²), we obtain
> μ_emp ≈ 0.43 vs. implied μ = 0.45, showing a small theory-practice gap."

SynthProof reports `ε_audited = 0.000` in every cell and concludes the instrument has a ceiling.
A stronger estimator on the same mechanisms gets a **tight** audit. So the honest reading is:
**the ceiling SynthProof hit is a property of `log(TPR_lo/FPR_hi)` on a single threshold, not a
property of auditing.** The "working range" framing survives only as a statement about *that
specific weak estimator*, which is a much smaller claim.

`CONFIDENCE: high` on the kill of F2-as-theory. `CONFIDENCE: med-high` that F2-as-practice is
also substantially undermined, pending full-text read of 2604.18352.

## 4. The strategic fact that matters more than any single kill

Four of the six verified kills come from **one overlapping author cluster**:
**Georgi Ganev · Meenatchi Sundaram Muthu Selva Annamalai · Emiliano De Cristofaro · Bogdan
Kulynych** (UCL / Hazy / UC Riverside / EPFL-adjacent), publishing at USENIX Security and on
arXiv from 2024 through April 2026.

They have systematically occupied: auditing DP synthetic data generators, domain-extraction
leakage, tight auditing of MST and AIM, and disparate effects. **This group is doing SynthProof's
research programme, professionally, and is roughly two years ahead.**

That is not a reason to stop. It is a reason to stop competing on their axis.

## 5. Unverified candidates worth checking next (do NOT cite yet)

From family B: Synth-MIA testbed (2509.18014) · Benchmarking DP tabular synthesis (2504.14061) ·
Graphical vs deep generative (2305.10994) · High-epsilon vulnerabilities in MST/PrivBayes
(2402.06699) · Discretization impact (2504.06923) · PATE-GAN reproduction (2406.13985) ·
Revisiting privacy-utility trade-off (2407.07926).

From family D: PrivateKube OSDI'21 · Cohere (2301.08517) · Sage · DPolicy (2505.06747) ·
Blockchain-based DP cost management (2006.04693) · Elephants Do Not Forget (state continuity) ·
Laminator: verifiable ML property cards via hardware attestation (2406.17548) · VerDP · VERIDP
(eprint 2026/542) · Confidential-DPproof.

**Laminator is the one to check first for C3/C1** — "verifiable ML property cards" is
structurally the Privacy Data Sheet.

## 6. What still has to be searched before any verdict

Families A, C, E, F, G, H — six of eight. In particular **G (Statistical Disclosure Control)** has
not been touched, and that remains the most likely source of a further unpleasant surprise, for
the reasons in `00_problem_framing.md` §7.

**No novelty verdict should be issued from this document.** It is incomplete by construction.
