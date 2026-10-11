"""A file-backed API ledger must still verify after the service restarts.

The API built its ledger with a fresh in-memory signing key on every start. On a file-backed
database that made the stored head signature unverifiable after any restart, so the one mode
meant to be durable reported itself broken. `_ledger_key` keeps the key in SYNTHPROOF_KEY_DIR.
"""

from synthproof.api.state import _ledger_key
from synthproof.ledger.ledger import Ledger
from synthproof.ledger.types import LedgerEntry


def _entry(i: int) -> LedgerEntry:
    return LedgerEntry(
        dataset_id="d", run_id=f"r{i}", mechanism_name="independent", eps_spent=1.0, delta=1e-5
    )


def test_a_file_backed_ledger_verifies_across_a_restart(tmp_path, monkeypatch):
    monkeypatch.setenv("SYNTHPROOF_KEY_DIR", str(tmp_path / "keys"))
    db = str(tmp_path / "ledger.db")

    first = Ledger(db_path=db, private_key=_ledger_key(db))
    first.append(_entry(0))
    assert first.verify()

    # A restart: a new process builds the ledger again from the same file and key directory.
    second = Ledger(db_path=db, private_key=_ledger_key(db))
    assert second.verify(), second.verify_with_reason()
    second.append(_entry(1))
    assert second.verify()


def test_the_old_behaviour_fails_which_is_why_the_key_is_persisted(tmp_path):
    db = str(tmp_path / "ledger.db")
    Ledger(db_path=db).append(_entry(0))
    assert not Ledger(db_path=db).verify()


def test_an_in_memory_ledger_still_gets_an_ephemeral_key():
    assert _ledger_key(":memory:") is None
