"""The provenance gate catches a number that no result supports, and the tree passes it.

A gate that has never been seen to fail proves nothing, so the first tests plant a fabricated
number in a copy of a real results document and require the gate to name it.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import build_results_docs as brd  # noqa: E402
from scripts import check_number_provenance as cnp  # noqa: E402

pytestmark = pytest.mark.skipif(
    shutil.which("git") is None or not (ROOT / ".git").exists(),
    reason="the gate reads tracked files through git",
)


def _doc(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "DOC.md"
    p.write_text(body, encoding="utf-8")
    return p


def test_a_number_from_the_declared_source_passes(tmp_path):
    cell = json.loads((ROOT / "results/auditor_comparison.json").read_text(encoding="utf-8"))
    real = f"{cell['cells'][0]['one_run_eps_mean']:.3f}"
    doc = _doc(tmp_path, f"<!-- provenance: results/auditor_comparison.json -->\nIt read {real}.\n")
    assert cnp.check([doc]) == {}


def test_a_fabricated_number_is_caught(tmp_path):
    doc = _doc(
        tmp_path,
        "<!-- provenance: results/auditor_comparison.json -->\nThe auditor certified 4.321.\n",
    )
    assert cnp.check([doc]) == {"DOC.md": [(2, "4.321")]}


def test_a_fabricated_number_planted_in_a_real_document_is_caught(tmp_path):
    src = (ROOT / "results/AUDITOR_COMPARISON.md").read_text(encoding="utf-8")
    doc = _doc(tmp_path, src + "\nOn a fresh run the one-run auditor certified 4.321.\n")
    assert "4.321" in [n for _, n in cnp.check([doc]).get("DOC.md", [])]


def test_a_negative_number_written_with_a_hyphen_is_checked(tmp_path):
    # It used to be skipped entirely, so a stale "-0.0829" in a table was never examined.
    doc = _doc(tmp_path, "<!-- provenance: results/auditor_comparison.json -->\nr = -0.8291\n")
    assert cnp.check([doc]) == {"DOC.md": [(2, "0.8291")]}


def test_a_declared_source_that_does_not_exist_fails(tmp_path):
    doc = _doc(tmp_path, "<!-- provenance: results/no_such_file.json -->\nr = 0.25\n")
    [(line, msg)] = cnp.check([doc])["DOC.md"]
    assert line == 0 and "declared source missing" in msg


def test_numbers_restated_from_a_generated_block_are_sourced(tmp_path):
    doc = _doc(
        tmp_path,
        "<!-- provenance: results/auditor_comparison.json -->\n"
        "<!-- BEGIN GENERATED: t -->\n| 0.8123 |\n<!-- END GENERATED: t -->\n"
        "As the table says, 0.8123.\n",
    )
    assert cnp.check([doc]) == {}


def test_an_allowlist_entry_without_a_reason_is_rejected(tmp_path, monkeypatch):
    bad = tmp_path / "allow.json"
    bad.write_text(json.dumps({"README.md": {"0.25": "  "}}), encoding="utf-8")
    monkeypatch.setattr(cnp, "ALLOWLIST", bad)
    with pytest.raises(SystemExit, match="no reason"):
        cnp.load_allowlist()


def test_every_tracked_results_document_passes():
    assert cnp.check() == {}


# ------------------------------------------------------------------ generated tables


def test_every_generated_table_matches_its_json():
    assert brd.build(check_only=True) == []


def test_a_stale_generated_table_is_detected(tmp_path, monkeypatch):
    doc = tmp_path / "results" / "X.md"
    doc.parent.mkdir()
    doc.write_text(
        "<!-- BEGIN GENERATED: t -->\n| stale |\n<!-- END GENERATED: t -->\n", encoding="utf-8"
    )
    monkeypatch.setattr(brd, "ROOT", tmp_path)
    monkeypatch.setattr(brd, "BLOCKS", [("results/X.md", "t", lambda: "| fresh |")])
    assert brd.build(check_only=True) == ["results/X.md:t"]
    assert "stale" in doc.read_text(encoding="utf-8")  # --check never writes
    brd.build(check_only=False)
    assert "fresh" in doc.read_text(encoding="utf-8")


def test_the_cli_passes_on_the_committed_tree():
    out = subprocess.run(
        [sys.executable, "scripts/check_number_provenance.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert out.returncode == 0, out.stdout + out.stderr
