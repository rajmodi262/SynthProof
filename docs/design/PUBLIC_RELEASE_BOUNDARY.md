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
| Sheet `seed`, Croissant `dp:seed` | `certificate.py`; `croissant.py` prov | **every noise draw** | released, signed | **D5** — withheld; an unset seed is drawn from the OS |
| `mechanism`, `delta`, `target_column`, `dataset_name` | operator configuration | public declaration | fine | unchanged |
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

## D5 — the run seed

Found while implementing D2, and measured before anything was changed. The sheet recorded `seed`
and the Croissant record mirrored it as `dp:seed`. Every noise draw derives from that seed, so a
release is a deterministic function of (table, seed). The standard adversary rebuilds the release
for both candidate tables with the published seed and sees which one matches.

`research/release_boundary/seed_replay_probe.py`: n = 1000, one record removed, ε = 1, the same
900 output rows in both worlds so the row count cannot be what separates them, 5 trials each.

| Code | Mechanism | Replay of true table matches | Replay of neighbour matches | Wrong seed matches |
|---|---|---:|---:|---:|
| `0da936e` | independent | 5 / 5 | 0 / 5 | 0 / 5 |
| `0da936e` | pairwise | 5 / 5 | 0 / 5 | 0 / 5 |
| `0da936e` | aim | 5 / 5 | 0 / 5 | 0 / 5 |
| `ab0107e` | independent | 5 / 5 | 0 / 5 | 0 / 5 |
| `ab0107e` | pairwise | 5 / 5 | 0 / 5 | 0 / 5 |
| `ab0107e` | aim | 0 / 5 | 0 / 5 | 0 / 5 |

`independent` and `pairwise` were exactly replayable before this work. AIM was not, only because
private-pgm's sampler drew from NumPy's unseeded global generator. Seeding that sampler (`0da936e`)
made AIM replayable too. `INFERENCE:` AIM's measurement and selection noise was replayable at
`ab0107e` as well, so an adversary could have compared model output distributions rather than
tables; that weaker attack was not run.

**Fix.** The seed is never written to a sheet, a Croissant record or a capsule. `FrontierEngine()`,
the CLI and the API draw a 63-bit seed from the OS when none is given. The old default of 42 was a
published seed. A seed the operator supplies is kept for their reproducibility and never recorded;
the CLI warns that the release is only as private as that number is secret.

Two consequences were measured and fixed:

- The evaluators and attacks pass their seed to NumPy's legacy generator and scikit-learn, which
  reject seeds of 2³² or more, so every mechanism crashed under a 63-bit seed. They draw no DP
  noise and now receive `seed % 2**32`, which is unchanged for every research seed.
- With x64 off, `jax.random.PRNGKey` keeps only the low 32 bits: 2⁴⁰ + 7 and 2⁴⁰ + 2³³ + 7 gave the
  identical key. DP-VAE now folds the high words into the key, and a seed below 2³² keeps exactly
  the key it had.

**Residual, not fixed.** Every mechanism draws its per-measurement noise seeds as
`rng.integers(0, 2**31 - 1)` from a full-entropy generator. Recovering one such 31-bit sub-seed by
brute force needs the noisy measurement it produced, and no artefact publishes one. Widening
the sub-seeds would change every committed result, so it is recorded rather than done.

**Separate open issue found by the new tests.** For DP-VAE, `run_sweep`'s differential accountant
refuses the release. `dp_accounting` composes to ε = 0.94 and autodp to 2.45 at 900 rows, and to 9.50
at 3000 rows, identically with seeds 3 and 2⁶³ − 1. It is independent of D2–D5. It is pinned as a
strict expected failure in `tests/test_release_boundary.py` and has not been investigated yet.

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
