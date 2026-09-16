# 15 — Can any existing standard express release-boundary safety? (gap analysis, 2026-09-15)

> The honest backbone of the paper. Differential privacy is defined on the *mechanism*, but what
> ships to a data recipient is a *document* (a dataset card / metadata record). This asks a narrow,
> checkable question: do the metadata standards that people actually use have fields that can express
> the properties needed to keep that document from leaking outside ε? Each cell below is checked
> against the actual specification, not asserted. Standing rules apply.

## The properties a boundary-safe DP release artefact must express

Derived from the release boundary (`docs/design/PUBLIC_RELEASE_BOUNDARY.md`). P1–P3 are the
guarantee's parameters; P4–P11 are what makes the *artefact itself* safe and checkable.

| # | Property | Why it matters |
|---|---|---|
| P1 | ε value | the guarantee's strength |
| P2 | δ value | the guarantee's failure probability |
| P3 | Mechanism named | ε is uninterpretable without it (Dibia P12) |
| P4 | **Neighbour relation** (add/remove vs replace; bounded/unbounded) | fixes what one "record" is; under add/remove the exact row count is private |
| P5 | **Release-size provenance** (is n declared/charged, not the exact private count?) | an exact n leaks membership under add/remove-one |
| P6 | **Seed secrecy** (the run seed is withheld) | a published seed replays the release → deterministic membership oracle |
| P7 | **Keyed input fingerprint** (not an unkeyed hash of the table) | an unkeyed hash is a membership test for the standard adversary |
| P8 | **Evaluation-privacy label** (utility/attack metrics are on the real table, outside ε) | otherwise a reader assumes ε covers them |
| P9 | **Audit operating range / LoD** (the empirical audit was powered enough to matter) | prevents "privacy theater" — Dibia's own experts (P11) |
| P10 | **Tamper-evidence** (a signature over the claims) | a plain JSON/HTML label can be edited post-release |
| P11 | **Machine-checkable** (a validator can enforce the above without human reading) | humans do not re-read every release |

## The standards, checked against their actual specifications

Legend: **Y** = the standard has a field/vocabulary term for it; **~** = partial / adjacent but not
this property; **N** = no field exists.

| Property | Croissant 1.1 (MLCommons) | HF dataset card (YAML) | Datasheets (Gebru 2021) | Model Cards (Mitchell 2019) | Dibia DP label (PoPETs 2026) | **SynthProof PDS + boundary-audit** |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| P1 ε | N | N | N | N | **Y** | **Y** |
| P2 δ | N | N | N | N | **Y** | **Y** |
| P3 Mechanism | N | N | N | ~ | **Y** | **Y** |
| P4 Neighbour relation | N | N | N | N | ~ (unit-of-privacy: user vs record, not add/remove-vs-replace) | **Y** |
| P5 Release-size provenance | N (publishes exact `numRows`) | N (publishes exact `num_examples`) | N | N | N | **Y** (`release_rows_source`) |
| P6 Seed secrecy | N (provenance can carry a seed) | N | N | N | N | **Y** (withheld by construction) |
| P7 Keyed fingerprint | N (FileObject `sha256`, unkeyed) | N | N | N | N | **Y** (HMAC) |
| P8 Evaluation-privacy label | N | N | N | ~ (metrics section, no privacy status) | ~ (empirical-metrics category, no "outside ε" flag) | **Y** (`evaluation_privacy`) |
| P9 Audit operating range / LoD | N | N | N | N | N (experts flagged the absence as "privacy theater") | **Y** (`audit_ceiling`, MIQE LoD transfer) |
| P10 Tamper-evidence | N | N | N | N | N (editable label) | **Y** (Ed25519) |
| P11 Machine-checkable | ~ (validates syntax/structure, not privacy) | ~ (schema, not privacy) | N (prose Q&A) | N (prose) | N (human-facing label) | **Y** (`boundary-audit`) |

### Per-cell justification (the checkable part)

- **Croissant 1.1** — base vocabulary is schema.org + the RAI (Responsible AI) extension: `name`,
  `distribution` (FileObject with an **unkeyed** `sha256`), `recordSet`, `dataBiases`,
  `dataCollection`, `personalSensitiveInformation`. It has **no** DP terms. `dp:epsilon`,
  `dp:inputFingerprintHmacSha256`, etc. exist **only as SynthProof's own extension**
  (`synthproof/frontier/croissant.py`), which is exactly the point: the standard cannot express
  these until someone extends it. Its validator (`mlcroissant.validate`) checks JSON-LD structure,
  not privacy — it accepts a record carrying a plaintext seed or an exact private count with 0
  warnings (verified in the project's own tests). `numRows` is an exact count field (P5 = N).
- **HF dataset card** — YAML front-matter: `license`, `task_categories`, `language`, `tags`,
  `size_categories`, `configs`, and `dataset_info` with `features`/`splits`/`num_examples`/
  `num_bytes`. `num_examples` publishes the exact count (P5 = N). No DP fields at all.
- **Datasheets for Datasets** (Gebru et al., CACM 2021) — a qualitative Q&A across seven themes
  (motivation, composition, collection, preprocessing, uses, distribution, maintenance). Prose, not
  machine-checkable; no DP parameters, no crypto. P11 = N.
- **Model Cards** (Mitchell et al., FAT\* 2019) — intended use, factors, metrics, evaluation/training
  data, ethical considerations, caveats. The metrics section is the only adjacency (P3, P8 = ~); no
  release-boundary or crypto fields.
- **Dibia et al. DP label** (PoPETs 2026, arXiv:2507.15997) — nine expert-elicited categories:
  ε, δ, **unit of privacy**, utility information, mechanism, algorithm hyperparameters, deployment
  model, **empirical metrics**, privacy semantics. Rich on the *parameters* (P1–P3 = Y). Its
  "unit of privacy" is user-level vs record-level granularity — adjacent to P4 but not the
  add/remove-vs-replace distinction that makes the row count private (P4 = ~). It is a **human-facing,
  two-layer label**: it proposes **no signature** (P10 = N), **no machine-checkable schema**
  (P11 = N), and **no operating-range / limit-of-detection** for its empirical-metrics category —
  an omission the authors' own expert P11 named "**privacy theater**" (P9 = N). It does not treat the
  label itself as a potential leak channel, so P5–P7 = N.

## What this establishes (and what it does not)

`INFERENCE:` Every widely-used dataset-documentation standard can describe a dataset; **none can
express that a DP *release artefact* is safe** — none has fields for the neighbour relation as an
artefact property, release-size provenance, seed secrecy, a keyed fingerprint, an evaluation-privacy
label, an audit operating range, tamper-evidence, or a privacy-aware machine check. Dibia et al.
(2026) is the closest and the right thing to build on, and by their own account they stop at a
human-facing label and flag the operating-range gap themselves. `CONFIDENCE: high` for P4–P11
across Croissant / HF / Datasheets / Model Cards (checked against the specs); `CONFIDENCE: med-high`
for the Dibia column (checked against the paper's Tables 3–5 and §5–6, but the label's Appendix E
design was not exhaustively enumerated here).

**This is the honest contribution and its limit.** The contribution is *filling a named gap*: a
machine-checkable, signed, boundary-safe DP release artefact (the Privacy Data Sheet) plus a static
linter (`boundary-audit`). It is **integration and engineering**, complementary to Dibia et al., not
a new privacy theory and not a claim that anyone else's standard is "wrong" — they simply target a
different thing (describing data, or communicating parameters to humans) than keeping the release
document itself inside ε. That framing is what survives review; "we invented a new DP vulnerability"
does not (see `research/12`).

## Sources (each fetched or checked against the artefact)

1. Dibia, Lu, Bhattacharjee, Near, Feng — *"We Need a Standard": Toward an Expert-Informed Privacy
   Label for Differential Privacy*. PoPETs 2026(1) / arXiv:2507.15997. Tables 3–5, §4–6 (read).
2. Croissant — Akhtar et al., *Croissant: A Metadata Format for ML-Ready Datasets*, MLCommons; and
   the project's own `synthproof/frontier/croissant.py` (the `dp:` terms are our extension, not
   standard).
3. Gebru et al. — *Datasheets for Datasets*, CACM 2021.
4. Mitchell et al. — *Model Cards for Model Reporting*, FAT\* 2019.
5. HF dataset card spec — Hugging Face Hub datasets-cards documentation (YAML `dataset_info`).
