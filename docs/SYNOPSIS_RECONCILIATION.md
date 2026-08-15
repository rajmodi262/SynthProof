# Synopsis reconciliation — every promise, accounted for

> **Purpose: viva defence.** The submitted synopsis describes an ambitious system. A panel will
> read it and ask what happened to each part. This table answers that before it is asked.
>
> Nothing here is spin. A promise that was dropped is listed as dropped, with the reason.
> Source: `SynthProof-Synopsis.pdf` / `synopsis/SynthProof-Synopsis.docx`.

## How to read the verdicts

| Verdict | Meaning |
|---|---|
| ✅ **Built** | Implemented, tested, and used to produce committed results |
| ⚠️ **Partial** | Implemented in a reduced form; the difference is stated |
| 🔻 **Descoped** | Deliberately dropped with a reason. Not attempted and not claimed |
| ❌ **Not built** | Intended but not reached. No reason beyond time |

---

## 1. Core pipeline

| Synopsis promise | Verdict | What actually exists |
|---|---|---|
| Formal accountant charging from the moment the schema is read, including range inference | ✅ Built | `dp_accounting` composition; the DP domain profiler charges for category-domain discovery. Public schema bounds cost nothing *because they reveal nothing* — a stronger position than the synopsis described |
| Canary auditing on every release, one training run | ✅ Built | One-run Steinke construction, plus the earlier paired auditor retained for comparison |
| Both numbers reported side by side (ε_proved, ε_audited) | ✅ Built | Every result carries both, **plus the audit ceiling** — which the synopsis did not anticipate and which turns out to disqualify the comparison at these ε values |
| Privacy budget as a ledger, not a per-run flag | ✅ Built | Append-only SHA-256 chain, Ed25519-signed, tamper-tested |
| Signed, machine-readable Privacy Data Sheet | ✅ Built | Persistent key; `synthproof verify sheet.json --pubkey org.pub` |
| Allocator weighting columns by contribution | ❌ Not built | `Allocator` exists but drives nothing. H3 untested — see §5 |
| Frontier engine sweeping ε and drawing the curve | ✅ Built | `make h1`; figures via `make figures` |

## 2. Generators — three promised, three delivered, but not the same three

| Synopsis promise | Verdict | Reality |
|---|---|---|
| Marginal-based synthesiser descended from NIST winners | ✅ Built | **Real AIM** on private-PGM (McKenna et al. 2022) — the current marginal-based SOTA |
| Tabular diffusion (latent VAE + denoising head) under DP-SGD | 🔻 **Descoped** | See the box below |
| Fast copula baseline | ⚠️ Partial | `GaussianCopulaGenerator` exists but is **per-column Gaussian moments, not a copula** — no covariance, no rank transform. It is honestly named in code and docs as a control, not a copula |
| — | ✅ Added | `PairwiseMarginalGenerator` (tree-structured 2-way), not in the synopsis. It is what separates the mechanism families in H1 |

> **Why diffusion was dropped.** It is VRAM-bound and the available hardware is a 4 GB RTX
> 3050, where DP-SGD per-sample gradients hit OOM. More importantly it was not needed: H1 asks
> whether mechanism *families* differ, and independent / pairwise-tree / AIM are already three
> genuinely distinct families. A fourth would have cost the entire remaining budget to answer
> a question the first three already answer. **This is the single largest deviation from the
> synopsis and should be stated in the viva rather than waited for.**

## 3. Attacks — four promised, three delivered

| Synopsis promise | Verdict | Reality |
|---|---|---|
| Shadow-model membership inference | ❌ Not built | Needs 64+ shadow *generators* — days of compute for a result that is noisy on tabular data at this scale. Declared future work |
| Density-ratio membership attack (DOMIAS) | ✅ Built | k-NN density-ratio estimator. A false positive (AUC 0.576 on a release with no real records) was caught by the negative control and fixed |
| Attribute inference by linear reconstruction | ❌ Not built | Declared future work. If added, it **must** report the imputation baseline (Jayaraman & Evans 2022) or it measures predictability, not leakage |
| Singling out / linkability / inference (Anonymeter-style) | ⚠️ Partial | Exact-match singling-out only. Linkability and inference are not implemented; an earlier version fabricated them as affine functions of singling-out and they were deleted |
| — | ✅ Added | Distance-MIA baseline, honestly labelled as a weak baseline and **not** as LiRA |
| Held-back control group | ✅ Built | Every attack reports against a control; the auditor has both positive and negative controls in CI |

## 4. Platform and infrastructure — promised big, built proportionate

| Synopsis promise | Verdict | Reality |
|---|---|---|
| React + Vite + Tailwind + D3/visx console | ✅ Built | React + Vite + Tailwind + Framer Motion + react-three-fiber. 3D record cloud instead of D3 |
| FastAPI backend | ✅ Built | With SSE streaming of pipeline stages |
| Celery + Redis for long jobs | 🔻 Descoped | A single SSE stream covers the demo. Adding a broker and worker tier would be infrastructure with no experiment behind it |
| WebSocket progress streaming | ⚠️ Partial | Server-sent events rather than WebSockets — one-directional is all progress needs |
| PostgreSQL for ledger and metadata | 🔻 Descoped | SQLite. `docker-compose.yml` still provisions Postgres and nothing reads it — **remove it or wire it before the viva** |
| DuckDB + Parquet for columnar evaluation | 🔻 Descoped | pandas is sufficient at n ≤ 50k |
| MinIO / S3 for release artefacts | 🔻 Descoped | Local files plus a reproducibility manifest |
| Docker Compose deployment | ⚠️ Partial | Dockerfile and compose exist; the Postgres service is vestigial |
| Opacus for DP-SGD | 🔻 Descoped | Follows from dropping diffusion — no gradient-based mechanism remains |
| PyTorch 2.x | 🔻 Descoped | Same reason. Nothing in the delivered system needs a GPU |

## 5. Datasets and evaluation

| Synopsis promise | Verdict | Reality |
|---|---|---|
| UCI Adult | ✅ Built | SHA-256 verified, hand-declared public schema |
| ACS PUMS via folktables | ❌ Not built | **The most consequential gap.** One dataset means every H1/H2 conclusion is single-dataset. Declared as preregistration deviation D1 |
| Give Me Some Credit, Bank Marketing, MIMIC-IV, Covertype | 🔻 Descoped | Four extra datasets was never realistic alongside the auditing work |
| Non-private CTGAN as a utility ceiling | ❌ Not built | The TRTR baseline serves as the ceiling instead. A non-private generator would be a cleaner comparison |
| TSTR accuracy, marginal distances, correlation error | ✅ Built | TSTR macro-F1, correlation error, per-column histograms on shared bins |
| Fairness gaps in the utility vector | ❌ Not built | H2 measures per-subgroup *privacy*, not per-subgroup *utility*. An earlier `fairness_drift` field was a fabrication (`utility_gap / 10`) and was deleted |

## 6. Hypotheses

| | Synopsis / preregistration | Outcome |
|---|---|---|
| **H1** | Mechanism families differ | ✅ **Supported** on structure and utility, non-overlapping CIs. Privacy half **disqualified** by the audit ceiling |
| **H2** | Minority subgroups leak more | ⚠️ **Not supported.** Bounded null with a power statement: the adversary needed accuracy 0.600 and reached 0.562 |
| **H3** | Ledger-driven allocation improves utility | ❌ **Not tested** |

---

## The honest summary for the viva

**Delivered beyond the synopsis:** real AIM rather than a generic marginal mechanism; a
pairwise-tree family the synopsis never mentioned; a *validated* auditor with measured floor
**and ceiling**; a differential test of the accountant against an independent implementation;
a reproducibility manifest; and the audit-ceiling finding itself, which reframes the project's
central question.

**Delivered below the synopsis:** one dataset instead of two-plus, three attacks instead of
four, no diffusion model, no distributed infrastructure, H3 untested.

**The defensible line:** the synopsis described a *platform*; what was built is a *calibrated
instrument* plus the finding that the instrument's working range does not cover the claim it
was built to check. That is a smaller system and a larger scientific result. The infrastructure
promises (Celery, MinIO, DuckDB, Postgres) were dropped because none of them had an experiment
behind them — adding them would have consumed the budget that produced the ceiling result.

**Two things to fix before the viva, both cheap:** remove the vestigial Postgres service from
`docker-compose.yml`, and either run ACS or state the single-dataset limitation on the first
results slide rather than in the appendix.
