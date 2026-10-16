# Preregistration — W10: is AIM better than pairwise at preserving structure, or equivalent?

> **Committed 2026-10-16, before any run it governs.** The output file records this file's
> SHA-256. Amendments after the first run go in §7 with reasons, never edited in place.

## 1. Question

The 5-seed H1 grid (`results/H1_RESULTS.md`, now the **pilot**) separates both AIM and pairwise
from `independent` on structure, but its AIM and pairwise intervals overlap. With adequate seeds,
is AIM's correlation error lower than pairwise's, higher, or equivalent within a margin fixed now?

## 2. Design

- **Datasets:** the four H1 datasets — adult, acs, bank, diabetes — at the H1 protocol size
  (`scripts/run_h1.py`, 6000 rows, declared schemas, the same structure columns). The full tables
  are not run: AIM costs about 70 s per cell at 6000 rows (checkpoint timestamps of the pilot), and
  grows with n; this is a compute limit, stated.
- **Mechanisms:** aim, pairwise, and independent (the reference the pilot already separates).
- **Epsilon:** 1 and 8 (delta 1e-5), the low and high ends where the pilot's AIM-pairwise ordering
  was least and most settled.
- **Seeds:** 100–114 (15 per cell), **disjoint from the pilot's seeds 0–4**, so no confirmatory
  observation was seen when this plan was written.
- **Code:** the repository at the commit that adds this file. Output:
  `results/h1_confirmatory/<dataset>.json`; checkpoints `results/h1_confirmatory/<dataset>_cells/`.

## 3. Outcome and comparisons

- **Primary outcome:** `correlation_error` (mean absolute difference between real and synthetic
  pairwise correlations over the structure columns), per cell.
- **Primary comparisons (8):** AIM vs pairwise, for each dataset × epsilon.
  - Difference: Welch two-sample test; **Holm** correction across the 8 at family-wise alpha 0.05.
    A difference is claimed only if it survives Holm.
  - Equivalence: TOST with margin **±0.005** absolute correlation error, alpha 0.05 / 8
    (Bonferroni) per comparison. Equivalence is claimed only if TOST rejects both one-sided nulls.
  - **Margin rationale (fixed now, from the pilot, not from the confirmatory data):** half the
    pilot's AIM correlation error at epsilon 8 on Adult (0.0105), i.e. the smallest difference
    that would change which mechanism a practitioner should prefer on this metric.
  - Each comparison is reported as exactly one of: AIM lower · pairwise lower · equivalent ·
    **inconclusive** (neither a Holm-surviving difference nor TOST equivalence).
- **Secondary (descriptive, no claims):** AIM and pairwise vs independent; TSTR F1; proved epsilon
  per cell.
- **Power / MDE:** for every comparison, the minimum detectable difference at 80% power given the
  observed pooled SD and n = 15 per arm, reported beside the result.

## 4. What is reported regardless of outcome

All 24 dataset × epsilon × mechanism cells with mean, SD and 95% CI; all 8 primary verdicts,
including inconclusive ones; the MDE. The pilot table stays as the pilot.

## 5. Stopping

None: all 360 fits run (4 × 2 × 3 × 15). A crashed cell is re-run with the same seed; a cell that
cannot complete is reported missing with its error, never dropped silently.

## 6. Deviations from the paper protocols

None claimed: this is an internal confirmatory comparison, not a replication.

## 7. Amendments after the first run

None yet.
