# SynthProof — Thesis & Research Framing

> **Thesis Statement:**  
> Empirical canary privacy auditing ($\epsilon_{\text{audited}}$) of tabular generative mechanisms reveals significant, systematic gaps below formal theoretical differential privacy bounds ($\epsilon_{\text{proved}}$), and budget-charged domain profiling combined with signed hash-chain ledger allocation prevents privacy degradation across multi-release programs.

---

## Key Hypotheses

1. **H1 (Proved vs. Audited Gap):** Across tabular DP synthesis mechanisms (AIM/MST vs. Gaussian Copula), the empirical privacy loss recovered via one-run canary auditing ($\epsilon_{\text{audited}}$) is strictly lower than the formal RDP bound ($\epsilon_{\text{proved}}$), with the magnitude of the gap varying systematically by mechanism family and feature correlation structure.
2. **H2 (Subgroup Disparate Privacy Impact):** Under uniform DP budget allocation, records belonging to minority demographic subgroups exhibit higher empirical leakage ($\epsilon_{\text{audited}}$) than majority records at fixed target $\epsilon$.
3. **H3 (Ledger-Driven Utility Optimization):** Utility-weighted budget allocation across tabular feature columns driven by historic spend ledgers yields significantly higher downstream classifier macro F1 than uniform allocation at equal total privacy spend.
