# Phase 1 — Problem Framing

> **Note on inputs.** Every field in the Phase-0 template arrived blank. I filled them from
> direct observation of this repository rather than asking for a retype. **If this protocol was
> aimed at a different project, everything below is void.**
>
> **Citation status: ZERO searches have been run.** Every work named in §6 is recall-based and
> marked `[UNVERIFIED]`. Per Ground Rule 1 no argument here rests on any of them. They are
> search targets for Phase 2, not evidence.

---

## 1. Reconstructed inputs

| Field | Value (observed) |
|---|---|
| Title | SynthProof — "Synthetic Data That Ships With Its Proof" |
| One-line | A DP tabular-synthesis platform that releases synthetic data with a certificate stating both the formal bound (eps_proved) and an empirically audited lower bound (eps_audited), backed by a signed cross-release budget ledger |
| Field | Differential privacy · synthetic tabular data · empirical privacy auditing |
| Claimed novelty | (1) dual-sided assurance, (2) budget-charged domain profiling, (3) append-only signed budget ledger, (4) subgroup leakage disparity (H2) |
| Resources | 4 people; ~6 h/week each; single Windows workstation, CPU-only; no paid APIs observed |
| Constraints | Capstone 2026-27, MIT-WPU; Python 3.11; full H1 grid ~4 h wall-clock |
| Target outcome | **UNKNOWN — blocking. See Q1.** |
| Seed papers | McKenna et al. (AIM); Steinke/Nasr/Jagielski (one-run audit); Canonne-Kamath-Steinke (discrete Gaussian); Stadler et al.; Gebru et al. — all cited in `docs/thesis/ch02`, none yet fetched |

---

## 2. Restatement

A data holder wants to release a useful tabular dataset without disclosing individuals. Formal
DP gives an upper bound on disclosure that nobody verifies against the implementation. Empirical
auditing gives a lower bound from real attacks, but carries no guarantee, accumulates no budget
across releases, and is published in a paper rather than attached to the artefact. SynthProof
proposes to compute both bounds for the same release, bind them to a tamper-evident record of
the organisation's cumulative spend, and ship the result as a machine-verifiable certificate.

## 3. Formalisation

Let `D` in `X^n` be sensitive, drawn i.i.d. from unknown `P`. Let `S` be a **public** schema
(per-column type; numeric bounds; category domain) whose contents do not depend on `D`. Let
`B = (eps_total, delta)` be the release budget.

A release procedure `R : (D, S, B, seed) -> (D_synth, C)` emits synthetic `D_synth` in `X^m` and
certificate `C = <eps_proved, eps_audited, attack vector, utility vector, ledger head,
signature>`.

**Requirements.**

| # | Requirement | Formal statement | Status in repo |
|---|---|---|---|
| R1 | Soundness | `R` is `(eps_total, delta)`-DP under add/remove-one on `D` | met (composition delegated to `dp_accounting`) |
| R2 | Calibration | `eps_proved <= eps_total` and `eps_proved >= (1-eta)*eps_total` | met, eta ~ 0.08 |
| R3 | Audit | `eps_audited` is a `(1-alpha)`-confidence lower bound on the loss achieved by adversary class `A` | met but **out of working range** |
| R4 | Verifiability | a third party with `C` and `pk` validates `C` without `D` and without trusting the holder | **not met** |
| R5 | Cross-release composition | for `R_1..R_k`, ledger `L` records the running sum such that no `R_i` can be silently altered or removed | partially met (sheet unsigned) |

**Two objectives are conflated in the project, and they have different success criteria.**

- **O-sys (engineering):** produce release + verifiable certificate. Success = an independent
  party validates `C`, and a tamper attempt is detected. Binary, demonstrable, low risk.
- **O-sci (empirical):** characterise `G(M, eps, D) = eps_audited / eps_proved` across mechanism
  families `M`, budgets, datasets, and subgroups. Success = a replicated, CI-backed difference.
  **This is where the project is in trouble** (§5).

Treating these as one project is a framing weakness. They can be separated, and probably should
be — one is a systems contribution, the other an empirical study, and a reviewer will judge them
by different standards.

**Critical distinction: R2 is not a privacy property.** A system delivering eps_proved = 70 when
the operator requested 8 is still perfectly DP. It has violated nothing. It has *misled its
operator*. That makes R2 a human-factors / API-design property wearing privacy clothing — and,
INFERENCE, that reframing makes it *more* interesting to a systems venue, not less.

## 4. Sub-problem decomposition

| # | Sub-problem | State | Who solved it | Contribution potential |
|---|---|---|---|---|
| SP1 | Sound RDP composition | **solved** | Google `dp_accounting` | none — dependency |
| SP2 | Budget-to-noise inversion (calibration) | **solved here** | this repo | low as method, **high as a finding** (§5.1) |
| SP3 | Public-domain handling without leakage | **solved here** | converged on the standard answer | none — see §5.2 |
| SP4 | DP synthesis preserving joint structure | **solved elsewhere** | AIM / MST / private-PGM | none — integration |
| SP5 | Empirical eps lower bound | **partial** | Steinke et al. | low; instrument is theirs |
| SP6 | Cross-release tamper-evident accounting | **open in repo** | ? | **candidate** |
| SP7 | Third-party-verifiable certificate | **not built** | ? | **candidate** |
| SP8 | Per-subgroup leakage measurement | **attempted, null** | ? | high prior-art risk |
| SP9 | **Auditor working range (floor + ceiling)** | **measured here** | ? | **strongest candidate** (§5.3) |

## 5. What the project actually found, as distinct from what it set out to find

This section matters more than §1. The interesting results are **not** the four claimed
contributions. They are by-products.

### 5.1 The calibration gap
Requesting eps = 8 produced a release composing to **eps = 70.49** — an 8.8x overshoot that grew
with eps. Fixed by inverting the composition theorem; `proved/target` now 0.91-0.93 and CI-gated.
INFERENCE: mature libraries (OpenDP/SmartNoise) calibrate correctly, so the *method* is not
novel. The *observation that a plausible hand-rolled implementation silently misleads its
operator by ~9x* is a defect-class finding, and defect-class findings about DP implementations
are thin on the ground.

### 5.2 Budget-charged profiling collapsed into the standard answer
The project set out to "price" schema discovery. Its final design does the opposite: it takes
**public declared bounds at zero cost** and only falls back to a noisy estimate when no bound is
declared. That *is* the practice OpenDP mandates. INFERENCE: claimed contribution (2) is likely
dead — the project rediscovered the field's existing answer. `CONFIDENCE: med` — Phase 2 must
confirm what OpenDP/SmartNoise actually require.

### 5.3 The auditor has a ceiling, and it is measured
`results/DETECTION_FLOOR.md` reports that `eps_audited = log(TPR_lo / FPR_hi)` from
Clopper-Pearson intervals is bounded by canary count alone, *even against a 100% verbatim
release with a perfect adversary*:

| m | 10 | 25 | 50 | 100 | 200 | 400 | 800 |
|---|---:|---:|---:|---:|---:|---:|---:|
| max eps_audited | 0.81 | 1.84 | 2.57 | 3.28 | 3.98 | 4.68 | **5.38** |

Detection floor, from the same file: verbatim release detected at m = 10; 25% leakage needs
m = 400; 5% and 1% leakage undetected at m <= 800; the 0% control correctly never fires.

**Consequence, self-inflicted:** H1 ran at m = 60 (ceiling ~2.7) against eps_proved ~7.36. The
privacy half of the project's primary hypothesis is therefore **disqualified by its own
instrument**, and the repo says so in `results/H1_RESULTS.md` §3.6.

INFERENCE: this is the project's most defensible asset. It is a *negative result about the
auditing literature's own evaluation practice*, it is measured rather than argued, and the team
demonstrated its bite by using it to invalidate their own headline. `CONFIDENCE: med-high` that
it is the strongest card; `CONFIDENCE: low` that it is unpublished — the underlying inequality is
almost certainly already in Steinke et al. (§6).

### 5.4 The self-audit defect count
Five defects found in the team's own DP implementation, each of which silently voided or
misstated a guarantee, and **every one surfaced by refusing to accept a result that pointed the
wrong way**: a sigma<0.3 zero-noise shortcut; an unsound subsampling bound under-reporting eps by
~2x; canaries dropping the schema; canaries placed outside the public domain, fabricating
correlation (0.093 -> 0.334); a utility target defaulting to the wrong column. Two published
result documents were retracted in-repo.

### 5.5 H1/H2/H3 status
- **H1**: supported on *structure and utility* — AIM corr-err 0.0078 [0.0031, 0.0125] vs
  independent 0.0947 [0.0817, 0.1071] at eps = 8, non-overlapping CIs. Privacy half disqualified.
- **H2**: **not supported.** Direction weakly consistent — rarest subgroup (`Other`, 0.8% of
  rows) has highest attack accuracy at both eps. Per-subgroup ceiling 3.27-4.19.
  Instrument-limited, not mechanism-limited.
- **H3**: run; uniform vs utility-weighted allocation at fixed total eps.

## 6. Preliminary prior-art threat assessment — ALL `[UNVERIFIED]`

Recall-based. Phase 2 must fetch or discard each. **No argument here depends on them.**

| Claim at risk | Suspected prior art `[UNVERIFIED]` | If real, effect |
|---|---|---|
| (1) dual-sided assurance | Jagielski, Ullman & Oprea 2020 — auditing DP-SGD, proved-vs-audited framing | **kills the framing**; leaves only per-release packaging |
| (2) budget-charged profiling | OpenDP / SmartNoise public-bounds requirement | kills it — standard practice |
| (3) signed ledger | Rogers, Roth, Ullman & Vadhan 2016 "Privacy Odometers and Filters"; Certificate-Transparency-style logs; Narayan et al. 2015 "Verifiable Differential Privacy" | may kill the *formal* half; the crypto + odometer *combination* may survive |
| (4) H2 subgroup leakage | Kulynych et al. "Disparate Vulnerability to Membership Inference"; Ganev et al. "Robin Hood and Matthew Effects" | **high kill risk**; possible survival only in the eps_audited-on-synthetic-data framing |
| §5.3 auditor ceiling | Steinke/Nasr/Jagielski 2023 derive the bound; Nasr et al. 2023 "Tight Auditing"; Zanella-Beguelin et al. Bayesian DP estimation | math almost certainly known; the *reporting-standard critique* may survive |

## 7. Glossary and cross-community synonyms

The single largest cause of missed prior art here is that **four separate communities have been
working on this for thirty years under different vocabulary.**

| SynthProof term | Also called, and where |
|---|---|
| eps_audited | empirical privacy loss · privacy lower bound · attack-based privacy evaluation (ML security) |
| privacy-utility frontier | **R-U confidentiality map** (Duncan et al., official statistics) · risk-utility trade-off |
| Privacy Data Sheet | datasheet · model card · AI FactSheet (IBM) · **privacy nutrition label** (Apple / usable-privacy) · **disclosure risk report** (SDC) |
| synthetic data | **fully / partially synthetic microdata** (SDC) · multiple imputation (Rubin 1993; Reiter) — *the origin of the idea, routinely missed by CS work* |
| budget ledger | privacy budget management · **privacy odometer / filter** (formal) · budget scheduler |
| canary | planted record · honeypot record · **secret sharer** (Carlini) · shadow record |
| tamper-evident log | transparency log · Merkle log · certificate transparency · append-only audit log |
| disclosure risk | re-identification risk · singling-out / linkability / inference (Anonymeter, WP29) |
| the field itself | **Statistical Disclosure Control (SDC)** — Eurostat / ONS / US Census, decades of it |

**Phase 2 must search SDC and official-statistics venues, not only ML venues.** `CONFIDENCE:
high` that this is where an unpleasant surprise lives.

## 8. Blind spots the field appears to inherit — targets for "attack the benchmark"

1. **UCI Adult as the default benchmark.** Measured here: strongest numeric correlation is
   **0.1034**. A benchmark that barely has joint structure is a poor instrument for evaluating
   structure preservation — yet it is the field's default.
2. **eps reported without interface fidelity.** Nobody reports what their implementation actually
   delivered versus what was requested. This project's own answer was 8.8x off before it looked.
3. **Audit results reported without the instrument's working range.** See §5.3.
4. **Public-bounds assumption glossed.** Where the domain came from is frequently unstated.

## 9. Assumptions made to fill blanks — correct any that are wrong

1. This protocol targets SynthProof.
2. The deliverable is primarily a capstone thesis; publication is aspirational. **(Q1)**
3. Novelty is *desired* but the pass condition is a defensible thesis. **(Q3)**
4. The four claimed contributions in the synopsis are not contractually locked. **(Q4)**
5. Compute is one CPU workstation; a 4 h grid is affordable, a 40 h one is not. **(Q5)**
6. ACS PUMS is obtainable — the repo has `results/acs/` and a loader, but the prereg deviation
   log says the ACS run was not completed. **(Q6)**

## 10. Verdict on the framing, before any search

The project as *originally framed* is a systems-integration project whose four claimed
contributions each face a credible prior-art threat. The project as *actually executed* has
produced three findings — the calibration gap, the auditor working range, and the self-audit
defect count — that were not in the plan and are, INFERENCE, more defensible than the plan was.

**Recommended reframing, to be tested in Phases 6-8:** move the auditing *working range* to the
headline and demote the Privacy Data Sheet to the vehicle that carries it. `CONFIDENCE: med` —
contingent entirely on whether Phase 2 finds §5.3 already published.
