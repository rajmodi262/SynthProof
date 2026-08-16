"""End-to-end tests for the CLI commands other than `run`.

`verify` is the reason this file exists. It is the command the README advertises as runnable
by a third party, and it carries the whole claim that a release can be checked without
trusting whoever produced it. Coverage analysis found its body had no direct test: `cli.py`
sat at 59%, with `keygen`, `verify`, `infer-schema` and `demo` exercised only by `--help`.

A verification command that is never tested against a TAMPERED sheet is not evidence of
anything, so most of what follows is tampering.
"""

import json

import numpy as np
import pandas as pd
import pytest
from click.testing import CliRunner

from synthproof.cli import main


@pytest.fixture()
def keys(tmp_path, monkeypatch):
    """A fresh keypair in an isolated directory, so tests never touch a real `.keys/`."""
    kd = tmp_path / "keys"
    monkeypatch.setenv("SYNTHPROOF_KEY_DIR", str(kd))
    r = CliRunner().invoke(main, ["keygen", "--key-dir", str(kd)])
    assert r.exit_code == 0, r.output
    return kd


@pytest.fixture()
def signed(tmp_path, keys):
    """A real signed data sheet, produced through the CLI rather than constructed."""
    rng = np.random.default_rng(0)
    n = 800
    csv = tmp_path / "in.csv"
    pd.DataFrame(
        {
            "age": rng.integers(18, 90, n),
            "hours": rng.integers(1, 60, n),
            "grp": rng.choice(list("abcd"), n),
            "label": rng.choice(["yes", "no"], n),
        }
    ).to_csv(csv, index=False)

    out = tmp_path / "sheet.json"
    r = CliRunner().invoke(
        main,
        ["run", "--input", str(csv), "--out", str(out), "--eps", "1.0", "--sign"],
    )
    assert r.exit_code == 0, r.output
    return out, keys / "synthproof_ed25519.pub"


# ------------------------------------------------------------------ keygen


def test_keygen_writes_a_usable_keypair(tmp_path):
    kd = tmp_path / "k"
    r = CliRunner().invoke(main, ["keygen", "--key-dir", str(kd)])
    assert r.exit_code == 0, r.output
    assert (kd / "synthproof_ed25519").exists()
    assert (kd / "synthproof_ed25519.pub").exists()


def test_keygen_refuses_to_clobber_an_existing_key_without_overwrite(tmp_path):
    """Replacing a key silently would invalidate every signature it ever made."""
    kd = tmp_path / "k"
    assert CliRunner().invoke(main, ["keygen", "--key-dir", str(kd)]).exit_code == 0
    before = (kd / "synthproof_ed25519").read_bytes()

    r = CliRunner().invoke(main, ["keygen", "--key-dir", str(kd)])
    assert r.exit_code != 0
    assert (kd / "synthproof_ed25519").read_bytes() == before, "the key was replaced anyway"


def test_keygen_overwrite_warns_that_signatures_become_unverifiable(tmp_path):
    kd = tmp_path / "k"
    CliRunner().invoke(main, ["keygen", "--key-dir", str(kd)])
    before = (kd / "synthproof_ed25519").read_bytes()
    r = CliRunner().invoke(main, ["keygen", "--key-dir", str(kd), "--overwrite"])
    assert r.exit_code == 0, r.output
    assert (kd / "synthproof_ed25519").read_bytes() != before


# ------------------------------------------------------------------ verify: the happy path


def test_verify_accepts_a_genuinely_signed_sheet(signed):
    sheet, pub = signed
    r = CliRunner().invoke(main, ["verify", str(sheet), "--pubkey", str(pub)])
    assert r.exit_code == 0, r.output
    assert "VERIFIED" in r.output


def test_verify_states_the_limit_of_what_it_proves(signed):
    """The command must not let a reader believe more than it establishes: it proves origin
    and integrity, not that the numbers are right."""
    sheet, pub = signed
    r = CliRunner().invoke(main, ["verify", str(sheet), "--pubkey", str(pub)])
    assert "does not prove the numbers in it are correct" in r.output


def test_verify_echoes_the_fields_a_reader_needs(signed):
    sheet, pub = signed
    r = CliRunner().invoke(main, ["verify", str(sheet), "--pubkey", str(pub)])
    for field in ("dataset", "mechanism", "eps proved", "eps audited", "ledger head"):
        assert field in r.output


# ------------------------------------------------------------------ verify: tampering


def _tamper(path, **changes):
    """Alters a field, asserting the value genuinely changed.

    Without this check a tamper test can pass for the wrong reason: setting a field to the
    value it already holds leaves the sheet byte-identical, so `verify` correctly accepts it
    and the test records a detection that never happened. Caught exactly that way — the first
    version set `total_audited_eps` to 0.0 on a sheet where it was already 0.0.
    """
    d = json.loads(path.read_text(encoding="utf-8"))
    for k, v in changes.items():
        assert k in d, f"{k!r} is not a field of the sheet; the test is checking nothing"
        assert d[k] != v, (
            f"{k!r} is already {v!r}, so this 'tamper' changes nothing and the test would "
            "pass without exercising the signature"
        )
    d.update(changes)
    path.write_text(json.dumps(d, indent=2), encoding="utf-8")


@pytest.mark.parametrize(
    "field,value",
    [
        ("total_proved_eps", 0.01),
        ("total_audited_eps", 3.14),
        ("num_rows", 999999),
        ("mechanism", "aim"),
        ("dataset_name", "something_else"),
        ("domain_source", "declared"),
        ("audit_ceiling", 99.0),
        ("unit_of_privacy", "user-level"),
    ],
)
def test_verify_rejects_a_sheet_with_any_altered_field(signed, field, value):
    """Every claim-bearing field must be covered by the signature.

    `domain_source` and `audit_ceiling` are in this list deliberately: a holder who could
    downgrade `inferred-nonprivate` to `declared`, or inflate the ceiling so a null audit
    looks informative, would be able to strip exactly the disclosures that were added to stop
    a reader being misled.
    """
    sheet, pub = signed
    _tamper(sheet, **{field: value})
    r = CliRunner().invoke(main, ["verify", str(sheet), "--pubkey", str(pub)])
    assert r.exit_code != 0, f"altering {field} was not detected"
    assert "FAILED" in r.output


def test_verify_rejects_a_sheet_signed_by_a_different_key(signed, tmp_path):
    """The attack the public key exists to stop: a valid signature from the wrong signer."""
    sheet, _ = signed
    other = tmp_path / "other"
    CliRunner().invoke(main, ["keygen", "--key-dir", str(other)])
    r = CliRunner().invoke(
        main, ["verify", str(sheet), "--pubkey", str(other / "synthproof_ed25519.pub")]
    )
    assert r.exit_code != 0
    assert "FAILED" in r.output


def test_verify_rejects_an_unsigned_sheet(tmp_path, keys):
    """An unsigned sheet is a record, not a proof, and must not pass."""
    rng = np.random.default_rng(1)
    n = 800
    csv = tmp_path / "u.csv"
    pd.DataFrame({"age": rng.integers(18, 90, n), "grp": rng.choice(list("abcd"), n)}).to_csv(
        csv, index=False
    )
    out = tmp_path / "unsigned.json"
    r = CliRunner().invoke(main, ["run", "--input", str(csv), "--out", str(out), "--eps", "1.0"])
    assert r.exit_code == 0, r.output

    r = CliRunner().invoke(
        main, ["verify", str(out), "--pubkey", str(keys / "synthproof_ed25519.pub")]
    )
    assert r.exit_code != 0
    assert "FAILED" in r.output


def test_verify_rejects_a_stripped_signature(signed):
    """Deleting the signature must fail, not be treated as 'nothing to check'."""
    sheet, pub = signed
    d = json.loads(sheet.read_text(encoding="utf-8"))
    d["signature"] = None
    sheet.write_text(json.dumps(d, indent=2), encoding="utf-8")
    r = CliRunner().invoke(main, ["verify", str(sheet), "--pubkey", str(pub)])
    assert r.exit_code != 0


def test_verify_fails_on_a_missing_file_without_a_traceback(tmp_path, keys):
    r = CliRunner().invoke(
        main,
        ["verify", str(tmp_path / "nope.json"), "--pubkey", str(keys / "synthproof_ed25519.pub")],
    )
    assert r.exit_code != 0
    assert "Traceback" not in r.output


# ------------------------------------------------------------------ infer-schema


def test_infer_schema_writes_a_schema_and_warns_that_it_leaks(tmp_path):
    """The bounds it produces are read from the data. If the warning ever goes missing, users
    will treat the output as safe to release against."""
    rng = np.random.default_rng(2)
    csv = tmp_path / "s.csv"
    pd.DataFrame({"age": rng.integers(18, 90, 300), "grp": rng.choice(list("abc"), 300)}).to_csv(
        csv, index=False
    )

    out = tmp_path / "schema.json"
    r = CliRunner().invoke(main, ["infer-schema", "--input", str(csv), "--out", str(out)])
    assert r.exit_code == 0, r.output
    assert out.exists()
    assert "leak" in r.output.lower()

    spec = json.loads(out.read_text(encoding="utf-8"))
    names = {c["name"] for c in spec["columns"]}
    assert names == {"age", "grp"}


def test_infer_schema_prints_to_stdout_when_no_out_given(tmp_path):
    rng = np.random.default_rng(3)
    csv = tmp_path / "s.csv"
    pd.DataFrame({"a": rng.integers(0, 5, 100), "b": rng.choice(["x", "y"], 100)}).to_csv(
        csv, index=False
    )
    r = CliRunner().invoke(main, ["infer-schema", "--input", str(csv)])
    assert r.exit_code == 0, r.output
    assert '"columns"' in r.output


# ------------------------------------------------------------------ demo / mechanisms


def test_demo_runs_end_to_end_and_announces_the_skipped_checks():
    """The demo bypasses admission control because the toy table is generated and below the
    row floor. It must say so — a demo that quietly takes a path real releases cannot take
    teaches the wrong thing."""
    r = CliRunner().invoke(main, ["demo", "--rows", "120", "--eps", "1.0"])
    assert r.exit_code == 0, r.output
    assert "SKIPPED" in r.output
    assert "R1" in r.output
    assert "PRIVACY DATA SHEET" in r.output


def test_mechanisms_lists_what_is_actually_available():
    r = CliRunner().invoke(main, ["mechanisms"])
    assert r.exit_code == 0
    assert "independent" in r.output and "pairwise" in r.output
