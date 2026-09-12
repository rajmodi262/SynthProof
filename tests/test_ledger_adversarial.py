"""Adversarial tests against the ledger.

`tests/test_ledger.py` covers the happy path. This file assumes a MALICIOUS operator with
full write access to the SQLite file and knowledge of the source, but WITHOUT the signing
key — which is the only adversary worth designing against, since a careless one is caught by
almost anything.

Every test here corresponds to an attack that was actually executed against the running code.
"""

import sqlite3

import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519

from synthproof.ledger.ledger import Ledger
from synthproof.ledger.types import LedgerEntry

COLS = (
    "entry_id",
    "prev_hash",
    "hash",
    "timestamp",
    "dataset_id",
    "run_id",
    "mechanism_name",
    "sensitivity",
    "noise_scale",
    "eps_spent",
    "delta",
    "seed",
    "actor",
    "signature",
)


@pytest.fixture()
def ledger(tmp_path):
    """A file-backed ledger with a persistent key and four entries."""
    key = ed25519.Ed25519PrivateKey.generate()
    db = tmp_path / "ledger.db"
    led = Ledger(db_path=str(db), private_key=key)
    for i in range(4):
        led.append(
            LedgerEntry(
                entry_id=f"e{i}",
                prev_hash="",
                timestamp=f"2026-01-0{i + 1}T00:00:00",
                dataset_id="adult",
                run_id=f"r{i}",
                mechanism_name="gaussian",
                sensitivity=1.0,
                noise_scale=2.0,
                eps_spent=0.5,
                delta=1e-5,
                seed=i,
                actor="operator",
                signature="",
            )
        )
    return led, str(db)


def sql(db, *stmts):
    conn = sqlite3.connect(db)
    for s in stmts:
        conn.execute(s) if isinstance(s, str) else conn.execute(*s)
    conn.commit()
    conn.close()


def rows(db):
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    r = conn.execute("SELECT * FROM ledger_entries ORDER BY id ASC").fetchall()
    conn.close()
    return r


def test_an_untampered_ledger_verifies(ledger):
    led, _ = ledger
    ok, reason = led.verify_with_reason()
    assert ok, reason


# ------------------------------------------------------------------ truncation


def test_truncating_the_tail_is_detected(ledger):
    """REGRESSION (critical): hash chaining alone does NOT detect truncation — a shortened
    chain is still internally consistent. Before the signed head existed, deleting the last
    two entries left verify() == True, so an operator could delete the entries recording a
    budget overspend and still pass.
    """
    led, db = ledger
    sql(db, "DELETE FROM ledger_entries WHERE entry_id IN ('e2','e3')")
    ok, reason = led.verify_with_reason()
    assert not ok
    assert "count" in reason.lower(), reason


def test_truncation_reports_a_reason_that_names_the_failure_mode(ledger):
    """'Someone deleted entries' and 'someone edited an entry' need different responses."""
    led, db = ledger
    sql(db, "DELETE FROM ledger_entries WHERE entry_id='e3'")
    _, reason = led.verify_with_reason()
    assert "head commits to 4" in reason and "found 3" in reason, reason


def test_deleting_the_head_row_does_not_launder_a_truncation(ledger):
    """The obvious follow-up attack: drop the evidence that there was ever a head."""
    led, db = ledger
    sql(
        db,
        "DELETE FROM ledger_entries WHERE entry_id IN ('e2','e3')",
        "DELETE FROM ledger_head WHERE id=1",
    )
    ok, reason = led.verify_with_reason()
    assert not ok
    assert "head" in reason.lower(), reason


# ------------------------------------------------------------------ modification


def test_editing_a_field_is_detected(ledger):
    led, db = ledger
    sql(db, "UPDATE ledger_entries SET eps_spent=0.01 WHERE entry_id='e1'")
    assert not led.verify()


def test_editing_a_field_and_recomputing_the_stored_hash_is_still_detected(ledger):
    """The adversary knows the hash function. Only the Ed25519 signature stops this."""
    led, db = ledger
    r = rows(db)[1]
    forged = LedgerEntry(
        entry_id=r["entry_id"],
        prev_hash=r["prev_hash"],
        timestamp=r["timestamp"],
        dataset_id=r["dataset_id"],
        run_id=r["run_id"],
        mechanism_name=r["mechanism_name"],
        sensitivity=r["sensitivity"],
        noise_scale=r["noise_scale"],
        eps_spent=0.01,
        delta=r["delta"],
        seed=r["seed"],
        actor=r["actor"],
        signature=r["signature"],
    )
    sql(
        db,
        (
            "UPDATE ledger_entries SET eps_spent=?, hash=? WHERE entry_id='e1'",
            (0.01, forged.compute_hash()),
        ),
    )
    ok, reason = led.verify_with_reason()
    assert not ok
    assert "signature" in reason.lower() or "modified" in reason.lower(), reason


# ------------------------------------------------------------------ insertion / replay


def test_replaying_a_signed_entry_under_a_new_id_is_detected(ledger):
    """The UNIQUE constraint on entry_id blocks a verbatim duplicate, but that is a database
    accident, not a security property. Renaming the copy defeats it — the signature must be
    what actually stops the replay.
    """
    led, db = ledger
    r = rows(db)[1]
    vals = {k: r[k] for k in COLS}
    vals["entry_id"] = "e1-replay"
    sql(
        db,
        (
            # The column list is a module constant and every VALUE is a bound parameter.
            # This file's entire purpose is attacking the ledger's own database.
            f"INSERT INTO ledger_entries ({','.join(COLS)}) VALUES ({','.join('?' * 14)})",  # nosec B608
            tuple(vals[k] for k in COLS),
        ),
    )
    assert not led.verify()


def test_appending_a_forged_entry_and_rewriting_the_head_is_detected(ledger):
    """The strongest attack available without the key: append a well-formed entry and update
    the head to match. Forging the head signature is what the adversary cannot do."""
    led, db = ledger
    tip = rows(db)[-1]["hash"]
    evil = LedgerEntry(
        entry_id="evil",
        prev_hash=tip,
        timestamp="2026-01-09T00:00:00",
        dataset_id="adult",
        run_id="evil",
        mechanism_name="gaussian",
        sensitivity=1.0,
        noise_scale=2.0,
        eps_spent=0.0,
        delta=1e-5,
        seed=9,
        actor="attacker",
        signature="",
    )
    sql(
        db,
        (
            # The column list is a module constant and every VALUE is a bound parameter.
            # This file's entire purpose is attacking the ledger's own database.
            f"INSERT INTO ledger_entries ({','.join(COLS)}) VALUES ({','.join('?' * 14)})",  # nosec B608
            (
                "evil",
                evil.prev_hash,
                evil.compute_hash(),
                evil.timestamp,
                evil.dataset_id,
                evil.run_id,
                evil.mechanism_name,
                evil.sensitivity,
                evil.noise_scale,
                evil.eps_spent,
                evil.delta,
                evil.seed,
                evil.actor,
                "00" * 64,
            ),
        ),
        ("UPDATE ledger_head SET entry_count=5, tip_hash=? WHERE id=1", (evil.compute_hash(),)),
    )
    assert not led.verify()


def test_deleting_a_middle_entry_is_detected(ledger):
    led, db = ledger
    sql(db, "DELETE FROM ledger_entries WHERE entry_id='e1'")
    assert not led.verify()


def test_reordering_entries_is_detected(ledger):
    led, db = ledger
    sql(
        db,
        "UPDATE ledger_entries SET id=999 WHERE entry_id='e1'",
        "UPDATE ledger_entries SET id=998 WHERE entry_id='e2'",
        "UPDATE ledger_entries SET id=3 WHERE entry_id='e1'",
        "UPDATE ledger_entries SET id=2 WHERE entry_id='e2'",
    )
    assert not led.verify()


# ------------------------------------------------------------------ head invariants


def test_an_empty_ledger_verifies_without_a_head(tmp_path):
    """There is nothing to commit to, so absence of a head is not evidence of tampering."""
    led = Ledger(
        db_path=str(tmp_path / "empty.db"), private_key=ed25519.Ed25519PrivateKey.generate()
    )
    assert led.verify()


def test_the_head_tracks_the_tip_after_every_append(ledger):
    """If the head lagged, every legitimate append would look like tampering."""
    led, db = ledger
    for i in range(4, 7):
        led.append(
            LedgerEntry(
                entry_id=f"e{i}",
                prev_hash="",
                timestamp="2026-02-01T00:00:00",
                dataset_id="adult",
                run_id=f"r{i}",
                mechanism_name="gaussian",
                sensitivity=1.0,
                noise_scale=2.0,
                eps_spent=0.1,
                delta=1e-5,
                seed=i,
                actor="operator",
                signature="",
            )
        )
        assert led.verify(), f"verification broke after appending e{i}"
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    head = conn.execute("SELECT * FROM ledger_head WHERE id=1").fetchone()
    conn.close()
    assert head["entry_count"] == 7
    assert head["tip_hash"] == rows(db)[-1]["hash"]


def test_clearing_the_ledger_clears_the_head_too(ledger):
    """REGRESSION: adding the signed head broke `/api/ledger/reset`, which deleted only
    `ledger_entries`. That left a head committing to 3 entries over an empty table, so the
    demo's own reset was reported as a truncation attack. The head and the entries are one
    invariant and must be cleared together.
    """
    led, db = ledger
    assert led.verify()
    led.clear()
    ok, reason = led.verify_with_reason()
    assert ok, f"an emptied ledger must verify, got: {reason}"
    assert rows(db) == []


def test_a_cleared_ledger_can_be_appended_to_again(ledger):
    """The reset exists so the tamper demo can be run twice."""
    led, _ = ledger
    led.clear()
    led.append(
        LedgerEntry(
            entry_id="fresh",
            prev_hash="",
            timestamp="2026-03-01T00:00:00",
            dataset_id="adult",
            run_id="r",
            mechanism_name="gaussian",
            sensitivity=1.0,
            noise_scale=2.0,
            eps_spent=0.5,
            delta=1e-5,
            seed=0,
            actor="operator",
            signature="",
        )
    )
    assert led.verify()
