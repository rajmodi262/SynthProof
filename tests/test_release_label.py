"""Conformance runner (scripts/validate_release_label.py) — the executable definition of the DP
Release Label spec (docs/design/DP_RELEASE_LABEL_SPEC.md).

Each verdict has a reintroduction negative control (project standard): a conformant label, then
the same label perturbed on exactly one axis (leak / broken signature / incoherent range /
unpinned key) to prove the runner catches that one thing and nothing masks it.
"""

import json

from scripts import validate_release_label as vrl
from synthproof.ledger import signing


def _sign(sheet: dict, key) -> dict:
    """Attach a real Ed25519 signature over the canonical payload, as the emitter does."""
    sheet = dict(sheet)
    sheet.pop("signature", None)
    sheet.pop("public_key", None)
    sheet["signature"] = key.sign(signing.canonical_sheet_payload(sheet)).hex()
    sheet["public_key"] = signing.public_key_hex(key.public_key())
    return sheet


def _clean_sheet() -> dict:
    """A boundary-clean label: no seed, declared count, no fingerprint, labelled eval, sound
    domain/discretization, coherent operating range (audited <= ceiling, ceiling >= proved)."""
    return {
        "dataset_name": "adult-demo",
        "mechanism": "aim",
        "delta": 1e-5,
        "total_proved_eps": 1.0,
        "total_audited_eps": 0.0,
        "audit_ceiling": 2.97,
        "audit_estimator": "steinke-2023",
        "audit_budget": 60,
        "audit_alpha": 0.05,
        "num_rows": 6000,
        "release_rows_source": "declared",
        "domain_source": "declared",
        "contribution_bound": 1,
        "evaluation": {"corr_err": 0.01},
        "evaluation_privacy": "outside-epsilon",
        "unit_of_privacy": "one row",
        "deployment_model": "central",
        "discretization_source": "uniform-public",
    }


def _keypair(tmp_path):
    signing.generate_keypair(key_dir=tmp_path / "keys", overwrite=True)
    priv = signing.load_private_key(tmp_path / "keys" / signing.PRIVATE_KEY_NAME)
    return priv, tmp_path / "keys" / signing.PUBLIC_KEY_NAME


def test_clean_signed_pinned_is_conformant(tmp_path):
    priv, pub = _keypair(tmp_path)
    doc = _sign(_clean_sheet(), priv)
    result = vrl.validate(doc, pub)
    assert result["verdict"] == "conformant"
    assert result["exit_code"] == 0
    assert result["checks"]["signature"]["tone"] == vrl.OK
    assert result["checks"]["boundary"]["tone"] == vrl.OK


def test_leak_is_non_conformant(tmp_path):
    """REINTRODUCE a leak: publish the run seed. RB1 must flag it -> exit 1, even though the
    signature and range are fine."""
    priv, pub = _keypair(tmp_path)
    sheet = _clean_sheet()
    sheet["seed"] = 123456789  # the one perturbation
    doc = _sign(sheet, priv)
    result = vrl.validate(doc, pub)
    assert result["verdict"] == "non-conformant"
    assert result["exit_code"] == 1
    assert result["checks"]["boundary"]["tone"] == vrl.FAIL
    assert any(f["code"] == "RB1" for f in result["boundary_findings"])


def test_tampered_signature_is_non_conformant(tmp_path):
    """REINTRODUCE tampering: sign, then edit a covered field. The signature must not verify."""
    priv, pub = _keypair(tmp_path)
    doc = _sign(_clean_sheet(), priv)
    doc["total_proved_eps"] = 99.0  # altered after signing
    result = vrl.validate(doc, pub)
    assert result["verdict"] == "non-conformant"
    assert result["exit_code"] == 1
    assert result["checks"]["signature"]["tone"] == vrl.FAIL


def test_incoherent_range_is_non_conformant(tmp_path):
    """REINTRODUCE an incoherent range: audited eps above the audit ceiling is impossible."""
    priv, pub = _keypair(tmp_path)
    sheet = _clean_sheet()
    sheet["total_audited_eps"] = 5.0  # > ceiling 2.97
    doc = _sign(sheet, priv)
    result = vrl.validate(doc, pub)
    assert result["verdict"] == "non-conformant"
    assert result["exit_code"] == 1
    assert result["checks"]["operating_range"]["tone"] == vrl.FAIL


def test_unsigned_is_non_conformant(tmp_path):
    """An unsigned label is not conformant even if boundary-clean: spec 4.2a needs a signature."""
    _priv, pub = _keypair(tmp_path)
    result = vrl.validate(_clean_sheet(), pub)  # never signed
    assert result["exit_code"] == 1
    assert result["checks"]["signature"]["tone"] == vrl.FAIL


def test_unpinned_signature_is_not_fully_checked(tmp_path):
    """A valid signature with NO pinned key is self-consistent but untrusted -> exit 2, never 0.
    A sheet that carries its own key proves only that it signed itself."""
    priv, _pub = _keypair(tmp_path)
    doc = _sign(_clean_sheet(), priv)
    result = vrl.validate(doc, pubkey=None)
    assert result["verdict"] == "not-fully-checked"
    assert result["exit_code"] == 2
    assert result["checks"]["signature"]["tone"] == vrl.WARN


def test_uninformative_audit_is_not_fully_checked(tmp_path):
    """Ceiling below proved eps: the audit could not have detected the proved budget, so a small
    audited eps is not reassurance. Conformance is not failed, but it is not a clean pass."""
    priv, pub = _keypair(tmp_path)
    sheet = _clean_sheet()
    sheet["audit_ceiling"] = 0.5  # < proved 1.0
    doc = _sign(sheet, priv)
    result = vrl.validate(doc, pub)
    assert result["exit_code"] == 2
    assert result["checks"]["operating_range"]["tone"] == vrl.WARN


def test_json_render_is_valid_json(tmp_path):
    priv, pub = _keypair(tmp_path)
    doc = _sign(_clean_sheet(), priv)
    result = vrl.validate(doc, pub)
    # the CLI emits json.dumps(result); make sure it round-trips
    assert json.loads(json.dumps(result))["verdict"] == "conformant"
