# SynthProof: Brutal Capstone Project Review & Rating

> **Project Title:** SynthProof: Synthetic Data That Ships With Its Proof  
> **Domain:** Differential Privacy, Trustworthy Machine Learning, Generative Modeling, Data Governance  
> **Team:** Raj Modi (P1), Krishna Renuse (P2), Aaditya Kumar Sinha (P3), Levinesh G R (P4)  
> **Institution:** MIT World Peace University, Pune (CSE-AIDS Level 1, Panel B)  

---

## 1. Overall Scorecard & Executive Verdict

| Dimension | Rating | Verdict |
|---|---|---|
| **Ambition & Theoretical Depth** | **9.8 / 10** | Research-paper grade (NeurIPS / USENIX Security workshop tier). Far above standard undergraduate capstones. |
| **Industry Relevance & Problem Framing** | **9.5 / 10** | Identifies a massive blindspot: published $\epsilon$ guarantees are rarely audited, budget leakage across releases is ignored, and schema profiling cheats. |
| **Engineering Architecture** | **9.2 / 10** | Impressive modularity, clear component separation, append-only budget ledger, pre-registration, and comprehensive CI/CD. |
| **Feasibility & Execution Risk** | **4.5 / 10** | **DANGER ZONE.** 958 tasks across 12 phases in 12 weeks for 4 students is an extreme over-engineering trap. Hardware constraints (4GB RTX 3050) will cause severe compute bottlenecks. |
| **Panel / Viva Presentation Risk** | **6.0 / 10** | High risk of over-explaining dense DP math while college evaluators ask basic questions like *"Where is the accuracy graph?"* or *"Why didn't you just use CTGAN?"*. |
| **OVERALL WEIGHTED RATING** | **8.6 / 10** | **A Masterpiece on Paper, a Nightmare to Deliver Unscoped.** |

---

## 2. What Makes This Project Outstanding (The "Drool" Factor)

1. **Dual-Sided Assurance ($\epsilon_{\text{proved}}$ vs. $\epsilon_{\text{audited}}$):**  
   - Most synthetic data libraries (SDV, SmartNoise, Synthcity) either generate with formal DP without auditing, or audit without knowing the DP mechanism. SynthProof bridges this gap directly by reporting the empirical gap between proved and audited privacy loss.
2. **Charging the Schema Discovery (DP Profiler):**  
   - A critical, under-discussed leak in literature: inferring minimum/maximum bounds and category sets from raw data without spending budget. Charging this step to the accountant is mathematically honest.
3. **Budget Ledger vs. Per-Run Flag:**  
   - Moving from $\epsilon$ as a CLI argument to an append-only, signed, cryptographic ledger. This treats DP budget as a finite organizational asset across multiple dataset releases.
4. **Research Methodological Rigour:**  
   - Pre-registration (`preregistration.md`), metamorphic testing (24 relations), differential testing against reference accountants (Google `dp-accounting`, `autodp`), and mutation testing (`mutmut` target 80%) reflect elite software engineering and scientific standards.

---

## 3. Brutal Reality Check & Hidden Trapdoors

### ⚠️ Trap 1: The Compute & Hardware Bottleneck (The 4GB RTX 3050 Wall)
- **The Issue:** Private Tabular Diffusion (Latent VAE + Denoising Diffusion under DP-SGD via Opacus) is computationally heavy and VRAM-intensive. Furthermore, running membership inference attacks (LiRA) often requires training **dozens or hundreds of shadow models** to establish empirical distributions.
- **The Brutal Reality:** A single RTX 3050 laptop GPU with 4GB VRAM will frequently hit **CUDA Out-Of-Memory (OOM)** errors when computing per-sample gradients in DP-SGD or running diffusion sweeps. Sweeping 5 $\epsilon$ values $\times$ 3 seeds across 4 datasets could easily take **100+ hours of uninterrupted compute time**, during which thermal throttling will kill performance.
- **Fix:** Do not run Phase 9 sweeps on a laptop. Utilize Google Colab Pro, Kaggle free T4/P100 GPUs, or a cloud instance (AWS/GCP credit).

### ⚠️ Trap 2: The Canary Auditor Complexity on Tabular Generators
- **The Issue:** One-run privacy auditing (Steinke et al., 2023) was designed for gradient descent models (DP-SGD). Translating this cleanly to marginal mechanisms (AIM / MST / Private-PGM) is mathematically tricky.
- **The Brutal Reality:** How do you plant a "canary record" in AIM when AIM selects marginals based on exponential mechanism scoring? If the canary record does not heavily influence the selected cliques, the empirical lower bound ($\epsilon_{\text{audited}}$) will be near 0, yielding an uninformative proved-vs-audited gap.
- **Fix:** Validate the auditor on standard DP-SGD / DP-Gaussian mechanisms first before trying to prove canary lower bounds on complex combinatorial mechanisms like AIM.

### ⚠️ Trap 3: The 958-Task Mental Fatigue & Project Management Overhead
- **The Issue:** `TASKS.md` is 1,809 lines long with 958 tasks.
- **The Brutal Reality:** Managing this task board will become a full-time job. By Week 4, team members will stop updating individual `[ ]` check-boxes due to fatigue. 
- **Fix:** Immediately adopt Section **X.5 (Minimum Viable Capstone)** as your primary sprint scope (~180 tasks). Treat the remaining 778 tasks as optional stretch goals.

### ⚠️ Trap 4: Single Point of Failure Dependencies (P1 & P3 Bottlenecks)
- **The Issue:** 
  - **P1 (Raj)** owns the Privacy Accountant, Budget Ledger, Allocator, and Frontier Engine. If Phase 1 slips, Phase 5 and Phase 8 stall.
  - **P3 (Aaditya)** owns the Canary Auditor and Attack Range (LiRA, DOMIAS, Anonymeter). If LiRA shadow training fails or takes too long, Phase 6 and Phase 9 slip.
- **The Brutal Reality:** Parallel swimlanes in section X.4 help, but the code integration points (Phase 5 depending on Phase 1 & 4) will create severe blockage if one person falls sick or hits a wall.

---

## 4. Phase-by-Phase Technical Critique

### Phase 0: Setup & Experiment Design
- **Critique:** Excellent. Creating an empty results table and committing `preregistration.md` before writing code prevents p-hacking and arbitrary metric tweaks.
- **Warning:** 120 tasks in Week 1 is unrealistic. Ensure `check_env.py` and repository layout are done, but don't spend 4 days tweaking `.pre-commit-config.yaml`.

### Phase 1: Privacy Accountant
- **Critique:** Top-tier rigour. Differential testing against Google `dp-accounting` and `autodp` guarantees mathematical correctness.
- **Warning:** Discrete Gaussian sampling (`Canonne–Kamath–Steinke`) to prevent floating-point vulnerabilities is great research, but ensure it doesn't slow down standard generator loops.

### Phase 2: Budget Ledger & Allocator
- **Critique:** Append-only SQLite/Postgres with Ed25519 signatures and hash chains is clean and demo-ready.
- **Warning:** Avoid over-complicating key management or multi-node consensus. A local signed hash chain is more than sufficient for capstone scope.

### Phase 3 & 4: Data Layer & Generator Bank
- **Critique:** AIM/MST (marginal-based) is the absolute best choice for tabular DP data (NIST competition winner).
- **Warning:** Tabular Diffusion (VAE + Diffusion head under DP-SGD) is a major time sink. If Krishna gets stuck on diffusion loss convergence, **cut Diffusion immediately and ship AIM + Gaussian Copula.**

### Phase 5 & 6: Auditor & Attack Range
- **Critique:** Having 4 attacks (LiRA, Attribute Inference, Anonymeter, DOMIAS) creates an unbeatable evaluation suite.
- **Warning:** LiRA on tabular datasets can be noisy. Ensure you have clear positive controls (non-private CTGAN where attacks succeed with >80% accuracy) to prove your attack range works.

### Phase 7, 8, 10: Utility, Frontier & Web Console
- **Critique:** Building a React + D3 + FastAPI + Redis app makes the project tangible and visually stunning for evaluators.
- **Warning:** Do not start building live WebSockets and long-polling UI in Week 10. Follow the schedule in X.4: build the attack console skeleton early (Week 5) with mock/static JSON data.

---

## 5. Strategic Recommendations to Secure a Top Grade

1. **Commit to the MVC (Minimum Viable Capstone) Scope Immediately:**
   - Primary Generator: **AIM / MST** + **Gaussian Copula** baseline.
   - Primary Attacks: **LiRA** + **Anonymeter**.
   - Primary Dataset: **UCI Adult** + **ACSIncome**.
   - Drop multi-table synthesis, complex relational schemas, and tabular diffusion to "Future Scope" / "Exploratory".

2. **Prepare a 3-Minute "Confrontational Demo" for the Panel:**
   - **Step 1:** Show a naive synthetic dataset (non-private). Run Anonymeter/LiRA $\rightarrow$ **ATTACK SUCCESSFUL (Red Banner, 85% Linkability)**.
   - **Step 2:** Run SynthProof on the same dataset ($\epsilon = 1.0$). Show attack dossier $\rightarrow$ **ATTACK FAILED (Green Banner, 52% Linkability, Chance Level)**.
   - **Step 3:** Show the signed Privacy Data Sheet and the Proved ($\epsilon = 1.0$) vs. Audited ($\epsilon = 0.62$) gap curve.
   - *This presentation flow will blow away any capstone panel regardless of their deep DP expertise.*

3. **Offload Compute to Cloud / Colab:**
   - Set up automated scripts to run Phase 9 experimental sweeps on Google Colab or Kaggle GPUs overnight, storing JSON outputs directly to Git or S3/MinIO.

---

## 6. Final Summary Score

$$\text{Final Score}: \mathbf{8.8 / 10} \quad (\text{Grade: A+} / \text{Distinction potential})$$

SynthProof is an extraordinary capstone concept. It moves beyond standard "we built an ML model" projects into real-world privacy engineering and research. If you maintain strict discipline over the execution cut-gates, it will easily be the best project in your department.
