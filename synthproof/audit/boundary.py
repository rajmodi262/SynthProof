"""What a differentially private release leaks OUTSIDE its epsilon, checked from the artefact alone.

WHY THIS MODULE EXISTS. An epsilon bounds what the mechanism's output reveals about one record. It
says nothing about the rest of the artefact that ships with that output. On 2026-09-14 this
project found four such channels in its own signed releases
(docs/design/PUBLIC_RELEASE_BOUNDARY.md):

  * the run seed. Every noise draw derives from it, so anyone who knows every other record could
    rebuild the release for both candidate tables and see which one matched. Measured: 15 of 15
    exact matches from the true table, 0 of 15 from its neighbour (research/release_boundary/);
  * the exact row count, which is private under add/remove-one;
  * an unkeyed SHA-256 of the input table, a deterministic membership test;
  * measurements on the real table, published with nothing saying epsilon does not cover them.

WHAT IT CAN AND CANNOT SAY. It reads only the published artefact, a Privacy Data Sheet or a
Croissant record, never the data or the producer's code, so a third party can run it. That makes it
asymmetric. It can show a channel is OPEN: a published seed is a published seed. It cannot show one
is closed: a producer can label an exact row count `declared`, and a keyed HMAC and a plain SHA-256
are both 64 hex characters. Every finding therefore carries one of three severities:

  leak          the artefact itself discloses something epsilon does not cover;
  unverifiable  the artefact is consistent with a sound release, but only the producer's honesty
                makes it one;
  note          the artefact states a sound basis, and nothing in it contradicts that.

NOVELTY, CHECKED (research/25, 2026-09-17). The leak phenomena are partly known (domain/metadata
leakage is documented for DP synthesizers -> RB6/RB9) and empirical MIA/GDP auditing is crowded.
What is not built elsewhere is the thing this module is: a SIGNED, ARTEFACT-ONLY, machine-checkable
conformance checker for a DP release label -- exactly what Dibia et al. (arXiv:2507.15997) propose
and do not build. So describe this as an ENGINEERING/INTEGRATION contribution (implementing the
proposed label + filling its signature and operating-range gaps), never as inventing non-epsilon
auditing.
"""

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Mapping, Optional

LEAK = "leak"
UNVERIFIABLE = "unverifiable"
NOTE = "note"
_SEVERITY_ORDER = {LEAK: 0, UNVERIFIABLE: 1, NOTE: 2}

_HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")
_SOUND_DOMAIN_SOURCES = ("declared", "codebook", "charged")


@dataclass(frozen=True)
class BoundaryFinding:
    """One channel, what the artefact shows about it, and what to do."""

    code: str  # RB1..RB14
    severity: str  # leak | unverifiable | note
    field: str
    finding: str
    consequence: str
    remedy: str

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class BoundaryReport:
    """The audit of one artefact."""

    artefact: str  # "privacy-data-sheet" | "croissant"
    findings: List[BoundaryFinding] = field(default_factory=list)

    @property
    def leaks(self) -> List[BoundaryFinding]:
        return [f for f in self.findings if f.severity == LEAK]

    @property
    def unverifiable(self) -> List[BoundaryFinding]:
        return [f for f in self.findings if f.severity == UNVERIFIABLE]

    @property
    def passed(self) -> bool:
        """No open channel. NOT a statement that the release is sound: see `unverifiable`."""
        return not self.leaks

    def to_dict(self) -> Dict[str, Any]:
        return {
            "artefact": self.artefact,
            "passed": self.passed,
            "leaks": len(self.leaks),
            "unverifiable": len(self.unverifiable),
            "findings": [f.to_dict() for f in self.findings],
        }


# --------------------------------------------------------------------------- the checks


def _seed(sheet: Mapping[str, Any]) -> List[BoundaryFinding]:
    seed = sheet.get("seed")
    if seed is None:
        return [
            BoundaryFinding(
                "RB1",
                NOTE,
                "seed",
                "The run seed is withheld.",
                "Nobody outside the curator can replay the noise, so the release is not a "
                "deterministic function of the table for a reader.",
                "None. Keep the seed with the curator if it is kept at all.",
            )
        ]
    return [
        BoundaryFinding(
            "RB1",
            LEAK,
            "seed",
            f"The sheet publishes the run seed ({seed}).",
            "Every noise draw derives from the seed, so the release is a deterministic function of "
            "(table, seed). A reader who knows every other record rebuilds it for both candidate "
            "tables and sees which one matches: membership decided with certainty, whatever "
            "epsilon says. Measured on this project's own releases: 15 of 15.",
            "Withhold the seed. Draw it from the operating system; if it must be kept for "
            "reproducibility, keep it with the curator and never in the artefact.",
        )
    ]


def _row_count(sheet: Mapping[str, Any]) -> List[BoundaryFinding]:
    n = sheet.get("num_rows")
    source = sheet.get("release_rows_source")
    if source in (None, "unknown"):
        return [
            BoundaryFinding(
                "RB2",
                LEAK,
                "num_rows",
                f"num_rows = {n} is published with no stated basis (no release_rows_source).",
                "Under add/remove-one the exact row count is private: two neighbouring tables "
                "differ in length by one. A size with no stated basis has to be read as the "
                "input's exact count.",
                "Release a size declared before the data is read, or a charged noisy count, and "
                "record which in release_rows_source.",
            )
        ]
    if source == "dp_count":
        cost = sheet.get("release_rows_eps") or 0.0
        if cost <= 0:
            return [
                BoundaryFinding(
                    "RB2",
                    LEAK,
                    "release_rows_eps",
                    "num_rows is called a noisy count, but no epsilon is recorded for it.",
                    "An uncharged count is not a DP count. The size may be exact, or its cost may "
                    "be missing from total_proved_eps.",
                    "Record the count's epsilon and include it in the proved total.",
                )
            ]
        return [
            BoundaryFinding(
                "RB2",
                NOTE,
                "num_rows",
                f"num_rows = {n} is a noisy count costing epsilon {cost:g}, stated as included "
                "in total_proved_eps.",
                "The size is covered by the guarantee, provided the stated cost was really "
                "charged.",
                "None.",
            )
        ]
    if source in ("declared", "protocol"):
        return [
            BoundaryFinding(
                "RB2",
                UNVERIFIABLE,
                "num_rows",
                f"num_rows = {n} is {source}: fixed before the data was read, by the producer's "
                "account.",
                "Nothing in the artefact can show the number was not read off the table. A "
                "declared size that happens to equal the input's length leaks it.",
                "Rely on it only if the curator's declaration process is trusted.",
            )
        ]
    return [
        BoundaryFinding(
            "RB2",
            LEAK,
            "release_rows_source",
            f"release_rows_source = {source!r} is not a recognised basis.",
            "An unrecognised basis gives no reason to believe the size is public.",
            "Use declared, protocol or dp_count.",
        )
    ]


_UNKEYED_SCHEMES = ("sha256", "sha-256", "unkeyed", "plain")
_KEYED_SCHEMES = ("hmac-sha256", "hmac", "hmac-sha-256")


def _fingerprint(sheet: Mapping[str, Any]) -> List[BoundaryFinding]:
    fp = sheet.get("input_fingerprint")
    if not fp:
        return []

    # A declared scheme is the checkable path (added 2026-09-17). The old heuristic could only
    # ever say "unverifiable" for a keyed fingerprint, because a plain SHA-256 and an HMAC are
    # both 64 hex characters. A producer that DECLARES the scheme -- and, in a signed sheet,
    # binds that declaration under the signature -- turns the guess into something a reader can
    # act on: a self-declared unkeyed hash is a self-declared membership test (LEAK), and a
    # declared HMAC with a named key is a claim the producer cannot later repudiate (NOTE).
    scheme = sheet.get("fingerprint_scheme")
    if scheme is not None:
        s = str(scheme).lower()
        if s in _UNKEYED_SCHEMES:
            return [
                BoundaryFinding(
                    "RB3",
                    LEAK,
                    "fingerprint_scheme",
                    f"The sheet declares its input fingerprint is {scheme!r} -- an unkeyed hash.",
                    "By the producer's own declaration this is a deterministic function of the "
                    "input table: a reader who knows every other record hashes both candidate "
                    "tables and compares. A membership test no epsilon covers.",
                    "Switch to an HMAC under a curator secret (fingerprint_scheme='hmac-sha256' "
                    "with a fingerprint_key_id), or omit the fingerprint.",
                )
            ]
        if s in _KEYED_SCHEMES:
            key_id = sheet.get("fingerprint_key_id")
            if key_id:
                return [
                    BoundaryFinding(
                        "RB3",
                        NOTE,
                        "fingerprint_scheme",
                        f"The fingerprint is declared {scheme!r} under key {key_id!r}.",
                        "A keyed fingerprint is not a membership test for a reader without the "
                        "key. The named key binds the claim: in a signed sheet the producer "
                        "cannot later deny the fingerprint was keyed, so this is checkable "
                        "accountability rather than a guess (it does not verify the bytes).",
                        "None. Keep the key secret; publish only its id/commitment.",
                    )
                ]
            return [
                BoundaryFinding(
                    "RB3",
                    UNVERIFIABLE,
                    "fingerprint_scheme",
                    f"The fingerprint is declared {scheme!r} but no fingerprint_key_id is given.",
                    "A keyed scheme with no named key is not bound to anything -- nothing stops "
                    "the value being an unkeyed hash relabelled.",
                    "Publish a fingerprint_key_id (a public identifier or commitment for the "
                    "secret key), so the keyed claim is bound.",
                )
            ]
        return [
            BoundaryFinding(
                "RB3",
                UNVERIFIABLE,
                "fingerprint_scheme",
                f"fingerprint_scheme = {scheme!r} is not a recognised scheme.",
                "An unrecognised scheme gives no reason to believe the fingerprint is keyed.",
                "Use 'hmac-sha256' (keyed) or 'sha256' (unkeyed, and a leak).",
            )
        ]

    # No declared scheme: fall back to the legacy heuristic.
    legacy = sheet.get("release_rows_source") in (None, "unknown")
    if legacy and isinstance(fp, str) and _HEX64.match(fp):
        return [
            BoundaryFinding(
                "RB3",
                LEAK,
                "input_fingerprint",
                "A 64-hex input fingerprint is published by a producer that predates keyed "
                "fingerprints. Treat it as an unkeyed SHA-256 of the input table.",
                "A reader who knows every other record hashes both candidate tables and compares: "
                "a deterministic membership test that no epsilon covers.",
                "Publish an HMAC under a curator secret, or omit the field.",
            )
        ]
    return [
        BoundaryFinding(
            "RB3",
            UNVERIFIABLE,
            "input_fingerprint",
            "An input fingerprint is published with no declared scheme.",
            "A keyed HMAC and a plain SHA-256 look identical from outside. Only the producer's "
            "code decides whether this is a membership test.",
            "Declare fingerprint_scheme ('hmac-sha256' with a fingerprint_key_id), or omit it.",
        )
    ]


def _evaluation(sheet: Mapping[str, Any]) -> List[BoundaryFinding]:
    has_measurements = bool(sheet.get("evaluation")) or sheet.get("total_audited_eps") is not None
    if not has_measurements:
        return []
    if sheet.get("evaluation_privacy"):
        return [
            BoundaryFinding(
                "RB4",
                NOTE,
                "evaluation_privacy",
                "Measurements on the real table are published and labelled as outside epsilon.",
                "They are non-private statistics of the input. The label stops a reader assuming "
                "epsilon covers them.",
                "None, beyond deciding whether they need publishing at all.",
            )
        ]
    return [
        BoundaryFinding(
            "RB4",
            LEAK,
            "evaluation",
            "Measurements computed on the real table (utility, membership-inference AUC, audited "
            "epsilon) are published with no statement that epsilon does not cover them.",
            "Each is a non-private statistic of the input, and a reader will reasonably assume the "
            "headline epsilon covers everything in the artefact.",
            "Label them outside epsilon in the artefact itself, or do not publish them.",
        )
    ]


def _cross_check(sheet: Mapping[str, Any]) -> List[BoundaryFinding]:
    agreement = sheet.get("accountant_agreement") or {}
    verdict = agreement.get("verdict") if isinstance(agreement, Mapping) else None
    if verdict == "under_report":
        return [
            BoundaryFinding(
                "RB5",
                LEAK,
                "accountant_agreement",
                "A second accountant composed this release to a LARGER epsilon than the one "
                "published.",
                "The published guarantee is not supported by an independent computation.",
                "Do not rely on total_proved_eps until the disagreement is resolved.",
            )
        ]
    if verdict in ("agree", "conservative"):
        return [
            BoundaryFinding(
                "RB5",
                NOTE,
                "accountant_agreement",
                f"A second accountant was consulted: {verdict}.",
                "The epsilon does not rest on one implementation alone.",
                "None.",
            )
        ]
    return [
        BoundaryFinding(
            "RB5",
            UNVERIFIABLE,
            "accountant_agreement",
            f"The epsilon was not independently cross-checked (verdict: {verdict or 'absent'}).",
            "It rests on a single accounting implementation, and audits of DP libraries have found "
            "guarantee violations in them.",
            "Treat total_proved_eps as one implementation's claim.",
        )
    ]


def _domain(sheet: Mapping[str, Any]) -> List[BoundaryFinding]:
    source = sheet.get("domain_source")
    if source == "inferred-nonprivate":
        return [
            BoundaryFinding(
                "RB6",
                LEAK,
                "domain_source",
                "Column bounds and category domains were read from the sensitive table and not "
                "charged.",
                "The domain itself is released outside the guarantee. A category present in one "
                "record announces that record.",
                "Declare the schema from public knowledge, or charge its construction.",
            )
        ]
    if source in _SOUND_DOMAIN_SOURCES:
        return []
    return [
        BoundaryFinding(
            "RB6",
            UNVERIFIABLE,
            "domain_source",
            f"How the domain was obtained is not stated (domain_source: {source or 'absent'}).",
            "Every epsilon in the artefact is conditional on a domain that may have leaked.",
            "State domain_source.",
        )
    ]


def _contribution(sheet: Mapping[str, Any]) -> List[BoundaryFinding]:
    bound = sheet.get("contribution_bound", 1)
    if bound in (1, None):
        return []
    return [
        BoundaryFinding(
            "RB7",
            UNVERIFIABLE,
            "contribution_bound",
            f"Up to {bound} rows per person.",
            f"The guarantee is per record, so a person with {bound} rows is protected about "
            f"{bound} times less than epsilon suggests.",
            "Pre-process to one row per person, or read epsilon as a per-record figure.",
        )
    ]


_SOUND_DISCRETIZATION = ("uniform-public", "dp-charged", "declared", "not-applicable")


def _public_invariants(sheet: Mapping[str, Any]) -> List[BoundaryFinding]:
    """RB8. Quantities the producer declares as published OUTSIDE epsilon (e.g. the 2020 Census
    invariants: exact state totals, structural zeros). A declared invariant with a stated basis is
    a sound outside-epsilon label; one without a basis reads like an uncharged private statistic."""
    inv = sheet.get("public_invariants")
    if not inv:
        return []
    if isinstance(inv, Mapping):
        items = [{"name": k, "basis": v} for k, v in inv.items()]
    elif isinstance(inv, (list, tuple)):
        items = [x if isinstance(x, Mapping) else {"name": x, "basis": None} for x in inv]
    else:
        items = [{"name": str(inv), "basis": None}]
    missing = [str(i.get("name")) for i in items if not i.get("basis")]
    if missing:
        return [
            BoundaryFinding(
                "RB8",
                UNVERIFIABLE,
                "public_invariants",
                f"{len(missing)} invariant(s) declared outside epsilon with no stated basis: "
                f"{', '.join(missing)}.",
                "A quantity published outside the budget needs a reason (statutory, public "
                "aggregate, structural zero); without one a reader cannot tell a policy invariant "
                "from an uncharged private statistic.",
                "Give each public invariant a basis, e.g. 'statutory' or 'structural-zero'.",
            )
        ]
    names = ", ".join(str(i.get("name")) for i in items)
    return [
        BoundaryFinding(
            "RB8",
            NOTE,
            "public_invariants",
            f"{len(items)} quantity(ies) declared outside epsilon with a stated basis: {names}.",
            "They are labelled as published outside the budget by policy, so a reader will not "
            "mistake them for epsilon-covered outputs (cf. the 2020 Census invariants).",
            "None. The exact values still rest on the declaration; a private count also trips RB2.",
        )
    ]


def _discretization(sheet: Mapping[str, Any]) -> List[BoundaryFinding]:
    """RB9. How continuous columns were binned. Bins read from the data (quantile, k-means) and not
    charged release the input distribution outside epsilon (Ganev et al., 2504.06923)."""
    src = sheet.get("discretization_source")
    if src is None:
        return []
    if src == "data-derived":
        return [
            BoundaryFinding(
                "RB9",
                LEAK,
                "discretization_source",
                "Bin edges were chosen from the sensitive data (e.g. quantile or k-means) and not "
                "charged.",
                "Data-derived bins release information about the input distribution outside "
                "epsilon; reading the binning off the data can break end-to-end DP.",
                "Use uniform bins over the public domain, or charge the discretiser (PrivTree).",
            )
        ]
    if src in _SOUND_DISCRETIZATION:
        return []
    return [
        BoundaryFinding(
            "RB9",
            UNVERIFIABLE,
            "discretization_source",
            f"discretization_source = {src!r} is not a recognised basis.",
            "An unrecognised basis gives no reason to believe the bins were public or charged.",
            "Use uniform-public, dp-charged, declared, or not-applicable.",
        )
    ]


def _amplification(sheet: Mapping[str, Any]) -> List[BoundaryFinding]:
    """RB10. If a release claims a smaller epsilon via amplification (subsampling, missingness), the
    assumption must be stated or the published epsilon is an unverifiable under-estimate (P7)."""
    amp = sheet.get("privacy_amplification")
    if not amp:
        return []
    basis = amp.get("basis") if isinstance(amp, Mapping) else None
    factor = amp.get("factor") if isinstance(amp, Mapping) else None
    if not basis:
        return [
            BoundaryFinding(
                "RB10",
                LEAK,
                "privacy_amplification",
                "The release claims amplified (smaller) epsilon but states no amplification basis.",
                "An amplification factor with no stated assumption (subsampling rate, MCAR "
                "missingness) cannot be checked, and a wrong assumption makes the published "
                "epsilon an under-estimate.",
                "State the basis and its assumption, e.g. 'poisson-subsampling q=0.01' or "
                "'mcar-missingness'.",
            )
        ]
    return [
        BoundaryFinding(
            "RB10",
            NOTE,
            "privacy_amplification",
            f"Epsilon is amplified (factor {factor}) on a stated basis: {basis}.",
            "The tighter epsilon rests on the stated assumption, which a reader can check.",
            "None, provided the assumption holds.",
        )
    ]


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


_CHECKS = (
    _seed,
    _row_count,
    _fingerprint,
    _evaluation,
    _cross_check,
    _domain,
    _contribution,
    _public_invariants,
    _discretization,
    _amplification,
    _relational_unit,
    _fk_degree,
    _join_cardinality,
    _cross_table_fingerprint,
)


# --------------------------------------------------------------------------- entry points


def _ordered(findings: List[BoundaryFinding]) -> List[BoundaryFinding]:
    return sorted(findings, key=lambda f: (_SEVERITY_ORDER[f.severity], f.code))


def audit_sheet(sheet: Mapping[str, Any]) -> BoundaryReport:
    """Audits a Privacy Data Sheet, as parsed from its JSON."""
    findings: List[BoundaryFinding] = []
    for check in _CHECKS:
        findings.extend(check(sheet))
    return BoundaryReport("privacy-data-sheet", _ordered(findings))


def audit_croissant(record: Mapping[str, Any]) -> BoundaryReport:
    """Audits a Croissant record: its embedded sheet, and what the record adds outside it.

    The human-visible layer of a record is not covered by the signature, so a channel can be open
    there even when the signed sheet is clean.
    """
    sheet = record.get("dp:privacyDataSheet")
    if not isinstance(sheet, Mapping):
        return BoundaryReport(
            "croissant",
            [
                BoundaryFinding(
                    "RB0",
                    UNVERIFIABLE,
                    "dp:privacyDataSheet",
                    "The record carries no Privacy Data Sheet.",
                    "There is nothing to audit beyond the record's own fields.",
                    "Embed the signed sheet.",
                )
            ],
        )
    findings = list(audit_sheet(sheet).findings)
    prov = record.get("prov:wasGeneratedBy")
    prov = prov if isinstance(prov, Mapping) else {}
    if prov.get("dp:seed") is not None:
        findings = [f for f in findings if f.code != "RB1"]
        findings.append(
            BoundaryFinding(
                "RB1",
                LEAK,
                "prov:wasGeneratedBy.dp:seed",
                f"The record publishes the run seed ({prov.get('dp:seed')}) in its provenance.",
                "The provenance layer is outside the signature, and a seed there replays the "
                "release exactly as one in the sheet would.",
                "Remove dp:seed from the provenance.",
            )
        )
    used = prov.get("prov:used")
    used = used if isinstance(used, Mapping) else {}
    if used.get("dp:inputFingerprintSha256"):
        findings = [f for f in findings if f.code != "RB3"]
        findings.append(
            BoundaryFinding(
                "RB3",
                LEAK,
                "prov:used.dp:inputFingerprintSha256",
                "The record labels its input fingerprint a plain SHA-256.",
                "By its own label it is an unkeyed hash of the input table: a membership test.",
                "Publish an HMAC (dp:inputFingerprintHmacSha256) or nothing.",
            )
        )
    return BoundaryReport("croissant", _ordered(findings))


def audit_release(document: Mapping[str, Any]) -> BoundaryReport:
    """Audits whichever artefact `document` is: a Croissant record or a bare sheet."""
    if "dp:privacyDataSheet" in document or "@context" in document:
        return audit_croissant(document)
    return audit_sheet(document)


def render(report: BoundaryReport, width: Optional[int] = 96) -> str:
    """A plain-text report for a terminal."""
    import textwrap

    wrap = (
        (lambda s, indent: textwrap.fill(s, width=width, subsequent_indent=indent))
        if width
        else (lambda s, indent: s)
    )
    lines = [
        f"Release-boundary audit of a {report.artefact}",
        f"  open channels (leak): {len(report.leaks)}   rest on producer honesty: "
        f"{len(report.unverifiable)}",
        "",
    ]
    labels = {LEAK: "LEAK", UNVERIFIABLE: "UNVERIFIABLE", NOTE: "ok"}
    for f in report.findings:
        lines.append(wrap(f"[{labels[f.severity]:>12}] {f.code} {f.field}: {f.finding}", " " * 15))
        if f.severity != NOTE:
            lines.append(wrap(f"               why: {f.consequence}", " " * 20))
            lines.append(wrap(f"               fix: {f.remedy}", " " * 20))
    lines.append("")
    lines.append(
        "PASSED: no open channel found. Not proof of a sound release; see UNVERIFIABLE."
        if report.passed
        else "FAILED: this artefact discloses something its epsilon does not cover."
    )
    return "\n".join(lines)
