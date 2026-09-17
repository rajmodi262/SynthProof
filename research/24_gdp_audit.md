# 24 — GDP audit: an informative privacy number where the canary audit gave zero

> Built by `scripts/run_gdp_audit.py` (results in `results/gdp_audit_*.json`). This realises the
> mechanism/privacy-side improvement from the plan: the H1 grid's `audited_eps = 0.000` on every
> mechanism and dataset is **substantially an estimator artefact**, not purely an information-
> theoretic ceiling. A GDP/f-DP estimator recovers a real, nonzero privacy lower bound.
> **Read the caveats in §3 before quoting any number** — this is a worst-case replication, not a
> tight audit of AIM/MST as deployed.

## 1. The result

Worst-case setup, following Ganev, Annamalai & Kulynych (TPDP 2026, arXiv:2604.18352): `D_out` =
10 identical records `[0,0,0]`; `D_in` = `D_out` + one target `[1,1,1]`; 50 synthetic rows per run;
**2000 runs per world**; a scikit-learn gradient-boosting adversary scores each synthetic table;
`mu` lower-bounded over all thresholds with one-sided Clopper–Pearson bounds (`audit/gdp.py`).

| mechanism | GDP `mu_emp` | canary `audited_eps` (H1 grid) | ceiling (this n) | implied μ from (ε=1, δ=1e-2) | exceeds implied? |
|---|---|---|---|---|---|
| independent | **0.363** | 0.000 | 5.36 | 0.5325 | no |
| aim *(ours)* | **0.183** | 0.000 | 5.36 | 0.5325 | no |
| mst *(ours)* | **0.151** | 0.000 | 5.36 | 0.5325 | no |

**Every mechanism gives an informative `mu_emp > 0`** where the black-box Steinke canary auditor
used in the H1 grid reports exactly 0.000. All three sit **below** the implied bound (0.5325) with
`exceeds_implied = False` — the expected, correct ordering (no violation of the proof).

## 2. What it means (and what it does not)

- **The zeros were largely the estimator, not the mechanism.** Ganev et al. diagnose that a
  black-box canary audit with unstable threshold selection collapses to `eps_emp = 0` in the
  strong-privacy regime; measuring the whole FPR/FNR curve and fitting one `mu` avoids that. Our
  numbers reproduce the *direction* of that diagnosis in this codebase.
- **Ordering, stated as INFERENCE (`CONFIDENCE: med`):** independent (0.363) leaks more about the
  single target than aim (0.183) or mst (0.151). Plausibly the graphical-model smoothing dilutes
  one record's influence on the release; but this is a worst-case 11-record, single-target setup,
  so it is not a general utility/privacy claim about the mechanisms.
- **It does not change the H1 grid.** The grid's `audited_eps` still comes from `SteinkeAuditor`
  (one-run canary). This GDP audit answers a *different* question — "what `mu` does the FPR/FNR
  curve support across many runs" — and is reported alongside, not in place of, the one-run number.

## 3. Honest caveats (from `audit/gdp.py` and `scripts/run_gdp_audit.py`, do not quote around these)

1. **This is a worst-case 11-record replication, NOT a tight audit of AIM/MST as deployed.** The
   paper's tight numbers come from a restricted configuration (fixed graph, one-way marginals,
   domain compression off) in which MST and AIM both reduce to an independent-marginal model.
2. **Weaker adversary.** The paper uses XGBoost over query features plus white-box marginal counts;
   `xgboost` is not installed here, so this uses sklearn gradient boosting. A weaker adversary
   yields a *smaller* `mu_emp`, so these numbers **under-claim**.
3. **More conservative estimator.** One-sided Clopper–Pearson bounds, not the paper's Bayesian
   90%-posterior estimator; the numbers are not directly comparable to their 0.43.
4. **2000 runs/world, not their 10,000.** The ceiling for this n (5.36) is reported beside the
   result so the `mu_emp` is never read out of range.
5. **`implied μ = 0.5325` is the LOOSE comparator** (inverting the released (ε=1, δ=1e-2), which is
   not tight). It is not the mechanism's own μ and must not be presented as reproducing the paper's
   "implied μ = 0.45". The tight comparator (`sqrt(k)/σ`) was not captured for these runs.
6. **Not a novelty claim.** The estimator and the ceiling are published (Koskela & Mohammadi 2025;
   Dong, Roth & Su 2022); the contribution is the runnable check, not the quantity.

## 4. One line for the viva

*A Gaussian-DP audit of our own mechanisms returns an informative empirical privacy lower bound
(μ ≈ 0.15–0.36) exactly where the black-box canary audit collapses to zero — evidence that the
project's headline "audited ε = 0" is substantially an estimator artefact, honestly bounded, and
below the proved guarantee in every case.*
