# GDP audit — audited against proved epsilon, every mechanism

<!-- provenance: results/gdp_audit.json, results/h1_all_families.json, results/auditor_comparison.json, results/gdp/ -->

## W9 (2026-10-16): every mechanism, preregistered, held-out threshold

> Plan committed before the runs: [`docs/prereg/W9_gdp_audit.md`](../docs/prereg/W9_gdp_audit.md);
> each cell records its SHA-256. Raw output: [`gdp/`](gdp/) · `make gdp-audit`.
> **Estimator change:** the threshold is now chosen on half the scored runs and the bound computed
> on the other half. The August estimator below chose it on the scores it bounded, which biases
> the bound upward (`tests/test_gdp.py`); its numbers are kept for the record and superseded.
> A cell reading "not run" has not finished yet.

<!-- BEGIN GENERATED: gdp-w9-table -->
| Mechanism | target ε | proved ε | **audited ε** (lower bound) | ceiling ε | audited / proved | μ_emp | comparator μ | violation | bounded runs/world |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| `independent` | 1 | 0.9999 | **0.2161** | 26.01 | 0.216 | 0.1743 | 0.4547 | none | 1000 |
| `independent` | 4 | 3.9999 | **1.5945** | 26.01 | 0.399 | 0.7560 | 1.3297 | none | 1000 |
| `moments` | 1 | 0.9999 | **0.2161** | 26.01 | 0.216 | 0.1743 | 0.5325 | none | 1000 |
| `moments` | 4 | 3.9999 | **1.5945** | 26.01 | 0.399 | 0.7560 | 1.4946 | none | 1000 |
| `pairwise` | 1 | 0.9999 | **0.0287** | 26.01 | 0.029 | 0.0531 | 0.5325 | none | 1000 |
| `pairwise` | 4 | 3.9999 | **1.2831** | 26.01 | 0.321 | 0.6422 | 1.4946 | none | 1000 |
| `fixed_workload` | 1 | 1.0000 | **0.3643** | 26.01 | 0.364 | 0.2522 | 0.5325 | none | 1000 |
| `fixed_workload` | 4 | 3.9999 | **2.2359** | 26.01 | 0.559 | 0.9736 | 1.4946 | none | 1000 |
| `mst` | 1 | 0.9999 | **0.0597** | 22.44 | 0.060 | 0.0771 | 0.5325 | none | 500 |
| `mst` | 4 | 3.9998 | **1.3886** | 22.44 | 0.347 | 0.6815 | 1.4946 | none | 500 |
| `aim` | 1 | 0.9999 | **0.0000** | 15.22 | 0.000 | 0.0000 | 0.5325 | none | 125 |
| `dpvae` | 1 | 1.0000 | **0.0000** | 15.22 | 0.000 | 0.0000 | 0.5325 | none | 125 |

*Generated from `results/gdp/*.json`. delta = 1e-2, alpha = 0.05; every cell ran under the preregistration with SHA-256 233f53e650e4…*
<!-- END GENERATED: gdp-w9-table -->

**Audited ε is a lower bound** from μ_emp at the same δ as the proved ε; the ceiling is the most
this run count could certify against a perfect adversary. A cell where audited ε sits far below
proved ε says this adversary on this instance did not reach the proof, not that the mechanism
is more private than proved.

---

## August 2026 (superseded): `independent` only, threshold chosen on the scored runs

> **Run 2026-08-25.** 5,000 fits (2,500 per world), `independent` mechanism, worst-case instance.
> Raw output: [`gdp_audit.json`](gdp_audit.json) · Runner: `scripts/run_gdp_audit.py` ·
> Regenerate: `python -m scripts.run_gdp_audit --runs 2500`
>
> **This is a replication, not a novelty claim.** Method from Ganev, Annamalai & Kulynych,
> *Tight Auditing of Differential Privacy in MST and AIM*, TPDP 2026
> ([arXiv:2604.18352](https://arxiv.org/abs/2604.18352)) — title, authors and headline numbers
> verified against the arXiv abstract on 2026-08-25.

---

## The headline

| quantity | value | what it is |
|---|---:|---|
| **`mu_emp`** | **0.4014** | empirical lower bound, one-sided Clopper-Pearson at alpha = 0.05 |
| **mechanism `mu`** | **0.4547** | `sqrt(3)/sigma` at `sigma = 3.809` — the mechanism's own GDP parameter |
| implied `mu` | 0.5325 | inverting the released `(eps, delta) = (1, 1e-2)` — the loose comparator |
| ceiling at this n | 5.5073 | most this run count could certify against a perfect adversary |
| FPR / FNR | 0.0072 / 0.9536 | the operating point the bound came from |

**`mu_emp` reaches 88% of the mechanism's own `mu`, and sits correctly below it.**

## Why this matters more than any other number in the project

Every canary audit here reports `eps_audited = 0.000`, and `results/DETECTION_FLOOR.md` read that
as an information-theoretic ceiling. **That reading was incomplete.** Ganev et al. diagnose a
second cause: unstable threshold selection picks overly small thresholds, inflating FPR and
collapsing the bound to zero — *"which explains why prior work reports `eps_emp = 0` results in
the strong-privacy regime"*. Their Fig. 3 ablation shows Clopper-Pearson collapsing to 0.00 where
their estimator reaches 0.43. **SynthProof uses Clopper-Pearson.**

This run produces **0.4014 with Clopper-Pearson still in place**, purely by changing *what is
estimated*: a `mu` fitted to the whole FPR/FNR tradeoff curve rather than a single `(eps, delta)`
point, with the threshold chosen on a held-out half so it cannot be fitted to the data it is
scored on.

So the zeros were substantially an **artefact of the estimand and the threshold**, not only of
the canary budget. The proved-vs-audited comparison is no longer vacuous.

## Three things this establishes

1. **No violation.** `mu_emp = 0.4014 < 0.4547`. An empirical bound above the mechanism's own
   parameter would have been evidence of a defect in the noise sampler, the accountant, or the
   mechanism. It is below, in the correct ordering, on a worst-case instance designed to make
   leakage as visible as possible.
2. **Independent corroboration of the accounting.** The mechanism lands at `mu = 0.4547` at
   `(1, 1e-2)` — essentially the same regime as the paper's 0.45, arrived at through this
   project's own calibration and `dp_accounting` composition rather than by copying a number.
3. **The instrument had headroom.** The ceiling was 5.5073, so 0.4014 is a measurement, not a
   floor. Contrast with the canary audits, where the ceiling of 2.97 sat below the proved
   epsilon of 7.36 and the zero was uninterpretable.

## Setup

Following the paper: `D_out` = 10 identical records `[0,0,0]` over three binary columns; `D_in` =
`D_out` plus one target `[1,1,1]`; 50 synthetic rows per run; 2,500 independent runs per world.
The schema is **declared public**, so the profiler charges almost nothing and the audit measures
the synthesis mechanism rather than domain discovery.

Adversary: sufficient statistics from the synthetic table alone (per-column rate of `1`, and the
rate of the full `[1,1,1]` pattern), scored by a scikit-learn gradient-boosting classifier trained
on one half and evaluated on the other.

## Honest limits — read these before quoting the number

- **This is not the paper's number and must not be presented as reproducing 0.43.** Their
  adversary is XGBoost over query features *plus white-box noisy marginal counts*; theirs is a
  Bayesian estimator at 90% posterior mass (which they note "does not necessarily yield valid
  frequentist coverage"). Both differences push our figure **down**, so 0.4014 is a conservative
  replication of the *framework*, not of the *result*.
- **It says nothing about the Adult and ACS audits.** Those are a different regime — 60 canaries,
  a single training run, real data. This is 5,000 runs on an 11-record worst-case instance.
  `eps_audited = 0.000` on the H1 grid still stands, and the ceiling of 2.97 still applies there.
- **The mechanism audited is `independent`**, three one-way marginals. That matches the paper's
  own restricted configuration — they fix the dependency graph and disable domain compression so
  MST and AIM both reduce to an independent-marginal model. **Neither this nor the paper is a
  tight audit of AIM as deployed**, and any text implying otherwise is wrong.
- One `(eps, delta)` point, one mechanism, one target record. Not a sweep.

## What follows

- Re-run at `--mechanism fixed_workload` and `--mechanism aim` to see whether the bound holds up
  once adaptive selection is in play. **Not yet run.**
- Sweep epsilon to produce a proved-vs-audited curve on a common GDP axis — the comparison
  `ch07 §7.4` currently has to retract.
- The `audit_ceiling` field on the Privacy Data Sheet should carry `max_provable_mu` beside the
  canary ceiling, so both instruments report their range.

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

Full attribution: [`docs/MEASUREMENT_CONVENTIONS.md`](../docs/MEASUREMENT_CONVENTIONS.md).
