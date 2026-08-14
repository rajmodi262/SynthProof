# Auditor validation — detection floor and ceiling

> **Status: MEASURED.** UCI Adult, n = 3,000, 5 seeds per cell, α = 0.05.
> Raw output: [`detection_floor.json`](detection_floor.json) · Runner:
> `scripts/run_detection_floor.py` · Regenerate with `make floor`.

Every experiment in this repository reports `ε_audited = 0.000`. Until now that could not be
distinguished from a broken instrument — and this project's first self-audit found exactly
that: an auditor returning 0.00 in every cell for three structural reasons, unnoticed because
0.00 was also the expected answer.

This document measures what the auditor can and cannot see, against leakage we control.

---

## 1. Method

`LeakyGenerator` copies a known fraction `f` of its training rows verbatim and independently
permutes each column for the rest. At `f = 1.0` the release **is** the training table; at
`f = 0.0` every marginal is preserved exactly while no row corresponds to a real person. It
charges no budget and provides no privacy — it is a measuring standard, not a mechanism.

For each (`f`, canary count `m`) we run the audit over 5 seeds and record whether it fires
(`ε_audited > 0` and Fisher exact `p < 0.05`). A cell counts as detected only on a **majority**
of seeds; one lucky seed is not a floor.

---

## 2. Detection rate

Fraction of seeds where the audit fired:

| leak \ m | 10 | 25 | 50 | 100 | 200 | 400 | 800 |
|---|---:|---:|---:|---:|---:|---:|---:|
| **0.00** | 0.00 | 0.00 | 0.00 | 0.20 | 0.00 | 0.00 | 0.00 |
| **0.01** | 0.00 | 0.00 | 0.00 | 0.20 | 0.00 | 0.00 | 0.00 |
| **0.05** | 0.00 | 0.00 | 0.00 | 0.20 | 0.00 | 0.00 | 0.00 |
| **0.25** | 0.00 | 0.00 | 0.00 | 0.20 | 0.40 | 0.80 | **1.00** |
| **1.00** | **1.00** | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

**Detection floor** — smallest `m` that fires on a majority of seeds:

| leak fraction | floor |
|---|---|
| 1.00 (verbatim release) | **m = 10** |
| 0.25 | **m = 400** |
| 0.05 | not detected at m ≤ 800 |
| 0.01 | not detected at m ≤ 800 |
| 0.00 (control) | not detected — correct |

---

## 3. The auditor also has a **ceiling**, and it is the more damaging limit

`ε_audited = log(TPR_lower / FPR_upper)` from Clopper-Pearson intervals. With `m` canaries
those intervals cannot be arbitrarily tight, so there is a **maximum epsilon the instrument
can report**, even against a release that is 100% verbatim training data:

| m | 10 | 25 | 50 | 100 | 200 | 400 | 800 |
|---|---:|---:|---:|---:|---:|---:|---:|
| max ε_audited (leak = 1.0) | 0.81 | 1.84 | 2.57 | 3.28 | 3.98 | 4.68 | **5.38** |

At every one of these counts TPR = 1.00 and FPR = 0.00 — the adversary is perfect. The number
is bounded by the sample size alone.

### Consequence for every result this project has published

The H1 experiments run at **m = 60**, where the ceiling is ≈ **2.7**, and report against
`ε_proved ≈ 7.36`.

> **The gap was structurally guaranteed.** The instrument could not have reported
> `ε_audited > 2.7` at that canary count *even if the mechanism had released its training set
> verbatim*. Nothing about the observed gap is evidence concerning the mechanisms.

And the floor says the same thing from below: at m = 60 the auditor detects nothing under
~25% verbatim copying, which every DP mechanism trivially satisfies.

**So `ε_audited = 0` in the H1 table carries essentially no information.** It is consistent
with a perfectly private mechanism and with a badly leaky one. No claim about
ε_audited / ε_proved should be made from any experiment run at these canary counts, and none
is made anywhere in this repository.

---

## 4. What the instrument does do correctly

The controls all hold, which is what makes the negative results above trustworthy rather than
just more absence of evidence:

- **Positive control passes.** A verbatim release is detected at m = 10 with TPR 1.00,
  FPR 0.00, p < 0.001.
- **Negative control passes.** The shuffled release — perfect marginals, no real records — is
  never detected on a majority of seeds. A privacy metric that fired here would be measuring
  *similarity* rather than *disclosure*, which is the failure Stadler et al. (2022) document
  in the field generally.
- **Monotone in leakage.** At fixed m = 800, mean ε_audited rises 0.000 → 0.137 → 5.377 across
  f = 0.05, 0.25, 1.00.
- **Monotone in sample size.** At f = 0.25 the p-value falls 0.334 → 0.113 → 0.062 → 0.011 →
  0.004 → 0.000 as m grows. More evidence, more significance — as it should.
- **Bound tightens with m.** At f = 1.0, ε_audited climbs 0.81 → 5.38. The instrument gets
  sharper with more canaries rather than noisier.

### The one anomaly, reported rather than smoothed away

At **m = 100** exactly one seed of five fires at leak levels 0.00, 0.01 and 0.05 — a false
positive, with mean ε_audited 0.014 and max 0.070.

This is consistent with the nominal error rate: at α = 0.05 across 5 seeds,
P(at least one false positive) = 1 − 0.95⁵ ≈ 23%. It is the *same seed* in each row, because
at low leakage the releases are near-identical in structure, so it is one event replicated
rather than three.

It is also why the majority rule exists. A "smallest m where it ever fired" definition would
have reported a floor of 100 for a table containing no leaked records at all.

---

## 5. What this means for the project

| | |
|---|---|
| **Blocked** | Any claim about the proved-versus-audited gap, at any canary count used so far. This includes the privacy half of H1 and all of H2. |
| **Required for H2** | Subgroup audits inherit this floor and are worse off — a subgroup is a *fraction* of the canaries, so per-subgroup `m` is smaller still. H2 at m = 60 total is not measurable. |
| **Cheapest fix** | Raise m. The ceiling grows roughly logarithmically, so m = 800 buys ε_audited ≤ 5.38 — still below a proved ε of 7.36. |
| **Real fix** | The full Steinke, Nasr & Jagielski (2023) one-run construction, whose randomised inclusion vector extracts far more signal per canary than the present member-vs-holdout split. That is M2.1. |

**The honest framing for the thesis:** we built an instrument, calibrated it, and found its
working range does not cover the regime we need. That is a legitimate and reportable result —
and it is considerably more useful than a confident null would have been.

---

## 6. Threats to validity

- **One dataset**, one subsample size (n = 3,000). The floor may move with n.
- **`LeakyGenerator` is a coarse model of leakage.** Verbatim copying is the easiest possible
  case; a real mechanism leaks in subtler ways that may be harder or easier to detect.
- **5 seeds per cell.** Enough to reject one-seed artefacts, not enough to estimate the false
  positive rate precisely — 1/5 and 0.05 are not distinguishable at this sample size.
- **The floor is a property of *this* auditor**, not of canary auditing in general. M2.1 would
  change it substantially.
