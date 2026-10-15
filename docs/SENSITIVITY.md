# Sensitivity — one argument per charge site

Every place SynthProof charges privacy budget, what it perturbs, why the declared sensitivity is
right, and the test that fails if it stops being right. Written 2026-10-16 (W5), after the sweep
that produced it found four defects (listed at the end).

**Neighbouring relation.** Add/remove one record (`unit_of_privacy = add/remove-one-record`,
`contribution_bound = 1`). The release size is declared in advance and the input is subsampled to
it (`release_rows_source = declared`), so `n` in a sampling rate or a release size is public.

**How the declared sensitivity is checked.** `tests/test_sensitivity.py` swaps each generator's
noise sampler for a zero-valued recording array, captures the exact statistic the noise is added
to, fits on a table and on two neighbours (one record removed, one extreme record added), and
requires the statistic to move no more than the sensitivity passed to the accountant. A planted
10x understatement fails it. An observed change on chosen neighbours is a *lower* bound on the
true sensitivity, so the test is necessary, not sufficient — the arguments below are the proof.

**Real-valued queries.** The samplers emit integers and are a DP mechanism only for an integer
query. Any real-valued query goes through `accounting.noise.noisy_real_query`: rounded onto a grid
of `Delta / 1000`, with integer sensitivity `1001` (rounding moves a value by at most half a unit
each side), noise drawn at the same noise-to-sensitivity ratio, so the charged epsilon is unchanged.

| # | Site | Statistic perturbed | Mechanism | Sensitivity | Argument | Pinned by |
|---|---|---|---|---|---|---|
| 1 | `generators/independent.py` | one count vector per column (numeric: bins over the profiled range; categorical: the profiled domain) | discrete Gaussian, one charge per column | L2 = 1 | a record falls in exactly one cell of each column's histogram; removing or adding it changes that cell by 1 | `test_sensitivity[independent]` |
| 2 | `generators/pairwise.py` | root 1-way count vector; one 2-way joint count matrix per edge of a public chain | discrete Gaussian | L2 = 1 each | as (1): one cell per histogram. The chain is public, so the structure costs nothing | `test_sensitivity[pairwise]` |
| 3a | `generators/aim.py` measure | 1-way and selected-clique marginal count vectors | discrete Gaussian | L2 = 1 each | as (1) | `test_sensitivity[aim]` |
| 3b | `generators/aim.py` select | quality score `‖true − est‖₁ − penalty` per candidate clique | exponential mechanism, charged as zCDP ε²/8 | 1 | `est` comes from the model fitted to earlier noisy releases and `penalty` from public sizes, so under adaptive composition both are fixed; `‖true‖` moves by exactly 1 in L1 | argument only (see below); index use pinned by `test_aim_selection_index.py` |
| 3c | `generators/aim.py` model total | the table size used to fit the graphical model | post-processing | — | estimated from the noisy measurements, never read from the data (the D1 fix) | `test_model_total_is_private.py` |
| 4 | `generators/fixed_workload.py` | marginals of a public workload | discrete Gaussian | L2 = 1 each | as (1); the workload is public | inherits (3a) |
| 5a | `generators/mst.py` measure | 1-way and selected 2-way marginal count vectors | discrete Gaussian | L2 = 1 each | as (1) | `test_sensitivity[mst]` |
| 5b | `generators/mst.py` select | per-pair L1 error of the current model | exponential mechanism | 1 | as (3b) | argument only |
| 6 | `generators/moments.py` numeric | with x' = clip(x) − a in [0, w]: S1 = Σx', S2 = Σx'², N = count | discrete Gaussian via `noisy_real_query` (S1, S2) | w, w², 1 | one record contributes one term in [0, w] to S1, in [0, w²] to S2 and 1 to N | `test_sensitivity[moments]` |
| 6b | `generators/moments.py` categorical | count vector over the profiled domain | discrete Gaussian | L2 = 1 | as (1) | `test_sensitivity[moments]` |
| 7 | `generators/dpvae.py` | sum of per-example gradients clipped to C, each step | Gaussian, Poisson-subsampled at q = batch/n, T steps | L2 = C | one record contributes at most one clipped gradient to a step's sum; padding rows have weight 0; the update divides by the expected (public) batch size | `test_dpvae.py::test_batches_are_poisson_not_fixed_size`; RDP ≥ PLD in `test_differential_accounting.py` |
| 8a | `data/profiler.py` declared range | — | none | 0 | a declared public range reveals nothing and is charged nothing | `test_profiler_soundness.py` |
| 8b | `data/profiler.py` undeclared range | min and max | discrete Laplace via `noisy_real_query` | **assumed** | min/max of an unbounded column has unbounded sensitivity; the charge rests on the configured sensitivity being true. **Not a DP guarantee** unless it is; the boundary auditor flags inferred domains (RB6). Declare bounds instead | `test_profiler_soundness.py` |
| 8c | `data/profiler.py` categorical domain | counts of observed values, thresholded | discrete Laplace, stability-based histogram | L1 = 1, L∞ = 1 | one record changes one count by one; the δ-calibrated threshold `1 + b·log(1/2δ)` bounds the chance a singleton survives (Rogers 2023, Alg. 1) | `test_profiler_soundness.py` |
| 9a | `data/imputation.py` A3 categorical | counts over the declared categories | report-noisy-max, Laplace(1/ε) | L1 = 1 | one record changes one count by one | `test_imputation.py` |
| 9b | `data/imputation.py` A3 numeric | shifted sum (via `noisy_real_query`) and count | discrete Laplace | w, 1 | each record contributes [0, w] after shifting by the public lower bound | `test_imputation.py`, `test_sensitivity.py` grid tests |
| 10 | `data/imputation.py` A4_CHARGED | k-NN vote vectors / shifted neighbour sums | report-noisy-max / discrete Laplace | 2 / w | **Not a proven DP mechanism**: the per-query ε divides by the number of missing cells, a private count. A budget-debited heuristic comparator, labelled as such | `test_imputation.py` |
| 11 | `audit/boundary.py` | — | none | — | recomposes the declared events to check the claimed ε; reads no data | `test_release_boundary.py` |

## Why selection is argued, not measured

AIM's and MST's selection scores depend on a model fitted to the *earlier* noisy measurements. In
the zero-noise recording test those earlier releases differ between the two neighbours, so the
score difference mixes the data change with a model change and is not a clean sensitivity
measurement. Under adaptive composition the earlier outputs are conditioned on — fixed — and only
`‖true marginal‖₁` depends on the data, which moves by exactly 1.

## Defects this sweep found (fixed 2026-10-16)

1. **Integer noise on real values** — `moments` mean/std, profiler min/max, imputation sums. The
   output kept the true value's fractional part, so neighbours had disjoint supports and the
   release was not DP at any ε. Fixed by `noisy_real_query`.
2. **`moments` sensitivity** — a clipped mean charged at 1.0 has sensitivity (b − a)/n (audit F5).
   Replaced by the S1/S2/N queries in row 6.
3. **A4_CHARGED raw sum** — perturbed `Σx` (sensitivity max(|lo|, |hi|)) while charging width.
   Now the shifted sum.
4. **DP-VAE sampling** — accounted as Poisson, trained on fixed-size batches. Now Poisson in the
   loop.

Results produced by the old code for these mechanisms are listed in `CORRECTIONS.md`.
