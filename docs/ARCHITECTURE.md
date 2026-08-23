# SynthProof — Code-Level Technical Reference

> **Compiled 22 August 2026 from a full read of every module at HEAD `0d818c5`.**
> ~8,300 lines of Python across 11 packages, ~5,500 lines of tests, ~2,400 lines of TypeScript.
>
> This is the map a reviewer, an examiner or a returning collaborator needs: what each module
> does, the design decision behind it, and the defect it was written to prevent. Almost every
> module in this codebase carries a docstring naming a specific bug — that is the project's
> most distinctive engineering property and it is invisible from the outside.
>
> **§9 lists documentation drift** — docstrings that describe a state the project has left
> behind. Fix these before the viva; an examiner who reads the source will find them.

---

## 0. Data flow

```
   public Schema  ─────────────────────────────┐
        │                                      │
        ▼                                      ▼
   preflight.enforce()  ──refuse──►  PreflightRefused
        │  (reads schema + row count ONLY — never a cell)
        ▼
   BudgetPlan.split(total_eps)  ──►  profile_eps (10%) + synthesis_eps (90%)
        │                                      │
        ▼                                      │
   DPDomainProfiler ──charge──► Accountant ◄───┤
        │  public bounds free; category domains via noisy threshold
        ▼                                      │
   DomainProfile                               │
        │                                      │
   SteinkeAuditor.plant_canaries()             │
        │  m canaries, each included w.p. 0.5  │
        ▼                                      ▼
   Generator.fit()  ──charge──►  Accountant ──►  proved_eps
        │  independent | moments | pairwise | aim
        ▼
   synthetic DataFrame
        ├──► SteinkeAuditor.audit()  ──►  audited_eps + ceiling + saturated flag
        ├──► DOMIAS / DistanceMIA / ExactMatch / AttributeInference
        ├──► UtilityEvaluator  ──►  TSTR, TRTR, correlation error
        └──► PrivacyDataSheet ──sign──► Ed25519 signature
                    │
                    ▼
              Ledger.append()  ──►  SHA-256 chain + signed head (entry_count, tip_hash)
```

Two properties this diagram encodes that are easy to miss:

1. **Utility is measured on a second, canary-free fit.** Canaries contaminate the joint
   distribution — 60 of them once destroyed 89% of the correlation being measured — so the
   audited fit and the evaluated fit are separate runs.
2. **The profiler and the generator draw from one `BudgetPlan`.** The composed ε of a complete
   release approximates the number the operator typed, rather than exceeding it by whatever the
   earlier stages happened to spend.

---

## 1. `accounting/` — 661 lines

### `accountant.py` (185)
Composition delegated entirely to Google's `dp_accounting` RDP accountant. This module owns
only the *interface*: budget enforcement, spend history, `dry_run`, `snapshot`/`restore`.

**Design decisions worth defending:**
- `noise_scale == 0` maps to `NonPrivateDpEvent`, not a Gaussian with tiny sigma. Zero noise is
  not "a very small privacy loss" — it is none, and ε must be infinity.
- An unrecognised mechanism name **raises**. A previous version silently accounted unknown
  mechanisms as Gaussian.
- `compose(event, count)` rather than `count` separate compositions — otherwise calibration
  search is prohibitively slow at high step counts.
- The RDP order grid includes integer orders, because the subsampled-RDP bounds require them.
- `PrivacySpend` distinguishes `computed_eps` (cumulative total after this charge) from
  `marginal_eps` (the increase attributable to it). Composition is sublinear, so the total is
  not the sum of the marginals — a distinction most implementations blur.

**Replaces:** a hand-rolled RDP implementation using `min(q·ρ(α), truncated_MTZ)`. Neither
branch was a citable theorem: RDP does not amplify linearly under subsampling, the MTZ series
was truncated, and the α grid was non-integer while MTZ requires integer orders. Under-reported
ε by roughly 2× at q = 0.01.

### `calibration.py` (259)
Bisects the noise scale so composing the requested mechanism the requested number of times
yields the requested ε. ε is strictly decreasing in noise scale, so the search is well-posed.

**The subtle correctness argument, and it is the best comment in the codebase:** the loop
terminates on *bracket width*, not on `|eps(mid) − target|`. Terminating on the ε gap is unsafe —
if the final probe lands just above the target it updates `lo`, leaving `hi` stale, and
returning `hi` overshoots. The invariant `eps(hi) ≤ target < eps(lo)` holds at every iteration,
so returning `hi` is both correct and conservative. **The calibration never overspends.**

Also here: `BudgetPlan.split()` (profile/synthesis, routed through `Allocator` so budget
splitting has one implementation) and `calibrate_weighted_scales()`, which gives each query its
own noise scale while the composed total still lands on target. The *shape* of the weighted
split is analytic (Gaussian RDP cost goes as `1/scale²`, so weight `w` gets `scale ∝ 1/√w`); the
*size* is bisected against the accountant. No ε in that module is computed by the module. A
uniform weight vector reproduces the scalar calibration to within tolerance, asserted in tests.

**Fixed:** `noise_scale = sqrt(num_columns) / target_eps`, under which a target of 8.0 composed
to **70.49**.

### `noise.py` (144)
CKS'20 rejection sampler for the discrete Gaussian; two-sided geometric for the discrete
Laplace. χ²-tested against the exact PMFs.

**Unusually honest scoping.** The docstring states precisely what the floating-point claim does
and does not cover: integer output avoids Mironov (2012) in its usual form (leakage through the
output representation when a continuous sample is rounded), but the acceptance test uses
`rng.random() < math.exp(log_accept)` — a floating-point Bernoulli where CKS'20 specify integer
arithmetic. A bit-level or timing adversary is out of scope, and the call site says so.

**Fixed:** a `sigma < 0.3` shortcut that returned a deterministic zero vector — no noise, while
the accountant charged a finite ε. The comment marking its absence is left in place
deliberately.

---

## 2. `data/` — 1,423 lines

### `schema.py` (157)
`Schema` is **public metadata supplied by the holder**: names, coarse types, numeric bounds.
Nothing measured from the data. `Schema.infer_nonprivate()` exists and is *deliberately loudly
named* — it reads the sensitive table and must not be used for a real release.

Declared bounds are what make sensitivity defensible: clipping to a public `[lower, upper]`
gives mean sensitivity `(upper − lower)/n` rather than unbounded sensitivity.

### `profiler.py` (426)
Discovers ranges and category domains under a calibrated budget. Noise is calibrated so the
whole pass costs the ε it was given **regardless of column count** — replacing an `eps_per_col`
design under which total cost grew with the schema and no caller could predict the release's ε.

**The hierarchy** (independently identical to arXiv:2504.08254, April 2025):
public bounds cost nothing because they reveal nothing → a column with no declared range falls
back to a noisy min/max, documented as an assumption → an inferred schema with an unsatisfiable
budget **raises** rather than falling back.

**The subtlest defect in the project.** Tightening the category-suppression threshold made
things *worse*, not better. `infer_nonprivate` fills `ColumnSpec.categories` from
`series.unique()`, so on an inferred schema the "public" domain *is* the data; the empty-domain
fallback then treated it as publishable and released every observed value — all 2,000 of them on
an identifier column. A stricter threshold made the fallback fire *more often* and so made the
damage *larger*. Fixed with `schema_declared=False`, which removes the fallback entirely.

The old threshold `3 · noise_scale · √2` had no δ term, making the survival probability of a
singleton category a *constant of the mechanism* (~1 in 51 at ε=1) rather than something the
release controls. The δ-calibrated replacement is opt-in because switching it on changes
published results.

### `preflight.py` (260) — the design idea worth claiming
Refuses inputs that cannot be released honestly, with named codes R1–R10.

**The constraint that makes it interesting:** *a check that reads the data to decide whether the
data is safe is the defect it is meant to prevent.* Counting distinct values in a column is a
query against sensitive records, and its answer — "column 7 looks like an identifier" — is
exactly what DP exists to bound. **So every check reads only the declared schema and the row
count. Nothing in the module touches a cell.**

The honest consequence is stated rather than engineered around: a careless schema gets a
careless answer, and the report says which case applied via `domain_source`.

Thresholds, all judgement calls stated as such: `MIN_ROWS = 500`, `NEAR_UNIQUE_FRACTION = 0.5`,
`FREE_TEXT_LEVELS = 200`, `MAX_PAIRWISE_CELLS = 5000`.

**Motivating incident:** a table whose first column was a unique patient identifier ran to
completion and emitted a signed data sheet, with real identifiers appearing verbatim in the
output — a value present in exactly one record can clear the profiler's threshold.

*Targeted literature search found no paper stating the schema-only-precondition principle. It
follows from Papernot & Steinke (ICLR 2022) and DPBench principle 5, but as a deployed
refusal layer it appears unoccupied. Worth a Ch.4 subsection.*

### `acs.py` (262)
ACSIncome (CA 2018) via `folktables`, citing Ding, Hardt, Miller & Schmidt, *Retiring Adult*
(NeurIPS 2021).

**Correctly identifies the real problem.** Standard advice warns about one-hot encoding
inflating ACSIncome to ~284 features; that is not the binding constraint here because the
mechanisms consume raw categoricals. The binding constraint is **raw cardinality**: OCCP has 529
codes, POBP 219. One OCCP×POBP marginal would be 115,851 cells.

**The fix costs no budget, and the argument is the same one the public schema rests on.** ACS
occupation codes map to documented SOC major groups and POBP codes to documented ranges, both
published in the PUMS data dictionary. Collapsing to them uses the code book, not the data.
529 → 25 and 219 → 7; largest resulting 2-way clique 600 cells. Anything data-dependent —
merging rare occupations by observed frequency — would leak and is deliberately not done.

---

## 3. `generators/` — 963 lines

| Module | What it is | Honest labelling |
|---|---|---|
| `independent.py` (165) | 1-way marginals under calibrated Gaussian noise | The control. Flat across a 16× budget range, as it must be |
| `moments.py` (137) | Per-column Gaussian moments | **Renamed** from `GaussianCopulaGenerator` — it has no covariance and no rank transform, so it is not a copula. A second independent-marginal control |
| `pairwise.py` (210) | Tree-structured 2-way marginals, ancestral sampling | Structure is **fixed and public**, so selecting it costs nothing. Explicitly not MST and not AIM |
| `aim.py` (298) | Real AIM on private-PGM | Two deviations stated: report-noisy-max Laplace selection instead of the exponential mechanism (equivalent accounting, expressible in our accountant); no adaptive per-round budget growth (simpler and strictly more conservative) |
| `leaky.py` (120) | Copies a known fraction `f` of rows verbatim | **Not a mechanism — a measuring standard.** Charges no budget, provides no privacy. At `f=0` marginals are perfect and no row is real: the negative control |

`aim.py` bounds the junction tree at `DEFAULT_MAX_MODEL_MB = 128`, and records refused cliques
in `skipped_cliques_` rather than dropping them silently — which is what let the ACS diagnosis
rule the bound out as a cause. `DEFAULT_SELECTION_FRAC = 0.25` is the share spent choosing which
marginals to measure; for comparison, Ganev, Xu & De Cristofaro (CCS 2024) measured PrivBayes at
roughly 50/50 and MST at 1/3 to 2/3.

**Fixed:** a dispatch bug under which two "different" generators were secretly the same one, and
an `AIM_Marginal_Generator` label under which the CLI, API and console all reported AIM for a
run of independent 1-D histograms — **with a test asserting the false label**.

---

## 4. `audit/` — 1,407 lines, the scientific core

### `steinke.py` (333)
One-run audit after Steinke, Nasr & Jagielski (2023). Each canary is included independently
with probability 0.5; the adversary ranks by similarity, guesses the top half IN and the bottom
half OUT; the count of correct guesses is converted to an ε lower bound by bisecting the
binomial tail against `p(ε) = e^ε/(1+e^ε)`.

Three functions carry the project's central result:
- `max_provable_epsilon(r, α)` — solves `p^r = α`. **The instrument's ceiling.**
- `canaries_needed_for(ε, α)` — `≈ ln(1/α)·e^ε`. Exponential.
- `epsilon_lower_bound(correct, guesses, α, δ)` — returns `0.0` when the evidence rules out
  nothing, "which is the honest answer, not a failure."

`SteinkeResult.saturated` flags a bound that hit the ceiling, and `interpretation()` emits a
sentence a reader can act on rather than a bare number.

**Deviations stated:** δ handled by a union bound rather than the paper's tighter treatment
(6e-4 against α=0.05 at r=60, conservative); the adversary is a nearest-neighbour similarity
score, not mechanism-specific, so the bound is "a lower bound on a lower bound."

> ⚠️ **The docstring's claim that the ceiling is not escapable needs qualifying to the
> binary-guess estimator class.** See `docs/LITERATURE_SURVEY.md` §0.1.

### `canary.py` (262)
The earlier paired auditor, retained for comparison. `log(TPR_lo / FPR_hi)` from two
Clopper-Pearson intervals. Its FPR baseline is **measured** from held-out canaries drawn from
the same distribution, not hardcoded — that is what makes the ε a quantity rather than an
assertion.

**Two measured defects documented here, both with numbers, and both worth a thesis paragraph:**

1. **Canaries must lie inside the declared public domain.** Placing them outside it means the
   schema clips them away (so they can never be detected), and where clipping does not apply
   they drag the profiled range out — a canary age of ~250 stretched Adult's range to [17, 300]
   and compressed every real record into a handful of bins.
2. **Canaries must be extreme in a *random direction per column*.** Pinning every canary to the
   top of every numeric column packs the set into one corner of the joint distribution and
   **fabricates correlation**: 60 canaries shifted `corr(age, hours_per_week)` from 0.093 to
   0.334. Mechanisms that model dependence faithfully reproduced the artefact and were then
   scored against the un-canaried original, making them look far worse than the independent
   baseline.

Defect 2 is a *measurement-design* finding of independent interest: **canary construction can
invert the ranking of the mechanisms being audited.** It is not, as far as targeted searching
found, stated anywhere in the auditing literature.

### `equivalence.py` (350)
Converts a bare null into a bounded one. Three components, each with its methodological
justification in the docstring:

- **Multiplicity** — Benjamini-Hochberg for FDR plus Bonferroni for FWER, with `method=` passed
  explicitly in both calls because `multipletests` defaults to Holm-Šidák.
- **Equivalence (TOST)**, after Lakens (2017) — concludes *positively* that an effect lies within
  ±δ of chance. `H2_EQUIVALENCE_BOUND_ACCURACY = 0.10`, and the bound is **derived from the
  detection-floor study, before any H2 analysis**, with the justification stored on the result
  object so the reasoning travels with the number.
- **Minimum detectable effect** — `minimum_detectable_epsilon(r, α)` walks the correct-guess
  count upward until the binomial tail first clears α. The floor of the instrument's dynamic
  range, as the ceiling is its top.

`DetectabilityReport.interpretation()` produces the sentence the whole H2 chapter turns on:
*"A null at this scale bounds the effect; it does not establish its absence."*

### `subgroup.py` (290), `detection_floor.py` (172)
Per-subgroup auditing with **equal canary allocation**, deliberately: proportional allocation
would give `Other` (0.8% of Adult) about 3 canaries and `White` (85.7%) about 343, and since the
ceiling falls with the guess count, the rare groups H2 is *about* would get the weakest
instrument. The one thing that could not be held constant across datasets is documented and
pinned by a named test: `race` has 5 levels and `RAC1P` has 9, so ACS gets 44 canaries per group
against Adult's 80, and ceilings of 2.65 against 3.27.

---

## 5. `attacks/` — 578 lines

### `attribute_inference.py` (177) — methodologically the strongest attack module
Implements the comparison that makes attribute inference meaningful, citing **Jayaraman & Evans,
"Are Attribute Inference Attacks Just Imputation?" (CCS 2022)**, who showed a naive attacker
predicting the most common value *outperformed three published state-of-the-art attacks*.

Reports three numbers, not one:
- **Attack** — trained on the synthetic release.
- **Marginal baseline** — always predict the most frequent value. The floor.
- **Conditional baseline** — a model fit on *real reference data the mechanism never saw*, using
  the same auxiliary columns. **This is the strong baseline; beating it is the only evidence of
  individual-level leakage.**

`leakage_vs_conditional` is the reported quantity. If it is zero, that is the result: no
individual-level leakage beyond what population statistics already gave away.

One-hot encoding is done on the **union** of every frame's categories, because encoding
separately gives them different column spaces and the failure surfaces as silently misaligned
columns rather than an error.

### `domias.py` (236)
Density-ratio MIA after van Breugel et al. (2023). Scores `p_synthetic(x) / p_reference(x)`.
The docstring explains why the denominator matters: scoring by `p_synthetic` alone recovers a
*typicality* attack, which is largely what a nearest-neighbour distance heuristic measures.
Reports AUC and **TPR at 1% and 0.1% FPR**, never accuracy at a median threshold — Carlini
et al.'s methodological argument, applied.

Bandwidth defaults to Scott's rule rather than being tuned, because tuning against the target
would be attacker knowledge we have no right to assume.

**Fixed:** a reference self-match producing AUC 0.576 on a release containing **no real
records** — caught by the negative control, not by reading code.

### `exact_match_risk.py` (61)
Deliberately small and deliberately named. An earlier `AnonymeterEvaluator` additionally
reported `linkability` and `inference` computed as affine functions of the singling-out score
(`linkability = singling_out * 0.8 + 0.05`). Fabricated, and deleted rather than disclaimed.

### `distance_mia.py` (104)
Labelled a weak baseline, and treated as one.

---

## 6. `ledger/` — 621 lines

### `ledger.py` (317)
Append-only SQLite store, SHA-256 hash chaining, Ed25519 signature per entry.

**The signed head is what makes it actually append-only.** Hash chaining detects modification,
insertion and reordering but **not truncation**: deleting the last *k* entries leaves a shorter,
perfectly valid chain, so an operator who overspends can delete the entries recording it.
Verified — before `ledger_head` existed, dropping the final two entries left `verify()` returning
`True`. The head commits to `(entry_count, tip_hash)` and is signed, so shortening the chain
requires forging a signature over the new length.

*This is structurally **RFC 6962 Certificate Transparency's Signed Tree Head** over
`(tree_size, root_hash)`, rediscovered independently after finding the attack. Cite RFC 6962 —
and note the honest gap: CT draws its strength from public, gossiped logs and consistency
proofs, which a single-holder SQLite chain does not have.*

### `signing.py` (216)
Persistent Ed25519 keys and data-sheet signatures.

**States exactly what a signature means**, which most systems do not: it proves that whoever
holds the private key produced this exact sheet and that no field has been altered. **It does
not prove the ε is correct, the mechanism sound, or the audit honest** — a key holder can sign a
sheet full of wrong numbers. "It converts *trust our claim* into *verify that this claim came
from us and has not been edited*, which is a smaller but checkable thing."

`resolve_key_dir()` reads `SYNTHPROOF_KEY_DIR` at **call** time, not import time — a trap that
silently ignored anything set after first import. `generate_keypair` refuses to overwrite an
existing key, because every signature ever made with it would become unverifiable.

### `allocator.py` (40)
Uniform and weighted splits. Small, and now used by `BudgetPlan` and H3.

---

## 7. `frontier/` — 1,000 lines

### `experiment.py` (503)
The canonical run loop. `MECHANISMS` registry; AIM registered only when `mbi` imports, so the
grid still runs without private-PGM. `bootstrap_ci` — 4,000 percentile resamples. Five seeds per
cell, per the preregistration.

### `checkpoint.py` (196)
Makes the 4-hour grid resumable, so a session teardown costs one cell rather than the whole run.
Written after a teardown lost 11 of 75 cells.

### `certificate.py` (301)
Now a **thin exporter** over `run_cell`. It previously carried its own copy of the pipeline,
which drifted in three ways that all corrupted published numbers: it only ever instantiated the
independent and moments generators while labelling the first "AIM_Marginal_Generator"; it had no
multi-seed aggregation or CIs; and it defaulted the utility target to `categorical_cols[0]`,
which on Adult is `workclass` — not the benchmark task, and near chance for every mechanism.

Mechanism names now come from the same registry the experiments use, **so a data sheet cannot
name an algorithm the code did not run.**

The `PrivacyDataSheet` carries disclosure fields inside the signed payload so none can be
stripped: `domain_source` (was the schema declared, or read from your data?), `unit_of_privacy`,
`contribution_bound`, `audit_ceiling`, and a plain-language odds statement. `domain_source` is
described in the source as the most important field in the sheet — a release whose bounds were
read from the sensitive table has already leaked them, and every ε below it is conditional on
metadata that was never charged.

---

## 8. `api/` (1,073) · `cli.py` (366) · `web/` (~2,400 TS)

FastAPI with SSE streaming of pipeline stages; shared-key auth on every data and ledger
endpoint. CLI: `keygen`, `run`, `verify`, `infer-schema`, `demo`, with ε and δ validated before
the pipeline starts. React + Vite + Tailwind + Framer Motion + react-three-fiber console with a
live SSE pipeline view, a 3D record cloud, and a ledger tamper demo; vitest on the SSE parser.

The README is honest about what rules this out for real releases: **authentication is a single
shared key rather than real identity, so the ledger cannot say WHO spent the budget**; no
cross-session budget enforcement; no multi-table support; single-table CSV only.

---

## 9. Documentation drift — fix before the viva

An examiner who reads the source will find these. Each is a docstring describing a state the
project has left behind.

| File | Says | Reality |
|---|---|---|
| `ledger/ledger.py` header | "the signing key is generated in memory per instance and never persisted… See F10" | Closed by `signing.py`. Persistent keys exist and `synthproof verify` works |
| `generators/pairwise.py` header | "this project currently targets 3.10, so [private-pgm] could not be installed" | Python 3.11 is the target; real AIM runs |
| `evaluate/utility.py` | H2 "is tracked as Tier 3 work" | H2 has been run on two datasets and reported |
| `ledger/allocator.py` | "nothing in the pipeline currently calls this" | Called by `BudgetPlan.split` and by H3 |
| `attacks/exact_match_risk.py` | Anonymeter wiring "tracked as Tier 2 work" | Still true, but should now be framed against the EDPB's three criteria |
| `audit/canary.py` | "Replacing this with the full construction is tracked as Tier 2" | `steinke.py` exists and is the default |
| `README.md` vs `ch03` | README says **12** adversarial ledger tests; Ch.3 says **nine** | Reconcile — an examiner will check |
| `results/clique_confound.json` | `confound_confirmed = True` | Adult-only. Ch.6 §6.9 has the weakened, ACS-corrected version |

---

## 10. What the code says about the project

Three things a reader should take from the source that no summary conveys:

1. **Almost every module names the defect it prevents, with numbers.** σ<0.3 zero-noise;
   ε=8 composing to 70.49; canaries shifting a correlation from 0.093 to 0.334; a profiler
   releasing all 2,000 values of an identifier column; DOMIAS scoring AUC 0.576 on a release
   with no real records. This is a codebase written by people who got caught and decided to
   write it down.

2. **The honest-naming discipline is enforced in the type names.** `GaussianMomentGenerator`
   rather than `GaussianCopulaGenerator`. `DistanceMIABaseline` rather than LiRA.
   `ExactMatchRisk` rather than `AnonymeterEvaluator`. `Schema.infer_nonprivate` rather than
   `Schema.infer`. `LeakyGenerator` documented as "a measuring standard, not a mechanism."

3. **Several design decisions are correct for reasons the literature only published later.**
   The public-domain-free / DP-extract / never-raw hierarchy (arXiv:2504.08254, April 2025).
   The signed head over `(count, tip)` (RFC 6962, 2013). The conditional baseline for attribute
   inference (Jayaraman & Evans, CCS 2022 — this one *is* cited). The ACS code-book coarsening
   as a public transformation. Converging on published answers from first principles is
   evidence the reasoning was sound, and it is worth saying so out loud in Chapter 8.
