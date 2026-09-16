# K3 audit-power kill-check — result: PASS (imputation audit is viable)

> The gate the pivot scout (`research/11_pivot_scout_2026-09-03.md`) insisted on before committing to
> the missing-data / imputation experiment: at the n we intend to use, can a membership-inference
> auditor resolve a KNOWN leak from a KNOWN-private release with non-overlapping CIs? If not, a null
> imputation result is uninterpretable and the audit is dead. Script: `scripts/k3_audit_power.py`.
> Data: UCI Adult, 12 seeds per cell, 95% bootstrap CIs over seeds. Private arm = `independent` at
> ε=1; leak arms = `LeakyGenerator` copying 25/50/100% of training rows verbatim. Not canary
> insertion (memory: canary contamination destroyed the signal); member-vs-non-member construction.

## Result

**PASS at n = 1000, 2000 and 4000.** Both auditors, at every n, separate even a **25% partial
verbatim leak** from the private baseline with non-overlapping 95% CIs.

| n | private (distMIA) | leak 25% (distMIA) | leak 50% | leak 100% | verdict |
|---:|---|---|---|---|---|
| 1000 | 0.501 [0.495, 0.507] | **0.550 [0.544, 0.557]** | 0.602 | 0.692 | PASS |
| 2000 | 0.500 [0.495, 0.506] | **0.541 [0.538, 0.545]** | 0.579 | 0.653 | PASS |
| 4000 | 0.497 [0.492, 0.502] | **0.531 [0.528, 0.535]** | 0.559 | 0.621 | PASS |

(DOMIAS separates too but is weaker; the **distance-MIA baseline is the more sensitive instrument**
for verbatim-copy leakage and should be the primary auditor.)

## What this establishes, and its honest limits

`INFERENCE:` The instrument is **not blind** at the n an imputation experiment would use. A null
result in the imputation grid would therefore be **interpretable** — it would mean "imputation leaks
less than a 25%-verbatim-copy-equivalent at this resolution", not "we couldn't measure anything."
That is the whole point of the gate, and it clears it. `CONFIDENCE: high` — non-overlapping CIs
across 12 seeds at three sample sizes.

Honest caveats to carry into the experiment:
1. **Effect sizes are small.** The detectable floor corresponds to roughly a **25% verbatim leak**
   (AUC ≈ 0.53–0.55 vs private ≈ 0.50). If the privacy loss from imputation-fitted-across-records is
   subtler than that, it will register as an (interpretable) null, not a positive. Both directions
   are publishable findings; neither is "we proved imputation is safe".
2. **Signal weakens as n grows** for a fixed leak fraction (leak-100% distMIA 0.692 → 0.621 as n
   goes 1000 → 4000), because more members dilute the per-record signal. Use **n ≈ 1000–2000** for
   the strongest power; do not push n higher thinking it helps the audit.
3. Adult's four numeric columns carry the MIA signal here; a categorical-heavy imputation target may
   need a categorical-aware attack (marginal-ratio) as a third instrument.

## Verdict for the imputation paper (arm 3A)

**Green-lit, with n ≈ 1000–2000 and distance-MIA as the primary auditor.** The experiment can now be
run knowing that a null is meaningful. Recommended design (from the pivot scout, scoped honestly):

- Arms: A0 complete-case drop (bias story only, **not** claimed as a leak); A1 `"?"`-as-category
  (zero extra budget); **A2 imputation fitted across records on private data (the suspected genuine
  violation)**; A3 the same imputation charged from the budget.
- Grid: A2/A3 vs A0/A1 × real AIM + the DP-SGD VAE × ε ∈ {1, 4} × ≥8 seeds, at n ≈ 1500.
- Primary readout: distance-MIA AUC (member vs non-member) with bootstrap CIs, A2 vs A3 vs A0.
- Pre-registered claim: "imputation fitted across records leaks membership above the charged-DP
  baseline" — confirmed if A2's CI sits above A3's; an interpretable null otherwise.

Do not claim `dropna` is a DP bug (row-wise stability-1 filter). Race risk: the Ganev group's
preprocessing-audit series is active; date the claim "unaudited at time of writing".

Artefacts: `scripts/k3_audit_power.py`, `research/imputation_audit/k3_audit_power.json`.
