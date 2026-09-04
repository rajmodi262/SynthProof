# 08 — Novelty Verdict

> **Status: ISSUED 2026-08-23.** Phase 2 completed all 8 query families
> (`PHASE2_INTERIM.md`, `PHASE2_COMPLETE.md`). The four prerequisites named in
> `PHASE2_COMPLETE.md` §10 were executed first; §1 below records what each returned.
>
> **Ground rules observed.** Every source was fetched or returned with venue and identifier.
> `INFERENCE:` marks reasoning; `CONFIDENCE:` marks uncertainty with a reason. Adversarial by
> default: each surviving candidate below was attacked before it was kept.

---

## 1. The four prerequisites, and what they returned

| # | Task | Result |
|---|---|---|
| 1 | Fetch the blockchain DP cost-management work; settle whether any budget ledger is signed for external verification | **Han, Zhao & Zhao, ACM AsiaCCS 2020** ([2006.04693](https://arxiv.org/abs/2006.04693)). Keeps a blockchain ledger of noisy responses; its *purpose* is reusing old responses to reduce accumulated cost. **No cryptographic signing or external-verifier mechanism described.** `CONFIDENCE: med` — abstract-level read |
| 2 | Read the SDC output-checking literature properly; confirm nobody does a data-blind pre-check | The Handbook returned **HTTP 403**. The [SDC Practice Guide](https://sdcpractice.readthedocs.io/en/latest/SDC_intro.html) was fetched: **no metadata-only pre-analysis stage is described.** SDC is characterised as iterative and post-hoc — "after applying methods, disclosure risk and data utility are re-measured". The only forward-looking element is release-framework policy, a governance decision, not a technical check. `CONFIDENCE: med` — one guide, one fetch; the primary Handbook was unreachable |
| 3 | Search DP tooling issue trackers for the F1 failure mode | **Not found.** No issue matching "target epsilon does not compose to the requested epsilon" surfaced across OpenDP, SmartNoise or diffprivlib. `CONFIDENCE: low` — issue-tracker search via a web index is weak; this is not evidence of absence |
| 4 | Read the Croissant 1.1 extension mechanism and cost the integration | Fetched. Extensible by **referencing external vocabularies** at dataset, field and data level; **W3C PROV-O** for provenance chain-of-custody; **DUO + W3C ODRL** for machine-enforceable usage policies. **Signing, checksums and cryptographic attestation are not mentioned.** `CONFIDENCE: med-high` |

Two sources surfaced during this pass that changed the verdict more than any of the four tasks.
They are §2.

---

## 2. The two findings that decide this document

### 2.1 The Privacy Data Sheet's field set has been independently proposed — and expert-validated

**Dibia, Lu, Bhattacharjee, Near & Feng — *"We Need a Standard": Toward an Expert-Informed
Privacy Label for Differential Privacy*, [arXiv 2507.15997](https://arxiv.org/html/2507.15997),
July 2025.**

Their expert-informed label has nine categories. Set against ours:

| Their category | SynthProof field |
|---|---|
| Privacy parameters (ε, δ, other loss measures) | `total_proved_eps`, `delta` |
| **Unit of privacy** — "overlooked in documentations" | `unit_of_privacy`, `contribution_bound` |
| Utility information | `evaluation` (TSTR / TRTR) |
| Mechanism used | `mechanism`, from the registry that actually ran |
| Algorithm hyperparameters | partial |
| Deployment model | ✗ not carried |
| **Empirical privacy metrics** | `total_audited_eps`, `attacks_run` |
| **Privacy interpretation / semantics** | `plain_statement()`, `membership_odds()` |
| Other contextual parameters | `domain_source`, `input_fingerprint`, `preflight_findings` |

`INFERENCE:` this is a **kill on the concept** — "ship a structured privacy label with a DP
release" is independently proposed, expert-elicited, and published. It is simultaneously the
strongest external validation the project has: a panel of DP experts converged on almost exactly
the field set we built, including the two fields we most expected to have to justify
(`unit_of_privacy` and `domain_source`-style provenance). `CONFIDENCE: high` — full-text read.

**But the paper explicitly leaves two things open, and we do both.**

1. **"The paper contains no discussion of cryptographic signatures, third-party verification,
   or audit mechanisms for label authenticity."** Their prototype is HTML. Ours is signed
   Ed25519 and `synthproof verify` runs against a public key.

2. **This, verbatim from the fetched analysis, is the important one:**

   > "The paper does not address how empirical measurement uncertainty should be documented.
   > One expert noted concerns about empirical metrics potentially causing **'privacy theater'**
   > by emphasizing average-case performance without highlighting worst-case scenarios, but
   > **no standardized reporting of measurement limits is proposed.**"

   `INFERENCE:` an expert in a 2025 elicitation study named the precise hazard that
   `audit_ceiling` exists to prevent — an empirical privacy number read as reassurance when the
   instrument could not have produced any other answer — and the resulting standard proposal
   contains **no mechanism for it.** We ship one, inside the signed payload, and we found it the
   hard way: our own H1 reported ε_audited = 0.000 against a ceiling of 2.97.
   `CONFIDENCE: high` on the quote; `med` that no other proposal fills the gap, since this is a
   negative over a literature searched in one pass.

### 2.2 Practitioners do not verify DP guarantees — published, from the OpenDP team

**Song, Sarathy, Shoemate & Vadhan — *"I inherently just trust that it works": Investigating
Mental Models of Open-Source Libraries for Differential Privacy*, **CSCW 2024**,
[arXiv 2410.09721](https://arxiv.org/abs/2410.09721).** 5 library developers, 17 data analysts.

Finding: practitioners **do not verify** DP guarantees; they rely on implicit trust, assuming
libraries handle privacy correctly by default.

`INFERENCE:` this is the missing premise under the whole project, and it is now citable from a
CSCW paper by the OpenDP group. It is also the specific justification for **differential
accounting**: if nobody verifies, and a February 2026 grey-box audit found 13 violations across
12 libraries ([2602.17454](https://arxiv.org/html/2602.17454)), then a release resting on one
library rests on one library's unexamined bugs. `CONFIDENCE: high`.

---

## 3. Verdict

### 3.1 Dead — stop claiming these

| Claim | Killed by |
|---|---|
| Dual-sided assurance (proved + audited per release) | Annamalai, Ganev & De Cristofaro, USENIX Sec 2024 |
| Budget-charged domain profiling | Ganev, Annamalai, Mahiou & De Cristofaro, Apr 2025 |
| The audit ceiling as a result | Corollary of Steinke et al. Thm 2.1 / Eq. (3); verified bit-identical against our own code |
| Finding defects by self-audit | Cebere et al., Feb 2026 — 12 libraries, 13 violations, package released |
| **Shipping a structured privacy label with a DP release** | **Dibia et al., 2025 — expert-informed, nine categories** |
| **An automated release gate that refuses and records** | **Five Safes + SACRO — production practice in UK TREs since 2022** |
| **A machine-checkable release artefact** | **Croissant (a NeurIPS submission requirement), MRM3, Laminator** |
| Cross-release budget management | PrivateKube (OSDI'21), Cohere, DPack (EuroSys'25), DPolicy |

**Eight dead. That is the honest count.**

### 3.2 Surviving — narrow, defensible, and each attacked before being kept

**S1. Reporting the empirical measurement's own operating range inside the release artefact.**
`CONFIDENCE: med-high.`
*Attack:* SynthGuard-ReleaseBench ships evidence with a release. *Survives:* it bounds **utility**,
not the sensitivity of the privacy measurement. *Attack:* Dibia et al. propose empirical privacy
metrics. *Survives:* they explicitly propose **no** standard for measurement limits, and one of
their own experts named the "privacy theater" hazard it would address. *Attack:* the ceiling is
Steinke's corollary. *Survives:* the corollary is theirs; **putting it on the artefact beside the
number it qualifies is not in any proposal found.** *Residual risk:* the SDC field may report
disclosure-risk uncertainty in a form we did not reach — the Handbook 403'd.

**S2. Cryptographic signing of the privacy claim.** `CONFIDENCE: med.`
*Attack:* Laminator attests properties via TEE. *Survives:* it attests ML pipeline properties and
**does not address DP budgets**; and it needs trusted hardware where we need a public key.
*Attack:* SACRO emits SHA-256 checksums. *Survives:* a checksum binds a file to itself; it does
not bind a **claim** to an issuer. *Attack:* blockchain DP-cost ledgers. *Survives:* consensus
tamper-evidence, not an offline-verifiable signed claim — and no signing was described.
*Residual risk:* signing is a solved primitive; the novelty is only in the **application**, which
is a weak kind of novelty and should be claimed as engineering, not science.

**S3. A data-blind refusal gate.** `CONFIDENCE: med.`
*Attack:* SACRO. *Survives:* SACRO **reads output values** — cell frequencies, p%-rule, NK-rule,
regression dof — and **does not autonomously refuse** (its documentation states a "pass" is not a
certification, and human checkers hold final authority). Ours reads **schema and row count only**
and refuses. *Attack:* Five Safes has pre-access stages. *Survives:* "Safe Projects" / "Safe
People" are governance review, not an automated technical check on metadata. *Residual risk:* the
strongest of the three. The SDC literature is large, old, and poorly indexed by arXiv search; the
primary Handbook was unreachable. **Treat S3 as unrefuted, not as established.**

### 3.3 The recommended position

**Integration, not invention.** The evidence supports one coherent statement, and every clause
of it is now backed by a fetched source:

> The field has converged on what a DP release should disclose — Dibia et al. (2025) elicited a
> nine-category privacy label from experts, and Croissant has become the metadata standard ML
> datasets ship with. It has not converged on making those disclosures **checkable**: Dibia et
> al. propose no signing and no way to report the limits of an empirical privacy metric, an
> omission one of their own experts flagged as "privacy theater"; Croissant carries provenance
> but no attestation; SACRO gates releases but reads the data to do it and leaves the decision
> to a human. SynthProof is the case study of a release artefact that is **signed**, that
> **reports what its own privacy measurement could not have seen**, and whose gate **refuses
> without reading a cell** — built by hitting each of those problems in practice, including
> reporting ε_audited = 0.000 against a ceiling of 2.97 and having to work out why.

`INFERENCE:` this is defensible in a viva against a domain expert, because every kill is
volunteered and every surviving claim is narrow enough to check. It is **not** a claim to have
out-invented the Ganev / Annamalai / De Cristofaro cluster, and it should never be presented as
one.

---

## 4. What this changes in the repository

| Action | Where | Priority |
|---|---|---|
| Cite Dibia et al. (2507.15997) as the label proposal we align with, and state the two gaps we fill | ch02, ch04, defence pack | **highest** — it is the best positioning available |
| Cite Song et al. (CSCW 2024) as the premise: practitioners do not verify | ch01 motivation, differential-accounting rationale | high |
| Add the **deployment model** field to the sheet — the one Dibia category we lack | `frontier/certificate.py` | medium, cheap |
| ~~Emit the sheet as a **Croissant record** with a DP vocabulary extension~~ | `synthproof/frontier/croissant.py` | ✅ **BUILT 2026-08-23** — see below |
| State S3 as *unrefuted*, never *novel*, until the SDC Handbook is read | everywhere the gate is described | **highest** — this is the claim most likely to be wrong |

---

### 4.1 The integration MVP, as built (2026-08-23)

`synthproof/frontier/croissant.py` · `scripts/validate_croissant.py` · 43 tests in
`tests/test_croissant.py`. `synthproof run --croissant` emits it; `synthproof verify` checks
it; **the official MLCommons validator accepts it with 0 warnings.**

This is S1 + S2 made runnable rather than asserted, and it is the only claim in this document
that a reader can now execute:

| Gap named in §2.1 / §3.3 | What the record does |
|---|---|
| Croissant carries provenance, **no attestation** | Ed25519 signature travels inside the record; `verify` runs against a public key alone |
| Dibia et al. propose **no signing** | ditto — and the record states what the signature does *not* prove |
| Dibia et al. propose **no way to report an empirical metric's limits** ("privacy theater") | `dp:auditCeiling` + `dp:auditInterpretation`, which says in words when the audited ε could not have been anything else |

**Three findings from building it**, each of which is a better viva answer than the feature:

1. **A signature over an embedded node does not protect the record.** Fields mirrored into the
   human-visible layer — the ones a reader and every general-purpose Croissant consumer
   actually read — are outside the signed bytes. A record can therefore be *correctly signed
   and still show a false epsilon*. `verify_croissant` cross-checks all 11 mirrored fields and
   fails with `SIGNATURE VALID, RECORD UNTRUSTWORTHY`. Pinned by a parametrised negative
   control over every field, verified by disabling the check and watching 12 tests fail.
2. **Croissant requires a checksum on every FileObject**, so a release record that names its
   data file cannot omit one. The emitter refuses rather than emitting an invalid record — a
   file with no checksum can be swapped while the signed claim still verifies.
3. **The reference validator recurses infinitely on an empty JSON object inside the sheet.**
   `evaluation: {}` — an ordinary sheet — hit Python's recursion limit in
   `mlcroissant._src.core.json_ld.recursively_populate_jsonld`. Fixed correctly rather than by
   dropping empty containers: the sheet is declared a JSON literal (`@type: @json`), which is
   what it is, since the signature covers an ordered canonical serialisation and RDF triples
   are unordered. Our first validated record happened to have a populated `evaluation`, which
   is exactly how this class of defect survives.

**Dependency note, and it is the reason the design has no runtime dependency:** `mlcroissant`
pins a numpy that conflicts with `jax`/`mbi`/private-PGM and therefore **real AIM** — the same
conflict that ruled out `anonymeter`. A Croissant record is a dict, so the emitter builds one
directly and the reference validator runs out-of-band in an isolated venv, reporting **exit
code 2 for "not checked"** distinctly from 0, so an unrun check cannot look like a passed one.

---

## 5. Honest limits of this verdict

- **Family G remains the weak point.** The primary SDC Handbook returned 403 and the field
  predates arXiv. S3 rests on one fetched practice guide and one fetched toolkit paper.
- **Task 3 returned nothing, which is weak evidence.** Web-indexed issue-tracker search is not a
  search of issue trackers. F1 should not be claimed.
- **Several entries are abstract-level reads**, marked as such: the blockchain ledger paper,
  Laminator's DP coverage, MRM3.
- **One pass per family.** Saturation was not reached in any of the six families run on
  2026-08-23. A second pass, particularly on G and E, could kill S1 or S3.

The verdict is issued because the evidence is now sufficient to *act* on — not because the
search is complete.
