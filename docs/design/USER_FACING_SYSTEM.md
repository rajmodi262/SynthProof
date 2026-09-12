# From research harness to a system a stranger can use

**Status: design research. No code was written for this document and no behaviour was changed.**
Every claim about the current system was checked by reading or running the code, and every
external claim carries a link. Numbers produced by running the code are marked *(measured)*.

The question: today SynthProof synthesises a known benchmark under a hand-written schema with
hand-picked parameters. What stands between that and a stranger uploading their own sensitive
CSV and receiving synthetic data, a signed report they can hand to a regulator, and an honest
statement of what the release does and does not protect?

The short answer, stated up front because the rest of the document is easier to read with it in
mind: **a general "upload anything" system cannot be built soundly at this scope**, and the
reason is not engineering effort. It is that the act of understanding an unknown table is
itself a query against sensitive data, and there is no way to make that free. The largest
defensible subset is a **schema-first workflow for single-table, one-row-per-person data with a
declared public domain** — which is roughly what OpenDP SmartNoise and Tumult Analytics also
require, for the same reason. Section 6 states that boundary precisely.

---

## 1. What exists today, concretely

### 1.1 Parameters a stranger's dataset would not supply

Every one of these is currently hardcoded, defaulted, or inferred from the data.

| Parameter | Where | Today's behaviour | Why a stranger cannot supply it |
|---|---|---|---|
| Column kinds (numeric vs categorical) | `synthproof/data/schema.py:146` | Guessed: numeric **and** `nunique() > 20` → numerical, else categorical | The 20 is arbitrary. A 12-level ICD chapter code and a 30-level one land on opposite sides |
| Numeric bounds | `synthproof/data/schema.py:147` | `float(series.min()), float(series.max())` — the true extremes | These are the sensitive values. Releasing them leaks the extreme record exactly |
| Category domains | `synthproof/data/schema.py:154` | `sorted(map(str, series.unique()))` — verbatim | Publishing the observed value set leaks every singleton |
| Which column is the ML target | `synthproof/frontier/certificate.py:113-118` | `"income"` if present, else the **first categorical column** | An Adult-ism. On a stranger's table this silently picks an arbitrary column |
| Mechanism | `synthproof/cli.py:155-159` | Defaults to `pairwise` | Choosing between `pairwise` and `aim` needs domain-size reasoning the user has not done |
| Number of canaries | `synthproof/cli.py:162` | `30` | Determines the audit ceiling (§2.4). At 30 the ceiling is ~2.0 |
| Seed | `synthproof/cli.py:161` | `42` | Fine as a default, but it is reported in the data sheet as if chosen |
| Rows for the toy table | `synthproof/cli.py:160` | `100` | Only used when `--input` is omitted |
| δ | `synthproof/cli.py:148-153` | `1e-5` regardless of n | The convention is δ ≪ 1/n. For n = 500 this is fine; for n = 2,000,000 it is not |
| Contribution bound (rows per person) | *absent* | Assumed 1, never asked | `ch03-threat-model.md` §3.3 says a multi-row dataset "would need group privacy or a bounded-contribution preprocessing step". Neither exists |
| Profiling budget fraction | `BudgetPlan.split(..., profile_frac=0.1)` | 10% of total, fixed | The right split depends on how much domain is unknown |

Two further data-dependent operations happen in the upload path and are not charged to anything:

- `synthproof/api/main.py:417` — `df.dropna(axis=0, how="any")`. The number of complete rows is
  a function of the data, and that count is then published in the data sheet as `num_rows`.
- `synthproof/api/main.py:420-421` — tables over 20,000 rows are subsampled. Poisson
  subsampling would give amplification the accountant could credit; this is a fixed-size sample
  and is credited as nothing, so it is conservative rather than wrong — but it is also
  undeclared in the sheet.

### 1.2 What the Privacy Data Sheet contains, and what a compliance officer would need

Today (`synthproof/frontier/certificate.py:44-67`): `dataset_name`, `num_rows`, `mechanism`,
`mechanism_available`, `delta`, `seed`, `target_column`, `total_proved_eps`,
`total_audited_eps`, `frontier_curve`, `ledger_hash`, `evaluation`, `attacks_run`,
`attacks_not_implemented`, `signature`, `public_key`.

That is a good machine-readable record of *what the pipeline did*. A hospital compliance officer
or an ethics board needs answers to different questions, and the sheet is silent on all of them:

1. **Unit of privacy.** Whose privacy, at what granularity? The sheet never says
   "add/remove-one-record" or states the contribution bound. `ch03-threat-model.md` §3.3
   commits to record-level; the artefact does not carry it.
2. **What ε means here.** `total_proved_eps: 1.04` is not interpretable by the reader. §2.2.
3. **What was assumed public.** The single most important disclosure, and it is absent. If
   bounds came from `infer_nonprivate`, the release leaked them and the sheet does not say so —
   even though `/api/upload` does warn the *uploader* (`main.py:454-459`).
4. **Provenance of the input.** No dataset fingerprint. `ACSFingerprint.content_sha256`
   (`synthproof/data/acs.py`) exists for ACS only and never reaches the sheet.
5. **What the audit could have detected.** `total_audited_eps: 0.0` reads as "no leakage" unless
   the ceiling sits beside it. The repo computes the ceiling
   (`synthproof/audit/steinke.py:max_provable_epsilon`) but the sheet does not carry it.
6. **Residual risk in words.** No statement of what DP does not cover: correlated records,
   an adversary with the key, re-identification via an external join on quasi-identifiers.
7. **Who ran it and when.** No actor, no timestamp, no software version. The ledger entry has
   `actor` and `timestamp`; the sheet does not inherit them.
8. **Refusal record.** Nothing states what was rejected or degraded.

### 1.3 Trace: what happens today with an unseen schema

Four synthetic tables, each run through `FrontierEngine.run_sweep` with an inferred schema
*(measured)*:

| Input | Outcome | Line |
|---|---|---|
| All-numeric, 200×2 | `ValueError: A data sheet needs a categorical target column` | `frontier/certificate.py:120` |
| 12 rows × 2 | `ValueError: Column 'age' has no DP category domain` | `generators/pairwise.py:86` |
| Free-text column (200 distinct strings) | **SUCCEEDS**, picks `note` as the ML target | — |
| Direct identifier `MRN000000…` | **SUCCEEDS**, picks `mrn` as target, `proved_eps=0.940` | — |

The failures are survivable — they are loud and late. **The successes are the problem.**

### 1.4 The finding that governs this whole document

I ran the identifier case properly: 2,000 rows, a unique `MRN` per row, inferred schema
*(measured)*.

```
eps=1.0:  mrn domain size=13   real identifiers in the synthetic output:  6
eps=8.0:  mrn domain size=20   real identifiers in the synthetic output: 13
          e.g. MRN000012, MRN000538, MRN000765, MRN000788, MRN000935
```

**Real identifiers, each present in exactly one input record, appear verbatim in the synthetic
release.**

The cause is in `synthproof/data/profiler.py:265`:

```
threshold = self.category_threshold_factor * noise_scale * np.sqrt(2.0)   # factor = 3.0
```

This is a stability-based histogram over an unknown domain — the right family of mechanism —
but the threshold is a fixed 3 standard deviations of the noise and **carries no δ term at
all**. The literature's threshold does. Rogers'
[unifying analysis of unknown-domain algorithms](https://arxiv.org/abs/2309.09170) (2023) gives,
for the Laplace variant credited to Korolova et al. 2009 and Wilson et al. 2020:

> T = Δ∞ + (Δ∞/ε)·log(Δ₀/2δ)

δ is precisely *the probability that a newly-appearing item's noisy count exceeds the threshold*
— the event observed above. Because SynthProof's threshold omits δ, that probability is a
constant of the mechanism rather than something the release controls *(measured)*:

| ε_budget | noise scale b | SynthProof T | P(a singleton survives) | Literature T at δ=1e-5 |
|---:|---:|---:|---:|---:|
| 0.05 | 20.0 | 84.9 | 7.6e-03 | 217.4 |
| 0.5 | 2.0 | 8.5 | 1.2e-02 | 22.6 |
| 1.0 | 1.0 | 4.2 | 2.0e-02 | 11.8 |

At ε=1 a singleton survives about **1 time in 51**, against a declared δ of 1e-5 — roughly
**1,950× the failure probability the release claims**, per category. With 2,000 singleton
identifiers, ~13 survivors at ε=8 is exactly what the arithmetic predicts, and exactly what was
observed.

**Why this has not affected any committed result — and the reason is not the one you would
guess.** It is *not* that the benchmarks lack rare categories. They have them *(measured)*:
ACS `RAC1P` has `AlaskaNative` with **1** supporting row in the 6,000-row sample, and Adult has
`Without-pay` at 2 and `Armed-Forces` at 3. Under the current threshold a singleton survives
with probability ~0.8% at ε=8, so on ACS it occasionally does.

The actual reason is `synthproof/data/dataset.py:62-68`: when the schema **declares** a category
domain, every value outside it is mapped to a `__OTHER__` sentinel. So the profiler's candidate
set is a subset of the *declared, public* domain, and releasing "AlaskaNative is in the domain"
discloses nothing — the schema published that domain already. The thresholding is redundant
work on a public fact, not a leak.

That distinction is the whole boundary this document is about:

- **Declared schema** → candidate set is public → an under-calibrated threshold wastes budget
  but cannot release anything new. This is every committed experiment.
- **Inferred schema** (`infer_nonprivate`) → the candidate set *is* the data, taken from
  `series.unique()` → the threshold is the only thing between a singleton and the release. This
  is every upload, and it is where the `MRN` identifiers came from.

So the defect bites precisely when the domain is unknown — *the definition of a stranger's
upload*. It is the gating item for everything here, it is pre-existing, and it is a reason to
keep the schema-first path as the only unqualified one.

---

## 2. The hard problems

### 2.1 Schema and domain inference is a sensitive touch

**The difficulty.** To synthesise a table you must know its shape: which columns are numeric,
what range they span, which categories exist. Every one of those facts is a function of the
data. There is no "just look at it first" — looking *is* the query.

**How the field handles it: by refusing to infer, and saying so.**

[SmartNoise SQL's metadata documentation](https://docs.smartnoise.org/sql/metadata.html) requires
the analyst to declare column types and, for numeric aggregates, `lower`/`upper`. It states
plainly:

> "The data curator should take care not to use the actual min and max values from the dataset,
> when setting lower and upper, if these are sensitive, but instead should use a domain specific
> lower and upper (e.g. 0-100 for age)."

That is a direct description of what `schema.py:147` does wrong.

[Tumult Analytics](https://docs.tmlt.dev/analytics/latest/tutorials/clamping-bounds.html) is
more explicit still — clamping bounds are treated as **public information, deliberately outside
the DP guarantee**:

> "The value of clamping bounds themselves is not protected by differential privacy; Tumult
> Analytics considers these values as public information… it is crucial to not make the choice
> of clamping bounds depend too much on the private data — visualizing the data distribution and
> making a judgment call is typically acceptable, but taking the exact maximum value in the data
> isn't, as it would directly leak the value of a single data point."

Tumult also has the escape hatch SynthProof lacks: `get_bounds()`, which selects bounds from the
data **at a stated cost in privacy budget**, for use when bounds cannot be known a priori. Their
guidance is that bounds should cover roughly 95% of values. Tumult's related concept of a **data
invariant** — information you explicitly choose not to protect — is the right vocabulary for
what a schema is.

**So there are exactly three sound options, and SynthProof currently implements none of them
correctly:**

| Option | Cost | Sound? | Notes |
|---|---|---|---|
| **A. User declares a public schema** | 0 | Yes | The `--schema` path already supports this. It is the only free option and it is correct |
| **B. Public code book** | 0 | Yes | Already demonstrated: `synthproof/data/acs.py` coarsens OCCP/POBP using the published PUMS dictionary. Generalises to ICD-10, SNOMED, NAICS, ISO country codes |
| **C. Charged DP release of the domain** | Real ε and δ | Yes, if calibrated | This is what the profiler *attempts*. Numeric bounds via DP quantiles; categories via a δ-calibrated stability threshold |
| ~~D. Infer from the data for free~~ | 0 | **No** | `infer_nonprivate`. Disqualified: uncharged query on sensitive data |

**What C actually costs.** Numeric bounds are the cheap part: two DP quantiles per column
(say the 2.5th and 97.5th percentiles, following Tumult's 95% guidance) rather than min/max,
which is both sound and lower-sensitivity. Categories are the expensive part, and the cost is
δ, not ε: with the correct threshold `T = 1 + (1/ε)·log(1/2δ)`, at ε=1 and δ=1e-5 the threshold
is 11.8 rather than the current 4.2, so a category needs ~12 supporting records to survive.
**That is the honest price of discovering a domain, and it is the right price** — a category
present in fewer than a dozen people should not appear in a public release.

**Recommendation.** Option A as the default and the only path that produces an unqualified
sheet; B as assistance; C as an explicitly-priced fallback with the corrected threshold. And the
data sheet must state which was used — that is disclosure item 3 in §1.2.

### 2.2 The user cannot choose epsilon

**The difficulty.** ε is a bound on a likelihood ratio. Nobody outside DP research has intuition
for 1 versus 8, and the difference is a factor of e⁷ ≈ 1,100 in the worst-case odds an adversary
can achieve. A slider labelled "privacy ←→ utility" is not a solution; it delegates a decision
the user cannot make and then treats their arbitrary answer as consent.

**What the literature says.** The best empirical result here is Nanayakkara, Smart, Cummings,
Kaptchuk and Redmiles, *"What Are the Chances? Explaining the Epsilon Parameter in Differential
Privacy"*, [USENIX Security 2023](https://arxiv.org/abs/2303.00738). They tested three
explanation methods with 963 participants in a vignette study: two communicating **odds**, one
showing **concrete example outputs**, against a state-of-the-art baseline that omits ε entirely.

Their finding is directly actionable: **odds-based explanations beat both output-based
explanations and the ε-omitting baseline** for objective risk comprehension. Participants given ε
information were *more* willing to share than under the standard explanation, and their
willingness tracked the actual strength of the protection — which is the behaviour you want,
and evidence against the common assumption that disclosing ε merely frightens people.

Adjacent work matters too: Cummings et al. find textual descriptions alone ineffective and
incomplete ones trust-eroding, so a vague "your data is protected" banner is worse than nothing.
The [CDT's "You'll Probably Be Protected"](https://cdt.org/insights/youll-probably-be-protected-explaining-differential-privacy-guarantees/)
covers this for a policy audience, and there is now work toward a standardised
[privacy label for DP](https://arxiv.org/html/2507.15997).

The US Census experience is the cautionary half. The 2020 Disclosure Avoidance System's
privacy-loss budget moved from ε=4.5 to 12.2 to a final
[ε=19.61](https://www2.census.gov/library/publications/decennial/2020/2020-census-disclosure-avoidance-handbook.pdf)
— on the odds scale, roughly a 1,000-fold loosening between the last two. The lesson is that a
bare ε published without an odds interpretation invited the confusion it meant to prevent, and
that ε is chosen by policy, not derived.

**What a defensible interface looks like.**

1. **Never ask for ε directly.** Ask for the *release posture*: internal analysis, external
   research partner, or public release. Map each to a preset ε.
2. **Show the odds, from the presets, computed not asserted.** For each preset display the
   Nanayakkara-style statement: *"An adversary who is certain about everyone else can improve
   their guess about whether you are in this dataset from 50:50 to at most X:100."* That is
   `e^ε/(1+e^ε)` — arithmetic on ε, no data touched, free.
3. **Show a real utility consequence, computed on public data.** Not on their upload — see the
   rejection in §4. Precomputed Adult/ACS curves are honest and cost nothing.
4. **Make the preset a recorded choice.** The posture goes in the data sheet, so the reader sees
   the intent, not just the number.

The critical constraint: **the recommendation must not depend on the uploaded data.** Any
"we analysed your dataset and suggest ε=2" is a data-dependent parameter choice and must itself
be charged. That is rejected in §4.

### 2.3 Budget across sessions is unsolved here

**The difficulty.** DP composes. Two releases at ε=1 from the same table is a release at ε≈2.
A system that lets a user upload the same file twice, or the same file with one row changed, and
issues two sheets each claiming ε=1, has silently issued a release at ε=2 and printed a false
number on both.

**What exists today.** `ch03-threat-model.md` R6 states the goal as *"Cumulative organisational
spend is tamper-evident"* — evident, not enforced. That is accurate:
`synthproof/ledger/ledger.py` records entries and now detects modification, insertion,
reordering, replay and truncation, but nothing consults it before a run.
`synthproof/ledger/allocator.py:6-12` carries its own docstring admitting *"nothing in the
pipeline currently calls this."* A user who runs `synthproof run` twice gets two sheets and no
warning.

**Is `ACSFingerprint.content_sha256` the seed of it? Partly — and its limits are instructive.**
It is the right *idea*: identify the data, not the filename. But a content hash gives exact-match
identity only. It does not recognise:

- the same table with one row appended (a different hash, ~the same privacy exposure);
- a column subset of an earlier upload;
- the same people re-exported after a schema change;
- two departments uploading overlapping extracts.

Content hashing catches the honest repeat, which is the common case, and misses the adversarial
and the merely careless one. It is a necessary component and an insufficient policy.

**What a real budget-enforcing system looks like.** Four parts:

1. **Identity.** Budget attaches to a *data subject population*, not a file. In practice: an
   organisation declares a logical dataset ("2026 inpatient admissions") and every upload is
   claimed against it by the user. The declaration is a trust input — the system cannot verify
   it without reading the data — and must be recorded as such in the sheet.
2. **Fingerprint as corroboration.** `content_sha256` detects exact repeats and can challenge a
   mismatched claim. Advisory, not authoritative.
3. **A persistent wallet with a filter, not an odometer.** This is the precise literature hook.
   Rogers, Roth, Ullman and Vadhan,
   [*"Privacy Odometers and Filters: Pay-as-you-Go Composition"*](https://papers.nips.cc/paper/6170-privacy-odometers-and-filters-pay-as-you-go-composition),
   NIPS 2016, distinguish exactly these: an **odometer** reports realised privacy loss as you go
   without a pre-set budget; a **filter** is a stopping rule that halts before a declared budget
   is exceeded. SynthProof's ledger is an odometer. A user-facing system needs a **filter** —
   and the paper is the citation for why that is not merely "check a running total", since the
   parameters themselves may be chosen adaptively.
4. **Refusal semantics.** On exhaustion the system must refuse, not degrade. Silently shrinking
   ε to fit the remaining budget is worse than refusing: the user gets a release they did not ask
   for, of a quality they did not evaluate. Refuse, report the remaining budget, and name what
   would have to change.

**Honest status: this is open.** A correct implementation needs authenticated identity, a
server-side wallet the user cannot reset, and a policy for dataset identity that no amount of
cryptography supplies. It is a genuine research-and-engineering problem, not a missing feature.

### 2.4 Auditing a stranger's data — plainly

**You asked for a plain answer, so: cut live per-upload auditing. It would be theatre.**

Here is the reasoning, and I would rather lose the feature than defend the number.

The auditor plants canaries and asks how well an adversary can guess which were included. The
one-run construction is Steinke, Nasr and Jagielski,
[*"Privacy Auditing with One (1) Training Run"*](https://arxiv.org/abs/2305.08846),
NeurIPS 2023 (Outstanding Paper), which gets a bound from a single training run by randomising
inclusion over many canaries — the reason this repo can audit at all.

But the bound it can *possibly* return is capped by the number of guesses. From
`synthproof/audit/steinke.py`, with α = 0.05:

| canaries r | ceiling ε_max |
|---:|---:|
| 10 | 1.34 |
| 30 | 2.01 |
| 100 | 3.05 |
| 400 | 4.19 |

The CLI default is **30 canaries** (`cli.py:162`), giving a ceiling of ~2.0. So a user
requesting ε=8 and receiving `audited_eps = 0.0` has learned *nothing whatsoever*: the instrument
could not have returned a number above 2.0 even against a mechanism leaking everything. Printing
0.0 next to a requested 8 invites precisely the wrong inference.

Three further problems specific to *stranger* data:

- **Canaries need a domain to be drawn from.** `synthproof/audit/canary.py:95-105` draws them
  inside the declared public bounds, falling back to the raw min/max when no schema exists. On an
  unknown-domain upload, canary construction inherits the §2.1 problem entirely.
- **Canaries change the release.** This repo measured the cost, and then **retracted the size of
  it**: the originally reported loss does not replicate (`results/CANARY_DOSE_RESPONSE.md`).
  The shape survives — contamination scales with the canary FRACTION m/(n+m) and is significant only above ~3%; at m=60 on Adult (n=6,000) it is not significant (t=1.85). The fix was
  a second, canary-free fit, which means the audited artefact is *not the artefact the user
  receives*. Defensible in an experiment; hard to explain on a compliance document.
- **Cost.** A meaningful ceiling needs hundreds of canaries, and each is a row the generator must
  fit.

**Verdict.** Live per-upload auditing at a ceiling of 2.0 produces a number that looks like
evidence and is not. Two honest alternatives:

- **Ship the ceiling as a first-class field and report auditing as a property of the
  *mechanism*, not the release.** Publish a precomputed audit atlas from the committed
  experiments — "this mechanism family, audited at 400 canaries on two benchmarks, showed
  ε_audited ≤ X" — and cite it in the sheet.
- **Offer opt-in deep auditing** as an explicitly slow, explicitly expensive mode with a stated
  ceiling, off by default.

### 2.5 Failure and refusal

A system that always succeeds is lying somewhere. §1.3 shows two inputs that should have been
refused and were not. Proposed taxonomy, with the code-level reason each is required:

| # | Condition | Response | Why |
|---|---|---|---|
| R1 | Fewer than ~500 rows | **REFUSE** | At n=12 the pipeline already dies at `pairwise.py:86`, but it dies for the wrong reason. Below a few hundred rows any usable ε destroys utility; the release would be noise wearing a certificate |
| R2 | A column with near-unique values (distinct/n > 0.8) | **REFUSE**, name the column | The `mrn` case. Direct identifiers leaked verbatim (§1.4) |
| R3 | Free-text / unbounded string column | **REFUSE**, offer to drop | 200 distinct notes became a 200-category domain and were selected as the *ML target*. Tabular DP has no story for free text |
| R4 | No categorical column | **REFUSE early with a clear message** | Currently `ValueError` at `certificate.py:120` after work has been done |
| R5 | Domain product too large for the mechanism | **REFUSE or require coarsening** | The ACS lesson: OCCP×POBP alone was 115,851 cells. `aim.py` has a model-size bound; the user should be told before the run |
| R6 | ε below the domain's floor | **REFUSE with the arithmetic** | If the corrected §2.1 threshold suppresses every category, the release is empty. `InsufficientBudgetError` already does this for one column; it should be a pre-flight check |
| R7 | Budget exhausted for this dataset | **REFUSE** (§2.3) | Never silently reduce ε |
| R8 | Schema inferred rather than declared | **PROCEED, but mark the sheet** | Unqualified sheets require a declared schema |
| R9 | More than one row per person | **REFUSE unless a contribution bound is declared** | `ch03` §3.3 acknowledges the guarantee degrades; nothing enforces it |
| R10 | Column count high relative to n | **WARN** | Marginal-based mechanisms degrade; not a soundness issue |

R2 and R3 need care: **detecting them is itself a query on the data.** Counting distinct values
in a column is a sensitive computation. Two sound routes: derive the check from the *declared
schema* (a column declared categorical with 200 declared levels over 250 rows is refusable using
only public metadata), or charge a small DP distinct-count. The first is free and is another
argument for schema-first. **A refusal check implemented as a free query on the raw data would
reproduce exactly the defect it is meant to prevent.**

---

## 3. Ideas that survived

Twenty-nine were generated; §4 records the twenty that were killed.

**Ingest**
1. **Schema-first upload.** Declare the public schema before the data is read. Free, sound, and
   the only path to an unqualified sheet.
2. **Code-book library.** Ship public domains for common coding systems (ICD-10 chapters, ISO
   3166, NAICS). Generalises `acs.py`. Free.
3. **Schema proposal from column *names* only.** Suggest "a column called `age` is usually
   numeric, 0–120" from the header row, never the values. Free. User confirms.
4. **Pre-flight refusal report.** Run §2.5 against the declared schema before any data is read.
5. **Contribution-bound declaration.** Ask "how many rows can one person have?" and refuse or
   apply group privacy.

**The report artifact**
6. **Disclosure section in the sheet.** What was assumed public, and how the domain was
   obtained (declared / code book / charged). The single highest-value addition.
7. **Ceiling beside every audited ε.** Kills the `audited_eps = 0.0` misreading.
8. **Plain-language residual-risk statement.** What DP does not cover.
9. **Odds statement from ε.** `e^ε/(1+e^ε)`, per Nanayakkara et al. Free arithmetic.
10. **Input fingerprint in the sheet.** `content_sha256`, generalised from `acs.py`.
11. **Reproduction block.** The exact command that regenerates the release.

**Verification**
12. **Single-file offline verifier.** One HTML file, no network, checks the signature.
13. **Signed ledger head as a transparency anchor.** The head now exists; publishing it
    periodically gives third parties a consistency check.

**Console**
14. **Attacker's-eye panel.** Show the attack outputs as an adversary sees them.
15. **Budget wallet with visible refusal.** Show remaining budget; demonstrate a refusal.
16. **Posture selector rather than an ε slider.** §2.2.

**Integration**
17. **`synthproof verify` as a CI action.** Third parties check sheets in a pipeline.
18. **Precomputed audit atlas.** Auditing as a mechanism property. §2.4.
19. **Refusal taxonomy as a published table.** The refusal list is itself a contribution.

---

## 4. Ideas I rejected and why

The longest section, deliberately. Each idea carries the three-question verdict explicitly:
**[E]** does it already exist elsewhere, **[D]** is it defensible under DP, **[V]** substance or
decoration. An idea failing **[D]** is dead regardless of the other two, so those come first.

**Rejected because they require an uncharged query on sensitive data — the disqualifying
category**

1. **Automatic PII detection by scanning values.** Regex or entropy over cell contents to find
   emails, MRNs, names.
   [E] every commercial synthetic-data tool ships this. [D] **fails.** [V] would be substance if
   it were sound.
   This is the most tempting feature in the document and it is dead on arrival. Scanning values
   *is* a query, and its output — which columns look identifying — is a function of the data. The
   trap is that it feels like a safety feature, so it gets waved through: a check whose purpose
   is to prevent a leak, implemented as a leak. Worse, its output is exactly the high-sensitivity
   information you would least want released, since "column 7 contains something that looks like
   a national insurance number" is a strong statement about a specific population. Refusal must
   key off the *declared schema* instead (§2.5), which is free, and the cost of that decision is
   that the system cannot protect a user who declares their schema carelessly. That is the
   correct trade and it should be stated in the report rather than engineered around.
2. **"Smart" ε recommendation from the uploaded data.** "Your dataset has 47 rare combinations,
   so we suggest ε=2."
   [E] marketed by several vendors as risk-based tuning. [D] **fails.** [V] substance if sound.
   A data-dependent choice of the privacy parameter, uncharged. The recommendation is itself a
   release: an adversary who sees "we suggest ε=2 for this table" learns something about the
   table's rare combinations. This is the single most requested feature in this space and the
   least defensible, and it is why §2.2's recommendation interface is driven by *release
   posture* — a fact about the user's intent — rather than by anything measured from the data.
3. **Utility preview before committing budget.** "Here is what your synthetic data would look
   like at ε=1 — happy with that?"
   [E] standard product behaviour. [D] **fails.** [V] would be the single best UX addition.
   The preview *is* a release. If the user then chooses a different ε, they have composed two
   releases and paid for one. The only sound version shows the utility consequence on *public*
   benchmark data (surviving idea 3 in §2.2's interface), which is weaker but honest: it answers
   "what does ε=1 typically cost" rather than "what does ε=1 cost you".
4. **Try-until-it-looks-right.** Regenerate until the output pleases.
   [E] the default interaction model of every generative-data tool. [D] **fails.** [V] substance.
   This is the deepest problem in the whole design, because it is not a feature anyone would
   consciously add — it is what users *do* when regeneration is cheap. Stopping when the output
   looks good is a data-dependent stopping rule, so the realised privacy loss is not the sum of
   the declared budgets. This is precisely the setting Rogers, Roth, Ullman and Vadhan formalise:
   composition where "the privacy parameters themselves can be chosen adaptively, as a function
   of the outcome of previously run analyses" needs a filter, not a running total. The interface
   consequence is uncomfortable and unavoidable: **repeat runs must be expensive and visible**,
   not one click. A system that makes regeneration pleasant is a system whose ε is wrong.
5. **Automatic column-type detection from values.** The `nunique() > 20` heuristic at
   `schema.py:146`.
   [E] universal. [D] **fails.** [V] plumbing.
   The same defect in miniature, and currently live. Types must come from the schema.
6. **Outlier highlighting for the uploader.** "These 12 rows are unusual."
   [E] common in data-prep tools. [D] **fails in context.** [V] marginal.
   Showing a user their own outliers leaks nothing to them. But it becomes interface state, and
   the moment it influences which rows they drop before re-uploading it is uncharged
   data-dependent preprocessing — idea 25 by another route. The general lesson: a display that is
   individually harmless becomes unsound when it closes a loop back into the pipeline.
7. **Auto-selecting the ML target column by predictability.**
   [E] AutoML does this routinely. [D] **fails.** [V] convenience.
   Currently `certificate.py:113-118` picks the first categorical column, which is arbitrary but
   at least data-independent. Choosing the *most predictable* column would be strictly worse:
   data-dependent and uncharged. The user must name the target, or there is no target — and the
   present fallback should arguably become a refusal (§2.5 R4).

**Rejected because an LLM cannot touch this data safely**

8. **LLM reads the CSV and proposes a schema.**
   [E] increasingly common. [D] **fails.** [V] would be the highest-leverage feature here.
   The cell values go to a model. If hosted, that is disclosure of sensitive records to a third
   party with no DP accounting and, for hospital data, likely no lawful basis — a compliance
   failure before it is a privacy-theory failure. If run locally, the values are still read and
   the proposed schema is still a data-dependent artefact that must be charged; "the model is
   local" changes who sees the data, not whether a query occurred.
   **The one safe variant**, and the reason this is not a blanket rejection: a model shown *only
   the header row* — `age`, `diagnosis_code`, `postcode` — proposing public bounds from world
   knowledge ("age is usually 0–120"). Column names are metadata the user already treats as
   public and which appear in the data sheet regardless. That is surviving idea 3 in §3. The line
   is exact: **headers are public, values are not**, and it is the only line that makes an LLM
   defensible anywhere in this system.
9. **LLM-generated plain-English summary of the release.**
   [E] every product does this now. [D] **passes, narrowly** — it would read the data sheet,
   whose numbers were already released under DP, so it is post-processing and adds no leak.
   [V] **rejected on honesty grounds anyway.**
   Post-processing invariance means this is formally safe, which makes it the most interesting
   rejection in the section. It is rejected because generated prose drifts toward the reassuring:
   a bounded claim ("an adversary's guess improves from 50:50 to at most 73:100") becomes an
   unbounded one ("your data is anonymous"). This entire document argues that the wording of the
   guarantee is load-bearing. Wording that matters that much should be written once, by a person,
   and fixed — not regenerated per release.
10. **Chatbot answering questions about the synthetic data.**
    [E] table stakes in commercial tools. [D] depends entirely on what it queries: against the
    real table it is uncharged and dead; against synthetic output it is post-processing and
    sound. [V] in the sound version it is a chat wrapper over a CSV the user already has.
    Decoration.

**Rejected as unsound measurement, or as measurement that would mislead**

11. **A 0–100 "privacy score".**
    [E] ubiquitous. [D] sound to compute. [V] **decoration, and dangerous.**
    Compresses ε, δ, the audit ceiling and the threat model into one number with no operational
    meaning. It would become the most-read field on the sheet and the least defensible one, and
    a compliance officer would reasonably treat "87/100" as a finding. Any scalar that mixes a
    formal bound with an empirical measurement is lying about at least one of them.
12. **Similarity-based privacy metrics** — nearest-neighbour distance ratios, "no synthetic
    record is too close to a real one".
    [E] shipped by most commercial tools. [D] the metric reads real data, so it must be charged;
    but the fatal objection is not cost. [V] **actively misleading.**
    This is exactly what Stadler, Oprisanu and Troncoso attack in
    [*"Synthetic Data — Anonymisation Groundhog Day"*](https://www.usenix.org/conference/usenixsecurity22/presentation/stadler),
    USENIX Security 2022: studies relying on similarity tests between real and synthetic records
    "severely underestimate the privacy risks of synthetic data publishing", and the intuition
    that artificial records carry no link to real ones does not survive contact with their
    attacks. Adding such a metric would contradict a paper this project already cites, in a
    document whose purpose is honesty. This is the clearest case in the section of a feature that
    is popular, easy, and wrong.
13. **Live per-upload canary audit.**
    [E] nobody does this per-release, which should have been a warning. [D] sound. [V] **theatre.**
    §2.4 has the arithmetic: a ceiling of 2.01 at the default 30 canaries, so `audited_eps = 0.0`
    beside a requested ε = 8 conveys nothing while looking like evidence of safety. Cut, in
    favour of mechanism-level auditing measured once at high canary counts.
14. **"Re-identification risk: 0.3%" as a headline number.**
    [E] the standard output of legacy anonymisation tools. [D] requires an assumed auxiliary
    dataset — so it is a query against data the system does not have, dressed as a measurement.
    [V] decoration. Presented as a property of the release, it is a property of the assumptions,
    and the assumptions are where all the content is.
15. **3D record cloud rendered from *real* records.**
    [E] n/a. [D] **fails.** [V] the obvious next demo idea, which is why it is recorded here.
    The existing `web/src/components/RecordCloud.tsx` is fine: it renders synthetic output. A
    "before and after" view would put raw sensitive records into the browser's memory and onto a
    screen, outside the accountant entirely. The visual appeal of this idea is inversely related
    to its defensibility.

**Rejected as table stakes elsewhere — real, but not this project's contribution**

16. **A generator zoo — CTGAN, TVAE, tabular diffusion.**
    [E] **yes** — [SDV](https://sdv.dev/) ships these and more. [D] sound under DP-SGD, at cost.
    [V] breadth, not depth.
    A fourth generator adds a row to a table. It does not address a single problem in §2, and the
    synopsis already descoped diffusion with a stated reason. The project's marginal value is in
    what it *reports*, not how many ways it can generate.
17. **Multi-table with referential integrity.**
    [E] **yes** — SDV's `HMASynthesizer`. [D] a genuine open problem under DP: composition across
    joins, and contribution bounding when one person appears in several tables at once. [V] real
    substance, and out of scope by a wide margin.
    The honest answer is "we do single-table", stated in §6 as part of the defensible subset.
18. **Managed cloud service with accounts and billing.**
    [E] **yes** — Gretel, now part of NVIDIA, is this product. [D] orthogonal. [V] not a capstone
    contribution. Worth noting that the one genuinely hard part of such a service — authenticated
    identity — is also the missing prerequisite for budget enforcement (§2.3), so the boring
    infrastructure and the interesting research meet here.
19. **A metrics battery in the SDMetrics style.**
    [E] **yes.** [D] each metric reads real data and must be charged; a battery of fifty is a
    large uncharged bill unless designed carefully. [V] table stakes.
    The contribution is ceiling-aware reporting of a few metrics, not more metrics.

**Rejected as decoration**

20. **Animated pipeline visualisation of privacy budget "draining".**
    [E] every DP demo has one. [D] sound — it displays released parameters. [V] decoration, and
    actively harmful: it depicts budget *enforcement* the system does not have (§2.3). A
    visualisation of a guarantee you do not provide is the worst category of demo feature.
21. **Synthetic-data watermarking.**
    [E] an active research area in its own right. [D] a watermark is a function of the synthetic
    output, which is already released, so embedding one is sound. [V] decoration *here* — it
    answers "did this come from us", which the Ed25519 signature already answers, and it does not
    answer any privacy question. Rejected as solving a problem the signature solved.
22. **A "privacy budget marketplace" between departments.**
    [E] no. [D] the accounting is sound in principle. [V] elaborate governance theatre on top of
    a wallet that does not yet enforce anything (§2.3). Build the filter first; trading budget
    you cannot enforce is fiction.

**Rejected because the check itself is the leak — subtler cases worth recording**

23. **Auto-detecting the contribution bound (rows per person).**
    [E] Tumult handles this via declared privacy IDs. [D] **fails** — counting rows per identifier
    means reading the identifier column, and the resulting bound is a function of the data. The
    bound must be *declared* (§2.5 R9), which is unsatisfying and correct.
24. **Deduplicating identical uploads to "save the user budget".**
    [E] no. [D] **fails, subtly.** Returning a cached release for a byte-identical re-upload
    sounds free, and the release itself is unchanged — but *whether a cache hit occurred* is a
    one-bit function of the data, observable through timing and through the absence of a budget
    charge. It is a side channel that reveals whether a specific table was previously submitted.
    Worth recording precisely because it looks obviously safe.
25. **Showing the user which of their own rows are "most at risk".**
    [E] several commercial tools do this. [D] **fails** as a system feature. The user owns the
    data, so displaying it to them leaks nothing new — but the ranking is a data-dependent
    artefact, and the moment it influences which rows they drop before re-uploading, they have
    performed uncharged data-dependent preprocessing and the composition argument breaks.
26. **Automatic k-anonymity fallback when DP produces unusable output.**
    [E] yes, widely. [D] sound in isolation, incoherent in combination: k-anonymity provides no
    guarantee against the adversary in `ch03-threat-model.md` §3.2, and silently substituting it
    when DP "fails" means the certificate no longer describes the mechanism. [V] worse than
    refusing (§2.5 R6). Refusal is the honest failure mode.
27. **Letting the user set per-column ε.**
    [E] Tumult and OpenDP both support per-query budget splits. [D] sound — the split is declared,
    not derived. [V] rejected on scope only: it is adjacent to the untested H3, and offering a
    control whose consequences the project has not measured is worse than not offering it. This
    is the closest call in this section and would be the first to revisit.
28. **Exporting the pipeline as an OpenDP measurement for external verification.**
    [E] OpenDP is the reference implementation, so interop is real value. [D] sound. [V] genuine
    substance, rejected on feasibility: the generators are not expressed as OpenDP transformations
    and rewriting them is a project, not a feature. Recorded as a Tier 3 direction rather than a
    rejection on principle.
29. **A "compare your synthetic data to your real data" fidelity report.**
    [E] SDMetrics is exactly this. [D] the comparison reads the real data. Shown *after* the
    release is fixed, and computed only from statistics already paid for, it can be made sound —
    but computed fresh it is an uncharged query, and used to decide whether to re-run it is
    idea 4 in disguise. [V] table stakes elsewhere; the marginal-fidelity view already in the
    console covers the demo need.

---

## 5. Three tiers

### Tier 1 — demo-able in under 6 hours

**Status: T1.1–T1.4 are BUILT.** Implemented after this document was first written, in
`synthproof/data/preflight.py` and `synthproof/frontier/certificate.py`, covered by 23 tests in
`tests/test_preflight.py`. The table below records what "done" turned out to mean.

| # | Item | ε cost | Status |
|---|---|---|---|
| T1.1 | **Ceiling + disclosure fields in the data sheet** | 0 | **Built.** Sheet carries `domain_source`, `unit_of_privacy`, `contribution_bound`, `audit_ceiling`, `preflight_findings`, `residual_risk`. A test asserts every one is inside `signing_payload()` — a disclosure a holder could strip without breaking the signature is not a disclosure |
| T1.2 | **Odds statement from ε** | 0 | **Built.** `PrivacyDataSheet.plain_statement()`; the CLI prints it. At the measured ε=7.36 it reads "from 50 in 100 to at most 100 in 100", which is the honest reading of ε=8 and a more effective argument against high budgets than the number is |
| T1.3 | **Pre-flight refusal on the declared schema** | 0 | **Built.** R0–R5 and R9. The `mrn` and free-text tables from §1.3 are now refused before a cell is read. A test asserts `preflight()` accepts no data argument at all, so the constraint cannot erode |
| T1.4 | **Input fingerprint in the sheet** | 0 | **Built.** SHA-256 over the table; tested to differ across inputs and match across repeats — the prerequisite for §2.3's filter |
| T1.5 | **Posture selector in the console** | 0 | Not built. The console still shows a raw ε |

**What went wrong, and it is worth recording.** The refusal floor immediately rejected the
project's own demo: the toy table is 100 rows, below the 500-row R1 floor. The fix was *not* to
lower the floor to fit the demo — it was to have `demo` pass `skip_preflight=True` and **print
that it is doing so**, naming the rule it would otherwise trip. A demo that quietly takes a path
real releases cannot take teaches the wrong thing. The same flag is used by the research grids,
which run declared-schema benchmarks, and by tests.

The predicted risk was right: a refusal keyed on a declared schema is only as good as the
schema. Every refusal therefore names the column, the rule, and a remedy, and `enforce()` lists
*all* blocking reasons rather than the first.

### Tier 2 — a real project (weeks)

| # | Item | Why it matters | Risk | ε cost | Done |
|---|---|---|---|---|---|
| T2.1 | **δ-calibrate the unknown-domain threshold** | §1.4. Without it, upload is unsound | Higher threshold suppresses more categories; some tables become unusable at low ε — that is the correct outcome, not a regression | Reallocates δ; ε unchanged | Threshold is `1 + (1/ε)·log(1/2δ)`; the `mrn` test releases **zero** real identifiers across seeds |
| T2.2 | **Charged domain discovery as a first-class mode** | Makes upload possible without a schema | Users will pick it by default; must be priced visibly | Real ε and δ, reported separately in the sheet | Sheet shows `profiling_eps` and `synthesis_eps` split; DP quantiles replace min/max |
| T2.3 | **Budget wallet with a privacy *filter*** | §2.3. The guarantee is void without it | Dataset identity is a trust input and cannot be verified | 0 (bookkeeping) | Second run on the same declared dataset is **refused**, with remaining budget reported |
| T2.4 | **Regulator-facing report** | The actual deliverable a compliance officer receives | Easy to overstate; every sentence needs a source field | 0 | One PDF/HTML: unit of privacy, ε with odds, what was public, residual risk, refusals, verification instructions |
| T2.5 | **Offline single-file verifier** | Third-party verification without trusting us | Key distribution is the hard part | 0 | One HTML file verifies a signed sheet with no network |
| T2.6 | **Precomputed audit atlas** | Honest replacement for live auditing | Must not be read as a per-release guarantee | 0 at use | Sheet cites mechanism-level audited bounds with their ceilings and the dataset they came from |
| T2.7 | **Contribution bounding** | Closes the `ch03` §3.3 gap | Bounding changes the data; must happen before profiling | Sensitivity ×k | Declared bound enforced by truncation; sheet records it |

### Tier 3 — the ambitious version

- **A DP data-release *service* with a real privacy filter**, in the Rogers et al. sense: a
  server-side wallet, authenticated organisational identity, adaptive parameter selection under a
  filter, and refusal as a first-class outcome. This is the honest "what it becomes".
- **Transparency-log anchoring.** Publish the signed ledger head to an `append-only` public log (Certificate Transparency's
  construction, not ours) so
  a third party can detect divergence without trusting the operator — Certificate Transparency's
  model applied to privacy budgets.
- **Schema inference as a priced, published mechanism.** A proper treatment of "what does it cost
  to learn the shape of a table" — DP quantiles for bounds, δ-calibrated stability for
  categories, with an empirical study of the utility cost across many real tables. This is a
  publishable question and §1.4 shows why it matters.
- **Mechanism selection under a filter.** Choosing between `pairwise` and `aim` from the data is
  a data-dependent decision requiring the exponential mechanism. Doing it correctly, and pricing
  it, is a real contribution — and this repo has the specific evidence that mechanism choice
  matters and is confounded with the metric (`results/acs/H1_RESULTS.md` §4).
- **Subject-facing receipts.** A data subject receives a verifiable statement that a release
  including their record was made at a stated ε, checkable without trusting the holder.

---

## 6. The largest defensible subset

A general upload-anything system cannot be built soundly at this scope. Not for effort reasons —
because understanding an unknown table is a sensitive query, and the three sound answers
(declare it, use a public code book, or pay for it) all require something the "just upload a CSV"
experience is designed to avoid.

The largest defensible subset:

> **Single-table, one-row-per-person data, with a user-declared public schema, at a preset ε
> chosen by release posture, with a hard refusal list, and a signed sheet that states what was
> assumed public and what the audit could have detected.**

That is a real system, it is honest, and it is what SmartNoise and Tumult also require. It is
also within reach: Tier 1 plus T2.1 and T2.4.

Everything beyond it — inferring schemas for free, recommending ε from the data, auditing every
release, enforcing budget across sessions without authenticated identity — is either unsound or
unsolved, and this document has tried to say which is which.

---

## 7. Draft for Chapter 9 — Future work

*(~370 words. Every number traces to a committed result or a measurement recorded in this
document.)*

> The system evaluated here operates on benchmark datasets with hand-written public schemas.
> Extending it to arbitrary user-supplied data raises problems that are open rather than
> engineering gaps; two bound what can be claimed.
>
> The first is **schema and domain inference**. Determining a column's type, range, or category
> set is a query against sensitive data and cannot be performed for free. The mature libraries
> resolve this by refusing to infer: SmartNoise SQL requires the curator to supply bounds and
> warns against "the actual min and max values from the dataset" [1], and Tumult treats clamping
> bounds as public information outside the guarantee, offering a budget-charged `get_bounds()`
> only where bounds cannot be known a priori [2]. Our profiler
> attempts the charged route for categorical domains via a stability-based threshold, but that
> threshold is three noise standard deviations and carries no δ term. The correct form,
> T = Δ∞ + (Δ∞/ε)·log(Δ₀/2δ) [3], makes δ the probability that a singleton category survives.
> Without it that probability is a constant: at ε = 1 a category present in one record survives
> roughly once in fifty, against a declared δ of 10⁻⁵, and on a table with a unique identifier
> per row those identifiers appear verbatim in the release. No result reported here is affected —
> both benchmarks use declared public schemas — but it is why arbitrary upload is not yet
> supportable, and δ-calibrating that threshold is the first item of future work.
>
> The second is **budget enforcement across sessions**. Our ledger is an odometer in the sense of
> Rogers et al. [4]: it records realised loss and is tamper-evident against a malicious operator
> without the signing key, but it does not halt a run. A user who releases the same table twice
> at ε = 1 has released at ε ≈ 2 while holding two certificates each claiming ε = 1. Converting
> the odometer into a filter requires authenticated identity and a durable notion of dataset
> identity that content hashing alone does not provide.
>
> A third question is whether per-release auditing should be offered at all. The ceiling
> ε_max(r) ≈ log(r / ln(1/α)) caps what any canary-based audit can certify; at the default of 30
> canaries it is 2.01, so an audited bound of zero beside a requested ε = 8 carries no
> information. Auditing is better reported as a property of the mechanism, measured once at high
> canary counts, than per release.

**References for the paragraph**

[1] OpenDP SmartNoise SQL, *Metadata*. https://docs.smartnoise.org/sql/metadata.html
[2] Tumult Analytics, *Numerical aggregations / clamping bounds*.
    https://docs.tmlt.dev/analytics/latest/tutorials/clamping-bounds.html
[3] R. Rogers, *A Unifying Privacy Analysis Framework for Unknown Domain Algorithms in
    Differential Privacy*, 2023. https://arxiv.org/abs/2309.09170 (crediting Korolova et al.
    2009; Wilson et al. 2020)
[4] R. Rogers, A. Roth, J. Ullman, S. Vadhan, *Privacy Odometers and Filters: Pay-as-you-Go
    Composition*, NIPS 2016.
    https://papers.nips.cc/paper/6170-privacy-odometers-and-filters-pay-as-you-go-composition

---

## 8. All sources

- P. Nanayakkara, M. A. Smart, R. Cummings, G. Kaptchuk, E. Redmiles, *What Are the Chances?
  Explaining the Epsilon Parameter in Differential Privacy*, USENIX Security 2023.
  https://arxiv.org/abs/2303.00738
- T. Steinke, M. Nasr, M. Jagielski, *Privacy Auditing with One (1) Training Run*, NeurIPS 2023
  (Outstanding Paper). https://arxiv.org/abs/2305.08846
- T. Stadler, B. Oprisanu, C. Troncoso, *Synthetic Data — Anonymisation Groundhog Day*, USENIX
  Security 2022. https://www.usenix.org/conference/usenixsecurity22/presentation/stadler
- R. Rogers, A. Roth, J. Ullman, S. Vadhan, *Privacy Odometers and Filters*, NIPS 2016.
  https://papers.nips.cc/paper/6170-privacy-odometers-and-filters-pay-as-you-go-composition
- R. Rogers, *A Unifying Privacy Analysis Framework for Unknown Domain Algorithms*, 2023.
  https://arxiv.org/abs/2309.09170
- OpenDP SmartNoise SQL metadata docs. https://docs.smartnoise.org/sql/metadata.html
- Tumult Analytics clamping-bounds docs.
  https://docs.tmlt.dev/analytics/latest/tutorials/clamping-bounds.html
- Tumult Analytics paper. https://arxiv.org/pdf/2212.04133
- US Census Bureau, *Disclosure Avoidance for the 2020 Census: An Introduction*, 2021.
  https://www2.census.gov/library/publications/decennial/2020/2020-census-disclosure-avoidance-handbook.pdf
- CDT, *You'll Probably Be Protected: Explaining Differential Privacy Guarantees*.
  https://cdt.org/insights/youll-probably-be-protected-explaining-differential-privacy-guarantees/
- *"We Need a Standard": Toward an Expert-Informed Privacy Label for Differential Privacy*, 2025.
  https://arxiv.org/html/2507.15997
- SDV (Synthetic Data Vault). https://sdv.dev/

---

### Measurement convention — the ceiling is borrowed, and attributed

The audit ceiling reported beside every ε_audited is `log(r / ln(1/α))`, a one-line corollary
of Steinke, Nasr & Jagielski (NeurIPS 2023, arXiv:2305.08846) Thm 2.1 — **not a result of
ours** — and the same quantity is already named *maximum auditable epsilon* by Annamalai,
Ganev & De Cristofaro (USENIX Sec 2024, arXiv:2405.10994) §2.2.

Reporting it alongside the measurement is a transfer of **limit-of-detection (LoD) reporting**
from analytical chemistry, where **MIQE 2.0** (Bustin et al., *Clinical Chemistry*
2025;71(6):634–651) mandates LoD/LLOQ disclosure and a laboratory reports *"Not Detected,
< LOD"* rather than zero. The transfer is the claim; the convention is not our invention.

Full attribution: [`docs/MEASUREMENT_CONVENTIONS.md`](../MEASUREMENT_CONVENTIONS.md).
