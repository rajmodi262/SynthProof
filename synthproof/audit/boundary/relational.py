"""Multi-table release-boundary checks (RB11-RB14)."""

from typing import Any, List, Mapping

from synthproof.audit.boundary._types import (
    LEAK,
    NOTE,
    UNVERIFIABLE,
    BoundaryFinding,
)
from synthproof.audit.boundary.single_table import _KEYED_SCHEMES, _UNKEYED_SCHEMES

# --------------------------------------------------------------------------- multi-table (RB11-14)
#
# A relational release (linked tables joined on foreign keys) opens channels a single-table sheet
# has no field for: the neighbour relation is an ENTITY and its whole dependent subgraph, not one
# row, and the join itself leaks foreign-key degree, join cardinality and cross-table linkage. These
# checks are document-level like RB1-RB10 -- they read declared fields and never the data -- and are
# specified in docs/design/MULTITABLE_RELEASE_BOUNDARY.md. What is shipped here is the CHECKS; there
# is still no validated multi-table GENERATOR to run them against, and that remains declared future
# work (Paper 2). The asymmetry principle carries over unchanged.

_RELATIONAL_FIELDS = (
    "tables",
    "relational_unit",
    "fk_degree_source",
    "join_cardinality_source",
    "cross_table_fingerprint",
)
_SOUND_RELATIONAL_UNITS = ("entity", "node", "edge")
_SOUND_FK_DEGREE = ("uniform-public", "dp-charged", "declared", "not-applicable")
_SOUND_JOIN_CARDINALITY = ("declared", "dp-charged", "uniform-public", "not-applicable")


def _is_relational(sheet: Mapping[str, Any]) -> bool:
    """True when the sheet describes a multi-table release (any relational field is set)."""
    return any(sheet.get(f) for f in _RELATIONAL_FIELDS)


def _relational_unit(sheet: Mapping[str, Any]) -> List[BoundaryFinding]:
    """RB11. A relational release must declare its unit of privacy. `row` over linked tables
    undercounts an entity's footprint (one entity spans many rows across tables)."""
    if not _is_relational(sheet):
        return []
    unit = sheet.get("relational_unit")
    if unit is None:
        return [
            BoundaryFinding(
                "RB11",
                LEAK,
                "relational_unit",
                "A multi-table release states no relational unit of privacy.",
                "Across linked tables the neighbour relation is an entity and all its dependent "
                "rows, not a single row. Without a declared unit an epsilon cannot be read: a "
                "row-level guarantee does not cover an entity-level neighbour.",
                "Declare relational_unit: 'entity' (or 'node'/'edge' for graph data).",
            )
        ]
    if str(unit).lower() == "row":
        return [
            BoundaryFinding(
                "RB11",
                LEAK,
                "relational_unit",
                "relational_unit = 'row' is declared over linked tables.",
                "A row-level neighbour undercounts an entity whose footprint spans many rows "
                "across tables, so the epsilon protects far less than it appears to.",
                "Use an entity-level unit and bound each entity's contribution over the join.",
            )
        ]
    if str(unit).lower() in _SOUND_RELATIONAL_UNITS:
        return []
    return [
        BoundaryFinding(
            "RB11",
            UNVERIFIABLE,
            "relational_unit",
            f"relational_unit = {unit!r} is not a recognised unit.",
            "An unrecognised unit gives no basis for reading the guarantee over the join.",
            "Use entity, node, or edge.",
        )
    ]


def _fk_degree(sheet: Mapping[str, Any]) -> List[BoundaryFinding]:
    """RB12. Foreign-key degree (how many child rows an entity has) is a per-entity statistic; a
    degree distribution read off the data and published uncharged leaks it outside epsilon."""
    src = sheet.get("fk_degree_source")
    if src is None:
        return []
    if src == "data-derived":
        return [
            BoundaryFinding(
                "RB12",
                LEAK,
                "fk_degree_source",
                "The foreign-key degree distribution was taken from the data and not charged.",
                "Per-entity degree (e.g. a patient's number of admissions) is a private statistic; "
                "publishing its distribution uncharged releases information outside epsilon.",
                "Truncate degree at a declared bound, or charge the degree histogram (dp-charged).",
            )
        ]
    if src in _SOUND_FK_DEGREE:
        return []
    return [
        BoundaryFinding(
            "RB12",
            UNVERIFIABLE,
            "fk_degree_source",
            f"fk_degree_source = {src!r} is not a recognised basis.",
            "An unrecognised basis gives no reason to believe the degrees were public or charged.",
            "Use uniform-public, dp-charged, declared, or not-applicable.",
        )
    ]


def _join_cardinality(sheet: Mapping[str, Any]) -> List[BoundaryFinding]:
    """RB13. Exact join / per-table row counts are private under an entity-level neighbour (two
    neighbouring datasets differ by a whole entity's rows). RB2 lifted to the relational setting."""
    src = sheet.get("join_cardinality_source")
    if src is None:
        return []
    if src == "data-derived":
        return [
            BoundaryFinding(
                "RB13",
                LEAK,
                "join_cardinality_source",
                "Exact join or per-table row counts are published with no public basis.",
                "Under an entity-level neighbour the join size is private: two neighbouring "
                "datasets differ by one entity's whole set of rows. An exact count read off the "
                "data has to be treated as leaking that entity.",
                "Declare the sizes in advance, or release charged noisy counts (dp-charged).",
            )
        ]
    if src in _SOUND_JOIN_CARDINALITY:
        return []
    return [
        BoundaryFinding(
            "RB13",
            UNVERIFIABLE,
            "join_cardinality_source",
            f"join_cardinality_source = {src!r} is not a recognised basis.",
            "An unrecognised basis gives no reason to believe the counts are public or charged.",
            "Use declared, dp-charged, uniform-public, or not-applicable.",
        )
    ]


def _cross_table_fingerprint(sheet: Mapping[str, Any]) -> List[BoundaryFinding]:
    """RB14. A hash spanning linked tables is a linkage membership test. RB3 lifted across tables:
    a keyed scheme with a named key is bound (note); an unkeyed one is a self-declared leak."""
    fp = sheet.get("cross_table_fingerprint")
    if not fp:
        return []
    scheme = sheet.get("cross_table_fingerprint_scheme")
    if scheme is None:
        return [
            BoundaryFinding(
                "RB14",
                UNVERIFIABLE,
                "cross_table_fingerprint",
                "A cross-table fingerprint is published with no declared scheme.",
                "A keyed HMAC and a plain hash look identical from outside; only the producer's "
                "code decides whether this is a cross-table linkage membership test.",
                "Declare cross_table_fingerprint_scheme ('hmac-sha256' with a key id), or omit it.",
            )
        ]
    s = str(scheme).lower()
    if s in _UNKEYED_SCHEMES:
        return [
            BoundaryFinding(
                "RB14",
                LEAK,
                "cross_table_fingerprint_scheme",
                f"The cross-table fingerprint is declared {scheme!r} -- an unkeyed hash.",
                "By its own declaration it is a deterministic function of the linked tables: a "
                "membership test spanning the join that no epsilon covers.",
                "Use an HMAC under a curator secret with a named key, or omit the fingerprint.",
            )
        ]
    if s in _KEYED_SCHEMES:
        key_id = sheet.get("cross_table_fingerprint_key_id")
        if key_id:
            return [
                BoundaryFinding(
                    "RB14",
                    NOTE,
                    "cross_table_fingerprint_scheme",
                    f"The cross-table fingerprint is declared {scheme!r} under key {key_id!r}.",
                    "A keyed cross-table fingerprint is not a linkage test for a reader without "
                    "the key; the named key binds the claim under signature (accountability, not "
                    "byte-level verification).",
                    "None. Keep the key secret; publish only its id/commitment.",
                )
            ]
        return [
            BoundaryFinding(
                "RB14",
                UNVERIFIABLE,
                "cross_table_fingerprint_scheme",
                f"The cross-table fingerprint is declared {scheme!r} but names no key.",
                "A keyed scheme with no named key is bound to nothing.",
                "Publish a cross_table_fingerprint_key_id, so the keyed claim is bound.",
            )
        ]
    return [
        BoundaryFinding(
            "RB14",
            UNVERIFIABLE,
            "cross_table_fingerprint_scheme",
            f"cross_table_fingerprint_scheme = {scheme!r} is not a recognised scheme.",
            "An unrecognised scheme gives no reason to believe the fingerprint is keyed.",
            "Use 'hmac-sha256' (keyed) or 'sha256' (unkeyed, and a leak).",
        )
    ]
