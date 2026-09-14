"""Tests that generated Bank Marketing tables match results/bank/BANK_MARKETING.md.

Pinning generated tables ensures that typed or stale values cannot silently persist.
If this test fails, re-run:
    python scripts/compare_bank_full.py --write
"""

from scripts.compare_bank_full import BEGIN_MARKER, END_MARKER, ROOT, generate_bank_tables


def test_bank_tables_match_committed_file():
    bank_md_path = ROOT / "results" / "bank" / "BANK_MARKETING.md"
    assert bank_md_path.exists(), f"Missing {bank_md_path}"

    text = bank_md_path.read_text(encoding="utf-8")
    assert BEGIN_MARKER in text, f"Missing {BEGIN_MARKER} in {bank_md_path}"
    assert END_MARKER in text, f"Missing {END_MARKER} in {bank_md_path}"

    start_idx = text.index(BEGIN_MARKER)
    end_idx = text.index(END_MARKER) + len(END_MARKER)
    file_block = text[start_idx:end_idx]

    expected_block = generate_bank_tables(ROOT)

    assert file_block == expected_block, (
        f"Generated table block in {bank_md_path} is stale or modified.\n"
        "To update it from the committed results JSON, run:\n"
        "    python scripts/compare_bank_full.py --write"
    )
