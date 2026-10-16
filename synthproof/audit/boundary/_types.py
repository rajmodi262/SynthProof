"""Finding severities, the finding and report types, and number parsing."""

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

LEAK = "leak"
UNVERIFIABLE = "unverifiable"
NOTE = "note"
_SEVERITY_ORDER = {LEAK: 0, UNVERIFIABLE: 1, NOTE: 2}

_HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")
_SOUND_DOMAIN_SOURCES = ("declared", "codebook", "charged")


@dataclass(frozen=True)
class BoundaryFinding:
    """One channel, what the artefact shows about it, and what to do."""

    code: str  # RB0..RB15
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


def _number(value: Any) -> Optional[float]:
    """A sheet field as a float, or None when it is absent or not a number.

    The checker reads untrusted artefacts, so a malformed field must become a finding, never a
    crash. bool is excluded: JSON true is not an epsilon.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)
