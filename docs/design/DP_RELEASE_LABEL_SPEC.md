# The DP Release Label — a signed, machine-checkable specification

> Status: **draft spec, v0.1** (2026-09-17). This document specifies the artefact SynthProof
> already emits (the Privacy Data Sheet, optionally wrapped in a Croissant 1.1 record) as a
> named, versioned **release label** with a conformance definition a third party can run.
> It is a *formalisation* of shipped code, not a proposal for unbuilt work: every field and
> namespace named here exists in `synthproof/frontier/croissant.py`, `synthproof/ledger/signing.py`
> and `synthproof/audit/boundary.py` today. Where a part is not yet built, it says so.

## 1. Why this spec exists

The differential-privacy release literature has converged on documenting the *guarantee* and
stopped there. Dibia, Lu, Bhattacharjee, Near & Feng (arXiv:2507.15997, 2025) distilled an
expert-elicited **nine-category privacy label** for DP releases — ε, δ, mechanism, unit of
privacy, and so on. It overlaps the SynthProof Privacy Data Sheet almost field for field, which
is the strongest external validation this project has. But Dibia's label leaves two gaps that one
of their own experts called *"privacy theater"*:

1. **It is not signed.** Nothing binds the label to whoever produced it, and nothing detects a
   label that was edited after release.
2. **It has no standard for reporting the limits of an empirical privacy metric.** A label can
   report an audited ε of 0.000 without saying that the audit *could not have detected* anything
   larger at the canary budget used (the audit-ceiling / operating-range problem — see
   `research/18` and `synthproof audit-power`).

Twelve of the most prominent real-world DP deployments confirm the pattern from the field side:
all document ε and the mechanism, **none is signed, and none is machine-checkable**
(`research/21`). Across 286 HuggingFace synthetic-data cards, 0 declare DP at all
(`scripts/wild_audit_honest.py`).

This spec closes the two gaps by defining the SynthProof label as **the Dibia nine-category label
plus (a) an Ed25519 signature and (b) an operating-range field**, and — the part no prior label
has — defining **conformance as passing an executable checker** (`boundary-audit`, RB1–RB14).

### The asymmetry principle (governs the whole spec)

Conformance is **checkable openness, not certified privacy**. The checker reads only the artefact
— never the data, never the producer's code — so a third party can run it. That makes every claim
asymmetric:

- It **can** prove a channel is *open*: a published seed is a published seed.
- It **cannot** prove a channel is *closed*: a producer can label an exact row count `declared`,
  and a keyed HMAC and a plain SHA-256 are both 64 hex characters.

**A conformant label is therefore not a private release.** It is a release whose *openable
channels cannot be hidden from a reader who runs the checker*. Any use of this spec that states or
implies "conformant ⇒ private" is a misuse of it.

## 2. Terms

| Term | Meaning |
|---|---|
| **Label** | The machine-readable artefact: a Privacy Data Sheet (bare JSON) or a Croissant 1.1 record embedding one under `dp:privacyDataSheet`. |
| **Signature** | An Ed25519 signature over the label's canonical bytes (`synthproof/ledger/signing.py::canonical_sheet_payload`). |
| **Operating range** | The triple (proved ε, audited ε, audit ceiling) that states what the empirical audit *could* have detected, so a small audited ε is read as a measurement limit, not as reassurance. |
| **Conformance** | The label passes the checker in §6: signature verifies, operating range is present and coherent, and `boundary-audit` reports **no `leak`**. |
| **Openable channel** | A property of the artefact that can disclose something ε does not cover (seed, exact row count, unkeyed fingerprint, unlabelled evaluation, etc.). RB1–RB14 in §5. |

## 3. Namespace and format

- Croissant target: `conformsTo = "http://mlcommons.org/croissant/1.1"` (`CROISSANT_VERSION`).
- DP vocabulary IRI: `https://github.com/rajmodi262/SynthProof/vocab/dp#` (`DP_NAMESPACE`),
  emitted with `dp:` prefix. Its status is declared honestly in `dp:vocabularyStatus` — it is a
  project vocabulary, not a ratified standard, and the record says so.
- W3C PROV-O (`prov:`) carries provenance. Anything under the visible Croissant layer is **outside
  the signature** and is re-checked by `verify_croissant` against the signed sheet.

## 4. Required fields

### 4.1 The Dibia nine categories (guarantee layer)

| Dibia category | Label field | Croissant mirror |
|---|---|---|
| Privacy guarantee (ε) | `total_proved_eps` | `dp:epsilonProved` |
| Failure probability (δ) | `delta` | `dp:delta` |
| Mechanism | `mechanism` | `dp:mechanism` |
| Unit of privacy | `unit_of_privacy` | `dp:unitOfPrivacy` |
| Contribution bound | `contribution_bound` | `dp:contributionBound` |
| Deployment model | `deployment_model` | `dp:deploymentModel` |
| Domain provenance | `domain_source` | `dp:domainSource` |
| Empirical audit | `total_audited_eps` | `dp:epsilonAudited` |
| Data reference | (Croissant `distribution`) | `distribution[].contentUrl` + `sha256` |

### 4.2 The two additions SynthProof makes (the gaps Dibia leaves)

**(a) Signature** — required for a *conformant* label:
```
"signature":  "<hex>",        # Ed25519 over canonical_sheet_payload(sheet)
"public_key": "<hex>"         # the verifying key; excluded from the signed payload
```
In a Croissant record this is mirrored under `dp:signature` (`@type: dp:Ed25519Signature`,
`dp:algorithm: "Ed25519"`, `dp:publicKeyHex`, `dp:signatureHex`).

**(b) Operating range** — required, so an audited ε is never read out of context:
```
"total_proved_eps": <float>,  # the analytic budget actually charged
"total_audited_eps": <float>, # the empirical lower bound the audit reported
"audit_ceiling":    <float>,  # the largest ε that audit COULD have reported (Steinke Thm 2.1)
"audit_estimator":  <str>,    # e.g. "steinke-2023" | "gdp-koskela-2025"
"audit_budget":     <int>,    # canaries (or runs) spent
"audit_alpha":      <float>   # significance level
```
Coherence rule (checked, not assumed): `audited ε ≤ audit_ceiling`, and if
`audit_ceiling < proved ε` the audited ε is flagged **uninformative** — it means the instrument
could not have detected the proved budget, not that nothing leaked.

### 4.3 Boundary-provenance fields (feed RB1–RB14)

`seed` (must be absent), `num_rows` + `release_rows_source`, `input_fingerprint`,
`evaluation` + `evaluation_privacy`, `accountant_agreement`, `domain_source`,
`contribution_bound`, and the three added by T6a: `public_invariants`,
`discretization_source`, `privacy_amplification`. Sound values for each are defined by the
checker in §5.

## 5. Conformance checks (RB1–RB14)

Conformance is defined by the checker in `synthproof/audit/boundary.py`. Each check emits at most
one finding at severity `leak` (artefact discloses something ε does not cover — **fails
conformance**), `unverifiable` (consistent with a sound release, but only producer honesty makes
it one — **does not fail**, but is reported), or `note` (a sound basis is stated).

| Code | Field(s) | `leak` when… | Source |
|---|---|---|---|
| RB1 | `seed` | the run seed is published (replays the release; measured 15/15) | D1 |
| RB2 | `num_rows`, `release_rows_source` | count has no public basis, or a "dp_count" with no charged ε | D2 |
| RB3 | `input_fingerprint`, `fingerprint_scheme`, `fingerprint_key_id` | scheme declared `sha256`/unkeyed (self-declared membership test); else the legacy 64-hex heuristic | D3 |
| RB4 | `evaluation`, `evaluation_privacy` | real-table measurements published with no outside-ε label | D4 |
| RB5 | `accountant_agreement` | a second accountant composed to a **larger** ε (`under_report`) | cross-check |
| RB6 | `domain_source` | domain read from the sensitive table, uncharged (`inferred-nonprivate`) | Ganev P4/P5 |
| RB7 | `contribution_bound` | (`unverifiable`) >1 row per person weakens the per-record ε | contribution |
| RB8 | `public_invariants` | (`unverifiable`) invariant declared outside ε with no stated basis | Census P9 |
| RB9 | `discretization_source` | bins read from the data (`data-derived`), uncharged | Ganev P5 |
| RB10 | `privacy_amplification` | amplified (smaller) ε claimed with no stated basis | Mohapatra P7 |
| RB11 | `relational_unit` | multi-table release with no unit, or `row` over linked tables | T6d / Census P9 |
| RB12 | `fk_degree_source` | `data-derived` foreign-key degree distribution (uncharged) | T6d / Cebere P3 |
| RB13 | `join_cardinality_source` | `data-derived` exact join / per-table counts | T6d / RB2 |
| RB14 | `cross_table_fingerprint` (+`_scheme`,`_key_id`) | scheme unkeyed/`sha256` (linkage membership test) | T6d / RB3 |

RB11–RB14 are the **relational** checks (`docs/design/MULTITABLE_RELEASE_BOUNDARY.md`). They fire
only on a multi-table sheet (any of `tables`, `relational_unit`, `fk_degree_source`,
`join_cardinality_source`, `cross_table_fingerprint` set); a single-table release never triggers
them, so its conformance is effectively RB1–RB10. The checks are shipped; a **validated multi-table
generator** to run them against is not (declared future work / Paper 2).

Sound (non-flagging) values are enumerated in the checker:
`release_rows_source ∈ {declared, protocol, dp_count(+charged ε)}`;
`domain_source ∈ {declared, codebook, charged}`;
`discretization_source ∈ {uniform-public, dp-charged, declared, not-applicable}`;
`public_invariants` items each need a `basis`; `privacy_amplification` needs a `basis`;
`fingerprint_scheme = hmac-sha256` **with** a `fingerprint_key_id` is a NOTE (a keyed claim the
producer is bound to under signature — checkable accountability, not byte-level verification),
while `fingerprint_scheme ∈ {sha256, unkeyed}` is a self-declared membership test (leak).

For a Croissant record the checker additionally re-audits the **visible layer outside the
signature**: a `dp:seed` in provenance or a `dp:inputFingerprintSha256` there is a `leak` even if
the signed sheet is clean.

## 6. The conformance runner

`scripts/validate_release_label.py` is the executable definition of conformance. It composes three
existing pieces and reports a single verdict:

1. **Signature** — verifies the Ed25519 signature via `synthproof.ledger.signing` (bare sheet) or
   `synthproof.frontier.croissant.verify_croissant` (record; also re-checks mirrored fields). A
   supplied `--pubkey` is checked against; without one, an *unpinned* signature is reported as
   present-but-untrusted (distinct from missing).
2. **Operating range** — asserts the §4.2(b) fields are present and coherent
   (`audited ≤ ceiling`; informative-vs-not).
3. **Boundary** — runs `boundary.audit_release` (RB1–RB14) and requires **no `leak`**.
4. **(Croissant, optional)** — points the reader at `scripts/validate_croissant.py`, which runs
   the **official MLCommons validator** in an isolated env; a green there plus a green here is the
   full claim.

Exit codes are deliberately distinct so an un-run check never reads as a pass:

| Code | Meaning |
|---|---|
| 0 | **conformant** — signature verified (or trusted-on-pin), operating range coherent, no leak |
| 1 | **non-conformant** — a `leak`, a bad/missing signature when one was required, or an incoherent operating range |
| 2 | **not fully checked** — e.g. a signature is present but no `--pubkey` was pinned, so trust is unestablished (reported, not silently passed) |

## 7. Positioning (for the paper / viva)

> This label **implements the Dibia et al. (2507.15997) nine-category privacy label and makes it
> checkable.** It adds the two things their own experts flagged as missing — a cryptographic
> signature and an operating-range field — and, uniquely, defines conformance as passing an
> executable checker (`boundary-audit`, RB1–RB14) that reads only the artefact. It does not claim
> to certify privacy: by the asymmetry principle it proves only that openable channels cannot be
> hidden from a reader who runs the checker.

## 8. Honest limits and open items

- **Not a standard.** `dp:vocabularyStatus` says so in every record. This is a project vocabulary
  proposed *as* a Croissant extension, not a ratified one.
- **Conformance ≠ private** (the asymmetry principle, §1). Restated here because it is the single
  most misusable sentence in the document.
- **The MLCommons validator runs out of band** (`scripts/validate_croissant.py`): `mlcroissant`
  conflicts with the `numpy>=2` that AIM needs, so it lives in a throwaway env. Its exit code 2
  ("not checked") is kept distinct from 0.
- **Multi-table: checks shipped, synthesis not** (T6d): the auditor now includes relational checks
  **RB11–RB14** (relational_unit, fk_degree, join_cardinality, cross_table_fingerprint — see
  `docs/design/MULTITABLE_RELEASE_BOUNDARY.md`), so a relational label is auditable. But SynthProof
  still synthesises only single tables — there is no validated multi-table generator — so end-to-end
  multi-table synthesis remains declared future work / Paper 2 and must not be described as working.
