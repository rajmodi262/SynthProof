# Chapter 6 — Experimental Methodology

**Target: 1,200 words.** Depends on M1.11.
**This chapter must honour [`../preregistration.md`](../preregistration.md) exactly.**

## 6.1 Preregistration (~200 words)

State that hypotheses were registered before any sweep ran, with the commit hash and tag.
State the commitment to report results regardless of direction — and then honour it in Ch.7.

## 6.2 Datasets (~250 words)

UCI Adult (n = 48,842, 14 columns) and ACS PUMS via `folktables`. Provenance, licence,
preprocessing, and SHA-256 checksums. Name the subgroup variables used for H2 and justify the
choice.

## 6.3 Experimental design (~350 words)

- ε grid {0.5, 1, 2, 4, 8}; δ = 1e-5 (justify δ < 1/n).
- 5 seeds per cell; state what varies per seed and what is held fixed.
- Train/test protocol: TSTR and TRTR scored on the **same** held-out real split. Explain why —
  the earlier in-sample TRTR produced a constant 0.971 and a meaningless utility gap.
- Which mechanisms are compared and what genuinely distinguishes them.

## 6.4 Metrics (~250 words)

- **Privacy:** ε_proved (RDP composition), ε_audited (Clopper-Pearson lower bound), audit
  p-value (Fisher exact).
- **Attacks:** AUC and **TPR at 0.1% FPR**. Justify via Carlini et al. (2022) — average-case
  accuracy is the wrong metric for membership inference.
- **Utility:** macro F1 (TSTR/TRTR), Wasserstein-1 marginal distance, correlation preservation.

## 6.5 Statistical analysis (~150 words)

Bootstrapped confidence intervals, multiple-comparison handling, and the significance threshold
— fixed in advance, not selected after seeing results.

## 6.6 Reproducibility (~150 words)

Seed policy, environment capture, `make reproduce`, and the emitted manifest hash.
