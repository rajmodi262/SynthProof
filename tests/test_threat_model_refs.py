"""Every test docs/threat_model.md cites as evidence must exist.

The table maps each threat to the test that fails if its mitigation is removed. A renamed or
deleted test would leave a mitigation claimed with nothing behind it -- the documentation
version of an unsourced number.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_every_cited_test_exists():
    doc = (ROOT / "docs" / "threat_model.md").read_text(encoding="utf-8")
    missing, cited = [], 0
    for row in doc.splitlines():
        current = None
        for m in re.finditer(r"(tests/[\w/]+\.py)|::(\w+)", row):
            if m.group(1):
                current = m.group(1)
                assert (ROOT / current).exists(), f"{current} does not exist"
                continue
            if current is None:
                continue
            cited += 1
            if f"def {m.group(2)}(" not in (ROOT / current).read_text(encoding="utf-8"):
                missing.append(f"{current}::{m.group(2)}")
    assert cited >= 20, "the threat table should cite its evidence"
    assert not missing, f"threat_model.md cites tests that do not exist: {missing}"
