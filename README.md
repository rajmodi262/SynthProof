# SynthProof — Synthetic Data That Ships With Its Proof

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Status: research prototype](https://img.shields.io/badge/status-research%20prototype-orange.svg)](docs/AUDIT_AND_ROADMAP.md)

**SynthProof** generates differentially private synthetic tabular data, charges every
operation that touches the sensitive table to a privacy accountant, records the spend in an
append-only signed ledger, and audits the release against empirical attacks — reporting both
the formal bound (ε_proved) and an empirical lower bound (ε_audited).

> [!WARNING]
> **This is a capstone research prototype, not a system for releasing real data.**
> The accounting is sound and CI-verified, and the auditor's detection floor and ceiling are
> now both measured — so `ε_audited = 0` is reported alongside the smallest leak the
> instrument could have seen, rather than passed off as "no leakage". What still rules this
> out for real releases: authentication is a **single shared key** rather than real identity
> (so the ledger cannot say WHO spent the budget), no cross-session budget enforcement, no
> multi-table support, and single-table CSV only. Known gaps and the
> remediation plan are in **[docs/AUDIT_AND_ROADMAP.md](docs/AUDIT_AND_ROADMAP.md)**.

---

## What is implemented

| Component | Status | Notes |
|---|---|---|
| **Privacy accountant** | ✅ Working | Composition delegated to Google's `dp_accounting`. Budget enforcement, `dry_run`, `snapshot`/`restore`. |
| **ε-calibration** | ✅ Working | Inverts the composition theorem by bisection. proved/target ≈ 0.92, **never overspends**. CI-gated across 24 configurations. |
| **Discrete Gaussian / Laplace** | ✅ Working | CKS'20 rejection sampler, χ²-tested against the exact PMF. |
| **DP domain profiler** | ✅ Working | Public schema bounds cost nothing; category domains released through a noisy threshold. |
| **Append-only signed ledger** | ✅ Working | Ed25519 over a SHA-256 hash chain **plus a signed head** committing to `(entry_count, tip_hash)`. Stops modification, insertion, reordering, replay and **truncation** — **nine distinct attacks** covered by 14 tests in [tests/test_ledger_adversarial.py](tests/test_ledger_adversarial.py) — each attack run against live SQLite by an adversary with file access but no key, the remaining tests pinning correct behaviour (untampered, empty, head-tracks-tip, clear/re-append). Does not stop an adversary who holds the signing key. |
| **Differential accounting** | ✅ Working | Every release is composed through **two independent accountants** — Google's `dp_accounting` and `autodp` — and the verdict travels **inside the signed payload** (`accountant_agreement`). Under-reporting relative to the second accountant **refuses the release**; a conservative gap ships with the gap stated. `unavailable`/`unsupported` are reported rather than hidden, so an absent check never looks like a passed one. Motivated by Cebere et al. (arXiv 2602.17454, 2026): 12 DP libraries audited, 13 guarantee violations found. |
| **Pre-audit power analysis** | ✅ Working | `synthproof audit-power --eps 7.36 --canaries 60` answers *before* you run an audit whether it could certify the epsilon you want. This project ran the experiment that motivates it: H1 used 60 canaries against a proved ε of 7.36, where the ceiling is 2.97. The ceiling is **not our theorem** — it is a one-line corollary of Steinke et al. (2023) Thm 2.1, pinned bit-identical by a test. |
| **Signed Privacy Data Sheet** | ✅ Working | Persistent key; `synthproof verify sheet.json --pubkey org.pub` is runnable by a third party. Carries `domain_source` (was the schema declared, or read from your data?), `unit_of_privacy`, `contribution_bound`, `audit_ceiling`, and a plain-language odds statement — all inside the signed payload, so none can be stripped. |
| **Croissant 1.1 export** | ✅ Working | `synthproof run ... --croissant release.json` emits the signed sheet as a [Croissant](https://docs.mlcommons.org/croissant/) record with a `dp:` vocabulary extension, so a DP release loads in ordinary ML dataset tooling **and** stays third-party checkable. **Validated by the official MLCommons validator, 0 warnings** — run out-of-band via [scripts/validate_croissant.py](scripts/validate_croissant.py), because `mlcroissant` pins a numpy that breaks private-PGM and therefore AIM. The signature is **not** recomputed over the JSON-LD: it still covers the embedded sheet's canonical bytes, and `verify` cross-checks every field mirrored into the visible layer, refusing with `SIGNATURE VALID, RECORD UNTRUSTWORTHY` when they diverge. This is the [integration position](research/08_novelty_verdict.md) §3.3 made runnable: Croissant carries provenance and no attestation; Dibia et al. (2025) elicited the field set and propose no signing and no way to report an empirical metric's limits. We ship both. |
| **Pre-flight refusal** | ✅ Working | Refuses inputs that cannot be released honestly — too few rows, a near-unique identifier column, free text, no categorical target, a 2-way domain blow-up — using **only the declared schema and row count**, never the data. See [docs/design/USER_FACING_SYSTEM.md](docs/design/USER_FACING_SYSTEM.md) §2.5. |
| **Generators** | ✅ 6 mechanisms, 3 model classes | **Marginal-based:** `independent` (baseline) · `pairwise` (tree-structured 2-way) · `aim` (private-PGM) · `moments` (per-column mean/sd, a **second** independent-marginals control — it is **not** a copula: no covariance is estimated and no rank transform is applied). **Deep generative:** `dpvae` (DP-SGD variational autoencoder in JAX; per-example gradients via `vmap`, Poisson subsampling declared to the accountant). **Control arm:** `fixed_workload` — AIM's engine with the exponential-mechanism selection deleted and a public, data-independent workload substituted at identical ε, so selection can be isolated. See [results/SELECTION_ABLATION.md](results/SELECTION_ABLATION.md) |
| **Canary auditor** | ✅ Working, and its limits are measured | Paired Clopper-Pearson *and* the one-run Steinke construction. The **detection floor is now measured** ([results/DETECTION_FLOOR.md](results/DETECTION_FLOOR.md)): at 400 canaries the auditor resolves a 25% leak; at 10 canaries it needs a 100% leak. The **audit ceiling** `log(r/ln(1/α))` is reported beside every ε_audited, so a 0 is never mistaken for evidence of no leakage. |
| **Attack suite** | ✅ 5 attacks, **all three EDPB risks** | `distance_mia` (nearest-neighbour) · `exact_match_risk` (singling-out) · `domias` (k-NN density ratio, Breugel et al. 2023) · `linkability` (two disjoint halves of a record matched independently, scored against a row-shuffled release) · `attribute_inference` (scored against a conditional baseline, not a marginal one). **LiRA is deliberately NOT implemented** — a shadow-model attack is ~21h of compute for a likely wide-CI null, and calling anything cheaper "LiRA" would misname it. |
| **API authentication** | ⚠️ Shared key only | Set `SYNTHPROOF_API_KEY` and every endpoint that reads uploaded data, spends budget or exposes the ledger requires `Authorization: Bearer <key>` or `X-API-Key`. Unset by default so the local demo needs no configuration, and `/api/health` reports `auth: "disabled"` loudly when it is. **Not user authentication**: one key means one principal, so the ledger's `actor` cannot distinguish callers and rotation invalidates everyone at once. |
| **Web console** | ✅ Working, now tested | React + R3F. Live SSE pipeline, 3D record space, ledger tamper demo. **10 vitest tests** (`make console-test`) cover the hand-rolled SSE parser in `src/lib/api.ts` — including a frame split across two network chunks, which previously would have dropped a pipeline stage in silence. |
| **H1** — mechanism families | ⚠️ **Supported on Adult, NOT reproduced on ACS** | On UCI Adult all three families separate at ε=8 with non-overlapping CIs (aim > pairwise > independent). On ACSIncome the ordering **inverts** and AIM is indistinguishable from the independent baseline. Diagnosed and then **tested directly**: AIM's advantage over a no-dependence baseline is 11.9x larger on the pair it selects than anywhere else on Adult, but only 2.3x on ACS — so the metric's choice of column pair materially affects the ranking, while the effect itself does not transfer. The stronger reading, that AIM only wins where it selects, is **not** supported: each dataset has a counterexample. Reported, not tuned away — [results/acs/H1_RESULTS.md](results/acs/H1_RESULTS.md). |
| **H2** — subgroup disparity | ✅ **Bounded null** | 14 subgroup comparisons, 0 significant raw, 0 surviving BH-FDR or Bonferroni. 2 of 14 are statistically **equivalent** to chance within a pre-specified margin (TOST) — a bound on the effect, not merely absence of evidence. Detectability is stated: the adversary needed accuracy 0.600 and reached 0.562. See [results/H2_RESULTS.md](results/H2_RESULTS.md). |
| **H3** — budget allocation | ✅ **Null, replicated** | Utility-weighted vs uniform allocation at fixed total ε, on both datasets. **Not supported**: at none of the 5 ε values on either dataset does the paired weighted-minus-uniform gap in TSTR macro F1 have a bootstrap CI excluding zero. Weights are **declared public metadata**, never measured from the table — deriving them would be an uncharged query. See [results/h3_allocation.json](results/h3_allocation.json) and ch06 §6.10. |

---

## Quick start

```bash
pip install -e ".[dev]"
```

```bash
python -m pytest
```

Run a release on the built-in toy table:

```bash
python -m synthproof.cli demo --rows 200 --eps 1.0
```

Run it on your own CSV, and ship a signed data sheet:

```bash
python -m synthproof.cli keygen
```

```bash
python -m synthproof.cli run --input mydata.csv --schema myschema.json --eps 2.0 --mechanism aim --sign --out sheet.json
```

Anyone can then check that sheet with nothing but the file and your public key:

```bash
python -m synthproof.cli verify sheet.json --pubkey .keys/synthproof_ed25519.pub
```

> [!NOTE]
> Without `--schema`, column bounds are inferred **from your data**, which leaks. Generate a
> starter schema with `synthproof infer-schema`, then replace each range with a publishable
> fact about the domain before using it for a real release.

### Shipping the release as a Croissant record

To emit the synthetic table, the signed claim and a standards-conformant metadata record in
one step:

```bash
python -m synthproof.cli run --input mydata.csv --schema myschema.json --eps 2.0 --mechanism aim --sign --out sheet.json --synthetic-out release.csv --croissant release.croissant.json
```

`verify` takes either format and tells you which it got:

```bash
python -m synthproof.cli verify release.croissant.json --pubkey .keys/synthproof_ed25519.pub
```

The record mirrors ε, δ, the mechanism and the **audit ceiling** into fields a Croissant
consumer can read without knowing anything about DP, and carries the signed sheet verbatim
underneath. Editing a mirrored field leaves the signature valid but the record inconsistent,
and `verify` fails on exactly that:

```
FAILED
SIGNATURE VALID, RECORD UNTRUSTWORTHY.
The embedded Privacy Data Sheet is correctly signed, but the human-visible fields above it
have been altered and no longer match it.
  dp:epsilonProved: record says 0.01, signed sheet says 0.9615567837005196
```

To check conformance against the reference implementation (one-time setup builds an isolated
venv; it is kept separate because `mlcroissant` pins a numpy that breaks AIM):

```bash
python scripts/validate_croissant.py --setup
```

```bash
python scripts/validate_croissant.py release.croissant.json
```

## The console

Two processes:

```bash
make serve
```

```bash
cd web && npm install && npm run dev
```

Then open <http://localhost:5173>. See [web/README.md](web/README.md).

---

## Repository structure

```
synthproof/
├── accounting/     # DP accountant, calibration, discrete noise samplers
├── ledger/         # Ed25519-signed hash-chain ledger, allocator, data sheet signing
├── data/           # Schema, dataset wrapper, benchmark loaders, DP domain profiler
├── generators/     # independent · pairwise · aim (private-PGM) · moments · leaky
├── audit/          # Paired Clopper-Pearson + one-run Steinke, subgroup auditor,
│                   #   detection floor, audit ceiling, TOST equivalence
├── attacks/        # Distance MIA, exact-match singling-out, DOMIAS, attribute inference
├── evaluate/       # Downstream ML utility (TSTR / TRTR)
├── frontier/       # Experiment runner, Privacy Data Sheet exporter
├── api/            # FastAPI service backing the console
└── cli.py          # Command line interface
web/                # React console
```

---

## Results

See **[results/H1_RESULTS.md](results/H1_RESULTS.md)** (Adult),
**[results/acs/H1_RESULTS.md](results/acs/H1_RESULTS.md)** (ACSIncome) and
**[results/acs/CROSS_DATASET.md](results/acs/CROSS_DATASET.md)**.
Regenerate with `make h1` and `make h1-acs`.

**On UCI Adult**, the three mechanism families separate at ε = 8 with mutually non-overlapping
CIs: `aim` (0.0078) < `pairwise` (0.0283) < `independent` (0.0947) correlation error.

**On ACSIncome the ordering does not reproduce.** It inverts — `pairwise` (0.0202) <
`independent` (0.0535) ≈ `aim` (0.0626) — and AIM is not statistically distinguishable from
the independent-marginals baseline. We diagnosed rather than adjusted: the structure metric is
the correlation of a *single column pair*, and AIM selects exactly that pair as a clique at
every ε tested on Adult but at only one of three on ACS. The Adult headline is therefore partly
a coincidence between the metric and the mechanism's internal clique selection. That is a
finding about how DP-synthesis benchmarks are scored, and it is the most useful thing the
second dataset bought.

Both results required fixing our own measurement harness first — utility had been scored on a
model trained with 60 planted canaries, destroying 89% of the correlation signal and
systematically penalising the mechanisms that model dependence best. Two earlier versions of
the H1 document reported the opposite conclusion in good faith. §4 explains it.

---

## Development

```bash
make test        # pytest with coverage
make lint        # ruff + black, matching CI
make security    # bandit SAST, pip-audit, npm audit
make h1          # the H1 grid on UCI Adult (long)
make console-test # the console's vitest suite
```

Pull requests are reviewed by [CodeRabbit](.coderabbit.yaml), configured with this project's
standing rules — never report a number that was not computed, a charged mechanism must be
applied, name algorithms accurately.

---

## Citing and reproducing

- **[ARTIFACT.md](ARTIFACT.md)** — artifact-evaluation guide: every thesis claim mapped to the
  command that reproduces it, with expected output and runtime.
- **[CITATION.cff](CITATION.cff)** — GitHub renders a "Cite this repository" button from this.
- **[docs/SYNOPSIS_RECONCILIATION.md](docs/SYNOPSIS_RECONCILIATION.md)** — every promise in the
  submitted synopsis mapped to built / partial / descoped-and-why.

```bash
make reproduce
```

## License

MIT — see [LICENSE](LICENSE). © 2026-2027 SynthProof Authors
(Raj Modi, Krishna Renuse, Aaditya Kumar Sinha, Levinesh G R).
