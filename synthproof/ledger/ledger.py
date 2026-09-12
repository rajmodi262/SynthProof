"""Hash-chained, signed privacy budget ledger.

SHA-256 chaining plus an Ed25519 signature over each entry, and a signed head committing to
(entry_count, tip_hash).

Deliberately NOT called "append-only". Hash chaining detects modification, insertion and
reordering, but a TRUNCATED chain is internally consistent -- dropping the last k entries,
including the ones recording an overspend, leaves something that verifies. The signed head is
what closes that, and the distinction is why the phrase is retired across this repository.

KEY CUSTODY. If no key is passed, one is generated in memory for this instance -- fine for a
demo, useless for a durable record, because signatures become unverifiable after restart. For
any real use pass a persistent key: `ledger.signing.keygen()` writes an Ed25519 keypair and
`load_private_key()` reads it back, which is what the CLI and `synthproof verify` use. F10 in
brutal_project_audit.md is closed; this docstring described it as open until 2026-08-23.
"""

import sqlite3
from typing import List, Optional

from cryptography.hazmat.primitives.asymmetric import ed25519

from synthproof.ledger.types import LedgerEntry


class LedgerVerificationError(Exception):
    """Raised when ledger tamper verification fails."""

    pass


class Ledger:
    """Hash-chained, signed store: SHA-256 chaining, Ed25519 per entry, plus a signed head."""

    def __init__(
        self, db_path: str = ":memory:", private_key: Optional[ed25519.Ed25519PrivateKey] = None
    ):
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
        # SIGNED HEAD — what makes this ledger actually append-only.
        #
        # Hash chaining alone detects modification, insertion and reordering, but NOT
        # truncation: deleting the last k entries leaves a shorter, perfectly valid chain, so
        # an operator who overspends can simply delete the entries that record it. Verified:
        # before this table existed, dropping the final two entries left verify() == True.
        #
        # The head commits to (entry_count, tip_hash) and is signed, so shortening the chain
        # requires forging a signature over the new length.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ledger_head (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                entry_count INTEGER NOT NULL,
                tip_hash TEXT NOT NULL,
                signature TEXT NOT NULL
            )
        """)
        conn.commit()
        if not self._conn:
            conn.close()

    # ------------------------------------------------------------------ signed head

    @staticmethod
    def _head_bytes(entry_count: int, tip_hash: str) -> bytes:
        """Canonical bytes committing to the chain's length and tip."""
        return f"synthproof-ledger-head\x1f{entry_count}\x1f{tip_hash}".encode("utf-8")

    def _write_head(self, conn: sqlite3.Connection, entry_count: int, tip_hash: str) -> None:
        sig = self._private_key.sign(self._head_bytes(entry_count, tip_hash)).hex()
        conn.execute(
            "INSERT INTO ledger_head (id, entry_count, tip_hash, signature) VALUES (1, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET entry_count=excluded.entry_count, "
            "tip_hash=excluded.tip_hash, signature=excluded.signature",
            (entry_count, tip_hash, sig),
        )

    def _verify_head(self, conn: sqlite3.Connection, entry_count: int, tip_hash: str) -> str:
        """Returns '' when the head is valid, else a human-readable reason."""
        row = conn.execute("SELECT * FROM ledger_head WHERE id = 1").fetchone()
        if row is None:
            if entry_count == 0:
                return ""  # an empty ledger has nothing to commit to
            return "no signed head (ledger predates head signing, or the head was deleted)"
        if row["entry_count"] != entry_count:
            return (
                f"entry count mismatch: head commits to {row['entry_count']}, "
                f"found {entry_count} — entries were added or removed"
            )
        if row["tip_hash"] != tip_hash:
            return "tip hash mismatch: the last entry is not the one the head commits to"
        try:
            self._public_key.verify(
                bytes.fromhex(row["signature"]), self._head_bytes(entry_count, tip_hash)
            )
        except Exception:
            return "head signature invalid"
        return ""

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
        conn.execute(
            """
            INSERT INTO ledger_entries (
                entry_id, prev_hash, hash, timestamp, dataset_id, run_id,
                mechanism_name, sensitivity, noise_scale, eps_spent, delta, seed, actor, signature
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                signed_entry.entry_id,
                signed_entry.prev_hash,
                entry_hash,
                signed_entry.timestamp,
                signed_entry.dataset_id,
                signed_entry.run_id,
                signed_entry.mechanism_name,
                signed_entry.sensitivity,
                signed_entry.noise_scale,
                signed_entry.eps_spent,
                signed_entry.delta,
                signed_entry.seed,
                signed_entry.actor,
                signed_entry.signature,
            ),
        )
        count = conn.execute("SELECT COUNT(*) AS c FROM ledger_entries").fetchone()["c"]
        self._write_head(conn, count, entry_hash)
        conn.commit()
        if not self._conn:
            conn.close()
        return signed_entry

    def verify(self) -> bool:
        """Verifies the chain, the per-entry signatures, and the signed head."""
        return self.verify_with_reason()[0]

    def verify_with_reason(self) -> "tuple[bool, str]":
        """Same as `verify()` but returns why it failed.

        The reason matters operationally: 'entry count mismatch' (truncation) and 'hash
        mismatch' (modification) call for very different responses.
        """
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM ledger_entries ORDER BY id ASC").fetchall()
        expected_prev = "0" * 64
        valid = True
        reason = ""
        for row in rows:
            if row["prev_hash"] != expected_prev:
                valid, reason = False, f"broken chain link at entry {row['entry_id']!r}"
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
                valid, reason = False, f"content modified at entry {row['entry_id']!r}"
                break
            if not self.verify_entry_signature(entry, row["signature"]):
                valid, reason = False, f"bad signature at entry {row['entry_id']!r}"
                break
            expected_prev = row["hash"]

        # The head check is what catches TRUNCATION, which the chain walk above cannot see:
        # a shortened chain is still internally consistent.
        if valid:
            head_reason = self._verify_head(conn, len(rows), expected_prev)
            if head_reason:
                valid, reason = False, head_reason

        if not self._conn:
            conn.close()
        return valid, reason

    def clear(self) -> None:
        """Empties the ledger, head included.

        The head and the entries are one invariant, so they must be cleared together. Deleting
        only `ledger_entries` leaves a head committing to a chain that no longer exists, which
        verification then correctly reports as truncation — the caller's cleanup would look
        exactly like an attack. This exists so no caller has to know that.
        """
        conn = self._get_conn()
        conn.execute("DELETE FROM ledger_entries")
        conn.execute("DELETE FROM ledger_head")
        conn.commit()
        if not self._conn:
            conn.close()

    def get_entries(self, dataset_id: Optional[str] = None) -> List[LedgerEntry]:
        """Retrieves list of ledger entries, optionally filtered by dataset_id."""
        conn = self._get_conn()
        if dataset_id:
            rows = conn.execute(
                "SELECT * FROM ledger_entries WHERE dataset_id = ? ORDER BY id ASC",
                (dataset_id,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM ledger_entries ORDER BY id ASC").fetchall()
        entries = []
        for row in rows:
            entries.append(
                LedgerEntry(
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
            )
        if not self._conn:
            conn.close()
        return entries
