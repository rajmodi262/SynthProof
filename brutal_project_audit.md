# SynthProof — Brutal Code-Level Audit

> **Audit date:** 2026-08-07 · **Method:** full-file read of all 28 source files + test-suite execution + live execution of the sweep pipeline to verify claims empirically.
>
> Every finding below was **reproduced by running the code**, not inferred from reading it. Commands used are shown so any finding can be re-checked independently.

---

## Verdict

> ### **3.5 / 10 as a research capstone**
> (≈6/10 graded purely as a software-engineering artifact.)
>
> **A beautifully packaged shell around algorithms that do not do what they claim, evaluated on data that cannot test the hypothesis, producing a headline metric that is structurally guaranteed to be zero.**
>
> The *idea* is a genuine 9/10. The architecture is a genuine 7.5/10. The science, as implemented, is a 1–2/10. That gap is the whole story.

### Scorecard

| Dimension | Score | Weight | Weighted |
|---|---|---|---|
| Package architecture & engineering | 7.5/10 | 15% | 1.13 |
| Cryptographic ledger | 7/10 | 10% | 0.70 |
| **DP correctness (the core claim)** | **2/10** | 30% | **0.60** |
| **Experimental rigor** | **1/10** | 25% | **0.25** |
| Novelty *as implemented* | 2/10 | 10% | 0.20 |
| Documentation & presentation | 6.5/10 | 5% | 0.33 |
| Testing | 4/10 | 5% | 0.20 |
| **TOTAL** | | | **3.47 / 10** |

> [!NOTE]
> **Tier 0 remediation was applied on 2026-08-07, after this audit was written.** The findings
> below describe the state that was audited. See the Tier 0 checklist at the end for what has
> since been fixed. Findings F2, F4, F5, F6 and F11 (partial) remain open.

---

## Changes since the previous audit (2026-08-06)

| Previous finding | Status today |
|---|---|
| §1 "Discrete Gaussian is `np.random.normal` rounded" | ✅ **FIXED.** [`noise.py:48`](synthproof/accounting/noise.py) now implements a correct CKS'20 rejection sampler with a DLap envelope. Credit where due. |
| §8 "Accountant ignores subsampling" | ⚠️ **SUPERSEDED — and the previous claim was wrong.** Subsampling *is* now implemented ([`accountant.py:73`](synthproof/accounting/accountant.py)), but the bound used is **not sound**. See F4. |
| §4 "Canary auditor always returns 0" | ❌ Still true — and now traced to **three independent** structural causes. See F1. |
| §11 "Unused dependencies" | ❌ Still true. Verified by grep: 6 of 14 runtime deps have zero imports. |
| All others | ❌ Still open. |

---

## ✅ What is genuinely good

| Aspect | Score | Notes |
|---|---|---|
| **Package architecture** | 8/10 | `accounting / ledger / data / generators / audit / attacks / evaluate / frontier` is textbook. Proper `BaseGenerator` ABC, frozen dataclasses with `__post_init__` validation, entry points, Docker, Makefile. |
| **Cryptographic ledger** | 7/10 | Real Ed25519 signing, real SHA-256 hash chaining, and tamper tests that actually `UPDATE`/`DELETE` SQLite rows and assert `verify() is False`. The strongest component in the repo. |
| **Accountant API design** | 7/10 | `dry_run` / `charge` / `snapshot` / `restore` / `remaining` is exactly the interface a real budget system needs. The *interface* is a contribution; only the math behind it is unsound. |
| **Discrete Gaussian sampler** | 8/10 | Now genuinely correct CKS'20. |
| **Research framing** | 6.5/10 | `thesis.md`, `threat_model.md`, `preregistration.md` show the right instincts. Real citations to real papers. |

---

## 💀 Fatal findings

### F1 — The headline metric is structurally always zero

`ε_audited` — the entire point of the project — is `0.00` in every row of [`results/RESULTS.md`](results/RESULTS.md). Verified that this is not noise but a structural impossibility:

```
target=0.5   proved=  0.964   audited=0.0
target=1.0   proved=  1.948   audited=0.0
target=2.0   proved=  4.001   audited=0.0
target=4.0   proved=  8.460   audited=0.0
target=8.0   proved= 18.744   audited=0.0
```

Three independent causes, any one of which alone is fatal:

1. **Numerical canaries can never match.** [`canary.py:37`](synthproof/audit/canary.py) plants `max*3 + 100.0` floats; [`canary.py:55`](synthproof/audit/canary.py) then tests exact float membership against continuously-sampled synthetic values. P(match) ≈ 0, and the loop `break`s on first miss.
2. **Categorical canaries are not in the sampling support.** [`sweep.py:51-54`](synthproof/frontier/sweep.py) profiles *before* planting, so `profile.columns[col].categories` never contains `CANARY_VAL_*`; [`aim.py:55`](synthproof/generators/aim.py) iterates only over profiled categories via `counts.get(c, 0)`.
3. **The estimator is fabricated regardless.** [`canary.py:64-74`](synthproof/audit/canary.py) claims "Clopper-Pearson / Steinke audit lower bound" in a comment but computes `log(p_in / 0.05)` with a **hardcoded** `p_out`, and a `p_value` hardcoded to `0.01` or `0.5`. No confidence interval, no hypothesis test, no one-run construction.

> **Consequence: H1 — the primary thesis — has not been tested, and cannot be tested by this code.**

---

### F2 — `target_eps` is not a privacy budget

No calibration inversion exists anywhere. `target_eps` picks a noise scale; RDP composition then re-derives ε from scratch. The error is not constant — it grows:

| target ε | proved ε | ratio |
|---|---|---|
| 0.5 | 0.96 | 1.93× |
| 1.0 | 1.95 | 1.95× |
| 2.0 | 4.00 | 2.00× |
| 4.0 | 8.46 | 2.11× |
| 8.0 | 18.74 | **2.34×** |

A DP platform whose "ε = 8" ships ε = 18.7 does not have a budget interface. The root cause is [`aim.py:32`](synthproof/generators/aim.py) — `noise_scale = sqrt(d)/target_eps` is a heuristic, not an inversion of the composition theorem.

---

### F3 — Silent zero-noise hole (most dangerous line in the repo)

[`noise.py:112`](synthproof/accounting/noise.py):

```python
if sigma < 0.3:
    return np.zeros(size, dtype=np.int64)
```

Verified: `sample_discrete_gaussian(0.29, size=10)` → `[0 0 0 0 0 0 0 0 0 0]`.

**The accountant charges ε for a mechanism that adds no noise at all.** This silently converts a privacy guarantee into a false statement. Worse, it is *reachable in the actual sweep*: at `d=3, target_eps=8`, `noise_scale = √3/8 = 0.216 < 0.3`.

---

### F4 — Unsound subsampling amplification

[`accountant.py:99-107`](synthproof/accounting/accountant.py) returns `min(q·ρ(α), truncated_MTZ)`:

- **`q·ρ(α)` is not a theorem.** RDP does not amplify linearly under subsampling. No reference licenses this bound.
- **The second branch truncates** the binomial series of Mironov–Talwar–Zhang (2019) Prop. 10 — the docstring admits this ("for simplicity and numerical stability").
- **`DEFAULT_ALPHAS` are non-integer** (`np.linspace(1.1, ...)`), while the MTZ bound is stated for integer orders.

Verified impact at `q=0.01`: ε drops **5.30 → 0.48**. That 11× discount is not provably yours.

Additionally, [`accountant.py:136`](synthproof/accounting/accountant.py) cites "Balle et al. (2020) Proposition 3" but implements the classic Mironov conversion `ρ(α) + log(1/δ)/(α−1)`. Sound, but mis-attributed — a viva examiner will ask.

---

### F5 — The DP profiler leaks the exact data domain

[`profiler.py:71-84`](synthproof/data/profiler.py): the categorical branch **charges ε**, then publishes `dataset.df[col].unique()` — the true, un-noised category list.

Paying budget and then not applying the mechanism is strictly worse than not paying: privacy is spent *and* the domain leaks deterministically. Rare or unique categorical values — exactly the ones that identify individuals — are released verbatim.

Compounding this: min/max over an **unbounded** column has unbounded sensitivity, yet [`profiler.py:47`](synthproof/data/profiler.py) declares `sensitivity=1.0`. No clipping is applied anywhere before mean/std estimation in [`copula.py:42`](synthproof/generators/copula.py) either, so that `sensitivity=1.0` is equally unjustified. **The foundational step of the pipeline is not DP.**

---

### F6 — Both generators are the same model, and neither is what it is named

- **AIM is not AIM.** No exponential-mechanism marginal selection, no iteration, no 2D/kD marginals (grep confirms the only occurrence of "2D" is in a docstring), no PGM inference. It is independent noisy 1-D histograms.
- **The copula has no copula.** No covariance matrix, no rank transform, no correlation anywhere. [`copula.py:83`](synthproof/generators/copula.py) draws independent `np.random.normal` per column.
- **`abs()` on the noise breaks DP.** [`copula.py:48`](synthproof/generators/copula.py): `noise_std = abs(sample_discrete_gaussian(...))` is a biased one-sided perturbation, not the Gaussian mechanism.

Verified: the two "mechanism families" are statistically indistinguishable.

| | TSTR F1 | TRTR F1 | LiRA acc |
|---|---|---|---|
| AIM / MST | 0.3246 | 0.9706 | 0.48 |
| Gaussian Copula | 0.3280 | **0.9706** | **0.48** |

> H1 requires comparing mechanism families. There is one family, instantiated twice.

---

### F7 — Fabricated metrics in a research artifact

This is the category that ends vivas.

| Location | Code | Problem |
|---|---|---|
| [`lira.py:61`](synthproof/attacks/lira.py) | `auc_score = min(1.0, acc + 0.05)` | AUC is **invented arithmetic**, never computed |
| [`anonymeter.py:34-35`](synthproof/attacks/anonymeter.py) | `linkability = singling_out*0.8 + 0.05` | Two of three "independent risks" are affine functions of the third |
| [`utility.py:73`](synthproof/evaluate/utility.py) | `fairness_drift = abs(tstr−trtr)*0.1` | Not a fairness metric — it is `utility_gap/10`. No subgroups exist anywhere → **H2 untestable** |
| [`utility.py:36-42`](synthproof/evaluate/utility.py) | returns `0.75, 0.80, 0.05, 0.02, 0.01` | Hardcoded "good-looking" results on the fallback path |
| [`canary.py:67,74`](synthproof/audit/canary.py) | `p_out = 0.05`, `p_value = 0.01 or 0.5` | Magic constants presented as statistics |

---

### F8 — TRTR is measured on training data

[`utility.py:47-50`](synthproof/evaluate/utility.py):

```python
clf_trtr.fit(X_real, y_real)
trtr_preds = clf_trtr.predict(X_real)   # ← same data
```

That is a RandomForest's **training** accuracy — hence the constant `0.971`. There is **no train/test split anywhere in the project**. The TSTR-vs-TRTR gap therefore compares a held-out score against an overfit in-sample score. The reported 62-point gap is an artifact of this bug, not a privacy–utility finding.

---

### F9 — The experiments violate the project's own preregistration

| [`preregistration.md`](docs/preregistration.md) commits to | [`sweep.py`](synthproof/frontier/sweep.py) actually does |
|---|---|
| UCI Adult (n=48,842), ACSIncome (n=100,000) | `create_synthetic_toy(num_rows=100)` |
| 5 seeds per configuration | 1 seed |
| Real correlation structure | age, income, category drawn **independently** ([`dataset.py:42-44`](synthproof/data/dataset.py)) |

And [`results/RESULTS.md`](results/RESULTS.md) is stamped **"Status: FILLED (Completed Experimental Sweeps)"**.

> **This is the most serious finding in the audit — not technically, but for academic integrity.** A signed preregistration plus a results table claiming completion, on toy data, is the one item that cannot be explained away in a viva. Fix the header today, independent of everything else.

Note also that the toy data is **independent by construction**, so there is no joint structure for a synthesizer to preserve or destroy. The entire utility evaluation is measuring nothing.

---

### F10 — The "signed Privacy Data Sheet" is neither signed nor ledgered

- [`certificate.py:55`](synthproof/frontier/certificate.py) constructs a `Ledger`, **appends nothing**, then reports `ledger.get_latest_hash()` — which returns the genesis `"0"*64`.
- `PrivacyDataSheet` has **no signature field**. The README's central promise — "ships with its proof" — is not implemented.
- The Ed25519 key is generated fresh in memory on every instantiation ([`ledger.py:22`](synthproof/ledger/ledger.py)) and never persisted. For a file-backed DB, all signatures become permanently unverifiable after restart. No external verifier exists, so no third party can check anything.

---

### F11 — README claims features that do not exist

| Claim | Reality |
|---|---|
| "four independent... attacks (LiRA, DOMIAS, Anonymeter, Attribute Inference)" | 2 exist, both stubs. Grep for DOMIAS / attribute inference → only a docstring in `attacks/__init__.py` |
| "signed Privacy Data Sheet" | Unsigned; empty ledger hash |
| "AIM / MST (marginal-based)" | Independent 1-D histograms |
| CI badge → `.github/workflows/ci.yml` | **No `.github/` directory exists** |
| "MIT License" | **No LICENSE file exists** |

---

## 🟠 Serious, non-fatal

- **Not a git repository.** No version control at all on a capstone.
- **6 runtime dependencies never imported** — verified by grep across `synthproof/`, `tests/`, `scripts/`: `opacus`, `dp-accounting`, `autodp`, `duckdb`, `pyarrow`, `scipy` have zero references. `torch` appears only in `check_env.py`. Google's DP accountant is declared as a dependency and then replaced by a less-sound hand-rolled one.
- **`hypothesis` in dev deps** and `conftest.py` advertises "property checks" — no property test exists.
- **Python version mismatch**: `requires-python = ">=3.11"`; the environment runs **3.10.0**.
- **`docker-compose.yml` provisions PostgreSQL** and sets `DATABASE_URL`; the code only ever uses in-memory `sqlite3`. Dead infrastructure.
- **API defects** ([`api/main.py`](synthproof/api/main.py)): `allow_origins=["*"]` with `allow_credentials=True` is an invalid and unsafe CORS combination; no auth; no rate limiting; the `mechanism` parameter is **accepted and silently ignored** (FrontierEngine hardcodes `AIMGenerator`); `UploadFile, File` are imported but **no upload endpoint exists**. Consequence: *there is no way to run SynthProof on your own data* — not via API, not via CLI.
- **Test quality**: every assertion is a shape or range check (`0.0 <= x <= 1.0`, `len(df) == 50`). Not one test asserts a correct *value*. 83% coverage, with **0%** on [`sweep.py`](synthproof/frontier/sweep.py) and [`cli.py`](synthproof/cli.py) — the two entry points that produce the reported results. None of these 25 tests would catch any finding in this document.
- **Reproducibility**: `sample_discrete_laplace` uses the global legacy `np.random` with no seed parameter, while `sample_discrete_gaussian` accepts one. Profiler noise is therefore not reproducible.
- **`_classify_columns`** ([`dataset.py:21`](synthproof/data/dataset.py)) uses `nunique() > 10` on raw data — a schema decision derived from sensitive data with no budget charged.
- **Repo hygiene**: `.coverage` and `.pytest_cache/` present in the working tree and absent from `.gitignore`.
- **Narrative drift**: 427 / 950 TASKS.md checkboxes complete (45%), yet README and RESULTS are written as though the project is finished.

---

## 🎯 Roadmap to 10/10

The architecture is the hard part and it is already right. Every module boundary is where it should be. This is not a rebuild — it is filling correct implementations in behind interfaces that already exist. Roughly 6–8 focused weeks.

### Tier 0 — Integrity & foundations ✅ COMPLETED 2026-08-07

1. ✅ `git init` + initial commit. *(Still to do: push to a remote and tag `prereg-v1`.)*
2. ✅ RESULTS.md now leads with a PRELIMINARY warning and a table contrasting the preregistered protocol against what was actually run, plus a "how to read this table" footer.
3. ✅ README rewritten with a per-component status table. CI badge removed. Unimplemented attacks, the unsigned data sheet, and the absence of any user-data input path are all stated explicitly.
4. ✅ Every fabricated metric deleted (F7): the `auc = acc + 0.05` fake, the affine linkability/inference risks, `fairness_drift`, the hardcoded `0.75/0.80` fallback, and the `p_out = 0.05` / hardcoded p-value constants.
5. ✅ `sigma < 0.3` zero-noise branch deleted (F3), with a regression test.
6. ✅ `LICENSE` added; 6 unused dependencies removed; `requires-python` corrected to `>=3.10`.

**Additional fixes pulled forward because they corrupted the regenerated results:**

- **F8 fixed** — TSTR and TRTR are now scored on a shared held-out real split. TRTR fell from a bogus 0.971 to ~0.334 (chance level, which is correct for the toy table's independent labels).
- **New finding, discovered while fixing the above: the mechanism dispatch never matched.** `run_cell` tested `mechanism_name.lower() in ("aim", "mst")` while the sweep passed `"AIM / MST"`. The AIM branch was **never taken** — both halves of the old results table were secretly the copula generator. This fully explains the previously identical rows in F6.
- **The canary auditor is now a real instrument** — Clopper-Pearson bounds with a *measured* FPR from held-out canaries, score-based rather than exact-match detection, and a Fisher exact test. It is validated by a test showing it recovers ε > 0 with p < 0.05 on a deliberately leaky release. `audited_eps` is still 0.00 across the sweep, but that is now a genuine null result rather than a structurally impossible one.
- **F10 partially fixed** — `FrontierEngine` now actually appends to its ledger, so `ledger_hash` is a real chain head instead of the genesis hash. The data sheet remains unsigned.
- **The API `mechanism` parameter is now honoured** instead of silently ignored; CORS `allow_credentials` disabled.
- Noise samplers are now seedable and reproducible; test suite grew 25 → 36, all passing.

**Still open after Tier 0:** F2 (no ε-calibration — now *more* visible, with proved ε reaching 70.49 at target 8.0), F4 (unsound subsampling), F5 (profiler domain leak), F6 (generators are not what they are named), F9 (toy data, 1 seed), F11 (LiRA / DOMIAS / attribute inference still absent), and the unsigned certificate.

### Tier 1 — Make the privacy real (weeks 1–3)

7. **Replace the accountant's internals with `dp_accounting`** — already a declared dependency. Keep the `Accountant` class and its excellent `dry_run/snapshot/restore/charge` API; swap only the RDP math. Correct subsampling comes for free, and the novel interface survives. *This converts the worst component into a strength.*
8. **Add ε-calibration**: `calibrate_sigma(target_eps, delta, n_compositions)` by binary search, so `target_eps=2.0` yields `proved_eps ≈ 2.0`.
9. **Clip before measuring.** Clamp every column to its DP-profiled `[min, max]` before any mean / std / count. Only then is `sensitivity` defensible.
10. **Fix the profiler leak** (F5): release the category domain through a DP mechanism (stability-based histogram or thresholded noisy counts with a known-domain fallback). Never emit `.unique()`.
11. **Property-test the DP layer with `hypothesis`**: composition monotonicity; `charge` never exceeds budget; `sigma → 0 ⇒ eps → ∞`; χ² goodness-of-fit of `sample_discrete_gaussian` against the true discrete-Gaussian PMF.

### Tier 2 — Make the science real (weeks 3–6)

12. **Real datasets**: UCI Adult, ACS PUMS (via `folktables`), plus a health or credit set. n ≥ 10k with genuine correlations. Add `data/CHECKSUMS.txt` — `.gitignore` already anticipates one.
13. **Real train/test protocol**: hold out 20% of the real data. TRTR = train real → test on held-out real. TSTR = train synthetic → test on the *same* held-out real. Same classifier, same split, same seed.
14. **Real AIM** via [`private-pgm`](https://github.com/ryan112358/private-pgm) or `smartnoise-synth`. Keep the current implementation, renamed `IndependentMarginalGenerator`, as an honest ablation baseline. The comparison then becomes AIM vs independent-marginals vs copula — a real mechanism-family comparison.
15. **Real Gaussian copula**: DP covariance estimation plus a rank/Gaussianization transform, so correlation preservation becomes measurable.
16. **Real one-run audit** (Steinke, Nasr & Jagielski, 2023): m canaries, per-canary membership *scores* rather than exact match, guess top-k / bottom-k, derive ε from the confusion counts via a **Clopper-Pearson** lower bound. Sanity check: audited ε must increase with target ε and be > 0 at ε = 8.
17. **Real attacks**: LiRA with actual shadow models and a Gaussian likelihood-ratio test; **DOMIAS** (density-ratio); the `anonymeter` package for singling-out and linkability; a genuine attribute-inference attack. Report **AUC and TPR@0.1%FPR** — never accuracy at a median threshold.
18. **5 seeds × the full grid**, reported as mean ± 95% CI, with a bootstrapped frontier curve.

### Tier 3 — What makes it world-class

19. **Ship the actual proof.** Sign `PrivacyDataSheet` with a persisted Ed25519 key, publish the public key, and provide `synthproof verify datasheet.json --pubkey key.pub` as a standalone command a *third party* can run. Anchor the ledger head hash inside each certificate. This is the project's title — make it literally true.
20. **Deliver H2 and H3, or cut them.** H2 (per-subgroup canary audits showing minority records leak more at fixed ε) is the strongest untapped result here and is genuinely publishable. H3 requires wiring the `Allocator` — currently a 36-line orphan that nothing calls — into the generators, then a head-to-head at equal total spend.
21. **Prove the accountant against ground truth.** Cross-validate ε against `dp_accounting` *and* `autodp` for identical mechanisms, asserting agreement to 1e-6 in CI. An accountant with a differential test against two independent implementations is a *defensible* accountant.
22. **Empirical soundness check — the killer demo.** Run the auditor against a mechanism with a *known* ε and show `ε_audited ≤ ε_proved` holds across the grid. Then deliberately re-introduce the F3 zero-noise bug and show the auditor **catches** it. That is a validated auditor rather than an asserted one.
23. **CI** (GitHub Actions): pytest + ruff + black + mypy on 3.11/3.12, coverage gate ≥ 85%, nightly smoke sweep.
24. **Reproducibility artifact**: `make reproduce` regenerates every number in the paper from scratch — pinned seeds, logged environment, emitted manifest hash.
25. **Make the UI tell the story**: upload your own CSV → watch the budget draw down live → see the frontier curve with CI bands → watch `ε_proved` and `ε_audited` diverge → download a signed certificate → paste it into an independent verifier.

### Where each tier lands you

| State | Score |
|---|---|
| Today | **3.5** |
| + Tier 0 (honesty) | 4.5 |
| + Tier 1 (sound DP) | 6.5 |
| + Tier 2 (real science) | 8.5 |
| + Tier 3 (verified, subgroup results, reproducible) | **9.5–10** |

---

## The blunt summary

You built the right skeleton, filled it with placeholders, and then wrote the documentation as though the placeholders were real. Only that last step is unrecoverable — and it is also the easiest to undo. Correct the claims today; then there are roughly eight weeks of honest, well-scaffolded work between this repository and a genuinely excellent capstone.
