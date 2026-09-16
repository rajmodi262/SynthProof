# In-the-wild measurement — honest findings (2026-09-15)

> **This supersedes `WILD_AUDIT_REPORT.md`, which is retracted.** That report claimed a "30.14%
> fatal leak rate" across 73 Hugging Face datasets. That number is not valid and must not be used in
> the paper, the defense, or any slide. This document records what is actually true.

## Why the earlier "30% fatal" number is retracted

`scripts/wild_audit.py` marked a dataset a **FATAL differential-privacy breach whenever the word
"seed" appeared in its name** (`with-seed`, `_seed_`, …). Two independent errors make that meaningless:

1. **A published seed is only a privacy failure for a mechanism that is actually differentially
   private and whose noise derives from that seed.** None of the flagged datasets claim DP. Publishing
   the seed of a non-DP tutorial dataset leaks nothing about anyone.
2. **Fork inflation.** 17 of the 22 "FATAL" hits were copies of ONE course exercise,
   `uplimit-synthetic-data-week-1-with-seed`, re-uploaded by ~8 students. All 22 were flagged solely
   for the substring "seed" in the name; **zero** were shown to declare DP.

An examiner who clicks one link finds a week-1 homework assignment. The number would damage
credibility on the parts of the project that are real.

## What is actually true (from `scripts/wild_audit_honest.py`, run 2026-09-15)

Corpus: 306 datasets (286 unique after collapsing forks/variants) gathered from 10 privacy/synthetic
queries against the Hugging Face datasets API.

| Measurement | Result |
|---|---|
| Unique base datasets examined | 286 |
| Base datasets that mention a DP mechanism | **0** |
| Base datasets that declare DP **with an ε value** | **0** |
| Base datasets publishing a seed (deduplicated, non-DP) | ~1 (a norm measurement, not a breach) |

**The headline finding is a negative one, and it is honest and reportable:** the Hugging Face Hub —
the largest open dataset hub — hosts **essentially no genuinely differentially private data
releases**. A "measurement study of DP releases in the wild" cannot be done on Hugging Face, because
the population is empty. The earlier "73 DP datasets" were synthetic-but-not-private datasets caught
by keyword.

`INFERENCE:` this is not a null result about the *problem*; it is a result about *where DP releases
live*. Real DP data releases are fragmented across places the ML hubs do not index:

- the **US Census 2020 Disclosure Avoidance System** (the flagship deployment; ε published in its
  documentation),
- the **NIST / SDNist** differential-privacy synthetic-data challenge deidentified data and reports,
- **OpenDP / SmartNoise** example releases,
- the **Oblivious Privacy Deployments Registry** and **Wikimedia Foundation's DP documentation**
  (both named in Dibia et al. 2026 §5 as existing registries that "often lack clear explanations
  about key aspects like privacy units and post-processing effects").

## What a defensible empirical section looks like instead

Do **not** scrape a hub for a percentage. Do a **curated case study** of the field's actual DP
releases — audit the *documentation* of a handful of real deployments (Census DAS, an SDNist
release, an OpenDP example, one or two paper-released DP synthetic datasets) against the
release-boundary properties in `research/15_standards_gap_analysis.md`. Small N, but every row is a
real, named, verifiable release. The honest finding there is expected to be: real DP releases state
ε and a mechanism, but rarely the neighbour relation, never a machine-checkable safe artefact, and
never a signature — which is exactly the gap the tool fills. **This case study is not yet done; it is
the concrete next step**, and it must read the real documentation, not a keyword regex.

## Salvageable honest data point (framed correctly)

Seed publication *is* widespread in synthetic-data releases generally — it is the reproducibility
norm (`random_state=42`, `with-seed`). Reported honestly, this says: *the practice differential
privacy forbids is already normalized in synthetic-data releasing culture, so when these pipelines
adopt DP, the release boundary is unsafe by default.* That is a motivation sentence, **not** a breach
count, and it must never be dressed up as "X% of DP datasets are broken."

## Files

- `scripts/wild_audit_honest.py` — the corrected, deduplicated, properly-gated measurement.
- `research/wild_audit/honest_audit_results.json` — its output.
- `scripts/wild_audit.py` and `WILD_AUDIT_REPORT.md` — **retained but RETRACTED**; kept only so the
  error and its correction are on the record.
