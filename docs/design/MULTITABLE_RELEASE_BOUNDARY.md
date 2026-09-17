# The multi-table release boundary — design and declared future work (Paper 2)

> Status: **design / research scope, v0.1** (2026-09-17). This is T6d from the next-steps plan.
> It is **not built and not validated.** Everything in SynthProof today — the Privacy Data Sheet,
> `boundary-audit` (RB1–RB10), the DP Release Label spec, the MST/AIM generators — describes a
> **single tabular release**. This document defines what a *relational* (multi-table) release
> boundary would be, why it is a paper-sized contribution on its own, and the honest reasons it is
> declared future work rather than claimed as done. Nothing here may be cited as an implemented
> capability. Where a check is proposed, it is a **candidate** (RB11+), not a shipped check.

## 1. Why single-table checks do not transfer

`boundary-audit` reads one artefact describing one table and asks what it leaks outside ε. A
relational release is several linked tables (e.g. `patients` — `admissions` — `labs`, joined on
foreign keys). Two things break the single-table model:

1. **The neighbour relation is no longer "one row."** In a single table, add/remove-one is
   unambiguous. Across linked tables, the unit whose privacy is protected is usually an **entity**
   (a patient), whose footprint is *one row in `patients` plus all of its `admissions` plus all of
   their `labs`*. Removing an entity removes a variable-size subgraph, not a row. An ε proved
   against row-level neighbours does **not** cover entity-level neighbours, and a release that
   quotes a row-level ε over a multi-table dataset is making a category error the current auditor
   cannot see.

2. **New channels open that have no single-table analogue.** Foreign-key degree distributions,
   join cardinalities, per-table row counts, and cross-table fingerprints each disclose structure
   about the private join graph. None of RB1–RB10 looks for them.

## 2. The relational neighbour relation (the definition everything rests on)

A multi-table release must **declare its unit of privacy explicitly**, because the choice changes
the guarantee entirely:

| Declared unit | Neighbouring datasets differ by… | Typical use |
|---|---|---|
| **row** (per table) | one row in one table | almost never correct for linked data |
| **entity / node** | one root entity and its entire dependent subgraph | the honest default for person-level data |
| **edge** | one foreign-key relationship | interaction/graph data (who-contacted-whom) |

The declared unit is a required field of a relational label (candidate `dp:relationalUnit`), and
the auditor's job — as in the single-table case — is only to check the artefact **declares** it
and that nothing in the artefact contradicts it (the asymmetry principle still holds: the checker
can prove a unit is *mis-declared* against a visible field, never that the proof is correct).

## 3. Per-entity contribution over joins

The single-table `contribution_bound` (RB7) generalises to a **per-entity contribution over the
join**: an entity with many `admissions` contributes to many rows of the joined table, so its
influence on any released marginal is multiplied by its degree. Bounding this is the relational
analogue of AIM's per-record sensitivity, and the established technique is **degree truncation** —
cap each entity's dependent rows at τ before measuring, and account for the τ-fold sensitivity
(cf. Cebere et al., P3, on truncation in DP graph/relational settings). A relational label must
disclose:

- the truncation threshold τ per relationship, and
- whether truncation was applied **before** or **after** any statistic was read (before = sound;
  after = the un-truncated statistic already leaked).

## 4. The new channels (candidate checks RB11–RB14 — NOT implemented)

Each mirrors the single-table pattern (`leak` if the artefact discloses the channel with no sound
basis; `unverifiable` if consistent-but-unconfirmable; `note` if a sound basis is stated). **These
are specifications for future work; the auditor has not been extended.**

| Candidate | Field | `leak` when… | Single-table analogue |
|---|---|---|---|
| **RB11 relational_unit** | `relational_unit` | absent, or `row` declared over linked tables | RB (unit-of-privacy) |
| **RB12 fk_degree** | `fk_degree_source` | foreign-key degree distribution published uncharged (it is a per-entity statistic) | RB4 evaluation |
| **RB13 join_cardinality** | `join_cardinality_source` | exact join/per-table row counts published with no public basis | RB2 num_rows |
| **RB14 cross_table_fingerprint** | `cross_table_fingerprint` | an unkeyed hash spanning tables (a linkage membership test) | RB3 fingerprint |

RB13 is RB2 applied per table **and** to the join result; RB14 is RB3 lifted to a linkage test.
The point of listing them is that the relational boundary is *not* just "run the single-table
auditor on each table" — the join itself opens channels (RB12, join cardinality in RB13, RB14)
that no per-table audit sees.

## 5. What building this actually requires (and why it is Paper 2)

1. **A multi-table generator with an honest entity-level guarantee.** SynthProof has none. Real
   candidates (e.g. relational adaptations of PrivBayes/PGM, or systems in the multi-table DP
   literature) each need their accounting re-derived at the entity unit — this is where a wrong
   guarantee would hide, so it cannot be rushed.
2. **A validation dataset with a genuine schema of linked tables** and a ground-truth join graph
   to test degree truncation against.
3. **Extending the auditor and the label spec** with RB11–RB14 and the relational fields, each
   with a reintroduction negative-control test (project standard).
4. **An honest empirical section** showing the entity-level audit actually behaves — not a table
   of numbers from a generator whose relational accounting was assumed rather than proved.

Any one of these is substantial; together they are a second paper. Attempting them inside the
capstone would either produce an **unvalidated multi-table generator emitting privacy claims we
cannot stand behind** (a direct violation of the honesty rules — no fabricated guarantees) or a
set of auditor checks with no relational release to run them on.

## 6. Honest status (read this before citing anything above)

- **Not implemented.** No relational generator, no RB11–RB14 in `boundary.py`, no relational
  fields in the label spec. This document is design only.
- **Not validated.** No multi-table dataset has been audited; the degree-truncation accounting
  above is a design sketch, not a proved bound.
- **Declared future work / Paper 2**, exactly as `research/22_T6_scope.md` recommended. The
  capstone contribution stops at the single-table release boundary, which *is* built, tested, and
  demonstrated end-to-end.
- The asymmetry principle carries over unchanged: even when built, a conformant relational label
  would prove only that its openable channels cannot be hidden — never that the release is private.
