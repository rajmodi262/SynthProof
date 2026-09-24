# 27 — Brutal system audit (2026-09-24)

Scope: generators (AIM, MST), accountant + calibration, DP profiler, dataset schemas, experiment
runner, utility/structure evaluation, attacks, canary audit, boundary-audit, signing, CLI, tests.
Every finding below was checked against the code or measured; line numbers are as of commit c9336e8.

## CRITICAL — DP correctness and honesty

| # | Finding | Evidence | Fix |
|---|---|---|---|
| C1 | **Category-domain release violates the declared δ, even with a declared schema.** `_profile_categorical` noises only the *observed* categories, so a public category with count 0 can never be kept while one with count 1 survives with p ≈ 1/51 at ε=1 (the code's own figure). That is δ ≈ 2·10⁻², not 10⁻⁵. The docstring's mitigation ("a declared schema means thresholding cannot release anything new") is false for this reason. | `data/profiler.py:370-389`, `_legacy_category_threshold` is the default | With a declared domain: noise **every** public candidate (pure ε-DP, no δ). Without one: make the δ-calibrated threshold the default. |
| C2 | **"Public" numeric bounds equal the observed extremes** — the exact data-derived-domain leak of P4, on P4's own dataset. Wine free SO₂ 1–72, total SO₂ 6–289; Diabetes lab procedures 1–132, medications 1–81, diagnoses 1–16; Adult age 17–90, hours 1–99. RB6 passes these because the sheet says "public". | `data/datasets.py:96-97, 403-406, 672-681`; observed min/max printed and matched | Replace with externally sourced / rounded bounds (e.g. 0–100, 0–300); add a lint test that fails when any declared bound equals the observed extreme. |
| C3 | **Distance MIA silently reports AUC = 0.50 on all-categorical tables.** `_scores` returns zeros when there is no numeric column; every one of the 300 Mushroom / Nursery / SF-Fire cells shows exactly 0.500, read as "attacker at chance". Contradicts the code's own rule that an absent check must never look passed. | `attacks/distance_mia.py` `_scores`; all cells = 0.5 | Raise → NaN "not applicable"; add a Gower / one-hot distance so categorical tables get a real attack. |
| C4 | **boundary-audit does not verify the signature, and RB5 trusts a self-reported verdict.** The checker reads `accountant_agreement.verdict` as written; a maker can type `"agree"`. The CLI registers `boundary-audit` **twice** (`cli.py:422` and `:789`); the second silently replaces the first. | `audit/boundary.py:323-360`, `cli.py` | Verify the Ed25519 signature inside boundary-audit when a key is given; embed the signed mechanism event list and **recompute ε with both accountants in the checker**; delete the duplicate command. |

## HIGH — mechanism quality (why results are not better)

| # | Finding | Evidence | Fix |
|---|---|---|---|
| H1 | **18–25 % of every privacy budget is never spent.** Proved ε at target 1: AIM 0.777, MST 0.760, baselines 0.911; at target 8: 6.53 / 6.36 / 7.34. Stages are calibrated separately and RDP composition is sub-additive. | SF Fire per-cell files; reproduced on Adult (6.54 at 8) | One global calibration over the full event list (`calibrate_weighted_scales` already exists); `BudgetPlan.tighten` is implemented but off. |
| H2 | **AIM is under-powered.** 6 fixed rounds measure 6 of 36–105 pairs; the selection score has no domain-size penalty; no target-aware workload. On SF Fire AIM **never measured a pair containing the target** `als_unit` → 67 % vs MST 97 %. | Instrumented fit: measured cliques listed, none include `als_unit` | Budget-driven rounds (~2d), AIM's penalised score, seed the target's pairs, exponential-mechanism (Gumbel) selection accounted as ε²/8-zCDP — measured 1.80 → 1.54 ε for the same selections at ε=8. |
| H3 | **AIM measures the wrong pair once any clique is skipped.** `pick` indexes `affordable`, but `remaining.pop(pick)` removes from `remaining`. Latent (no skips in the runs checked), MST does it correctly. | `generators/aim.py:322-323` vs `mst.py:247-248` | `clique = affordable[pick]; remaining.remove(clique)`. |
| H4 | **Suppressed categories are folded into a real category (level 0)**, inflating that category's count. | `aim.py:183-185`, `mst.py:126-128` | Add an explicit OTHER level. |
| H5 | **Uniform 12-bin discretisation** over wide public ranges collapses heavy-tailed columns (capital_gain, TOTAL_CHARGES, balance) into 1–2 bins. P5 reports +9–44 % utility from better binning. | `aim.py:161` | DP quantile / PrivTree bins, or log-scale bins for heavy tails. |
| H6 | **JAX float32 above 100K rows.** The code comment says grids run at 6,000 rows so the warning "does not apply" — the full grids now fit 70K–214K rows (Texas, ACS, Fire). | `aim.py:85-94` | Enable x64 when n > 100K; rerun those three datasets. |

## MEDIUM — evaluation validity

| # | Finding | Evidence | Fix |
|---|---|---|---|
| M1 | **"Structure error" is one correlation coefficient** on most datasets: `corr_cols` is a single pair (Adult age/hours, Texas LOS/charges, Bank age/balance, Diabetes 2 cols). The headline "0.103 vs 0.008" is one number. | `scripts/run_h1.py` DATASETS | All-pairs association matrix over every column + mean TVD of all 2-way marginals. |
| M2 | **TSTR is tested on rows the generator trained on**; the 30 % `holdout_df` is never used for utility. Measured effect on Adult: ≤ 1.6 pp, both directions — the result survives, the method is still wrong. | `experiment.py:460-464`, `utility.py:119` | Train real/synth models, test both on `holdout_df`. |
| M3 | One classifier (RF, 20 trees), one split. Seed spread is large (AIM Adult 74–80 %). | measured above | Add logistic regression + gradient boosting; report the mean. |
| M4 | **Canary audit certifies ε = 0.000 everywhere** (ceiling 2.97 at m = 60): on DP mechanisms it measures nothing. | all grids | Use the GDP / f-DP estimator already in `audit/gdp.py` (Ganev, Annamalai & Kulynych 2026 obtain tight audits on AIM/MST). |
| M5 | MIA is weak: numeric-only nearest neighbour on 400 records; ignores 8 of Adult's 12 columns. | `distance_mia.py` | Mixed-type distance, more records, report TPR@1 % FPR as the headline. |

## LOW

- L1 Selection charged as a Laplace mechanism though report-noisy-max is not one; measured gap +0.001–0.002 ε (negligible). Closed by H2's switch to the exponential mechanism.
- L2 4 failing tests: two stale generated tables (Bank, Adult) after the full reruns, a test double missing `sampling_rate`, and the pre-existing ACS pin. 1,010 pass.
- L3 `measured_cliques_` is not reset between fits; `UtilityEvaluator` mutates the global NumPy seed.
- L4 Accountant budget is `target × 1.02` — an unexplained 2 % overshoot allowance.

## What held up

The accountant correctly delegates to Google `dp_accounting` with a second-library cross-check;
the `known_total=None` fix; seeded, reproducible sampling; Ed25519 canonicalisation (only
1.0 → 1 normalisation); checkpointed grids; 1,010 of 1,016 tests pass; and the usefulness numbers
survive the held-out re-test (M2).

## Presentation claims these findings contradict

- "real test rows held out" (experiment slide) — false until M2 is fixed.
- "the signature is verified first" (checker slide) — boundary-audit does not verify it (C4).
- "MIA ≈ 0.50" for Mushroom / Nursery / SF Fire — not a measurement (C3).
- "public ranges cost 0" — for Wine and Diabetes the "public" ranges are the data's own extremes (C2).

---

## Fix log (2026-09-24, branch `fix/brutal-audit`)

| # | Status | What changed | Regression test |
|---|---|---|---|
| C1 | FIXED | A declared category domain is released whole and free (reads no data); undeclared domains use the δ-calibrated threshold by default. All 11 registry datasets declare their domains, so profiling now costs 0. | `test_data.py::test_declared_category_domain_is_used_whole_and_costs_nothing` (identical output on neighbouring tables, 20 seeds) |
| C2 | FIXED | Data-derived bounds replaced with round public ranges (Adult age 15–100, hours 0–100; Diabetes labs 0–150, meds 0–100, diagnoses 0–20; Wine SO₂ 0–100 / 0–300, citric 0–2, sulphates 0–2.5; Bank age 15–100; German duration 0–80). | `test_public_bounds_not_data_derived.py` fails if any declared non-zero bound equals the observed extreme (allowlist: loader clips and codebook ranges, each with its reason) |
| C3 | FIXED | Distance MIA measures categorical columns (mismatch count) and raises when there is nothing to compare; Adult now uses all 12 columns, all-categorical tables get a real attack. | `test_mia_categorical.py` (copy leak AUC > 0.9 on an all-categorical table; no constant 0.5) |
| C4 | FIXED | `boundary-audit --pubkey` verifies the signature first (RB0); sheets carry signed `mechanism_events` and RB5 recomposes ε with both accountants; a self-reported verdict without events is UNVERIFIABLE; duplicate CLI command removed. | `test_boundary_audit.py` (4 new: recompute, understated ε caught, self-report not trusted, tampered label fails RB0) |
| H1 | FIXED | One zCDP budget per release (AIM, MST); proved ε now equals the target (1.000 / 7.9996) instead of 0.78 / 6.5. Profiling share goes to synthesis when the schema is declared. Accountant cap = target (the 2 % slack is gone, L4). | `test_aim.py::test_aim_spends_its_whole_budget`, `test_mst.py::test_mst_spends_its_whole_budget` |
| H2 | FIXED | AIM rebuilt: exponential-mechanism selection (ε²/8-zCDP), AIM's noise penalty, sensitivity 1 (add/remove), no repeat measurements, d rounds, TARGET workload (3-way marginals with the declared target). MST: thirds split, EM selection. | `test_aim.py::test_selection_is_charged_as_the_exponential_mechanism`, `test_accounting.py::test_the_exponential_mechanism_is_charged_by_its_zcdp_bound_and_autodp_agrees` |
| H3 | FIXED | `clique = affordable[pick]`. | `test_aim_selection_index.py` (fails on the old code: measured ('b','d') when ('c','d') was selected) |
| H4 | FIXED | Thresholded domains get an explicit OTHER level (decided by the DP profile only). | encoder in `generators/_marginal.py` |
| H5 | FIXED | Log-scale bins for non-negative public ranges reaching ≥ 1,000 (capital_gain, TOTAL_CHARGES, credit_amount…); rule reads only public bounds. | `generators/_marginal.py::bin_edges` |
| H6 | FIXED | JAX x64 for estimation; sampling casts to float32 (private-PGM's sampler writes into a read-only float64 view otherwise). | exercised by every AIM/MST test |
| M1 | FIXED | Cells report `structure_error_all` (mixed association over every column pair) and `pair_tvd` (mean 2-way TVD). | sanity: 0 on identical tables, 0.154 / 0.080 on column-shuffled Adult |
| M2 | FIXED | Utility scored on `holdout_df`, rows neither release saw. | `test_categorical_evaluation.py::test_utility_is_scored_on_the_given_unseen_rows` |
| M3 | FIXED | `usefulness_multi` = mean TSTR/TRTR over random forest, logistic regression, gradient boosting. | — |
| M4 | IN PROGRESS | GDP audit re-run on the rebuilt AIM / MST / independent (`results/gdp_audit_*.json`). | the audit itself: μ_emp must stay below the implied μ |
| M5 | FIXED | with C3. | — |
| L1 | FIXED | with H2. | — |
| L2 | PARTLY | ACS pins of retracted findings removed with notes; coverage test double fixed; Bank / Adult generated tables regenerate after the re-run. | — |
| L3 | FIXED | cliques reset per fit; global NumPy seeding removed from the evaluator. | — |

### A/B evidence for the AIM rebuild (unseen-row usefulness, seed 0; `scripts/ab_aim_config.py`)

| Dataset | ε | old AIM | new AIM | MST (new) |
|---|---|---|---|---|
| SF Fire | 1 | 67 % (5-seed, old eval) | **98.4 %** | 98.3 % |
| SF Fire | 8 | 67 % | **99.0 %** | 98.1 % |
| Adult | 1 | 74–80 % | **93.3 %** | 82.5 % |
| Adult | 8 | 74–80 % | **94.3 %** | 83.9 % |

Annealing on/off at d rounds: Fire ε=1 79 % / 98 %, Adult ε=1 90 % / 93 % — so it is opt-in.
Every grid number is superseded by the `audit27` re-run (`PIPELINE_VERSION` in every cell hash);
pre-fix aggregates are kept in `results/archive_pre_audit27/`.
