# Chapter 7 — Results & Analysis

**Target: 2,500 words.** The core empirical chapter.

> **REWRITTEN 2026-08-24 as a specification.** The previous version of this file was written
> before the audit-ceiling finding, before ACSIncome, and before fairness/linkability landed.
> It instructed the writer to make the proved-vs-audited gap "the primary result" — the exact
> comparison the ceiling finding disqualifies — and to report LiRA and anonymeter, neither of
> which exists. Anyone drafting to it would have written three false claims in good faith.
>
> **Nobody outside the four authors writes the prose.** Every `[WRITE]` block below is yours.
> What is specified here is *which claim goes where and which committed number supports it*.

> **House rule:** if you cannot point at the script and the seed that produced a number, it
> does not go in the thesis. Everything below traces to `results/`, regenerable with
> `make reproduce`.

---

## Reading order for this chapter

The chapter has to establish the instrument before it reports anything measured with it.
That ordering is not stylistic: §7.2 is what makes §7.4 interpretable, and without §7.2 an
audited ε of 0.000 is indistinguishable from a broken auditor.

| § | Topic | Words | Verdict to report |
|---|---|---:|---|
| 7.1 | Calibration validation | 250 | ✅ holds |
| 7.2 | Auditor validation — floor **and ceiling** | 400 | ✅ instrument works, range is bounded |
| 7.3 | H1 utility & structure | 500 | ✅ Adult; **does not reproduce on ACS** |
| 7.4 | The proved-vs-audited gap, and why it is not a finding | 300 | ⚠️ **disqualified** |
| 7.5 | Clique selection — the confound | 400 | ⭐ **strongest result in the project** |
| 7.6 | Attack range | 250 | ✅ 5 attacks, 3/3 EDPB risks |
| 7.7 | H2 subgroup leakage | 250 | ⚠️ bounded null, replicated |
| 7.8 | Subgroup utility (fairness) | 200 | ✅ real on `sex`, control kills it on `race` |
| 7.9 | H3 allocation | 150 | ⚠️ null, replicated |

---

## 7.1 Calibration validation (~250 words)

Establishes that every ε reported downstream means what it says. It goes first because the
rest of the chapter depends on it.

| To establish | Evidence |
|---|---|
| Calibration never overspends | proved/target ≤ 1.0 in every cell, `results/h1_all_families.json` |
| Ratio is tight on a single stage | target 8.0 → 7.999605 |
| CI-gated | 24 configurations, `.github/workflows/ci.yml`, `calibration-guard` job |

**Trap.** The observed proved/target ≈ 0.92 across the grid is **not** a calibration-search
error. It is `BudgetPlan` splitting the total linearly across stages while RDP composition is
sublinear. Diagnosed 2026-08-23, deliberately **not fixed** because the fix changes every
published ε and invalidates the committed grid. Both numbers are pinned in
`tests/test_accounting_properties.py`. Report it as a known, diagnosed, deliberately-deferred
gap — not as a mystery and not as a defect you missed.

`[WRITE: ~250 words.]`

---

## 7.2 Auditor validation — the floor and the ceiling (~400 words)

**This section is load-bearing for the whole chapter.** Show the instrument works, then show
the range over which it works.

| To establish | Evidence |
|---|---|
| Positive control fires | verbatim leak detected at m = 10, `results/DETECTION_FLOOR.md` |
| Negative control silent | 0% leak correctly reports nothing |
| Detection floor | 25% leak needs m = 400; 5% and 1% undetected at m ≤ 800 |
| Ceiling of **this estimator** | `ε_max(r) ≈ log(r / ln(1/α))`; certifying ε costs ≈ `ln(1/α)·e^ε` canaries. Information-theoretic **given the single-threshold binomial estimator** — not a limit of auditing; see §7.4 |

**Two ceiling series exist and must never be quoted interchangeably.** This was caught by the
defence pack's own build gate on 2026-08-18 after a draft ran them together.

| canaries | 10 | 25 | 50 | 60 | 100 | 200 | 400 | 800 |
|---|---|---|---|---|---|---|---|---|
| paired Clopper-Pearson, **measured** (`results/detection_floor.json`, leak = 1.0) | 0.81 | 1.84 | 2.57 | — | 3.28 | 3.98 | 4.68 | 5.38 |
| one-run, **from the formula** | 1.05 | 2.06 | 2.79 | 2.97 | 3.49 | 4.19 | 4.89 | 5.59 |

`results/RESULTS.md` quotes the **paired** 5.38 at m = 800; `AUDITOR_COMPARISON.md` quotes the
**one-run** 2.972 at m = 60. Both are right in context. Mixing them (e.g. "60 to 800 lifts it
from 2.97 to 5.38") silently crosses instruments.

**Trap — the biggest in the thesis.** The ceiling inequality is **not ours**. It is a one-line
corollary of Steinke, Nasr & Jagielski (2023) Thm 2.1 / Eq. (3) — the paper we implement —
verified bit-identical against `max_provable_epsilon` at r = 10/60/100/400/800 and pinned by
`tests/test_audit_power.py`. **Ours is the measurement and the decision to report it beside
the number it qualifies.** Never write it as a discovery.

`[WRITE: ~400 words. Include the floor table and the correct ceiling series, labelled.]`

---

## 7.3 H1 — utility and structure across mechanism families (~500 words)

**Report the honest split: supported on Adult, not reproduced on ACS.**

| Dataset | correlation error at ε = 8 | CI separation |
|---|---|---|
| Adult | aim 0.0078 < pairwise 0.0283 < independent 0.0947 | all three mutually non-overlapping |
| ACS | pairwise 0.0202 < independent 0.0535 ≈ aim 0.0626 | **independent vs aim do NOT separate** |

TSTR F1 ordering (aim > pairwise > independent) **does** reproduce on both datasets — see
`results/acs/CROSS_DATASET.md`. So the utility claim generalises and the structure claim does
not. Say both.

The two datasets' true correlations differ (0.1034 vs 0.0721), so **absolute** correlation
error is not comparable between them. Only the ordering is. `compare_datasets.py` runs no
experiment; it reads committed files.

**Secondary, verified before being written down:** on ACS, AIM's TSTR F1 *falls* with ε
(0.704 [0.695, 0.713] at ε = 0.5 → 0.581 [0.539, 0.629] at ε = 8, CIs disjoint). Cause: the DP
profiler suppresses fewer rare categories at higher ε (OCCP 3→23, RELP 3→14), so a fixed clique
allowance covers proportionally less domain.

**Source:** `results/H1_RESULTS.md`, `results/acs/H1_RESULTS.md`, `results/acs/CROSS_DATASET.md`.

`[WRITE: ~500 words.]`

---

## 7.4 The proved-vs-audited gap, and why it is not a finding (~300 words)

**This section exists to retract a comparison, not to report one.** It was the project's
intended headline. It is disqualified, and saying so plainly is the contribution.

`ε_audited = 0.000` in every cell of every experiment. H1 ran at m = 60, one-run ceiling
**2.97**, against a proved ε of **7.36**. The instrument could not have reported above 2.97
*even against a release that was 100% verbatim training data*. **The gap was guaranteed before
any mechanism ran.**

Moving from the paired Clopper-Pearson auditor to the Steinke one-run construction improved it
only marginally (2.03 → 2.17 at m = 60 on a verbatim release), and a stronger *adversary* would
not change it either.

**Do not write "canary auditing cannot confirm tight bounds."** That is too strong and an
examiner in this area will know it. Ganev, Annamalai & Kulynych (Apr 2026,
[arXiv 2604.18352](https://arxiv.org/abs/2604.18352)) obtain **tight** audits of MST and AIM
using a Gaussian-DP / f-DP estimator, on mechanisms of the same family, where our estimator
returned 0.000. The ceiling `log(TPR_lo / FPR_hi)` is a property of **the single-threshold
binomial estimator this project chose**, not of auditing as such.

**The defensible statement, and it is narrower:** *our* auditor catches broken implementations
and cannot confirm tight ones. It found a verbatim release at m = 10 and will never confirm
ε = 7.36 is tight at m = 60. A better estimator exists, we did not use it, and that is a
limitation of this study rather than a limit of the method. Say so, and cite the paper that
does better — volunteering it is far stronger than being shown it.

**Trap.** No claim about the ratio `ε_audited / ε_proved` appears anywhere in this repository
and none should appear in the thesis. Reporting "7.36 vs 0" as a result about a *mechanism* is
the instrument reading its own floor.

`[WRITE: ~300 words. This is a retraction section. Write it as one.]`

---

## 7.5 Clique selection — the confound (~400 words) ⭐

**Lead the analysis with this.** It is the strongest scientific result in the project and it
converts a weak "our mechanism ranks best" claim into a methodological contribution.

The structure metric is the correlation of a **single column pair**. AIM selects ~6 two-way
cliques, and its score is essentially decided by whether the measured pair is one of them.

| Dataset | measured pair | selected? | consequence |
|---|---|---|---|
| Adult | `age × hours_per_week` | at **every** ε tested | AIM looks like a clear winner |
| ACS | `AGEP × WKHP` | at **1 of 3** ε | error tracks selection exactly: 0.0977 (not selected) → 0.0395 (selected) → 0.0626 (not selected) |

**Ruled out first:** the model-size bound is not responsible — `skipped_cliques_` is empty at
ε = 0.5 and ε = 8, with 17 cliques measured at both.

**The generalisable claim, and keep it to this width:** any DP-synthesis benchmark scoring a
marginal-based mechanism on a small fixed set of low-order statistics risks measuring clique
selection rather than fidelity.

**Do not overclaim.** The stronger reading — that AIM *only* wins where it selects — is **not**
supported: each dataset has a counterexample. Measured directly, AIM's advantage over a
no-dependence baseline is 11.9× larger on the selected pair on Adult but only 2.3× on ACS.

**Source:** `results/clique_confound.json`, `results/acs/H1_RESULTS.md`,
`tests/test_acs_h1_findings.py`, `docs/thesis/ch06-methodology.md` §6.9.

`[WRITE: ~400 words.]`

---

## 7.6 Attack range (~250 words)

Five attacks run on **every** cell, covering **all three EDPB disclosure risks**.

| Attack | Risk covered | Note |
|---|---|---|
| `exact_match_risk` | singling out | explicitly **not** Anonymeter; named as ours |
| `linkability` | linkability | two disjoint halves matched, scored against a row-shuffled release |
| `attribute_inference` | inference | scored against a **conditional** baseline, not a marginal one |
| `domias` | membership | k-NN density ratio, Breugel et al. 2023 |
| `distance_mia` | membership | nearest-neighbour |

Linkability controls: verbatim release gives excess **+0.997**, structureless release **+0.007**.
Reported **not applicable** on tables with < 4 columns rather than crashing the release.

**Traps.** (a) **LiRA does not exist** and its absence is a recorded decision — ~21 h compute
for a likely wide-CI null; calling anything cheaper "LiRA" would repeat audit finding F7.
(b) **Anonymeter is not integrated** — it pins `numpy < 2` while `jax`/`mbi`/private-PGM require
`numpy >= 2`; installing it broke AIM outright on 2026-08-23 and was rolled back. Report both
absences explicitly; the certificate does.

`[WRITE: ~250 words.]`

---

## 7.7 H2 — subgroup leakage (~250 words)

**Bounded null, and it replicated.** 0 of 14 comparisons significant on Adult, 0 of 22 on ACS,
none surviving BH-FDR or Bonferroni. 2 of 14 are statistically **equivalent** to chance within
a pre-specified TOST margin — that is a bound on the effect, not merely absence of evidence,
and it is the stronger statement.

State detectability: the adversary needed accuracy 0.600 and reached 0.562.

**Trap.** H2 asks about **leakage**. Ganev, Oprisanu & De Cristofaro (ICML 2022) is about
disparate impact on **accuracy**. That distinction is the only thing separating H2 from a 2022
ICML paper — state it precisely, and point to §7.8 as the half that answers their question.

**Source:** `results/H2_RESULTS.md`, `results/acs/H2_RESULTS.md`.

`[WRITE: ~250 words.]`

---

## 7.8 Subgroup utility — what synthesis costs each group (~200 words)

The other half of the subgroup story, and the half the ICML 2022 paper actually established.

| Attribute | ε | gap_spread [95% CI] | baseline_spread (**control**) | verdict |
|---|---:|---|---|---|
| `sex` | 1 | 0.077 [0.048, 0.125] | 0.029 [0.028, 0.030] | 2.7× — real |
| `sex` | 8 | 0.097 [0.079, 0.132] | 0.029 [0.028, 0.030] | 3.3× — real |
| `race` | 1 | 0.255 [0.158, 0.355] | 0.167 [0.105, 0.228] | 1.5× — weak |
| `race` | 8 | 0.131 [0.108, 0.161] | 0.167 [0.105, 0.228] | **0.8× — control larger** |

**The control earned its place and must be reported.** On `race` at ε = 8 the real-data
disparity is *larger* than the synthesis-induced one, so a raw-TSTR metric would have reported
a fairness finding that belongs to the **task**, not to DP. On `sex` the effect is genuine and
replicates across datasets. Direction is Robin Hood, not Matthew.

Report n per group; small subgroups produce wide intervals, and 3 of 5 `race` groups are
reliable.

**Source:** `results/FAIRNESS_RESULTS.md`, `results/acs/fairness.json`.

`[WRITE: ~200 words.]`

---

## 7.9 H3 — budget allocation (~150 words)

**Null, replicated on both datasets.** At none of the 5 ε values on either dataset does the
paired weighted-minus-uniform gap in TSTR macro F1 have a bootstrap CI excluding zero.

Weights are **declared public metadata**, never measured from the table — deriving them would
be an uncharged query. Note the scope limit: per-column weights work for `independent` only,
so H3 speaks for one family.

**Source:** `results/h3_allocation.json`, `results/acs/h3_allocation.json`, ch06 §6.10.

`[WRITE: ~150 words.]`

---

## Discipline for this chapter

- Refuted hypotheses are reported as clearly as confirmed ones. Three of the results above are
  nulls or retractions; that is the chapter's strength, not its weakness.
- Every table carries n, seed count and CI method.
- No result appears without an uncertainty estimate.
- **Report the ceiling beside every audited ε.** `scripts/check_thesis_claims.py` currently
  flags this file's predecessor under `missing-ceiling`; the check is right.
- Declare the preregistration deviations in ch06 §6.1: ACS PUMS was originally not planned,
  utility moved to a second canary-free fit mid-project, and the auditor changed from paired
  Clopper-Pearson to the one-run construction.
