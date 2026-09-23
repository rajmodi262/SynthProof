# 23c — Generalisation benchmarks: five more UCI datasets + a categorical-aware evaluator (2026-09-23)

> Extends the H1 grid (Adult, ACS, Bank, Diabetes) with five more public UCI benchmarks chosen
> to stress generalisation across data **types**, and records the evaluator upgrade that made
> two of them runnable. Reduced grid (ε ∈ {1, 4}, seeds {0, 1}) — a smoke/generalisation pass,
> not the preregistered grid. Standing rules apply: numbers below are copied from the runner,
> reduced runs are labelled reduced, nothing is invented.

## Why these five
| Dataset | Domain | Rows | Type | Literature use |
|---|---|---|---|---|
| Mushroom | biology | 8,124 | **all-categorical** | classic UCI benchmark |
| Nursery | admissions | 12,958 | **all-categorical, 4-class** | classic UCI benchmark |
| German Credit (Statlog) | finance | 1,000 | mixed | standard DP-synthetic benchmark |
| Wine Quality (red) | chemistry | 1,599 | all-numeric | standard benchmark |
| Breast Cancer Wisconsin | **healthcare** | 569 | all-numeric | standard benchmark |

## The blocker we hit, and the upgrade
The generators (AIM/MST/independent/pairwise) already synthesise all-categorical tables. The
**evaluator** did not: `UtilityEvaluator` trained on numeric feature columns only (raised on an
all-categorical table), the structure metric was Pearson-only (NaN for categorical), and two
distance-based attacks (DistanceMIA, DOMIAS) required a numeric column. Fixed by:

1. **Categorical-aware TSTR/TRTR** — one-hot encode categorical features against a vocabulary
   built from real+synth, so all three models share a feature space. (`evaluate/utility.py`)
2. **Categorical marginal fidelity** — Total-Variation distance per categorical column, alongside
   the existing standardised Wasserstein-1 for numeric columns.
3. **Mixed association matrix** — the structure metric now uses |Pearson| (num–num),
   correlation-ratio η (num–cat) and bias-corrected Cramér's V (cat–cat). It reduces **exactly**
   to the old Pearson computation when every column is numeric, so committed numeric results do
   not move (guarded by `tests/test_categorical_evaluation.py::test_all_numeric_path_is_unchanged_pearson`).
4. **Honest N/A for distance attacks** — MIA/DOMIAS report `not_applicable` on all-categorical
   releases instead of crashing (same rule linkability already followed).

New tests: `tests/test_categorical_evaluation.py` (7). All existing utility/data-sheet/script
tests still pass.

## Results (reduced grid: best of ε∈{1,4}, % of each dataset's real-data TRTR ceiling)
| Dataset | Ceiling (TRTR-F1) | independent | pairwise | AIM | MST | Best corr/assoc err |
|---|---|---|---|---|---|---|
| Mushroom | 0.998 | 51% | 54% | **98%** | **98%** | 0.019 (AIM) |
| Nursery | 0.945 | 28% | 55% | 71% | **75%** | 0.003 (pairwise) |
| German Credit | 0.663 | 76% | **80%** | 70% | 77% | 0.066 (MST) |
| Wine (red) | 0.765 | 67% | 86% | 67% | **89%** | 0.091 (pairwise) |
| Breast Cancer Wisc. | 0.953 | 63% | 51% | 59% | **89%** | 0.50 (AIM) |

## What it shows (honest reading)
- **The pipeline generalises** across five unseen datasets and three data types.
- **MST is the all-rounder** — best or tied-best on 4 of 5 (and strong on the 5th).
- **AIM is type-dependent**: excellent on categorical (Mushroom 98%) but weaker on continuous
  (Wine 67%, BCW 59%). AIM bins continuous columns, which costs utility there. A real,
  reportable characterisation, not a defect.
- **Fidelity needs scale**: Breast Cancer (569 rows, 10 numeric cols) has poor correlation
  fidelity (~0.5–1.0) — too little data to pin the structure. Consistent with the census results
  where fidelity improved markedly with row count.

## Utility engineering — levers tried, and the honest verdict (2026-09-23)
Goal: raise TSTR/ceiling at fixed (eps, delta) WITHOUT spending privacy silently. Disciplined
rule: keep a lever only if it improves the mean AND holds on >=2 datasets across 5 seeds.

1. **Oversample synthetic rows** (free post-processing). BCW +2% at a 3k sweet-spot but worse at
   8k; German monotonically worse. **Dataset-specific, rejected as a default.**
2. **More uniform bins** (12 -> 20; still public range, so no RB9 leak). Single-seed looked like
   +5% for MST on Wine and BCW, but **5-seed means overturned it**: Wine 87.6% -> 85.9% (worse),
   BCW 92.9% -> 96.5% (better but seeds swing 85-104% at n=569). Fails the >=2-dataset rule.
   **Rejected.** (The smoke-test "win" was luck — this is why the multi-seed rule exists.)

**Verdict: the mechanisms are already at their honest utility ceiling; there is no clean knob
that lifts all datasets.** The one reliable, privacy-free lever that survives is **mechanism
selection by data type**: categorical -> AIM (Mushroom 99%), everything else -> MST (best on
6/9). That needs no tuning and is a defensible contribution, not a fabricated number.

## Reproduce
```
python -m scripts.run_h1 --dataset mushroom --eps 1 4 --seeds 0 1
python -m scripts.run_h1 --dataset nursery  --eps 1 4 --seeds 0 1
python -m scripts.run_h1 --dataset german   --eps 1 4 --seeds 0 1
python -m scripts.run_h1 --dataset wine     --eps 1 4 --seeds 0 1
python -m scripts.run_h1 --dataset bcw      --eps 1 4 --seeds 0 1
```
Each dataset is a pinned `DatasetSource` (SHA-256) in `synthproof/data/datasets.py`; full grid
(ε 0.5–8, 5 seeds) is the next step for publication-grade numbers.
