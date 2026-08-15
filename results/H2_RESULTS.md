# H2 — Per-subgroup privacy leakage

> **Status: NOT SUPPORTED at this scale.** The direction is weakly consistent with the
> hypothesis; nothing reaches significance, and the instrument's working range is the binding
> constraint rather than the mechanisms.
> Raw output: [`h2_subgroups.json`](h2_subgroups.json) · Runner: `scripts/run_h2.py` ·
> Regenerate with `make h2`.

**H2 (preregistered):** under uniform DP budget allocation, empirical audited privacy loss is
significantly higher for minority demographic subgroups than for majority groups.

---

## 1. Setup

| | |
|---|---|
| Dataset | UCI Adult, 6,000-row subsample |
| Mechanism | `pairwise`, ε ∈ {1.0, 8.0}, δ = 1e-5 |
| Auditor | One-run (Steinke), α = 0.05 |
| Canaries | 400 total, **allocated equally across subgroups** |
| Seeds | 3 per cell |
| Attributes | `sex` (2 levels), `race` (5 levels) |

**Equal allocation is deliberate.** Proportional allocation would give `Other` (0.8% of rows)
about 3 canaries and `White` (85.7%) about 343 — and since the audit ceiling falls with the
guess count, the rare groups H2 is *about* would get the weakest instrument. Equal allocation
oversamples them so every subgroup is measured with the same ceiling.

---

## 2. Results

### `race`, ε = 8.0 (proved ε = 7.356)

| subgroup | population share | canaries | attack accuracy | ε audited | p |
|---|---:|---:|---:|---:|---:|
| Other | 0.008 | 80 | **0.562** | 0.036 | 0.224 |
| Amer-Indian-Eskimo | 0.010 | 80 | 0.533 | 0.000 | 0.340 |
| Asian-Pac-Islander | 0.030 | 80 | 0.521 | 0.000 | 0.445 |
| Black | 0.095 | 80 | 0.529 | 0.036 | 0.438 |
| White | 0.857 | 80 | 0.542 | 0.000 | 0.268 |

### `race`, ε = 1.0 (proved ε = 0.912)

| subgroup | share | canaries | accuracy | ε audited | p |
|---|---:|---:|---:|---:|---:|
| Other | 0.008 | 80 | **0.529** | 0.003 | 0.385 |
| Amer-Indian-Eskimo | 0.010 | 80 | 0.508 | 0.000 | 0.508 |
| Asian-Pac-Islander | 0.030 | 80 | 0.537 | 0.019 | 0.367 |
| Black | 0.095 | 80 | 0.537 | 0.000 | 0.314 |
| White | 0.857 | 80 | 0.500 | 0.000 | 0.542 |

### `sex` — nothing at either ε

| subgroup | share | accuracy (ε=1) | accuracy (ε=8) |
|---|---:|---:|---:|
| Female | 0.320 | 0.523 | 0.527 |
| Male | 0.680 | 0.530 | 0.507 |

**Per-subgroup ceiling: 3.27** (race, 80 canaries) and **4.19** (sex, 200 canaries).

---

## 3. Findings

### 3.1 H2 is not supported — but the direction is consistent

The rarest subgroup (`Other`, 0.8% of rows) has the **highest attack accuracy in both ε
settings**, and the largest subgroup (`White`, 85.7%) sits at or near exactly chance (0.500 at
ε=1, 0.542 at ε=8). That ordering is what H2 predicts.

It is also not significant. **No mean p-value across three seeds falls below 0.05.** The
largest audited ε is 0.036 against a ceiling of 3.27 — roughly **1% of the instrument's
range**. Individual seeds did occasionally reach p = 0.016, but those do not survive averaging,
and with 5 subgroups × 2 ε values × 2 attributes there are 20 tests here; at α = 0.05 one
false positive is expected by chance alone. Under any multiple-comparison correction nothing
survives.

**The honest statement: the effect, if it exists, is smaller than this instrument can
resolve.**

### 3.2 `sex` shows nothing, and that is expected

A 32/68 split is not much of a minority. Both groups sit within noise of chance at both ε.
The attribute was included because the preregistration names it, and the null is reported
rather than dropped.

### 3.3 The binding constraint is the audit ceiling, again

Splitting 400 canaries across 5 subgroups leaves 80 each, giving a per-subgroup ceiling of
3.27 against a proved ε of 7.36. Two compounding limits:

- Per-subgroup `m` is a **fraction** of total `m`, so H2 is strictly harder to measure than
  H1's aggregate audit — and H1's was already disqualified by its ceiling.
- Certifying an ε costs roughly `ln(1/α)·e^ε` canaries
  ([AUDITOR_COMPARISON.md](AUDITOR_COMPARISON.md)), so resolving a *difference* between two
  subgroups needs both to be individually resolvable first.

To detect a subgroup difference of, say, ε = 1.0 with confidence, each subgroup needs on the
order of 10 perfectly-detected canaries — but the observed accuracies are 0.50–0.56, not 1.0,
so the real requirement is far higher. **Scaling to 5,000+ canaries per subgroup is the
experiment H2 actually needs**, and that is a compute problem rather than a design one.

---

## 3a. The reframed analysis — multiplicity, equivalence, and power

A bare "not supported" is uninformative: failing to reject is consistent both with *no effect*
and with *no power to find one*. This section establishes which. Produced by
`make h2-analyse` from the committed `h2_subgroups.json`; raw output in
[`h2_analysis.json`](h2_analysis.json).

### Multiplicity — nothing to correct

14 subgroup-by-epsilon comparisons at α = 0.05. **Raw p < 0.05: zero.** Chance alone predicts
0.7 false positives, so there was nothing for a correction to remove — and both
Benjamini-Hochberg (FDR) and Bonferroni (FWER) leave zero surviving, trivially.

| comparison | raw p | BH p | Bonferroni p |
|---|---:|---:|---:|
| race=Other ε=8.0 | 0.2245 | 0.5306 | 1.0000 |
| sex=Male ε=1.0 | 0.2244 | 0.5306 | 1.0000 |
| race=White ε=8.0 | 0.2676 | 0.5306 | 1.0000 |
| … 11 more, all p > 0.2 | | | |

Reporting the correction matters even though it changes nothing: had a single raw p landed
under 0.05, it would have been within the 0.7 expected by chance across 14 tests, and treating
it as a finding would have been the error this guards against.

### The power result — why H2 is null

At **m = 80** canaries per subgroup and α = 0.05:

| | |
|---|---|
| Smallest detectable audited ε | **0.008** |
| Adversary accuracy required to reach it | **0.600** |
| Best accuracy actually observed | **0.562** (race=Other, ε=8) |
| Largest audited ε observed | 0.036 |
| Ceiling at this canary count | 3.27 |
| **Fraction of the instrument's range used** | **1.1%** |

> **The adversary fell short of the detection threshold.** It reached 0.562 where 0.600 was
> needed. H2 is null because the attack was not strong enough at this sample size — a *power*
> result, not an *absence* result. The distinction is the whole point of this section, and it
> is asserted as a regression test so the claim cannot rot
> (`test_the_adversary_fell_short_of_the_detection_threshold`).

### Equivalence testing — a positive bound where power allows

TOST (Lakens 2017) with an equivalence margin of **±0.10 in adversary accuracy**, chosen from
the measured detection floor *before* this analysis and not from the H2 data — see
`H2_BOUND_JUSTIFICATION` in `synthproof/audit/equivalence.py`.

- **2 of 14 comparisons** (`sex=Female ε=8`, p = 0.0365; `sex=Male ε=8`, p = 0.0453) are
  **statistically equivalent to chance** within that margin. For these two, the study
  positively bounds the effect rather than merely failing to find one.
- **12 of 14 are not** — the equivalence test is itself underpowered at m = 80. For those the
  honest statement is that the data neither establish an effect nor rule one out.

That the equivalence test succeeds only for `sex` is expected: `sex` gets 200 canaries per
group against `race`'s 80, because the budget is split across two levels rather than five.

### What this section establishes

1. **H2 is not supported.** No comparison is significant, before or after correction.
2. **The null is bounded, not empty.** For two comparisons the effect is positively bounded
   within ±0.10 of chance.
3. **The reason is power, not absence.** The adversary needed accuracy 0.600 and reached
   0.562, using 1.1% of the instrument's dynamic range.
4. **What would change the answer:** a stronger adversary, or thousands of canaries per
   subgroup. Both are stated in §4 as the experiment H2 actually needs.

### One limitation of this analysis

`h2_subgroups.json` stores per-subgroup mean accuracy but **not** the per-canary
correct/incorrect vectors. The TOST therefore reconstructs a Bernoulli sample consistent with
the recorded sufficient statistic rather than replaying the actual outcomes. The seed is fixed
so the numbers are reproducible, but a different seed would move each TOST p slightly. Storing
the raw outcome vectors in the H2 runner removes the reconstruction entirely and is the
correct fix.


---

## 4. What would make this measurable

| | |
|---|---|
| **Raise canaries per subgroup** to the thousands. Linear cost, and the clearest path. |
| **Strengthen the adversary.** Accuracy is 0.50–0.56; the bound scales with how far above chance the adversary gets, so a mechanism-aware attack would buy more than more canaries. |
| **Choose a dataset with a sharper minority.** `Other` at 0.8% is rare enough to be interesting but small enough that its canaries are a large fraction of its real population — which itself distorts the mechanism. |
| **Test the mechanism, not the release.** Per-subgroup *utility* degradation is measurable today at these scales and is a legitimate weaker form of the fairness question. |

---

## 5. Threats to validity

- **3 seeds.** Differences under ~0.05 in accuracy are inside noise.
- **20 tests, no correction applied.** Nothing survives correction, which is why the headline
  is a null; had something survived uncorrected we would have had to correct it.
- **One mechanism** (`pairwise`) and one dataset.
- **Canaries are synthetic outliers**, not real minority records. They are assigned the
  subgroup's attribute value but are otherwise drawn from the schema's ranges, so they test
  "a record labelled as this group" rather than "a typical member of this group".
- **Equal allocation inflates rare groups' canary share** relative to their real population.
  This is deliberate and stated, but it means the planted data distorts rare subgroups more
  than common ones — a confound in the direction of *finding* H2, and we still did not.
