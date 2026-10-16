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

import re  # noqa: F401  (kept for callers that relied on boundary.re)
from typing import Any, List, Mapping, Optional

from synthproof.audit.boundary._types import (  # noqa: F401  (public API re-exported)
    _HEX64,
    _SEVERITY_ORDER,
    _SOUND_DOMAIN_SOURCES,
    LEAK,
    NOTE,
    UNVERIFIABLE,
    BoundaryFinding,
    BoundaryReport,
    _number,
)
from synthproof.audit.boundary.audit_claim import _mechanism_audit  # noqa: F401
from synthproof.audit.boundary.epsilon import _cross_check, _recompute_epsilon  # noqa: F401
from synthproof.audit.boundary.relational import (  # noqa: F401
    _cross_table_fingerprint,
    _fk_degree,
    _is_relational,
    _join_cardinality,
    _relational_unit,
)
from synthproof.audit.boundary.single_table import (  # noqa: F401
    _amplification,
    _contribution,
    _discretization,
    _domain,
    _evaluation,
    _fingerprint,
    _public_invariants,
    _row_count,
    _seed,
)

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
    _mechanism_audit,
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


def _signature(document: Mapping[str, Any], public_key_path) -> BoundaryFinding:
    """RB0: is the label the one its maker signed? Checked FIRST; everything else reads it."""
    if public_key_path is None:
        return BoundaryFinding(
            "RB0",
            UNVERIFIABLE,
            "signature",
            "The signature was not checked (no public key given).",
            "Every other finding describes the label as received, which may have been edited.",
            "Re-run with --pubkey <the maker's public key>.",
        )
    from pathlib import Path

    from synthproof.frontier import croissant as croissant_mod
    from synthproof.ledger import signing

    try:
        if isinstance(document.get("dp:privacyDataSheet"), Mapping):
            croissant_mod.verify_croissant(dict(document), key_path=Path(public_key_path))
        else:
            signing.verify_datasheet(dict(document), key_path=Path(public_key_path))
    except (signing.SignatureError, croissant_mod.CroissantError) as exc:
        return BoundaryFinding(
            "RB0",
            LEAK,
            "signature",
            f"The signature does not verify: {exc}",
            "The label was altered after signing, or was not signed by this key. Nothing in it "
            "can be relied on.",
            "Obtain the original signed release from its maker.",
        )
    return BoundaryFinding(
        "RB0",
        NOTE,
        "signature",
        "Signature verified against the given public key.",
        "The label is exactly what the key holder signed (not that its numbers are true).",
        "None.",
    )


def audit_release(document: Mapping[str, Any], public_key_path=None) -> BoundaryReport:
    """Audits whichever artefact `document` is: a Croissant record or a bare sheet.

    The signature is checked first when a public key is given (RB0); without one the report
    says the label was taken as received.
    """
    if "dp:privacyDataSheet" in document or "@context" in document:
        report = audit_croissant(document)
    else:
        report = audit_sheet(document)
    return BoundaryReport(
        report.artefact, [_signature(document, public_key_path), *report.findings]
    )


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
