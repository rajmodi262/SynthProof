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

---

## 6.7 The preregistration tag — what it does and does not establish

`docs/preregistration.md` is tagged `prereg-v1`. State the following in the chapter, in these
terms, because a reviewer will check it and a stronger claim is not supportable.

**What is verifiable.** The tag points at commit `8a8e21d` (2026-08-07), the repository's
first commit, which is where `preregistration.md` first appears. **No result file in this
repository predates that commit** — `git log --reverse -- results/` confirms the earliest
result artefacts are in the same commit or later. The hypotheses, ε grid, δ, seed count and
primary metrics were therefore fixed in version control before any committed experiment ran.

**What is NOT verifiable, and must be said.** Three qualifications:

1. **The tag was applied retroactively**, on 2026-08-15, pointing at the historical commit. It
   was not created at the time. Git tags carry their own creation date, so this is discoverable
   and should be declared rather than left for a reviewer to notice.
2. **The document is dated 2026-08-05, two days before its first commit.** There is no
   independent timestamp for that earlier date. The earliest *verifiable* existence of the
   preregistration is 2026-08-07.
3. **This is not a third-party registration.** An OSF or AsPredicted entry is timestamped by a
   party with no interest in the outcome. A git tag is timestamped by us, and we control the
   repository. The correct description is a **version-controlled commitment**, not a
   preregistration in the clinical-trials sense.

**Why it is still worth having.** The commitment predates every committed result, the
deviations below are declared rather than discovered, and both H1's partial refutation and
H2's null are reported. That is the substance preregistration exists to protect. Overstating
its formal status would undermine exactly the credibility it is meant to supply.

## 6.8 Deviations from the preregistration

Every deviation, its reason, and its likely direction of effect on inference.

| # | Deviation | Reason | Effect on inference |
|---|---|---|---|
| D1 | **ACSIncome not run.** UCI Adult only | Time budget | Weakens external validity. Any H1/H2 conclusion is single-dataset and must be stated as such |
| D2 | **Utility measured on a second, canary-free fit** | Measuring it on the canary-trained model destroyed the signal being measured — 60 canaries cut corr(age, hours) from 0.1014 to 0.0109 | Removes a bias that had been penalising exactly the mechanisms that model dependence. Direction: made H1 *measurable*; without it H1 was falsely null |
| D3 | **Auditor changed** from paired Clopper-Pearson to the one-run construction | The paired estimator spends two canaries per comparison and saturates sooner | Slightly raises the audited bound at fixed canary budget. Both are reported and compared |
| D4 | **H1 primary metric supplemented.** Preregistration named TSTR macro F1; correlation error was added as a structure metric | TSTR alone cannot distinguish an independent-marginal mechanism from a structured one on this data | Additive, not substitutive — TSTR is still reported. The structure metric is what separates the families |
| D5 | **H3 not run** | Time budget | H3 is untested and reported as such, not omitted |

D2 is the deviation most likely to be challenged, because changing a measurement mid-study can
look like fishing. The defence is that the change was made for a diagnosed measurement defect,
the diagnosis is quantified and reproducible, and the fix moved the result *away* from the
direction that would have been convenient to report — the earlier contaminated analysis
supported "no difference between mechanism families", which is a weaker and less interesting
claim than the one the corrected analysis supports.
