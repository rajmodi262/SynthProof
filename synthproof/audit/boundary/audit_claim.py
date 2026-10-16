"""RB15: the empirical-audit claim a sheet carries, checked from the artefact alone (W9).

A sheet's `mechanism_audit` reports what a GDP adversary certified about the mechanism, with the
instrument's ceiling. Three things about it can be checked without trusting the producer: that it
audits the mechanism the sheet says ran, that each audited value sits inside its own instrument's
range, and whether the audit found the mechanism leaking more than its proof allows.
"""

from typing import Any, List, Mapping

from synthproof.audit.boundary._types import LEAK, NOTE, UNVERIFIABLE, BoundaryFinding, _number

_FIELD = "mechanism_audit"


def _mechanism_audit(sheet: Mapping[str, Any]) -> List[BoundaryFinding]:
    """RB15. Absent block: nothing to check (older sheets predate the field)."""
    block = sheet.get(_FIELD)
    if not block:
        return []
    if not isinstance(block, Mapping) or not isinstance(block.get("cells"), list):
        return [
            BoundaryFinding(
                "RB15",
                UNVERIFIABLE,
                _FIELD,
                "The sheet carries a mechanism audit that is not a mapping with a list of cells.",
                "Its numbers cannot be read, so the audit claim cannot be checked.",
                "Emit the block with synthproof.audit.mechanism_audit.mechanism_audit_for.",
            )
        ]
    if block.get("mechanism") != sheet.get("mechanism"):
        return [
            BoundaryFinding(
                "RB15",
                UNVERIFIABLE,
                f"{_FIELD}.mechanism",
                f"The audit is of '{block.get('mechanism')}' but the sheet says "
                f"'{sheet.get('mechanism')}' ran.",
                "Evidence about a different mechanism says nothing about this release.",
                "Embed the audit of the mechanism that produced the release, or none.",
            )
        ]
    findings: List[BoundaryFinding] = []
    for i, cell in enumerate(block["cells"]):
        where = f"{_FIELD}.cells[{i}]"
        emp = _number(cell.get("eps_emp")) if isinstance(cell, Mapping) else None
        ceiling = _number(cell.get("eps_ceiling_at_this_n")) if isinstance(cell, Mapping) else None
        if emp is None or ceiling is None or emp > ceiling + 1e-9:
            findings.append(
                BoundaryFinding(
                    "RB15",
                    UNVERIFIABLE,
                    where,
                    "An audited epsilon is missing its ceiling, or exceeds it.",
                    "No instrument can certify more than its ceiling; a value above it means the "
                    "cell was edited or mis-computed.",
                    "Report eps_emp beside eps_ceiling_at_this_n, as the audit runner writes them.",
                )
            )
        elif cell.get("violation_claimed"):
            findings.append(
                BoundaryFinding(
                    "RB15",
                    LEAK,
                    where,
                    f"The audit certified more than the proof allows at target eps "
                    f"{cell.get('target_eps')} (family-wise significant).",
                    "The mechanism, its accounting or the audit is wrong, and the proved epsilon "
                    "cannot be relied on until the cause is found.",
                    "Do not release under this mechanism; investigate and record the cause.",
                )
            )
    if not findings:
        findings.append(
            BoundaryFinding(
                "RB15",
                NOTE,
                _FIELD,
                f"A preregistered GDP audit of '{block.get('mechanism')}' is embedded "
                f"({len(block['cells'])} cell(s)), each audited value inside its ceiling, no "
                "violation claimed.",
                "It is evidence about the mechanism on a worst-case instance, not a measurement "
                "of this release's data; the block's `scope` field says so.",
                "None.",
            )
        )
    return findings
