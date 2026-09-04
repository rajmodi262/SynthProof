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

## 5.1 Technology choices (~250 words)

One sentence each on **why**, not what.

| Choice | The reason to give |
|---|---|
| Python **3.11** | Required by `private-pgm` (`mbi`) for real AIM. Use `.venv311/` |
| `dp_accounting` (Google) | Composition is **delegated, not implemented** — standing rule 1: never write a bound that cannot be cited |
| `autodp` | The **second** accountant. Cross-checks every release; see §5.7 |
| `private-pgm` / `mbi` | Real AIM. The `AIMGenerator` that ran independent histograms was audit finding F-series and is gone |
| `scipy.stats` | Exact binomial (Clopper-Pearson) intervals, not normal approximations |
| `cryptography` | Ed25519 |
| FastAPI + SQLite | API and file-backed ledger |

**Constraint worth reporting:** `numpy >= 2` is forced by `jax`/`mbi`. This is why
**`anonymeter` could not be integrated** (pins `numpy < 2`; installing it silently downgraded
to 1.26.4 and broke AIM outright on 2026-08-23) and why **`mlcroissant` is not a runtime
dependency** (same conflict). Both are recorded refusals, not oversights.

`[WRITE: ~250 words.]`

---

## 5.2 Package structure (~200 words)

Module boundaries match the pipeline stages in Ch.4, so the architecture diagram and the
package tree are the same picture. Make that point once and let the table carry the rest.

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

`[WRITE: ~200 words.]`

---

## 5.3 Noise sampling (~300 words)

- CKS'20 discrete Gaussian rejection sampler; discrete Laplace as a difference of geometrics.
- **Why discrete at all:** Mironov (2012) floating-point attack on inverse-CDF sampling.
- **Include the χ² goodness-of-fit test against the exact PMF.** A validated sampler is a
  different claim from an asserted one, and it is cheap evidence.
- Report the removed `σ < 0.3` shortcut that returned deterministic zeros while the accountant
  still charged ε — a one-line defect that voided the guarantee silently.

**Trap — narrow this claim.** `noise.py` previously claimed immunity to the Mironov attack
while using a float Bernoulli. The claim is now narrowed to the **output-representation form**,
which is what it actually defends. Do not widen it back.

`[WRITE: ~300 words.]`

---

## 5.4 Calibration implementation (~250 words)

Bracket-and-bisect, the convergence criterion, the CI guard across 24 configurations.
Cross-reference Ch.4 §4.4 rather than repeating the result.

**Report the diagnosed under-spend here, since it is an implementation fact:** the search lands
within 0.01% on a single stage (target 8.0 → 7.999605). The ≈ 0.92 ratio across the grid comes
from `BudgetPlan` splitting the total **linearly** across stages while RDP composition is
**sublinear**, so two stages at 0.2ε and 0.8ε compose to 0.83ε. Every added stage widens it,
which is why AIM loses most. Both numbers are pinned in `tests/test_accounting_properties.py`.

`[WRITE: ~250 words.]`

---

## 5.5 Ledger implementation (~250 words)

Canonical byte serialisation (fixed-precision floats, sorted keys — otherwise signatures are
not reproducible), chain construction, verification order.

**Update: hash chaining alone does not detect truncation.** A shortened chain is internally
consistent; deleting the last two entries left `verify()` returning `True`. Fixed with a
`ledger_head` table committing to `(entry_count, tip_hash)`, signed. **Nine attacks now
stopped where eight were before**, covered by 14 tests in `tests/test_ledger_adversarial.py`,
each run against live SQLite by an adversary with file access but no key.
`verify_with_reason()` names the failure mode.

Worth reporting as an honest consequence: the fix broke the demo's own reset
(`/api/ledger/reset` deleted entries but left a head over an empty table, so the reset looked
like an attack), fixed with `Ledger.clear()`.

`[WRITE: ~250 words.]`

---

## 5.6 The release artefact (~250 words) — NEW SECTION

Did not exist when this chapter was scaffolded.

- **Signed Privacy Data Sheet** — Ed25519 over canonical bytes; `synthproof verify` runs
  against a public key alone. Carries `domain_source`, `unit_of_privacy`,
  `contribution_bound`, `deployment_model`, `audit_ceiling`, `accountant_agreement`,
  `attacks_run` / `attacks_not_implemented`, and a plain-language odds statement — **all inside
  the signed payload**, so none can be stripped.
- **Croissant 1.1 export** (`frontier/croissant.py`) — the sheet emitted as a standards
  record with a `dp:` vocabulary extension. **Accepted by the official MLCommons validator with
  0 warnings**, checked out-of-band in an isolated venv by `scripts/validate_croissant.py`
  (exit **2** for *not checked*, distinct from 0).

**The implementation point worth 100 words on its own:** the signature covers the embedded
sheet, **not** the JSON-LD layer above it. Fields mirrored upward for human readers are outside
the signed bytes, so a record can be *correctly signed and still display a false ε*.
`verify_croissant` cross-checks all 11 mirrored fields and fails with `SIGNATURE VALID, RECORD
UNTRUSTWORTHY`. The negative control was verified by disabling the check and confirming 12
tests fail.

`[WRITE: ~250 words.]`

---

## 5.7 Testing and CI (~250 words)

| Metric | Value (2026-08-24) |
|---|---|
| Tests | **607 passed, 1 skipped** |
| Coverage | **93%**, CI gate at 90% |
| `make reproduce` | **passes**; manifest pins 11 result files |

- **Every defect the self-audit found has a named regression test**, and each was verified by
  **reintroducing the bug**, not by reading the test.
- Property tests, and the **differential test against `autodp`** — agreement within 0.05%
  across 12 configurations (this landed; drop the old "if M2.9 landed" hedge).
- Controls are tests: `tests/test_croissant.py` parametrises a negative control over every
  mirrored field so an unguarded surface fails the suite.
- The skipped test is the MLCommons conformance check, which **skips rather than passes** when
  the isolated env is absent — a silent pass would be a check that never ran.

**Trap.** Do not present the defect count as unusual. Cebere et al. (Feb 2026) found 13
violations across 12 libraries; our count is **typical of code that was actually audited**.
That is still the point worth making — see ch08 §8.2 — but it is not a distinction.

`[WRITE: ~250 words.]`

---

## Figures

- Discrete Gaussian: empirical vs exact PMF
- Coverage report

Both from `make figures`, which regenerates from `results/*.json` so neither can drift.
