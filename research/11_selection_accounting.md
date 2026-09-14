# 11 — Is AIM's selection step accounted correctly? (DEFECT CONFIRMED AND FIXED — re-runs in progress)

> **Status, 2026-09-14.** E1 and E2 below confirmed defect D1. It is fixed in `4225e76`, and
> `tests/test_model_total_is_private.py` pins it with a negative control. AIM sampling was made
> reproducible and grid checkpoints bumped to version 2 in `0da936e`. Every AIM and fixed_workload
> result is being recomputed. The published numbers are **superseded until those re-runs land**, and
> no AIM ε may be quoted from the old files. The scoping work found four further release-boundary
> defects (D2–D5, including a published seed that replays every release). They are specified and
> fixed in `docs/design/PUBLIC_RELEASE_BOUNDARY.md`, and the D5 measurement is in
> `research/release_boundary/`. E3 has not been run. Standing rules apply: no citation without a
> fetched source, `INFERENCE:` for reasoning, `CONFIDENCE:` with a reason.

## Why this was opened

The brutal re-rating (2026-09-14) scored scientific results 6.0 and novelty 4.5. The GDP audit
document (`results/GDP_AUDIT.md`, "What follows") lists auditing AIM with adaptive selection as
not yet run. Reading `synthproof/generators/aim.py` to design that audit raised two accounting
questions that must be settled first, because an audit of a mis-accounted mechanism would be
misread.

## Verified facts (each with its source)

1. **Prior work audited MST/AIM with selection switched off.** Ganev, Annamalai & Kulynych,
   *Tight Auditing of Differential Privacy in MST and AIM*, TPDP 2026, arXiv:2604.18352 (HTML v1,
   fetched 2026-09-14), §3: *"The dependency graph is fixed and no higher-order marginals are
   selected, so MST and AIM reduce to the same independent-marginal model"*; *"we disable domain
   compression"*. Appendix A adds 2- and 3-way marginals *"while keeping the dependency graph
   fixed"*. The selection mechanism is not audited there.
2. **The USENIX'24 audit did not audit AIM.** Annamalai, Ganev & De Cristofaro, arXiv:2405.10994
   (fetched 2026-09-14): audited PrivBayes (DS, Hazy), MST (NIST, SmartNoise), DPWGAN (NIST,
   Synthcity); AIM is mentioned only in passing. Selection not specifically audited.
3. **"Phantoms and Disclosures"** (Amin et al., arXiv:2606.16952v2, fetched 2026-09-14) audits
   LLM rewrites, SFT and DP-SGD — not marginal or workload-adaptive mechanisms.
4. **Report Noisy Max needs monotonicity for Lap(1/ε).** Dwork & Roth, *The Algorithmic
   Foundations of Differential Privacy* (PDF fetched 2026-09-14), p. 39, Claim 3.9, for counting
   queries; the proof uses *"Monotonicity of Counts"* and *"Lipschitz Property"*. p. 45: the
   one-sided noisy arg-max uses parameter ε/Δu for monotonic utility *"or parameter ε/2Δu for the
   case of a non-monotonic utility"*, and *"loses a factor of two when the utility is
   non-monotonic"* (Theorem 3.13).
5. **Reference AIM uses the non-monotone exponential mechanism.** private-pgm
   `mechanisms/mechanism.py` (raw GitHub, master, fetched 2026-09-14):
   `p = softmax(0.5 * epsilon / sensitivity * q)`. Reference `mechanisms/aim.py` never passes
   `known_total`.
6. **SynthProof's AIM differs in two ways** (`synthproof/generators/aim.py` at `ab0107e`):
   - selection is `argmax(scores + discrete_Laplace(b))`, with `b` calibrated as a Laplace
     mechanism of sensitivity 2 (`calibrate_noise_scale(..., name="laplace", sensitivity=2.0,
     steps=rounds)`) and each round charged as `LaplaceDpEvent(b/2)`. At target ε = 8: b = 5.9987,
     charged per-round ε = 0.3334; at target ε = 1: b = 47.8945, per-round ε = 0.0418.
   - the model is fitted with `known_total=n`, the exact row count (lines 251, 311), also in
     `synthproof/generators/fixed_workload.py:172`. private-pgm's `MirrorDescent.estimate`
     defaults to `minimum_variance_unbiased_total(loss_fn)`, i.e. a total derived from the noisy
     measurements.
7. **The threat model is add/remove-one-record** (`docs/thesis/ch03-threat-model.md` §3.x, lines
   46 and 53), so the row count is not public.

## The open question, stated precisely

`INFERENCE:` By fact 4, selection with Laplace scale `b` on a non-monotone score of true
sensitivity Δ is ε-DP for ε = 2Δ/b. The code charges 2/b. So the charge is correct iff **Δ ≤ 1**,
and under-charged by a factor Δ otherwise. The score is `L1(true_marginal − model_marginal)`:
the true marginal moves by 1 in one cell, contributing at most 1; the model marginal moves only
through `known_total=n`. **Whether Δ is 1 or 2 is therefore an empirical property of the fitted
model, not something to argue.**

A second, independent question: each round is composed as a Laplace *mechanism* in RDP. Report
Noisy Max is ε-DP by Claim 3.9, but that does not by itself give it the Laplace mechanism's Rényi
curve. `CONFIDENCE: low` on whether this matters numerically — to be computed exactly.

## Experiments that decide it

- **E1 — sensitivity probe** (`selection_sensitivity_probe.py`): hold the released noisy
  measurements fixed, add one record, refit, report max |Δ score| and mixed-sign shifts, with
  `known_total=n` and `known_total=None`.
- **E2 — exact privacy of one selection round** (`rnm_exact_privacy.py`): exact output
  distribution of `argmax(s + discrete_Laplace(b))` for worst-case neighbouring scores at
  Δ_true ∈ {1, 2}; realised pure ε and Rényi divergences versus the charged `LaplaceDpEvent`.
- **E3 — only if E1/E2 show a gap:** a GDP audit designed so selection changes the output
  (more columns than rounds, a target record that makes one pair's score jump), to see whether
  the gap is empirically detectable. Pre-registered before it is run.

## Results so far (2026-09-14)

Artefacts: `research/selection_accounting/` (scripts and their JSON output, copied verbatim).

**E1 — sensitivity probe** (`selection_sensitivity_probe.py`, 40 trials per row, add-one
neighbour, released noisy 1-way measurements held fixed):

| n | domain | noise σ | max \|Δ score\|, `known_total=n` | max \|Δ score\|, `known_total=None` | mixed-sign trials (n / None) |
|---:|---|---:|---:|---:|---|
| 10 | 2×2×2×2 | 1.0 | **1.7085** | 1.0000 | 35 / 32 of 40 |
| 50 | 2×3×2×3 | 2.0 | **1.5158** | 1.0000 | 36 / 33 of 40 |
| 200 | 3×3×3×2 | 4.0 | **1.3418** | 1.0000 | 39 / 39 of 40 |

**E2 — exact privacy of one selection round** (`rnm_exact_privacy.py`, exact output
distribution, worst case over a 49-point gap grid, k ∈ {2, 3, 6}):

| target ε | b | charged ε/round | realised, Δ_true = 1 | realised, Δ_true = 2 | RDP above charge? |
|---:|---:|---:|---:|---:|---|
| 1 | 47.8945 | 0.0418 | 0.0366 – 0.0418 (ratio ≤ 1.000) | 0.0731 – 0.0835 (ratio up to **2.000**) | no at Δ=1; **yes** at Δ=2 |
| 8 | 5.9987 | 0.3334 | 0.2922 – 0.3334 (ratio ≤ 1.000) | 0.5861 – 0.6668 (ratio up to **2.000**) | no at Δ=1; **yes** at Δ=2 |

`INFERENCE:` (a) The score is non-monotone in practice (mixed-sign shifts in most trials), so
Claim 3.9's monotone case does not apply and the non-monotone factor does. (b) With
`known_total=None` the score sensitivity is exactly 1, and E2 shows the existing Laplace
calibration is then exact — realised ε equals the charge and the Rényi curve does not exceed the
`LaplaceDpEvent` it is composed as. (c) With `known_total=n` — the code as shipped — one record
moved a score by up to **1.71** in these trials, which is a *lower* bound on the true worst case,
so the selection step is under-charged by **at least 1.71×**. (d) Separately, `known_total=n` is
also used in the final model fit (`aim.py:311`, `fixed_workload.py:172`), a data-dependent path
that no charge covers.

`CONFIDENCE: med-high` — (b) and the factor in (c) rest on an exact computation plus a primary
source; the size of the defect rests on a probe that can only under-estimate the worst case.

## Scope (2026-09-14)

**D1 — exact row count in the model fit (a bug).** `known_total=n` appears in exactly two
generators: `synthproof/generators/aim.py` (n set at line 202; used at 251 in the selection
rounds and 311 in the final fit) and `synthproof/generators/fixed_workload.py` (103; 172).
Nothing else in either file uses `n`. `independent`, `pairwise` and `moments` do not pass a total.
Reference private-pgm AIM never passes `known_total`.

`INFERENCE:` magnitude, using AIM's own split (0.75 measurement / 0.25 selection, 6 rounds) and the
real column counts (Adult 12, ACSIncome 11, Bank Marketing 13; the result is the same for all
three to 3 d.p.): a release requested at ε = 8 is charged 7.099; with selection sensitivity 1.71 it
costs 8.426, and at 2 it costs 8.996. At ε = 1: charged 0.850, true 0.992 / 1.057. **Both exceed the
requested budget**, which contradicts the calibration's never-overspend property for AIM. These
figures exclude the profiler's 10% share, so they are not the published `proved_eps` values
(6.543 at ε = 8); those must be recomputed on the real pipeline before any number is quoted, and
they still exclude the uncharged use of n in the final fit.

**D2 — exact n published outside the guarantee (a threat-model inconsistency, all mechanisms).**
The accountant composes under add/remove-one (ch03), but exact n reaches the output three ways:
the signed Privacy Data Sheet field `num_rows` (`synthproof/frontier/certificate.py:410`), the
synthetic table size (`synthproof/frontier/experiment.py:270`, `num_samples=len(fit_df)`), and the
refusal gate (`synthproof/data/preflight.py`, `MIN_ROWS = 500` and the near-unique check both read
`num_rows`). `docs/thesis/ch04-system-design.md` calls the row count "public metadata", which is
consistent only with replace-one accounting.

`INFERENCE:` in the H1 experiments this does not leak canary membership — the audit release is
sized to the canary-free fit table and n is a protocol constant — so the experimental numbers are
not invalidated by D2. For a real upload through the CLI or API, n is the user's data.
The resolution is a threat-model decision, put to the user on 2026-09-14.

## What would count as each outcome

| Outcome | Meaning | Action |
|---|---|---|
| Δ ≤ 1 and exact ε ≤ charged | Accounting correct despite the unusual construction | Record it; the `known_total=n` deviation still needs a decision |
| Δ = 2 or exact ε > charged | Published AIM ε values are understated | Fix, re-run affected results, retract/correct the numbers, report it as a self-found defect |
| E3 detects the gap | An empirical demonstration that selection leakage is auditable | Candidate scientific contribution, subject to a prior-art kill pass |
