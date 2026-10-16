# Preregistration — W9: GDP audit of every mechanism against its proved epsilon

> **Committed 2026-10-16, before any run it governs.** Each result file written under this plan
> records this file's SHA-256 (`preregistration_sha256`); a result whose hash does not match the
> committed file was not run under it. Changes after the first run are listed in §7 with reasons,
> never edited in place.

## 1. Question

For each SynthProof mechanism, how much of its **proved** epsilon can a strong black-box
membership adversary **certify** on the worst-case instance? Does any mechanism leak **more**
than its proof allows (a violation)?

## 2. Instance, mechanisms, grid

- **Instance:** `scripts/run_gdp_audit.py::worst_case_datasets` — `D_out` = 10 × `[0,0,0]` over
  three binary columns with a declared (public) schema; `D_in` = `D_out` + one `[1,1,1]`.
  50 synthetic rows per release. Profiling budget 2% of target (schema is public).
- **delta:** 1e-2 (the value of Ganev, Annamalai & Kulynych, arXiv:2604.18352, so their figures are
  a reference point; this is a replication with stated deviations, not a reproduction).
- **Cells:**

| mechanism | target eps | runs per world |
|---|---|---|
| independent, moments, pairwise, fixed_workload | 1, 4 | 4000 |
| mst | 1, 4 | 2000 |
| aim, dpvae | 1 | 500 |

  AIM (7.8 s/fit) and DP-VAE (3.5 s/fit) are reduced for runtime, measured 2026-10-16 on this
  machine. Their bounded ceiling (125 runs per world) is still far above the proved bound at
  eps = 1 (§4).
- Seeds: run `i` uses seed `i` in `D_in` and `i + 10^6` in `D_out`. One job at a time.

## 3. Adversary and estimator (fixed before the runs)

- Features: the five count statistics in `features()`. Adversary: scikit-learn
  `GradientBoostingClassifier(random_state=0, n_estimators=60, max_depth=2)` trained on the first
  half of each world's runs.
- **Estimator:** `synthproof.audit.gdp.mu_lower_bound_heldout` on the second half. The threshold is
  chosen on the first half of the scored runs and the bound is computed on the remaining half
  (so 1/4 of the runs per world are bounded). Clopper-Pearson one-sided upper bounds on FPR and
  FNR at alpha/2 each, alpha = 0.05. This replaces the max-over-thresholds bound used up to
  2026-08-25, which chooses the threshold on the scores it bounds (in a 300-trial null
  simulation it exceeded 0 in 6.0–6.7% of trials against the nominal 5%).
- The biased max-over-thresholds value is also recorded, labelled as such, for comparison with the
  August results only.

## 4. Outcomes

- **Primary:** `eps_emp = eps_for_mu(mu_emp, delta)` beside `proved_eps`, the epsilon the
  accountant reports for those releases (profiling included), and the ceiling `eps_ceiling` for the
  bounded run count. Reported for every cell, null or not.
- **Violation test:** a cell is a violation if `mu_emp` exceeds the mu implied by `proved_eps`
  (`mu_from_eps_delta`), or the mechanism's own composed mu where the code exposes its noise
  (independent). With 12 cells, a violation is **claimed** only if it also holds at
  alpha = 0.05 / 12 (Bonferroni); a violation at 0.05 alone is reported as a flag to investigate.
- **Descriptive:** `eps_emp / proved_eps`. The word "tight" is used only for a ratio ≥ 0.8; there
  is no hypothesis about which mechanism scores highest.

## 5. What would change the conclusions

- `mu_emp = 0` in a cell is reported as "this adversary certified nothing", with the ceiling
  beside it, never as evidence of privacy.
- A violation stops the write-up of that mechanism until the cause (mechanism, accountant or
  audit) is found, and is recorded in `CORRECTIONS.md`.

## 6. Reporting

Every cell goes into `results/gdp/` (one JSON per cell) and a generated table in
`results/GDP_AUDIT.md`. Nothing is dropped. The August single-mechanism results stay in place
and are labelled superseded.

## 7. Amendments after the first run

None yet.
