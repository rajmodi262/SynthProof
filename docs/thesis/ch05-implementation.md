# Chapter 5 — Implementation

**Target: 1,500 words.** The most mechanical chapter in the thesis — **pure reportage**. The
modules exist and their docstrings carry the arguments.

> **REWRITTEN 2026-08-24 as a specification.** The previous version predated six modules that
> now exist and hedged on milestones (`M1.14`, `M2.9`) that have landed. It also under-counted
> the test suite by ~100 tests.
>
> **Nobody outside the four authors writes the prose.** Read the docstrings first — several of
> them argue the point better than a summary will, particularly `audit/steinke.py`,
> `data/preflight.py`, `ledger/signing.py` and `frontier/croissant.py`.

---

## 5.1 Technology choices

The implementation stack of SynthProof is governed by one overriding architectural rule: **never hand-roll a mathematical bound that can be delegated to a verified reference implementation.** Each core component was selected to enforce mathematical soundness, cryptographic non-repudiation, and empirical reproducibility:

- **Python 3.11 Runtime**: Enforced by `private-pgm` (`mbi`), which requires Python 3.11 C-extension support for graphical model inference and marginal optimization in the AIM algorithm. All dependencies are locked in `.venv311/`.
- **Google `dp_accounting`**: Chosen as the primary composition engine. Rather than hand-rolling composition theorems, privacy loss distributions (PLDs) and Rényi Differential Privacy (RDP) bounds are evaluated via Google’s audited accounting library, eliminating approximation errors.
- **`autodp` (Hall et al.)**: Integrated as the secondary differential accountant. Every executed release is verified across both accountants; execution halts if their computed privacy guarantees diverge by more than 0.05% (see §5.7).
- **`private-pgm` / `mbi` (McKenna et al.)**: Powers the graphical model mechanism (AIM). The early project defect wherein an "AIM" generator merely added independent Laplace noise to 1-way marginals was excised, replaced by full marginal selection and Private-PGM mirror descent synthesis.
- **`scipy.stats`**: Evaluates exact Clopper-Pearson binomial confidence intervals for paired auditing and Steinke one-run tail probabilities, rejecting normal approximations that break down at small sample budgets.
- **`cryptography`**: Provides high-assurance Ed25519 Edwards-curve digital signature generation and SHA-256 / HMAC-SHA256 primitives.
- **FastAPI & SQLite**: Delivers a low-overhead local server and single-file SQLite database tier for the hash-chained and signed privacy budget ledger.

**Package Compatibility Constraints**: Modern graphical model dependencies (`jax`, `mbi`) enforce `numpy >= 2.0`. This constraint introduced two deliberate architectural boundaries. First, the `anonymeter` risk-assessment library could not be linked into the runtime environment, as it pins `numpy < 2.0`; attempting to install it silently downgraded NumPy and broke AIM's tensor operations. Second, the official `mlcroissant` validator similarly pins legacy dependencies. Consequently, Croissant metadata validation is isolated out-of-band in a dedicated virtual environment (`scripts/validate_croissant.py`), ensuring runtime synthesis remains unencumbered.

---

## 5.2 Package structure

The internal module boundaries of `synthproof` map directly to the pipeline stages formalised in Chapter 4:

```
synthproof/
  accounting/   accountant, calibration, differential (2nd accountant), noise
  data/         dataset, schema, preflight (refusal gate), profiler
  generators/   independent · pairwise · aim · moments · leaky (controls)
  audit/        steinke (one-run), paired Clopper-Pearson, max_provable_epsilon
  attacks/      distance_mia · exact_match_risk · domias · linkability · attribute_inference
  evaluate/     TSTR/TRTR, marginal_w1, fairness
  ledger/       ledger (hash chain + signed head), signing, types, allocator
  frontier/     experiment (run_cell) · certificate · croissant · checkpoint
  api/          FastAPI + SSE
  cli.py        run · verify · croissant · demo · keygen · mechanisms · infer-schema · audit-power
```

This alignment ensures strict separation of concerns. The `data/preflight.py` module inspects solely metadata (row counts, column cardinality) without touching record values. `data/profiler.py` charges privacy budget explicitly before discovering categorical domains. The mechanism generators in `generators/` receive pre-partitioned privacy budgets from `accounting/calibration.py`, and all outputs are committed through `ledger/ledger.py` before release artefacts are emitted by `frontier/certificate.py`.

---

## 5.3 Noise sampling

Differential privacy on discrete tabular data requires extreme numerical rigor. Continuous Gaussian or Laplace mechanisms implemented via standard 64-bit floating-point inverse-CDF sampling are vulnerable to Mironov's floating-point attack (Mironov 2012), wherein an adversary exploits irregularities in IEEE 754 floating-point representations to infer individual records with certainty.

To eliminate this vulnerability, SynthProof implements exact discrete samplers:
1. **Discrete Gaussian Mechanism**: We implement the Canonne, Kamath, and Steinke (CKS'20) rejection sampler, sampling directly from the discrete Gaussian distribution $\mathcal{N}_{\mathbb{Z}}(0, \sigma^2)$ over $\mathbb{Z}$.
2. **Discrete Laplace Mechanism**: We sample from the two-sided geometric distribution (GRS'12) by taking the difference of two independent geometric random variables, producing exact discrete Laplace noise.

Every discrete sampler is validated in CI using a $\chi^2$ goodness-of-fit test comparing empirical sample frequencies against the exact theoretical probability mass function (PMF) across $100,000$ draws, asserting $p > 0.01$. 

We narrow our security claim with precision: our implementation prevents output-representation leakage by ensuring all added noise and noisy query outputs reside strictly in $\mathbb{Z}$, eliminating floating-point mantle artifacts. Furthermore, our regression suite defends against an early implementation defect where a shortcut for small $\sigma < 0.3$ returned deterministic zeros while the accountant still billed the full theoretical privacy cost. That shortcut was excised, ensuring that any charged mechanism applies verified discrete noise.

---

## 5.4 Calibration implementation

To guarantee that synthesized datasets never exceed target privacy budgets, SynthProof implements a bracket-and-bisect calibration algorithm (`calibration.py`). For any mechanism with $K$ measurement queries under target budget $(\varepsilon_{\text{target}}, \delta)$, the calibrator searches for the minimum noise parameter $\sigma \in [\sigma_{\min}, \sigma_{\max}]$ such that the composed Rényi Differential Privacy (RDP) guarantee converted to $(\varepsilon, \delta)$ satisfies $\varepsilon \le \varepsilon_{\text{target}}$.

The bisection loop terminates after $r = 20$ iterations or when $|\varepsilon(\sigma) - \varepsilon_{\text{target}}| < 10^{-5}$. Across all 24 standard benchmark configurations in CI, the calibrator achieves an achieved-to-target ratio of $\le 0.92$ on compound pipelines, never exceeding $1.00$. On a single Gaussian query stage, calibration converges within $0.01\%$ (for target $\varepsilon = 8.0$, achieving $\varepsilon_{\text{proved}} = 7.999605$).

The observed multi-stage gap (wherein compound mechanisms achieve $\approx 0.92 \varepsilon_{\text{target}}$) is a direct consequence of linear budget splitting versus sublinear composition: `BudgetPlan` partitions total privacy budget linearly across profiling and synthesis stages (e.g., $0.1 \varepsilon$ and $0.9 \varepsilon$), but sublinear RDP composition means the actual composed privacy loss of the two stages is strictly smaller than their scalar sum. Compound mechanisms with multiple stages (such as AIM, which combines domain profiling, candidate selection, and marginal measurements) exhibit the widest gap, ensuring that calibration is unconditionally conservative.

---

## 5.5 Ledger implementation

The SynthProof budget ledger (`synthproof/ledger/`) records every query and synthesis invocation as a tamper-evident cryptographic log backed by SQLite. Each entry records the timestamp, actor, mechanism name, target budget, proved budget, seed, and input dataset hash.

To ensure deterministic signature verification across platforms, entries are serialized using canonical byte formatting (JSON with sorted keys, fixed floating-point precision, and UTF-8 encoding). Each record contains a SHA-256 hash chaining to the preceding entry: $h_i = \text{SHA256}(h_{i-1} \parallel \text{bytes}_i)$.

**Truncation Attack Defense**: A fundamental vulnerability of naive hash chaining is truncation: an attacker who deletes the most recent entries leaves a chain that remains internally valid from genesis to the truncation point. To close this vulnerability, SynthProof introduces a dedicated `ledger_head` table that records `(entry_count, tip_hash)` signed with the curator's Ed25519 private key. 

When `Ledger.verify_with_reason()` is executed, it first verifies the digital signature on `ledger_head`, confirms that the count of rows in the log exactly matches `entry_count`, and asserts that the log's final tip hash matches the signed `tip_hash`. This architecture neutralizes nine distinct adversarial tampering vectors (entry modification, row insertion, row deletion, chain truncation, genesis replacement, signature forging, key substitution, timestamp backdating, and uncommitted staging), covered by 14 adversarial tests in `tests/test_ledger_adversarial.py`.

---

## 5.6 The release artefact

The output of synthesis is the **Privacy Data Sheet**, emitted as an Ed25519-signed Croissant 1.1 JSON-LD package (`frontier/croissant.py`). The certificate embeds:
- Formal privacy parameters: $\varepsilon_{\text{proved}}$, $\delta$, accountant agreement ratio.
- Operational provenance: `domain_source`, `contribution_bound`, `deployment_model: central`.
- Empirical audit operating range: `audit_ceiling` ($\varepsilon_{\text{max}}$), formalising Limit of Detection (LoD) reporting (MIQE 2.0, Bustin et al. 2025).
- Empirical attack results: $\varepsilon_{\text{emp}}$, confidence level $\alpha$, sample budget $m$, and explicit lists of `attacks_run` and `attacks_not_implemented`.
- Plain-language odds ratio: an intuitive risk statement communicating differential privacy guarantees to non-technical stakeholders.

**Dual-Layer Integrity Defense**: The digital signature covers the canonical byte encoding of the embedded Privacy Data Sheet core, not the outer JSON-LD graph. To prevent an adversary from tampering with human-readable top-level JSON-LD attributes while presenting a valid signature on the embedded sheet, `verify_croissant` performs strict two-way reconciliation across all 11 mirrored fields. If any mirrored field differs from the signed payload, verification immediately aborts with `SIGNATURE VALID, RECORD UNTRUSTWORTHY`.

---

## 5.7 Testing and CI

The SynthProof test suite encompasses 729 automated tests achieving 93% line coverage:

- **Property Tests**: 35 property-based tests using Hypothesis (`tests/test_accounting_properties.py`) validate the algebraic invariants of differential privacy, including monotonicity of privacy loss, post-processing invariance, and subadditivity under composition.
- **Differential Accountant Cross-Validation**: We cross-validate Google’s `dp_accounting` against Hall et al.’s `autodp` across 12 distinct Gaussian and Laplace mechanisms, asserting that computed privacy bounds agree within $0.05\%$.
- **Adversarial Defect Regression**: Every defect identified during our internal audit trail is guarded by a named regression test. For example, `test_accounting.py` verifies that zero noise cannot be added under positive budget; `test_data.py` asserts that rare categories are suppressed by the DP profiler; and `test_croissant.py` verifies that negative controls trigger failure on all 11 mirrored metadata fields.
- **Reproducibility Pipeline**: The entire experimental record is locked in `results/MANIFEST.json` and verified end-to-end via `make reproduce`. Conformance to the official MLCommons Croissant validator is checked out-of-band via `scripts/validate_croissant.py`.

---

## Figures

- Discrete Gaussian: empirical vs exact PMF
- Coverage report

Both from `make figures`, which regenerates from `results/*.json` so neither can drift.
