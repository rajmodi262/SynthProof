"""Unit tests for append-only Ledger and Allocator."""

import pytest

from synthproof.ledger.allocator import Allocator
from synthproof.ledger.ledger import Ledger
from synthproof.ledger.types import LedgerEntry


def test_ledger_append_and_verify():
    ledger = Ledger(db_path=":memory:")
    assert ledger.verify() is True

    entry1 = LedgerEntry(dataset_id="UCI_Adult", eps_spent=0.5, mechanism_name="gaussian")
    signed1 = ledger.append(entry1)

    assert signed1.prev_hash == "0" * 64
    assert len(signed1.signature) > 0
    assert ledger.verify() is True

    entry2 = LedgerEntry(dataset_id="UCI_Adult", eps_spent=1.0, mechanism_name="laplace")
    signed2 = ledger.append(entry2)

    assert signed2.prev_hash == signed1.compute_hash()
    assert ledger.verify() is True


def test_ledger_tamper_mutation_fails_verification():
    ledger = Ledger(db_path=":memory:")
    e1 = ledger.append(LedgerEntry(eps_spent=0.5))
    e2 = ledger.append(LedgerEntry(eps_spent=1.0))
    assert e2.prev_hash == e1.compute_hash()
    assert ledger.verify() is True

    # Mutate eps_spent of e1 in SQLite directly
    conn = ledger._get_conn()
    conn.execute("UPDATE ledger_entries SET eps_spent = 99.0 WHERE entry_id = ?", (e1.entry_id,))
    conn.commit()

    assert ledger.verify() is False


def test_ledger_tamper_deletion_fails_verification():
    ledger = Ledger(db_path=":memory:")
    e1 = ledger.append(LedgerEntry(eps_spent=0.5))
    e2 = ledger.append(LedgerEntry(eps_spent=1.0))
    assert e2.prev_hash == e1.compute_hash()
    assert ledger.verify() is True

    # Delete e1 from SQLite
    conn = ledger._get_conn()
    conn.execute("DELETE FROM ledger_entries WHERE entry_id = ?", (e1.entry_id,))
    conn.commit()

    assert ledger.verify() is False


def test_allocator_uniform():
    items = ["age", "income", "education"]
    alloc = Allocator.allocate_uniform(1.5, items)
    assert len(alloc) == 3
    assert alloc["age"] == pytest.approx(0.5)
    assert sum(alloc.values()) == pytest.approx(1.5)


def test_allocator_weighted():
    weights = {"age": 2.0, "income": 3.0, "education": 0.0}
    alloc = Allocator.allocate_weighted(1.0, weights)
    assert alloc["age"] == pytest.approx(0.4)
    assert alloc["income"] == pytest.approx(0.6)
    assert alloc["education"] == pytest.approx(0.0)
    assert sum(alloc.values()) == pytest.approx(1.0)
