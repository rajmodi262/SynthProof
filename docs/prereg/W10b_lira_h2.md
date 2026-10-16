# Preregistration — W10b: LiRA at 64 shadows, and H2 with an audit that can resolve epsilon 1

> **Committed 2026-10-16, before any run it governs.** Each output records this file's SHA-256.
> Amendments after the first run go in §5 with reasons, never edited in place.

## 1. LiRA (Carlini et al. 2022) at a full shadow count

- **Runner:** `scripts/run_lira.py` (positive control first: a verbatim-copy generator must reach
  AUC ≥ 0.9, or nothing else runs).
- **Cells:** independent and pairwise × epsilon 1 and 8, UCI Adult, train size 1000.
  **40 targets, 64 shadows, 8 challenges**, seed 0. Output `results/lira_w10.json`.
- **Not run, with the measured reason:** MST and AIM. An MST fit takes about 270 s at this train
  size (the 2026-10-12 run, `results/lira_mst.json`), so 40 × (64 + 8) fits per cell is roughly
  200 hours per cell on this machine. They are reported as not run, never as nulls.
- **Outcome:** AUC with its 95% interval resampled by target, TPR at 1% and 10% FPR. A cell whose
  interval contains 0.5 is reported as "no attack advantage detected at 64 shadows", a bounded
  null, not evidence of privacy. No multiplicity correction: these are descriptive.

## 2. H2 with a canary budget whose ceiling exceeds the proved epsilon at epsilon 1

- **Runner:** `scripts/run_h2.py`, pairwise, UCI Adult, 6000 rows, attributes sex and race, epsilon 1
  and 8, balanced canary allocation as in the original protocol.
- **Change from the original:** **4000** canaries in total (was 400) and **10 seeds** (0–9, was 3).
  Race has 5 levels, so each race subgroup gets 800 canaries, whose one-run ceiling is 5.586
  (`synthproof.audit.steinke.max_provable_epsilon(800)`), above a proved epsilon of about 1, so at
  epsilon 1 the per-subgroup audit could in principle certify the full proved budget. At epsilon 8
  no subgroup can (ceiling below 8); the epsilon-8 cells are reported with that stated.
  Output `results/h2_w10.json`.
- **Analysis:** `scripts/analyse_h2.py` as committed (Benjamini–Hochberg and Bonferroni across the
  subgroup tests, TOST against the detection-floor bound, minimum detectable epsilon per subgroup),
  run on the new file.
- **Claim rule:** a subgroup difference is claimed only if it survives Bonferroni. A null is reported
  beside each subgroup's ceiling and minimum detectable epsilon.

## 3. Order

After the W10 H1 confirmatory run finishes (one heavy job at a time): LiRA, then H2.

## 4. Reporting

Every cell, null or not. The earlier LiRA (16 shadows) and H2 (400 canaries) results stay and are
labelled as the smaller runs.

## 5. Amendments after the first run

None yet.
