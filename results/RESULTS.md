# SynthProof — Results index

> **The toy sweep that used to live here has been deleted.** It ran 100 rows whose columns
> were drawn independently, with one seed and two generators that were both independent-
> marginal samplers. There was no joint structure for a synthesiser to preserve, so every
> utility number in it measured nothing. Its generator, `scripts/run_sweep.py`, and the
> pipeline behind it are gone rather than left in place with a disclaimer.

## Current results

| Result | Status | Document |
|---|---|---|
| **Auditor validation** | ✅ Detection floor and ceiling measured; controls hold | [`DETECTION_FLOOR.md`](DETECTION_FLOOR.md) |
| **H1** — mechanism families | ✅ Supported on structure and utility; the privacy half is **disqualified** by the auditor's working range | [`H1_RESULTS.md`](H1_RESULTS.md) |
| **Auditor comparison** | ✅ Paired vs one-run; the ceiling is information-theoretic | [`AUDITOR_COMPARISON.md`](AUDITOR_COMPARISON.md) |
| **H2** — subgroup disparity | ⚠️ **Not supported** at this scale; direction consistent, nothing significant | [`H2_RESULTS.md`](H2_RESULTS.md) |
| **H3** — budget allocation | ⚠️ **Null, replicated** on both datasets; no bootstrap CI excludes zero at any of 5 ε | [`h3_allocation.json`](h3_allocation.json) · [`acs/h3_allocation.json`](acs/h3_allocation.json) |
| **Clique-selection confound** | ⭐ The strongest result here. AIM's structure score tracks whether the measured pair is one it selected | [`clique_confound.json`](clique_confound.json) · [`acs/H1_RESULTS.md`](acs/H1_RESULTS.md) |
| **Subgroup utility (fairness)** | ✅ Real on `sex` (2.7–3.3×); on `race` at ε=8 the **control is larger** than the effect | [`FAIRNESS_RESULTS.md`](FAIRNESS_RESULTS.md) |
| **Cross-dataset comparison** | ⚠️ Structure ordering **disagrees** between datasets; utility ordering reproduces | [`acs/CROSS_DATASET.md`](acs/CROSS_DATASET.md) |

Raw output: [`h1_all_families.json`](h1_all_families.json).
Regenerate everything in this directory with `make h1`.

## The one number that is not interpretable, and why

`ε_audited = 0.000` in every cell of every experiment this project has run. The auditor is a
real instrument — the positive and negative controls both hold, and CI enforces them — but
[the floor study](DETECTION_FLOOR.md) shows its working range does not cover the regime we
need.

At the 60 canaries these experiments use, the auditor cannot detect leakage below ~25%
verbatim copying, and **cannot report an epsilon above ~2.7 even against a release that is
100% training data**. The proved epsilon is 7.36. The gap was guaranteed by the measurement
before any mechanism ran.

No claim about the ratio ε_audited / ε_proved appears anywhere in this repository, and none
should. **The full Steinke one-run construction has since landed** (`audit/steinke.py`) and did
not change this: it improved the m = 60 verbatim-release reading only from 2.03 to 2.17. Raising
the canary count is not sufficient either — m = 800 only lifts the paired ceiling to 5.38, and
certifying an ε costs canaries exponential in that ε. The limit is what canary auditing can
prove, not which auditor implements it.

## How to read anything here

Every number traces to a committed experiment with a recorded seed, and carries an
uncertainty estimate. Where a result is uninformative, it says so rather than being omitted.
See [`../docs/AUDIT_AND_ROADMAP.md`](../docs/AUDIT_AND_ROADMAP.md) §7 for the standing rules
this follows.
