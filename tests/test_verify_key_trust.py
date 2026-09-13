"""Tests for closing the verification key-trust gap (T2).

Closing the gap between:
- a valid signature (integrity: the sheet was not edited after signing)
- publisher authentication (provenance: the key that signed it is trusted)

Verifying against an embedded key proves only that the sheet signed itself.
"""

import hashlib
from pathlib import Path

import pytest
from click.testing import CliRunner
from fastapi.testclient import TestClient

from synthproof.api.main import app
from synthproof.capsule.generator import generate_capsule_html, verify_capsule
from synthproof.cli import main
from synthproof.frontier.certificate import PrivacyDataSheet
from synthproof.ledger import signing


def _make_sheet(name: str = "KeyTrustTest", proved_eps: float = 1.0) -> PrivacyDataSheet:
    return PrivacyDataSheet(
        dataset_name=name,
        num_rows=100,
        target_column="label",
        total_proved_eps=proved_eps,
        delta=1e-5,
        total_audited_eps=0.0,
        audit_ceiling=2.5,
        mechanism="pairwise",
        mechanism_available=True,
        seed=42,
        frontier_curve=[],
        ledger_hash="a" * 64,
    )


def test_sheet_signed_key_a_verified_no_key_embedded(tmp_path: Path):
    """A sheet signed with key A, verified with no key -> embedded, not authenticated."""
    sk_a, pk_a = signing.generate_keypair(key_dir=tmp_path / "keys_a")
    sheet = _make_sheet()
    signing.sign_datasheet(sheet, key_path=sk_a)

    capsule_path = tmp_path / "capsule_a.html"
    generate_capsule_html(sheet, [{"label": 1}], output_path=capsule_path)

    report = verify_capsule(capsule_path)
    assert report["verified"] is True
    assert report["key_source"] == "embedded"
    assert report["publisher_authenticated"] is False

    key_obj = signing.load_public_key(pk_a)
    raw_pk = key_obj.public_bytes(
        encoding=signing.serialization.Encoding.Raw,
        format=signing.serialization.PublicFormat.Raw,
    )
    expected_fp = hashlib.sha256(raw_pk).hexdigest()[:16]
    assert report["key_fingerprint"] == expected_fp


def test_sheet_signed_key_a_verified_key_a_supplied(tmp_path: Path):
    """Same sheet verified with key A supplied -> supplied, publisher_authenticated True."""
    sk_a, pk_a = signing.generate_keypair(key_dir=tmp_path / "keys_a")
    sheet = _make_sheet()
    signing.sign_datasheet(sheet, key_path=sk_a)

    capsule_path = tmp_path / "capsule_a.html"
    generate_capsule_html(sheet, [{"label": 1}], output_path=capsule_path)

    report = verify_capsule(capsule_path, key_path=pk_a)
    assert report["verified"] is True
    assert report["key_source"] == "supplied"
    assert report["publisher_authenticated"] is True


def test_sheet_signed_key_a_verified_key_b_supplied_fails(tmp_path: Path):
    """Same sheet verified with key B supplied -> verification fails."""
    sk_a, pk_a = signing.generate_keypair(key_dir=tmp_path / "keys_a")
    _, pk_b = signing.generate_keypair(key_dir=tmp_path / "keys_b")
    sheet = _make_sheet()
    signing.sign_datasheet(sheet, key_path=sk_a)

    capsule_path = tmp_path / "capsule_a.html"
    generate_capsule_html(sheet, [{"label": 1}], output_path=capsule_path)

    with pytest.raises(signing.SignatureError) as exc_info:
        verify_capsule(capsule_path, key_path=pk_b)
    assert "different key" in str(exc_info.value).lower()


def test_forgery_attacker_key_signed_sheet(tmp_path: Path):
    """The forgery case, as its own test: generate an attacker key, sign a sheet claiming

    eps = 0.01, verify with no key -> assert publisher_authenticated is False.
    This test proves the verification key-trust gap is closed.
    """
    sk_attacker, _ = signing.generate_keypair(key_dir=tmp_path / "attacker_keys")
    sheet = _make_sheet(name="ForgedSmallEps", proved_eps=0.01)
    signing.sign_datasheet(sheet, key_path=sk_attacker)

    capsule_path = tmp_path / "forged_capsule.html"
    generate_capsule_html(sheet, [{"label": 0}], output_path=capsule_path)

    report = verify_capsule(capsule_path)
    assert report["verified"] is True
    assert report["key_source"] == "embedded"
    assert report["publisher_authenticated"] is False


def test_api_verify_certificate_endpoint(tmp_path: Path):
    """API: POST /api/certificate/verify with and without public_key."""
    client = TestClient(app)
    sk, pk = signing.generate_keypair(key_dir=tmp_path)
    sheet = _make_sheet()
    signing.sign_datasheet(sheet, key_path=sk)
    sheet_dict = sheet.to_dict()

    # 1. Without public_key -> embedded, unauthenticated
    resp_embedded = client.post("/api/certificate/verify", json={"sheet": sheet_dict})
    assert resp_embedded.status_code == 200, resp_embedded.text
    data_emb = resp_embedded.json()
    assert data_emb["signature_valid"] is True
    assert data_emb["publisher_authenticated"] is False
    assert data_emb["key_source"] == "embedded"
    assert len(data_emb["key_fingerprint"]) == 16

    # 2. With matching public_key -> supplied, authenticated
    pk_hex = signing.public_key_hex(signing.load_public_key(pk))
    resp_supplied = client.post(
        "/api/certificate/verify",
        json={"sheet": sheet_dict, "public_key": pk_hex},
    )
    assert resp_supplied.status_code == 200, resp_supplied.text
    data_sup = resp_supplied.json()
    assert data_sup["signature_valid"] is True
    assert data_sup["publisher_authenticated"] is True
    assert data_sup["key_source"] == "supplied"
    assert data_sup["key_fingerprint"] == data_emb["key_fingerprint"]

    # 3. With mismatched public_key -> signature_valid False
    _, pk_other = signing.generate_keypair(key_dir=tmp_path / "other")
    pk_other_hex = signing.public_key_hex(signing.load_public_key(pk_other))
    resp_mismatch = client.post(
        "/api/certificate/verify",
        json={"sheet": sheet_dict, "public_key": pk_other_hex},
    )
    assert resp_mismatch.status_code == 200
    data_mismatch = resp_mismatch.json()
    assert data_mismatch["signature_valid"] is False
    assert data_mismatch["publisher_authenticated"] is False
    assert "different key" in (data_mismatch["error"] or "").lower()


def test_cli_verify_capsule_key_trust(tmp_path: Path):
    """CLI: verify-capsule without --key-path prints not-authenticated warning and exits 0;

    with a wrong --key-path exits 1.
    """
    sk, pk = signing.generate_keypair(key_dir=tmp_path / "good_keys")
    _, pk_wrong = signing.generate_keypair(key_dir=tmp_path / "wrong_keys")

    sheet = _make_sheet()
    signing.sign_datasheet(sheet, key_path=sk)

    capsule_path = tmp_path / "cli_test_capsule.html"
    generate_capsule_html(sheet, [{"label": 1}], output_path=capsule_path)

    runner = CliRunner()

    # Without --key-path: exits 0, warning printed
    res_no_key = runner.invoke(main, ["verify-capsule", "--capsule", str(capsule_path)])
    assert res_no_key.exit_code == 0, res_no_key.output
    assert "ED25519 SIGNATURE AUTHENTIC" in res_no_key.output
    assert "Not checked against a publisher key" in res_no_key.output
    assert "fingerprint" in res_no_key.output

    # With matching --key-path: exits 0, authenticated printed
    res_with_key = runner.invoke(
        main,
        ["verify-capsule", "--capsule", str(capsule_path), "--key-path", str(pk)],
    )
    assert res_with_key.exit_code == 0, res_with_key.output
    assert "Authenticated against supplied publisher key" in res_with_key.output

    # With wrong --key-path: exits 1
    res_wrong_key = runner.invoke(
        main,
        ["verify-capsule", "--capsule", str(capsule_path), "--key-path", str(pk_wrong)],
    )
    assert res_wrong_key.exit_code == 1, res_wrong_key.output
    assert "VERIFICATION FAILED" in res_wrong_key.output
