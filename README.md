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
> The privacy accounting is sound and the calibration is verified in CI, but the empirical
> auditor's detection floor has never been measured, so `ε_audited = 0` currently means
> "below this instrument's sensitivity", not "no leakage". Known gaps and the remediation
> plan are in **[docs/AUDIT_AND_ROADMAP.md](docs/AUDIT_AND_ROADMAP.md)**.

---

## What is implemented

| Component | Status | Notes |
|---|---|---|
| **Privacy accountant** | ✅ Working | Composition delegated to Google's `dp_accounting`. Budget enforcement, `dry_run`, `snapshot`/`restore`. |
| **ε-calibration** | ✅ Working | Inverts the composition theorem by bisection. proved/target ≈ 0.92, **never overspends**. CI-gated across 24 configurations. |
| **Discrete Gaussian / Laplace** | ✅ Working | CKS'20 rejection sampler, χ²-tested against the exact PMF. |
| **DP domain profiler** | ✅ Working | Public schema bounds cost nothing; category domains released through a noisy threshold. |
| **Append-only signed ledger** | ✅ Working | Ed25519 over a SHA-256 hash chain, tamper-tested against live SQLite. |
| **Signed Privacy Data Sheet** | ✅ Working | Persistent key; `synthproof verify sheet.json --pubkey org.pub` is runnable by a third party. |
| **Generators** | ✅ 3 real families | `independent` (baseline) · `pairwise` (tree-structured 2-way) · `aim` (private-PGM) · `copula` (per-column control) |
| **Canary auditor** | ⚠️ Underpowered | Real Clopper-Pearson bound, measured FPR, Fisher exact test — but **detection floor unmeasured**, so it reads 0 everywhere. |
| **Attack suite** | ⚠️ 1 of 4 | Nearest-neighbour MIA + exact-match singling-out. **LiRA, DOMIAS and attribute inference are NOT implemented.** |
| **Web console** | ✅ Working | React + R3F. Live SSE pipeline, 3D record space, ledger tamper demo. |
| **H1** — mechanism families | ✅ **Supported** | Structure and utility separate with non-overlapping CIs. See [results/H1_RESULTS.md](results/H1_RESULTS.md). Privacy half blocked on the auditor. |
| **H2** — subgroup disparity | ❌ Not started | |
| **H3** — ledger-driven allocation | ❌ Not started | `Allocator` exists; nothing drives generators with it. |

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
├── generators/     # independent · pairwise · aim (private-PGM) · copula
├── audit/          # Canary auditor (Clopper-Pearson lower bound)
├── attacks/        # Distance MIA baseline, exact-match singling-out
├── evaluate/       # Downstream ML utility (TSTR / TRTR)
├── frontier/       # Experiment runner, Privacy Data Sheet exporter
├── api/            # FastAPI service backing the console
└── cli.py          # Command line interface
web/                # React console
```

---

## Results

See **[results/H1_RESULTS.md](results/H1_RESULTS.md)**. Regenerate with `make h1`.

The headline: `pairwise` and `aim` both preserve joint structure substantially better than the
independent baseline at ε = 8, with non-overlapping confidence intervals, and both improve as
the budget grows while the baseline stays flat.

That result required fixing our own measurement harness first — utility was being scored on a
model trained with 60 planted canaries, which destroyed 89% of the correlation signal being
measured and systematically penalised the mechanisms that model dependence best. Two earlier
versions of the H1 document reported the opposite conclusion in good faith. §4 of the results
document explains it.

---

## Development

```bash
make test        # pytest with coverage
make lint        # ruff + black, matching CI
make security    # bandit SAST, pip-audit, npm audit
make h1          # the H1 grid on UCI Adult (long)
```

Pull requests are reviewed by [CodeRabbit](.coderabbit.yaml), configured with this project's
standing rules — never report a number that was not computed, a charged mechanism must be
applied, name algorithms accurately.

---

## License

MIT — see [LICENSE](LICENSE). © 2026-2027 SynthProof Authors
(Raj Modi, Krishna Renuse, Aaditya Kumar Sinha, Levinesh G R).
