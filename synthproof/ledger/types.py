"""Data structures and serialization for the append-only cryptographic ledger."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json

import hashlib
from typing import Any, Dict, Optional
import uuid


@dataclass(frozen=True)
class LedgerEntry:
    """Represents a single immutable, hash-chained spend record in the privacy ledger."""

    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    prev_hash: str = "0" * 64
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    dataset_id: str = "default_dataset"
    run_id: str = "default_run"
    mechanism_name: str = "gaussian"
    sensitivity: float = 1.0
    noise_scale: float = 1.0
    eps_spent: float = 0.0
    delta: float = 1e-5
    seed: int = 42
    actor: str = "synthproof_system"
    signature: str = ""

    def canonical_bytes(self) -> bytes:
        """Produces deterministic, canonical JSON representation for hashing and signing."""
        data = {
            "entry_id": self.entry_id,
            "prev_hash": self.prev_hash,
            "timestamp": self.timestamp,
            "dataset_id": self.dataset_id,
            "run_id": self.run_id,
            "mechanism_name": self.mechanism_name,
            "sensitivity": f"{self.sensitivity:.8f}",
            "noise_scale": f"{self.noise_scale:.8f}",
            "eps_spent": f"{self.eps_spent:.8f}",
            "delta": f"{self.delta:.8e}",
            "seed": self.seed,
            "actor": self.actor,
        }
        return json.dumps(data, sort_keys=True).encode("utf-8")

    def compute_hash(self) -> str:
        """Computes SHA-256 digest of canonical bytes."""
        return hashlib.sha256(self.canonical_bytes()).hexdigest()
