"""Append-only cryptographic Privacy Budget Ledger with SHA-256 hash chaining and Ed25519 signatures."""

import sqlite3
from typing import List, Optional, Tuple

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

from synthproof.ledger.types import LedgerEntry


class LedgerVerificationError(Exception):
    """Raised when ledger tamper verification fails."""
    pass


class Ledger:
    """Append-only database with cryptographic SHA-256 hash chaining and Ed25519 signature checks."""

    def __init__(self, db_path: str = ":memory:", private_key: Optional[ed25519.Ed25519PrivateKey] = None):
        self.db_path = db_path
        self._private_key = private_key or ed25519.Ed25519PrivateKey.generate()
        self._public_key = self._private_key.public_key()
        if self.db_path == ":memory:":
            self._conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        else:
            self._conn = None
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn:
            return self._conn
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ledger_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id TEXT UNIQUE NOT NULL,
                prev_hash TEXT NOT NULL,
                hash TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                dataset_id TEXT NOT NULL,
                run_id TEXT NOT NULL,
                mechanism_name TEXT NOT NULL,
                sensitivity REAL NOT NULL,
                noise_scale REAL NOT NULL,
                eps_spent REAL NOT NULL,
                delta REAL NOT NULL,
                seed INTEGER NOT NULL,
                actor TEXT NOT NULL,
                signature TEXT NOT NULL
            )
        """)
        conn.commit()
        if not self._conn:
            conn.close()

    def get_latest_hash(self) -> str:
        """Returns hash of the most recent ledger entry, or genesis '0'*64 if empty."""
        conn = self._get_conn()
        row = conn.execute("SELECT hash FROM ledger_entries ORDER BY id DESC LIMIT 1").fetchone()
        res = row["hash"] if row else "0" * 64
        if not self._conn:
            conn.close()
        return res

    def sign_entry(self, entry: LedgerEntry) -> str:
        """Signs the canonical bytes of entry using Ed25519 private key."""
        sig_bytes = self._private_key.sign(entry.canonical_bytes())
        return sig_bytes.hex()

    def verify_entry_signature(self, entry: LedgerEntry, signature_hex: str) -> bool:
        """Verifies Ed25519 signature against entry canonical bytes."""
        try:
            sig_bytes = bytes.fromhex(signature_hex)
            self._public_key.verify(sig_bytes, entry.canonical_bytes())
            return True
        except Exception:
            return False

    def append(self, entry: LedgerEntry) -> LedgerEntry:
        """Appends a new entry to the ledger after setting prev_hash and signing."""
        latest_hash = self.get_latest_hash()
        chained_entry = LedgerEntry(
            entry_id=entry.entry_id,
            prev_hash=latest_hash,
            timestamp=entry.timestamp,
            dataset_id=entry.dataset_id,
            run_id=entry.run_id,
            mechanism_name=entry.mechanism_name,
            sensitivity=entry.sensitivity,
            noise_scale=entry.noise_scale,
            eps_spent=entry.eps_spent,
            delta=entry.delta,
            seed=entry.seed,
            actor=entry.actor,
            signature="",
        )
        sig_hex = self.sign_entry(chained_entry)
        signed_entry = LedgerEntry(
            entry_id=chained_entry.entry_id,
            prev_hash=chained_entry.prev_hash,
            timestamp=chained_entry.timestamp,
            dataset_id=chained_entry.dataset_id,
            run_id=chained_entry.run_id,
            mechanism_name=chained_entry.mechanism_name,
            sensitivity=chained_entry.sensitivity,
            noise_scale=chained_entry.noise_scale,
            eps_spent=chained_entry.eps_spent,
            delta=chained_entry.delta,
            seed=chained_entry.seed,
            actor=chained_entry.actor,
            signature=sig_hex,
        )
        entry_hash = signed_entry.compute_hash()

        conn = self._get_conn()
        conn.execute("""
            INSERT INTO ledger_entries (
                entry_id, prev_hash, hash, timestamp, dataset_id, run_id,
                mechanism_name, sensitivity, noise_scale, eps_spent, delta, seed, actor, signature
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            signed_entry.entry_id, signed_entry.prev_hash, entry_hash,
            signed_entry.timestamp, signed_entry.dataset_id, signed_entry.run_id,
            signed_entry.mechanism_name, signed_entry.sensitivity, signed_entry.noise_scale,
            signed_entry.eps_spent, signed_entry.delta, signed_entry.seed, signed_entry.actor, signed_entry.signature
        ))
        conn.commit()
        if not self._conn:
            conn.close()
        return signed_entry

    def verify(self) -> bool:
        """Verifies integrity of the entire ledger chain and Ed25519 signatures."""
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM ledger_entries ORDER BY id ASC").fetchall()
        expected_prev = "0" * 64
        valid = True
        for row in rows:
            if row["prev_hash"] != expected_prev:
                valid = False
                break
            entry = LedgerEntry(
                entry_id=row["entry_id"],
                prev_hash=row["prev_hash"],
                timestamp=row["timestamp"],
                dataset_id=row["dataset_id"],
                run_id=row["run_id"],
                mechanism_name=row["mechanism_name"],
                sensitivity=row["sensitivity"],
                noise_scale=row["noise_scale"],
                eps_spent=row["eps_spent"],
                delta=row["delta"],
                seed=row["seed"],
                actor=row["actor"],
                signature=row["signature"],
            )
            if entry.compute_hash() != row["hash"]:
                valid = False
                break
            if not self.verify_entry_signature(entry, row["signature"]):
                valid = False
                break
            expected_prev = row["hash"]

        if not self._conn:
            conn.close()
        return valid

    def get_entries(self, dataset_id: Optional[str] = None) -> List[LedgerEntry]:
        """Retrieves list of ledger entries, optionally filtered by dataset_id."""
        conn = self._get_conn()
        if dataset_id:
            rows = conn.execute("SELECT * FROM ledger_entries WHERE dataset_id = ? ORDER BY id ASC", (dataset_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM ledger_entries ORDER BY id ASC").fetchall()
        entries = []
        for row in rows:
            entries.append(LedgerEntry(
                entry_id=row["entry_id"],
                prev_hash=row["prev_hash"],
                timestamp=row["timestamp"],
                dataset_id=row["dataset_id"],
                run_id=row["run_id"],
                mechanism_name=row["mechanism_name"],
                sensitivity=row["sensitivity"],
                noise_scale=row["noise_scale"],
                eps_spent=row["eps_spent"],
                delta=row["delta"],
                seed=row["seed"],
                actor=row["actor"],
                signature=row["signature"],
            ))
        if not self._conn:
            conn.close()
        return entries
