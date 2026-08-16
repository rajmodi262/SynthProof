# Chapter 3 — Threat Model & Problem Formulation

**Target: 1,500 words.** Depends on nothing. **Write this second.**

This chapter is where most capstones are vague and most reviewers push hardest. Being precise
here is cheap and buys a great deal of credibility. The existing
[`docs/threat_model.md`](../threat_model.md) is 177 words and is a starting skeleton, not a
chapter.

---

## 3.1 Setting (~250 words)

Name the actors explicitly.

| Actor | Holds | Wants |
|---|---|---|
| **Data holder** | The sensitive table *D* | To release something useful without disclosing individuals |
| **Analyst** | The released synthetic table *D̃* and its data sheet | To do useful work; to know how far to trust the release |
| **Adversary** | *D̃*, the data sheet, auxiliary knowledge | To learn whether a target record was in *D*, or to reconstruct its attributes |
| **Verifier** | The data sheet and a public key | To check the release's claims without trusting the data holder |

The **verifier** is the actor most systems omit, and introducing it is part of the contribution.
State that explicitly.

---

## 3.2 Adversary model (~400 words)

### Capabilities — be exact
- **Black-box access to the release.** The adversary receives *D̃* in full and the signed data
  sheet, including ε_proved, ε_audited, the mechanism name, and all hyperparameters.
- **Full knowledge of the algorithm.** Kerckhoffs's principle: the mechanism, the code, and the
  seed policy are public. Only the private randomness and *D* are secret.
- **Auxiliary distributional knowledge.** The adversary can sample from the population
  distribution and holds an independent reference set *D_holdout*.
- **Partial record knowledge.** For attribute inference, the adversary knows all but one
  attribute of the target.

### Explicitly NOT assumed
- No access to intermediate state — noisy histograms, model parameters, or the accountant's
  internals are never released.
- No repeated queries. Each release is a one-shot artefact.
- No influence over *D* before ingestion (poisoning is out of scope; see §3.5).

### Goals
1. **Membership inference** — decide whether target *x\** ∈ *D*.
2. **Attribute inference** — recover a sensitive attribute of *x\** given the rest.
3. **Singling out** — produce a predicate matching exactly one record in *D*.
4. **Linkability** — match records across two releases to the same individual.

### Writing note
Tie each goal to the specific attack that measures it in Chapter 7. A threat model that names
threats nothing measures is decoration.

---

## 3.3 Unit of privacy (~200 words)

State plainly: **add/remove-one-record, (ε, δ)-differential privacy**, with δ < 1/n.

Then address the honest subtleties, because a reviewer will:

- **Why record-level and not user-level?** If one individual contributes multiple rows, the
  guarantee degrades by their contribution count. UCI Adult is one row per person, so
  record-level is user-level there. Say so, and say that a multi-row dataset would need group
  privacy or a bounded-contribution preprocessing step.
- **Add/remove vs replace-one.** These differ by a factor of two in sensitivity. State which
  `dp_accounting` neighbouring relation is configured (`ADD_OR_REMOVE_ONE`) and stay consistent.
- **What δ means.** Not "a small probability of failure" hand-waved — the standard
  interpretation, and why δ < 1/n matters (otherwise releasing a few records verbatim
  technically satisfies the definition).

---

## 3.4 What the system must guarantee (~350 words)

Turn the threat model into checkable requirements. This is the bridge to Chapter 4.

| # | Requirement | Enforced by |
|---|---|---|
| R1 | Every operation reading *D* charges the accountant | Accountant + `MechanismSpec`; no generator touches *D* without a charge |
| R2 | Composed ε across a release does not exceed the declared budget | `BudgetPlan` + `charge()` raising `BudgetExceededError` |
| R3 | A requested ε is the ε delivered | `calibrate_noise_scale`, CI-gated across 24 configurations |
| R4 | Schema and domain discovery are not free | DP domain profiler with a noisy-threshold category release |
| R5 | Composition bounds are citable, not derived in-house | Delegated to `dp_accounting` |
| R6 | Cumulative organisational spend is tamper-evident | Ed25519-signed SHA-256 hash chain |
| R7 | Release claims are verifiable without trusting the holder | Signed data sheet + standalone verifier (M3) |
| R8 | Empirical leakage is measured, with uncertainty quantified | Canary auditor, Clopper-Pearson, Fisher exact |

**R3 deserves its own paragraph.** Before calibration, requesting ε = 8 produced a release
composing to ε = 70.49 — the budget interface was decorative. This is a good, concrete
illustration that a DP system can satisfy the *definition* while its *interface* misleads the
operator, and it is the kind of specific, self-critical detail that reads as rigour.

---

## 3.5 Out of scope

Naming what we do not defend is a strength, so this list is deliberately generous.

- **Hardware side channels** — timing, power, EM, cache.
- **Exact-arithmetic noise sampling.** We sample the discrete Gaussian and discrete Laplace
  directly (Canonne–Kamath–Steinke 2020), which avoids Mironov's (2012) attack in its usual
  form: leakage through the *output* representation when a continuous sample is rounded. We
  do **not** implement CKS'20's exact-arithmetic Bernoulli — the acceptance step uses a
  floating-point comparison, as do the underlying geometric draws. The sampled distributions
  are correct (χ² against the exact PMF; empirical variance within 0.3% of theory at
  σ ∈ {0.5, 1, 3, 10}), but an adversary who can observe the sampler at bit level or through
  timing is out of scope. `synthproof/accounting/noise.py` states this at the call site.
- **Upstream poisoning** of *D* before ingestion.
- **Compromise of the signing key.** The ledger is tamper-*evident*, not tamper-*proof*; an
  adversary holding the private key can rewrite history and re-sign. Key custody is an
  organisational control, not a cryptographic one. This is the honest limitation of the
  design and a reviewer will find it, so it is stated rather than buried.

  Within that boundary the adversary we *do* defend against is a **malicious operator with
  full write access to the ledger database and knowledge of the source, but no key** — not
  merely a careless one. Nine attacks in that model are executed against live SQLite in
  `tests/test_ledger_adversarial.py`: field modification, modification with the stored hash
  recomputed, middle-entry deletion, reordering, replay under a fresh entry id, appending a
  forged entry with the head rewritten, tail truncation, and truncation combined with
  deleting the head row. All nine are detected.

  Truncation deserves specific mention because hash chaining alone does **not** catch it: a
  shortened chain is internally consistent, so before the signed head existed, deleting the
  final two entries left `verify()` returning `True`. An operator could therefore have
  deleted the entries recording a budget overspend. The head commits to
  `(entry_count, tip_hash)` and is signed, so shortening the chain now requires forging a
  signature over the new length.
- **Multi-party or federated settings.** Single data holder only.
- **Correctness of `dp_accounting`.** We treat it as trusted, mitigated by a differential
  test against the independent `autodp` implementation — agreement between two libraries is
  evidence; agreement of our code with itself is not.

---

## 3.6 Formal statement (~100 words)

Close with the definition, stated once, properly:

> A randomised mechanism *M* satisfies (ε, δ)-differential privacy if for all neighbouring
> datasets *D*, *D′* differing in the addition or removal of a single record, and all
> measurable *S* ⊆ Range(*M*):
>
> Pr[*M*(*D*) ∈ *S*] ≤ e^ε · Pr[*M*(*D′*) ∈ *S*] + δ

Then the sentence that motivates the whole thesis:

> This bounds the *worst case over all adversaries*. It says nothing about what any *particular*
> adversary achieves. The distance between those two quantities — ε_proved and ε_audited — is
> the object this work measures.
