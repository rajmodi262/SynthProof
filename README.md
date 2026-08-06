# SynthProof — Synthetic Data That Ships With Its Proof

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Status: research prototype](https://img.shields.io/badge/status-research%20prototype-orange.svg)](brutal_project_audit.md)

**SynthProof** is a research prototype for differentially private tabular synthesis. It generates
privacy-preserving synthetic replacements, tracks every privacy expenditure in an append-only
cryptographic ledger, and audits the released data against empirical attacks — reporting both the
formal bound ($\epsilon_{\text{proved}}$) and an empirical lower bound recovered by canary
auditing ($\epsilon_{\text{audited}}$).

> [!WARNING]
> **This is an in-progress capstone prototype, not a system you should use to release real data.**
> Several components are simplified baselines rather than the published algorithms they are named
> after, and the formal privacy bounds are not yet sound. The current state, every known defect,
> and the remediation plan are documented in full in **[brutal_project_audit.md](brutal_project_audit.md)**.
> Read that before citing or reusing any number this project produces.

---

## What is actually implemented

| Component | Status | Notes |
|---|---|---|
| **Append-only signed ledger** | ✅ Working | Ed25519 signatures over a SHA-256 hash chain, with tamper-detection tests. The most complete part of the project. |
| **Discrete Gaussian / Laplace samplers** | ✅ Working | Correct CKS'20 rejection sampler; χ²-tested against the exact PMF. |
| **Budget-charged domain profiler** | ⚠️ Partial | Charges budget for range discovery, but still releases the categorical domain un-noised, and assumes unjustified sensitivity. |
| **RDP accountant** | ⚠️ Unsound | Correct API (`dry_run` / `charge` / `snapshot` / `restore`); the subsampling amplification bound is not a citable theorem. Being replaced with `dp-accounting`. |
| **Generators** | ⚠️ Baselines only | Both are **independent-marginal samplers**. Neither is AIM/MST (no adaptive selection, no PGM) nor a real Gaussian copula (no correlation structure). |
| **Canary auditor** | ⚠️ Simplified | Real Clopper-Pearson bound with a *measured* baseline FPR from held-out canaries. Not the full Steinke et al. (2023) one-run construction. |
| **Attack suite** | ⚠️ 2 weak baselines | Nearest-neighbour MIA + exact-match singling-out. **LiRA, DOMIAS and attribute inference are NOT implemented.** |
| **Utility evaluator** | ✅ Working | TSTR vs TRTR on a shared held-out real split. |
| **Privacy Data Sheet** | ⚠️ Unsigned | Exports a real ledger hash, but carries no signature and has no third-party verifier yet. |
| **Subgroup fairness (H2)** | ❌ Not started | |
| **Ledger-driven allocation (H3)** | ❌ Not started | `Allocator` exists but nothing calls it. |

---

## 🛠️ Quick start

```bash
pip install -e ".[dev]"
```

```bash
python scripts/check_env.py
```

```bash
python -m pytest
```

```bash
python -m synthproof.cli demo --rows 100 --eps 1.0
```

```bash
uvicorn synthproof.api.main:app --reload --port 8000
```

> [!NOTE]
> There is currently **no way to run SynthProof on your own data** — no upload endpoint and no
> CLI input path. Every entry point operates on a generated 100-row toy table. This is a known
> gap, not an oversight in the docs.

---

## 📁 Repository structure

```
synthproof/
├── accounting/     # DP accountant (RDP composition) + discrete noise samplers
├── ledger/         # Append-only Ed25519-signed hash-chain ledger & allocator
├── data/           # Dataset wrapper & budget-charged domain profiler
├── generators/     # Independent-marginal synthesis baselines
├── audit/          # Canary privacy auditor (Clopper-Pearson lower bound)
├── attacks/        # Distance MIA baseline, exact-match singling-out risk
├── evaluate/       # Downstream ML utility (TSTR / TRTR)
├── frontier/       # Privacy-utility sweep engine & Privacy Data Sheet export
└── cli.py          # Command line interface
```

---

## 📊 Results

See [results/RESULTS.md](results/RESULTS.md). **These are preliminary numbers on a 100-row
synthetic toy table with a single seed** — they do **not** execute the protocol committed to in
[docs/preregistration.md](docs/preregistration.md) (UCI Adult and ACSIncome, 5 seeds).

---

## 📜 License

MIT — see [LICENSE](LICENSE). © 2026-2027 SynthProof Authors
(Raj Modi, Krishna Renuse, Aaditya Kumar Sinha, Levinesh G R).
