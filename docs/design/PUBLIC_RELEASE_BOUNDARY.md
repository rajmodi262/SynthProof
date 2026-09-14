# The public release boundary

> **Decided 2026-09-14.** The project states its guarantee under the **add/remove-one-record**
> neighbouring relation (thesis ch03), and the user chose to keep that and make every artefact
> consistent with it rather than switch to replace-one. This document is the specification the
> implementation is checked against. Background: `research/11_selection_accounting.md`.

## The rule

Everything that leaves the curator — the synthetic table, the signed Privacy Data Sheet, the
Croissant record, the offline capsule, a refusal — must be one of:

1. a **charged** DP output, or a post-processing of charged outputs;
2. a **public declaration** made by the operator before the data is read; or
3. **labelled in the artefact itself** as computed on the sensitive table and not covered by ε.

Under add/remove-one, the exact row count n is private: two neighbouring tables differ in n by
one. So is anything that lets an adversary who knows every other record test for one record.

What the curator shows **its own operator** — console progress, the split sizes streamed over
SSE, the upload list — is not a release. SynthProof is central-model (`deployment_model:
"central"`): the operator already holds the table.

## Inventory

Every field that reaches an artefact, what it depends on, and what changes.

| Artefact / field | Where it is set | Depended on | Before | Decision |
|---|---|---|---|---|
| Synthetic table **row count** | `frontier/experiment.py:270` `num_samples=len(fit_df)` | **exact n** | released | **D2** — generate a **public** size `release_rows` |
| Sheet `num_rows`, Croissant `dp:numRows`, capsule record count | `frontier/certificate.py:410`; `api/routes/run.py:223` | **exact n** | released, signed | **D2** — becomes the release size, with `release_rows_source` |
| Refusal gate (`R1` minimum rows; `R2` identifier-like domain size) | `data/preflight.py` via `certificate.py:289` | **exact n** | a refusal leaks n near the threshold | **D2** — judged against the public size |
| Sheet `input_fingerprint`, Croissant `dp:inputFingerprint`, `dp:inputFingerprintSha256` | `certificate.py:391` | **the whole table**, SHA-256, unkeyed | released, signed | **D3** — keyed HMAC-SHA-256 under a curator secret that is never published |
| Sheet `evaluation` (TSTR F1, TRTR F1, correlation error, MIA AUC), `frontier_curve` utility fields, `total_audited_eps` | `certificate.py:338-344`; `api/routes/run.py` | **the real table** (holdout, canaries) | released, undisclosed | **D4** — kept, and labelled outside ε in the artefact |
| AIM / fixed_workload model total | `generators/aim.py`, `generators/fixed_workload.py` | **exact n**, uncharged | fixed | **D1 — fixed in `4225e76`** |
| `total_proved_eps`, `ledger_hash`, `accountant_agreement` | accountant | the charges; charges depend on the DP profile (post-processing) | fine | unchanged |
| `mechanism`, `delta`, `seed`, `target_column`, `dataset_name` | operator configuration | public declaration | fine | unchanged |
| Profile `num_rows` | `data/profiler.py:255,303` | exact n | **never read** by anything | set from the public size, so no private value sits in a structure that later code could publish |

## D2 — where the public size comes from

In priority order:

| Source | When | `release_rows_source` |
|---|---|---|
| **Protocol constant** | the research grids: the subsample size and holdout fraction are fixed before any data is read (`N_ROWS = 6000`, `holdout_frac = 0.3`), so `len(fit_df)` is a function of public constants only | `protocol` |
| **Operator declaration** | API `rows` (already a declared subsample size); CLI `--release-rows` | `declared` |
| **Charged noisy count** | CLI `--input` with no declaration: one Laplace counting query (sensitivity 1 under add/remove-one) charged to the accountant before the gate runs, rounded and floored at 1 | `dp_count` |

The exact n is never used for any of the three.

**The research numbers do not move.** Under `protocol`, the release size equals the value it has
today, so every H1/H2/H3 cell is unchanged by D2. What changes is the *justification* recorded
with it.

**A lying declaration is the operator's problem, and the sheet says so.** A gate judged against a
declared size cannot detect a false declaration without reading n, which is the leak it exists to
avoid. `release_rows_source` makes the basis visible to anyone reading the sheet.

## D3 — the fingerprint

The field exists so a curator can detect a repeat release of the same table, which a
cross-session budget filter needs. An **unkeyed** hash of the full table gives the standard DP
adversary — who knows every other record — a deterministic membership test: hash both candidate
tables and compare. No ε covers that.

A keyed HMAC-SHA-256 under a secret held with the signing key (`<key dir>/fingerprint.key`,
created on first use, never published) keeps repeat detection for the curator and gives a third
party nothing to test. Without the key file, the field is omitted, not filled with an unkeyed
hash. The Croissant term `dp:inputFingerprintSha256` becomes `dp:inputFingerprintHmacSha256`.

## D4 — measurements computed on the real table

TSTR/TRTR F1, correlation error and MIA AUC are computed against the real holdout; the audited ε
comes from canaries planted in the real table. They are the scientific reporting and they stay,
but **not silently**: the sheet carries `evaluation_privacy` stating they are computed on the
sensitive table and not covered by ε, and the residual-risk list says the same. The Croissant
record mirrors the label.

## Tests that must hold (each with a negative control)

1. **Size independence** — two tables that differ by one record, run with the same public size,
   produce the same `num_rows` and the same synthetic row count. *Negative control:* with the size
   taken from `len(fit_df)` of a table whose length is not protocol-fixed, the test fails.
2. **No unkeyed table hash anywhere** — the raw SHA-256 of the input table appears in no sheet,
   Croissant or capsule field. *Negative control:* restore the unkeyed hash; the test fails.
3. **Keyed fingerprint** — same table and key → same fingerprint; different key → different;
   no key → field absent.
4. **Gate uses the public size** — the gate's decision does not change when the table's true
   length changes and the declared size does not.
5. **`dp_count` is charged** — the accountant's total rises by exactly one counting query's cost.
6. **Disclosure present** — `evaluation_privacy` and the residual-risk item are in the signed
   payload and mirrored into Croissant.

## Re-runs required

- **D1:** every result produced by AIM or fixed_workload — `results/h1_all_families.json`,
  `results/acs/h1_all_families.json`, `results/bank/h1_all_families.json`,
  `results/clique_confound.json`, `results/acs/clique_confound.json`,
  `results/adversary_comparison.json`, the selection ablation — and every document that quotes
  them. Checkpoints are keyed by configuration, not code, so `CHECKPOINT_VERSION` is bumped to force
  recomputation; `independent` and `pairwise` cells then act as a control and must reproduce.
- **D2–D4:** no research number changes; the demo capsules and any committed sheet or Croissant
  record are regenerated.
