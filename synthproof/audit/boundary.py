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

NOT CLAIMED AS NOVEL. Whether auditing a DP release's non-epsilon channels has prior art has
not been checked yet. Until it is, describe this as a checker, not a contribution.
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

    code: str  # RB1..RB7
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


def _fingerprint(sheet: Mapping[str, Any]) -> List[BoundaryFinding]:
    fp = sheet.get("input_fingerprint")
    if not fp:
        return []
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
            "An input fingerprint is published.",
            "A keyed HMAC and a plain SHA-256 look identical from outside. Only the producer's "
            "code decides whether this is a membership test.",
            "Accept it only from a producer whose fingerprint is documented as keyed.",
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


_CHECKS = (_seed, _row_count, _fingerprint, _evaluation, _cross_check, _domain, _contribution)


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
