"""The GDP audit inside the signed sheet (W9), and boundary check RB15 that reads it back."""

import hashlib
import json

import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519

from synthproof.audit.boundary import audit_sheet
from synthproof.audit.boundary._types import LEAK, NOTE, UNVERIFIABLE
from synthproof.audit.mechanism_audit import SCOPE, mechanism_audit_for
from synthproof.frontier.sheet import PrivacyDataSheet
from synthproof.ledger import signing

CELL = {
    "mechanism": "pairwise",
    "target_eps": 1.0,
    "proved_eps": 0.9999,
    "delta": 0.01,
    "runs_per_world": 4000,
    "bounded_per_world": 1000,
    "alpha": 0.05,
    "mu_emp": 0.2,
    "eps_emp": 0.2632,
    "ceiling_at_this_n": 5.36,
    "eps_ceiling_at_this_n": 26.0,
    "violation_flagged": False,
    "violation_claimed": False,
    "preregistration_sha256": "a" * 64,
    "verdict": "AUDIT INFORMATIVE.",
}


def _write(tmp_path, name, cell):
    p = tmp_path / name
    p.write_text(json.dumps(cell), encoding="utf-8")
    return p


def test_no_results_means_null_not_a_made_up_block(tmp_path):
    assert mechanism_audit_for("pairwise", tmp_path / "absent") is None
    assert mechanism_audit_for("pairwise", tmp_path) is None


def test_the_block_copies_each_cell_verbatim_and_hashes_its_file(tmp_path):
    p = _write(tmp_path, "pairwise_eps1.json", CELL)
    _write(tmp_path, "pairwise_eps4.json", {**CELL, "target_eps": 4.0})
    block = mechanism_audit_for("pairwise", tmp_path)
    assert block["mechanism"] == "pairwise" and block["scope"] == SCOPE
    assert [c["target_eps"] for c in block["cells"]] == [1.0, 4.0]
    first = block["cells"][0]
    assert first["eps_emp"] == CELL["eps_emp"] and first["mu_emp"] == CELL["mu_emp"]
    assert first["result_sha256"] == hashlib.sha256(p.read_bytes()).hexdigest()
    assert "verdict" not in first  # only the listed numeric fields travel


def test_a_cell_not_run_under_the_preregistration_is_not_embedded(tmp_path):
    _write(tmp_path, "pairwise_eps1.json", {**CELL, "preregistration_sha256": None})
    assert mechanism_audit_for("pairwise", tmp_path) is None


def test_another_mechanisms_cell_is_never_picked_up(tmp_path):
    _write(tmp_path, "pairwise_eps1.json", {**CELL, "mechanism": "aim"})
    assert mechanism_audit_for("pairwise", tmp_path) is None


def _sheet(**over):
    base = {"mechanism": "pairwise", "evaluation_privacy": "x"}
    return {**base, **over}


def _rb15(sheet):
    return [f for f in audit_sheet(sheet).findings if f.code == "RB15"]


def test_rb15_is_silent_on_a_sheet_without_an_audit():
    assert _rb15(_sheet()) == []


def test_rb15_notes_a_clean_audit(tmp_path):
    _write(tmp_path, "pairwise_eps1.json", CELL)
    (f,) = _rb15(_sheet(mechanism_audit=mechanism_audit_for("pairwise", tmp_path)))
    assert f.severity == NOTE and "not a measurement of this release" in f.consequence


def test_rb15_rejects_an_audit_of_a_different_mechanism(tmp_path):
    _write(tmp_path, "aim_eps1.json", {**CELL, "mechanism": "aim"})
    (f,) = _rb15(_sheet(mechanism_audit=mechanism_audit_for("aim", tmp_path)))
    assert f.severity == UNVERIFIABLE and "different mechanism" in f.consequence


def test_rb15_rejects_a_value_above_its_own_ceiling(tmp_path):
    _write(tmp_path, "pairwise_eps1.json", {**CELL, "eps_emp": 30.0})
    (f,) = _rb15(_sheet(mechanism_audit=mechanism_audit_for("pairwise", tmp_path)))
    assert f.severity == UNVERIFIABLE


def test_rb15_reports_a_claimed_violation_as_a_leak(tmp_path):
    _write(tmp_path, "pairwise_eps1.json", {**CELL, "violation_claimed": True})
    (f,) = _rb15(_sheet(mechanism_audit=mechanism_audit_for("pairwise", tmp_path)))
    assert f.severity == LEAK


def test_the_audit_block_is_covered_by_the_signature(tmp_path):
    _write(tmp_path, "pairwise_eps1.json", CELL)
    key = ed25519.Ed25519PrivateKey.generate()
    sheet = PrivacyDataSheet(
        dataset_name="t",
        num_rows=100,
        target_column="y",
        total_proved_eps=1.0,
        delta=1e-5,
        total_audited_eps=0.0,
        mechanism="pairwise",
        mechanism_available=True,
        seed=None,
        frontier_curve=[],
        ledger_hash="a" * 64,
        mechanism_audit=mechanism_audit_for("pairwise", tmp_path),
    )
    signing.sign_datasheet(sheet, private_key=key)
    signed = sheet.to_dict()
    assert signing.verify_datasheet(signed, public_key=key.public_key())
    signed["mechanism_audit"]["cells"][0]["eps_emp"] = 0.0
    with pytest.raises(signing.SignatureError):
        signing.verify_datasheet(signed, public_key=key.public_key())
