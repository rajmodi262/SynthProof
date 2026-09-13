"""Process-wide state the API routes share.

Split out of `main.py` on 2026-09-13. A router cannot import the application object to reach
the ledger or the auth dependency -- `main` imports the routers in order to mount them, so
that would be circular. Everything genuinely shared therefore lives here, and `main` imports
it on the same terms a router does.

None of this is new code; it is the same objects, moved.
"""

import contextlib
import hmac
import os
from collections import OrderedDict
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
from fastapi import Header, HTTPException

from synthproof.data.dataset import TabularDataset
from synthproof.data.schema import Schema
from synthproof.ledger.ledger import Ledger
from synthproof.ledger.types import LedgerEntry

_LEDGER_DB = os.environ.get("SYNTHPROOF_LEDGER_DB", ":memory:")
GLOBAL_LEDGER = Ledger(db_path=_LEDGER_DB)

# `/api/ledger/tamper` and `/api/ledger/reset` exist to demonstrate that the chain is
# tamper-EVIDENT. They are destructive by design: one rewrites a spend, the other deletes the
# entire history. Against a file-backed ledger they would be unauthenticated remote primitives
# for destroying audit records, so they are refused unless demo mode is switched on
# deliberately, and refused outright on anything but an in-memory database.
DEMO_MODE = os.environ.get("SYNTHPROOF_DEMO", "1" if _LEDGER_DB == ":memory:" else "0") == "1"


def _seed_demo_ledger():
    """Gives the tamper studio a chain to attack on a fresh in-memory ledger.

    These are ILLUSTRATIVE budget charges, and the run ids say so where the console displays
    them (standing rule 5: label illustrative values where they are shown). No synthesis ran
    for them and they carry no audit result.

    Until 2026-09-13 they were indistinguishable from real releases, one named a
    `texas_inpatient` dataset that exists nowhere in this repository, and the launcher banner
    printed audited epsilons and "Verified" beside them -- numbers that were never computed.
    """
    if not DEMO_MODE or GLOBAL_LEDGER.get_entries():
        return
    seeds = [
        ("adult", "illustrative-charge-1_aim_eps1.0", "aim", 1.0, 1e-5, 42),
        ("adult", "illustrative-charge-2_pairwise_eps2.0", "pairwise", 2.0, 1e-5, 0),
        ("toy", "illustrative-charge-3_independent_eps0.5", "independent", 0.5, 1e-5, 7),
    ]
    for ds_id, run_id, mech, eps, delta, seed in seeds:
        GLOBAL_LEDGER.append(
            LedgerEntry(
                dataset_id=ds_id,
                run_id=run_id,
                mechanism_name=mech,
                eps_spent=eps,
                delta=delta,
                seed=seed,
            )
        )


_seed_demo_ledger()

# --------------------------------------------------------------------------- authentication
#
# WHAT THIS IS AND, MORE IMPORTANTLY, WHAT IT IS NOT.
#
# Setting SYNTHPROOF_API_KEY requires a shared bearer token on every endpoint that reads
# uploaded data, spends budget, or reveals the ledger. That closes the gap where anyone who
# could reach the port could upload a sensitive table, consume the privacy budget attached to
# someone else's dataset, or read the spend history.
#
# It is NOT user authentication. There is one key, so every caller is the same principal: the
# ledger's `actor` field cannot distinguish them, key rotation invalidates everyone at once,
# and there is no per-user budget or audit trail. A deployment that needs to know WHO spent
# the budget needs real identity, which is also the missing prerequisite for the cross-session
# budget filter described in docs/design/USER_FACING_SYSTEM.md §2.3. This is the smallest
# honest step, not the destination.
#
# Unset by default so the local demo keeps working. `/api/health` reports which mode is
# active, because a service that is open and does not say so is worse than one that is open.
API_KEY = os.environ.get("SYNTHPROOF_API_KEY", "").strip()
AUTH_ENABLED = bool(API_KEY)


def require_api_key(
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None),
) -> None:
    """Rejects a request that lacks the configured key. A no-op when no key is set.

    Accepts either `Authorization: Bearer <key>` or `X-API-Key: <key>`. Comparison is
    constant-time: a plain `==` on a secret leaks its prefix through response timing, which is
    a small thing to get wrong and a silly one to get wrong in a privacy project.
    """
    if not AUTH_ENABLED:
        return
    supplied = x_api_key or ""
    if authorization and authorization.lower().startswith("bearer "):
        supplied = authorization[7:].strip()
    if not supplied or not hmac.compare_digest(supplied, API_KEY):
        raise HTTPException(
            status_code=401,
            detail=(
                "This service requires an API key. Send it as `Authorization: Bearer <key>` "
                "or `X-API-Key: <key>`."
            ),
            headers={"WWW-Authenticate": "Bearer"},
        )


@contextlib.contextmanager
def _ledger_conn():
    """Yields a ledger connection and closes it if it was opened for this call.

    `Ledger._get_conn` returns the SHARED connection for an in-memory database and a NEW
    one per call for a file-backed database. Closing the shared connection would drop the
    whole in-memory database, so only per-call connections are closed — the same rule
    `Ledger.append` and `Ledger.verify` already follow internally.
    """
    conn = GLOBAL_LEDGER._get_conn()
    try:
        yield conn
    finally:
        if conn is not GLOBAL_LEDGER._conn:
            conn.close()


def _require_demo_ledger() -> None:
    """Refuses destructive ledger operations outside an in-memory demo."""
    if not DEMO_MODE:
        raise HTTPException(
            403,
            "Destructive ledger endpoints are disabled. Set SYNTHPROOF_DEMO=1 to enable "
            "them, and only against a throwaway ledger.",
        )
    if _LEDGER_DB != ":memory:":
        raise HTTPException(
            403,
            f"Refusing to modify a persistent ledger at {_LEDGER_DB!r}. These endpoints "
            "destroy audit records and are only ever appropriate against ':memory:'.",
        )


# Uploaded tables live in memory for the session. Nothing is written to disk: this service
# receives sensitive data by definition, and persisting it silently would be exactly the
# habit the project exists to argue against.
# Bounded and FIFO-evicting. An unbounded dict would hold every table ever uploaded for the
# lifetime of the process — at 20k rows each that is a slow memory leak, and worse, it keeps
# sensitive data resident long after anyone is using it.
_UPLOADS: "OrderedDict[str, TabularDataset]" = OrderedDict()
_MAX_UPLOADS = 8
_MAX_UPLOAD_BYTES = 25 * 1024 * 1024
_MAX_UPLOAD_ROWS = 20_000
_UPLOAD_CHUNK = 1 * 1024 * 1024


def _register_upload(upload_id: str, ds: TabularDataset) -> None:
    """Stores an upload, evicting the oldest once the cap is reached."""
    _UPLOADS[upload_id] = ds
    while len(_UPLOADS) > _MAX_UPLOADS:
        _UPLOADS.popitem(last=False)


_DEMO_DATASETS: "Dict[str, TabularDataset]" = {}


def _init_demo_datasets() -> None:
    """Discovers and caches the pre-verified demo CSV datasets if present."""
    if _DEMO_DATASETS:
        return
    possible_dirs = [
        Path(__file__).resolve().parent.parent.parent.parent / "04_Demo_CSV_Datasets",
        Path(__file__).resolve().parent.parent.parent / "04_Demo_CSV_Datasets",
        Path("04_Demo_CSV_Datasets"),
        Path("../04_Demo_CSV_Datasets"),
    ]
    for d in possible_dirs:
        if d.is_dir():
            for p in sorted(d.glob("*.csv")):
                try:
                    df = (
                        pd.read_csv(p, skipinitialspace=True, na_values=["?", ""])
                        .dropna()
                        .reset_index(drop=True)
                    )
                    if not df.empty:
                        name = p.stem
                        schema = Schema.infer_nonprivate(df)
                        _DEMO_DATASETS[name] = TabularDataset(df, name=name, schema=schema)
                except Exception:
                    pass
            if _DEMO_DATASETS:
                break


# --------------------------------------------------------------- dataset resolution
# Moved here from the dataset ROUTES on 2026-09-13. They resolve a name against the
# upload cache and the demo registry, both of which are defined above, and the run
# pipeline needs them too -- leaving them in the router made the two routers circular.


def _load_dataset(name: str, rows: int, seed: int = 0) -> TabularDataset:
    _init_demo_datasets()
    if name in _UPLOADS:
        ds = _UPLOADS[name]
    elif name in _DEMO_DATASETS:
        ds = _DEMO_DATASETS[name]
    elif name == "toy":
        return TabularDataset.create_synthetic_toy(num_rows=min(rows, 5000), seed=seed)
    elif name == "adult":
        from synthproof.data.datasets import load_adult

        ds = load_adult()
    else:
        raise HTTPException(
            404,
            f"Unknown dataset {name!r}. "
            "Use 'toy', 'adult', a demo dataset, or an upload id from /api/upload.",
        )

    if ds.num_rows > rows:
        sub = ds.df.sample(n=rows, random_state=seed).reset_index(drop=True)
        ds = TabularDataset(sub, name=ds.name, schema=ds.schema)
    return ds


def _describe(ds: TabularDataset) -> dict:
    return {
        "name": ds.name,
        "rows": ds.num_rows,
        "cols": ds.num_cols,
        "numerical": ds.numerical_cols,
        "categorical": ds.categorical_cols,
        "has_schema": ds.schema is not None,
        "bounds": {c: ds.bounds(c) for c in ds.numerical_cols} if ds.schema else {},
    }
