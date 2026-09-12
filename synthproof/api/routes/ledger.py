"""Ledger routes: read the chain, attack it, reset it.

`/api/ledger/tamper` and `/api/ledger/reset` exist to demonstrate that the chain is
tamper-EVIDENT, and they are destructive by design -- one rewrites a spend, the other deletes
the whole history. Against a file-backed ledger they would be unauthenticated remote
primitives for destroying audit records, which is why `_require_demo_ledger` refuses them
outside demo mode and on anything but an in-memory database.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

# Imported as a MODULE, not by name. `GLOBAL_LEDGER` is mutable process state, and
# `from state import GLOBAL_LEDGER` binds this module to whichever Ledger object existed at
# import time. tests/test_api_auth.py reloads the API to re-read the environment, which
# replaces that object -- and a by-name binding here would keep operating on the old ledger,
# so a tamper would be applied to one chain and verified against another. Nothing would fail
# loudly; the routes would just quietly describe a different ledger than the one under test.
from synthproof.api import state
from synthproof.api.state import require_api_key

router = APIRouter()

# --------------------------------------------------------------------------- ledger


@router.get("/api/ledger", dependencies=[Depends(require_api_key)])
def get_ledger():
    """Returns the budget ledger and the result of verifying its chain.

    `verified` is the live result of re-hashing every entry and checking the signed head, not
    a cached flag. The chain detects modification, insertion, reordering, replay and
    truncation; it does not defend against an adversary holding the signing key.

    Note the service's key is generated in memory per process, so these signatures do not
    survive a restart — see the preamble in `docs/API.md`.
    """
    entries = state.GLOBAL_LEDGER.get_entries()
    return {
        "verified": state.GLOBAL_LEDGER.verify(),
        "head": state.GLOBAL_LEDGER.get_latest_hash(),
        "count": len(entries),
        "total_eps_spent": round(sum(e.eps_spent for e in entries), 4),
        "entries": [
            {
                "entry_id": e.entry_id,
                "prev_hash": e.prev_hash,
                "hash": e.compute_hash(),
                "timestamp": e.timestamp,
                "dataset_id": e.dataset_id,
                "run_id": e.run_id,
                "mechanism_name": e.mechanism_name,
                "eps_spent": e.eps_spent,
                "delta": e.delta,
                "seed": e.seed,
                "signature": e.signature[:32],
            }
            for e in entries
        ],
    }


class TamperRequest(BaseModel):
    entry_id: Optional[str] = None
    eps_spent: float = 0.01
    attack_type: str = "modify_eps"  # modify_eps, truncate, corrupt_hash, corrupt_signature


@router.post("/api/ledger/tamper", dependencies=[Depends(require_api_key)])
def tamper(req: TamperRequest):
    """Runs an adversarial attack straight against the SQLite file, to show tamper-evidence."""
    state._require_demo_ledger()

    entries = state.GLOBAL_LEDGER.get_entries()
    if req.entry_id is not None and not any(str(e.entry_id) == str(req.entry_id) for e in entries):
        raise HTTPException(404, f"Entry {req.entry_id!r} not found in ledger")

    if not entries:
        raise HTTPException(
            400, "Ledger is empty. Run a synthesis release first before executing attacks."
        )

    target_id = req.entry_id or entries[-1].entry_id

    with state._ledger_conn() as conn:
        if req.attack_type == "truncate":
            # Delete the most recent row while leaving the signed ledger_head intact
            conn.execute("DELETE FROM ledger_entries WHERE entry_id = ?", (target_id,))
            conn.commit()
            broken_from = len(entries) - 1
            attack_desc = (
                "History Truncation: Deleted recent entry without updating the signed ledger_head."
            )
        elif req.attack_type == "corrupt_hash":
            conn.execute(
                "UPDATE ledger_entries SET hash = 'deadbeef00000000' WHERE entry_id = ?",
                (target_id,),
            )
            conn.commit()
            broken_from = next((i for i, e in enumerate(entries) if e.entry_id == target_id), 0)
            attack_desc = "Hash Corruption: Injected fraudulent row hash."
        elif req.attack_type == "corrupt_signature":
            conn.execute(
                "UPDATE ledger_entries SET signature = '00' * 64 WHERE entry_id = ?", (target_id,)
            )
            conn.commit()
            broken_from = next((i for i, e in enumerate(entries) if e.entry_id == target_id), 0)
            attack_desc = "Signature Forgery: Corrupted cryptographic entry signature."
        else:
            # Default: modify_eps
            conn.execute(
                "UPDATE ledger_entries SET eps_spent = ? WHERE entry_id = ?",
                (req.eps_spent, target_id),
            )
            conn.commit()
            broken_from = next((i for i, e in enumerate(entries) if e.entry_id == target_id), 0)
            attack_desc = (
                f"Retroactive Spend Manipulation: Altered recorded epsilon to {req.eps_spent}."
            )

    valid, reason = state.GLOBAL_LEDGER.verify_with_reason()
    return {
        "verified": valid,
        "reason": reason,
        "attack_type": req.attack_type,
        "attack_description": attack_desc,
        "tampered_entry": target_id,
        "broken_from_index": broken_from,
        "broken_count": len(entries) - broken_from if broken_from is not None else 1,
        # NOT "guarantee non-repudiation" -- that overstates what this construction does, and
        # contradicts ledger/signing.py, which records that anyone holding the private key can
        # rewrite the chain and re-sign it. Hash chaining plus a signed head makes tampering
        # DETECTABLE; it does not make it impossible, and it cannot bind a key to a person.
        "explanation": (
            "Hash chaining plus a signed head committing to (entry_count, tip_hash) makes "
            "this edit detectable. It is tamper-evident, not tamper-proof: a holder of the "
            "signing key could rewrite the chain and re-sign it."
        ),
    }


@router.post("/api/ledger/reset", dependencies=[Depends(require_api_key)])
def reset_ledger():
    """Clears the in-memory chain, so the tamper demo can be run again."""
    state._require_demo_ledger()
    state.GLOBAL_LEDGER.clear()
    return {"verified": state.GLOBAL_LEDGER.verify(), "head": state.GLOBAL_LEDGER.get_latest_hash()}
