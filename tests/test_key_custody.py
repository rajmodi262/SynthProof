"""Key custody (W7): the signing key encrypted at rest, and rotation that keeps old signatures
verifiable and never launders a tampered ledger."""

import json

import pytest
from click.testing import CliRunner

from synthproof.cli import main
from synthproof.ledger import signing
from synthproof.ledger.ledger import Ledger
from synthproof.ledger.types import LedgerEntry


@pytest.fixture
def keys(tmp_path, monkeypatch):
    monkeypatch.setenv("SYNTHPROOF_KEY_DIR", str(tmp_path / "keys"))
    monkeypatch.delenv("SYNTHPROOF_KEY_PASSPHRASE", raising=False)
    monkeypatch.delenv("SYNTHPROOF_KEY_PASSPHRASE_FILE", raising=False)
    return tmp_path / "keys"


def _entry(i):
    return LedgerEntry(
        dataset_id="d", run_id=f"r{i}", mechanism_name="independent", eps_spent=1.0, delta=1e-5
    )


# ---------------------------------------------------------------- encryption at rest


def test_with_a_passphrase_the_key_on_disk_is_encrypted(keys, monkeypatch):
    monkeypatch.setenv("SYNTHPROOF_KEY_PASSPHRASE", "correct horse battery staple")
    priv, _ = signing.generate_keypair()
    assert b"ENCRYPTED PRIVATE KEY" in priv.read_bytes()
    assert signing.load_private_key(priv) is not None


def test_an_encrypted_key_will_not_load_without_its_passphrase(keys, monkeypatch):
    monkeypatch.setenv("SYNTHPROOF_KEY_PASSPHRASE", "right")
    priv, _ = signing.generate_keypair()
    monkeypatch.delenv("SYNTHPROOF_KEY_PASSPHRASE")
    with pytest.raises(signing.SignatureError, match="encrypted"):
        signing.load_private_key(priv)
    monkeypatch.setenv("SYNTHPROOF_KEY_PASSPHRASE", "wrong")
    with pytest.raises(signing.SignatureError, match="wrong passphrase"):
        signing.load_private_key(priv)


def test_the_passphrase_can_come_from_a_file(keys, tmp_path, monkeypatch):
    secret = tmp_path / "pass.txt"
    secret.write_text("from-a-docker-secret\n", encoding="utf-8")
    monkeypatch.setenv("SYNTHPROOF_KEY_PASSPHRASE_FILE", str(secret))
    priv, _ = signing.generate_keypair()
    assert b"ENCRYPTED" in priv.read_bytes()
    assert signing.load_private_key(priv) is not None


def test_without_a_passphrase_keys_stay_unencrypted_as_before(keys):
    priv, _ = signing.generate_keypair()
    assert b"ENCRYPTED" not in priv.read_bytes()


# ---------------------------------------------------------------- rotation


def test_rotation_keeps_old_signatures_verifiable_and_destroys_the_old_private_key(keys):
    signing.generate_keypair()
    old_pub = signing.load_public_key()
    old_fp, new_fp = signing.rotate_keypair()
    assert old_fp != new_fp
    retired = keys / "retired" / f"{old_fp}.pub"
    assert retired.exists()
    assert signing.key_fingerprint(signing.load_public_key(retired)) == old_fp
    assert signing.key_fingerprint(old_pub) == old_fp
    assert not list((keys / "retired").glob("*_ed25519"))  # no private key retained
    log = [json.loads(line) for line in (keys / "ROTATIONS.jsonl").read_text().splitlines()]
    assert log[-1]["retired"] == old_fp and log[-1]["current"] == new_fp


def test_a_ledger_rotated_to_a_new_key_still_verifies(tmp_path, keys):
    signing.generate_keypair()
    db = str(tmp_path / "l.db")
    old_key = signing.load_private_key()
    led = Ledger(db_path=db, private_key=old_key)
    for i in range(3):
        led.append(_entry(i))
    hashes = [e.compute_hash() for e in led.get_entries()]
    signing.rotate_keypair()
    new_key = signing.load_private_key()
    led.rotate_key(new_key)
    assert led.verify()
    # A fresh process with only the NEW key verifies it; the chain itself is unchanged.
    reopened = Ledger(db_path=db, private_key=new_key)
    assert reopened.verify(), reopened.verify_with_reason()
    assert [e.compute_hash() for e in reopened.get_entries()] == hashes


def test_rotation_refuses_to_launder_a_tampered_ledger(tmp_path, keys):
    signing.generate_keypair()
    db = str(tmp_path / "l.db")
    led = Ledger(db_path=db, private_key=signing.load_private_key())
    led.append(_entry(0))
    led.append(_entry(1))
    with led._get_conn() as conn:
        conn.execute("UPDATE ledger_entries SET eps_spent = 0.01 WHERE run_id = 'r0'")
    assert not led.verify()
    with pytest.raises(ValueError, match="does not verify"):
        led.rotate_key(signing.load_private_key())


def test_the_cli_rotates_the_key_and_re_signs_the_ledger(tmp_path, keys):
    runner = CliRunner()
    assert runner.invoke(main, ["keygen"]).exit_code == 0
    db = str(tmp_path / "l.db")
    led = Ledger(db_path=db, private_key=signing.load_private_key())
    led.append(_entry(0))
    r = runner.invoke(main, ["keygen", "--rotate", "--ledger", db])
    assert r.exit_code == 0, r.output
    assert "Re-signed 1 ledger entries" in r.output
    assert Ledger(db_path=db, private_key=signing.load_private_key()).verify()


def test_ledger_without_rotate_is_a_usage_error(tmp_path, keys):
    db = tmp_path / "l.db"
    db.write_bytes(b"")
    r = CliRunner().invoke(main, ["keygen", "--ledger", str(db)])
    assert r.exit_code != 0 and "--rotate" in r.output
