# SynthProof — Experiment Preregistration Document

> **Date:** 2026-08-05  
> **Authors:** Raj Modi, Krishna Renuse, Aaditya Kumar Sinha, Levinesh G R  
> **Tag:** `prereg-v1`  

---

## 1. Primary Hypotheses

- **H1 (Main Thesis):** The ratio of empirical audited privacy loss to formal theoretical privacy loss ($\epsilon_{\text{audited}} / \epsilon_{\text{proved}}$) significantly differs across generator mechanisms (AIM/MST vs. Gaussian Copula) at equal target $\epsilon$.
- **H2 (Subgroup Disparate Impact):** Under uniform DP budget allocation, empirical audited privacy loss ($\epsilon_{\text{audited}}$) is significantly higher for minority demographic subgroups than for majority groups.
- **H3 (Adaptive Allocator Utility):** Utility-weighted budget allocation across tabular columns yields significantly higher downstream classifier macro F1 than uniform allocation at fixed total $\epsilon$.

---

## 2. Experimental Parameters

- **Datasets:** UCI Adult ($n=48,842$), ACSIncome ($n=100,000$).
- **Privacy Budget Grid ($\epsilon$):** `[0.5, 1.0, 2.0, 4.0, 8.0]`
- **Target Delta ($\delta$):** $1 \times 10^{-5}$ (ensuring $\delta < 1/n$).
- **Random Seeds per Configuration:** 5 seeds.
- **Primary Metric:** Downstream ML macro F1 score (TSTR: Train on Synthetic, Test on Real).
- **Primary Privacy Metric:** Empirical lower bound $\epsilon_{\text{audited}}$ recovered via one-run canary score distribution analysis (Steinke et al., 2023).

---

## 3. Commitment to Unbiased Reporting

All experimental runs conducted under this pre-registered protocol will be reported in `results/RESULTS.md` regardless of whether the outcomes support or refute H1, H2, or H3.
