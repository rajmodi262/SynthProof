# 22 — T6 scope: extend boundary-audit + propose the signed/checkable label as a standard

> T6 from the next-steps plan is big and multi-part. This is the sub-plan to approve before building.
> Guiding fact: `boundary-audit` already reads the *document* (mechanism-agnostic), and `croissant.py`
> already emits a `dp:` vocabulary — so parts of T6 are *formalisation*, not greenfield. The genuinely
> large, research-grade part is multi-table; it is flagged as future/Paper-2, not capstone-now.

## T6 broken into sub-tasks (with effort, risk, dependency)

### T6a — New RB checks motivated directly by the survey  ·  effort: **cheap** · risk: low
The auditor covers RB1–RB7. The survey points to three more checkable channels, each a small, tested
addition mirroring the existing `_domain` (RB6) pattern:
- **RB8 `public_invariants`** (from P9 / `research/20`): a declared list of fields published *outside*
  ε (state totals, structural zeros). Declared → NOTE; exact aggregates with no declaration → flag.
  Removes the current reliance on folding invariants into the evaluation-privacy label.
- **RB9 `discretization_source`** (from P5): parallels `domain_source` — `uniform-public` /
  `dp-charged` are sound; `bins-from-data` (quantile/k-means read off the data, uncharged) is a leak.
- **RB10 `amplification_disclosure`** (from P7): if a release claims a tighter ε via subsampling or
  missingness amplification, is the amplification factor + its assumption (e.g. independent-row
  missingness, MCAR) disclosed? Undisclosed amplification → unverifiable.
Deliverable: 3 checks + emission fields in `certificate.py`/`croissant.py` + negative-control tests in
`test_boundary_audit.py`. **Recommended to do first** — highest value per hour, fully in capstone scope.

### T6b — Formal "signed + machine-checkable DP release label" spec  ·  effort: **medium** · risk: low
Write `docs/design/DP_RELEASE_LABEL_SPEC.md`: the Privacy Data Sheet as a **Croissant 1.1 extension**
(the `dp:` vocabulary already in `croissant.py`) that (1) carries Dibia's nine categories (P10),
(2) adds the two gaps Dibia leaves — an **Ed25519 signature** and an **operating-range/LoD** field —
and (3) defines **conformance = passing `boundary-audit` RB1–RB10**. Position explicitly as
"implementing the Dibia label + making it checkable." Deliverable: the spec doc + a
`scripts/validate_release_label.py` conformance runner (wraps existing `boundary-audit` + the
MLCommons Croissant validator we already shell out to). Strong viva/paper material.

### T6c — More generators emitting a correct sheet  ·  effort: **medium** · risk: med (compute/deps)
"More mechanisms" = add MST and/or PrivBayes to the pipeline (both are `select–measure–generate`,
same family as our AIM path via Private-PGM) and confirm each emits a boundary-clean sheet. Note the
auditor itself needs no change (document-level). Risk: dependency/compute (MST via Private-PGM, memory
like AIM — one job at a time). Deliverable: generators + a row in the H1 grid + sheets that pass audit.

### T6d — Multi-table / relational release boundary  ·  effort: **BIG (research)** · risk: high
Define the release boundary for *relational* DP synthetic data: the neighbour relation across linked
tables, per-entity contribution over joins (cf. Cebere P3's degree-truncation), and the new channels a
multi-table release opens (foreign-key degree, join cardinality, per-table row counts, cross-table
fingerprints). Then extend the auditor + build/borrow a multi-table generator to test on. **This is a
paper-sized contribution on its own — recommend scoping it as Future Work / Paper 2, not capstone-now.**

## Recommended order & call for approval
1. **T6a** (cheap, do now) → 2. **T6b** (spec, leverages existing Croissant emitter) →
3. **T6c** (more generators, compute permitting) → 4. **T6d** (multi-table) = **future/Paper 2**.

**Decision needed:** approve **T6a + T6b now** (both in-scope, high value), defer **T6c** (compute), and
mark **T6d** as declared future work? Or a different split.

## Honesty guardrails for T6
- Every new RB check ships with a reintroduction negative-control test (project standard).
- The spec must state, as the code does, the **asymmetry principle**: conformance proves channels
  *open* can't be hidden; it never certifies a release private.
- Do not describe multi-table as done or in-progress until it is; it is a research bet.
