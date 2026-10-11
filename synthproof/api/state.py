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
from synthproof.ledger import signing
from synthproof.ledger.ledger import Ledger
from synthproof.ledger.types import LedgerEntry

_LEDGER_DB = os.environ.get("SYNTHPROOF_LEDGER_DB", ":memory:")


def _ledger_key(db_path: str):
    """The key that signs the ledger head: ephemeral in memory, persistent on disk.

    A file-backed ledger used to get a fresh in-memory key on every start, so after a restart
    its stored head signature no longer verified and /api/health reported a broken ledger --
    the persistent mode was unusable by construction. On disk the key now lives in
    SYNTHPROOF_KEY_DIR, created once on first start and reused after that.
    """
    if db_path == ":memory:":
        return None
    key_path = signing.resolve_key_dir() / signing.PRIVATE_KEY_NAME
    if not key_path.exists():
        try:
            signing.generate_keypair()
        except FileExistsError:  # another worker created it first
            pass
    return signing.load_private_key(key_path)


GLOBAL_LEDGER = Ledger(db_path=_LEDGER_DB, private_key=_ledger_key(_LEDGER_DB))

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
# A single shared key is NOT user authentication: every caller is the same principal. So
# SYNTHPROOF_API_KEYS takes NAMED keys -- "alice=<key>,bob=<key>" -- and every request is
# attributed to the name whose key it carried. The ledger records that name as the `actor` of
# each spend, so the spend history says WHO spent the budget, and one person's key can be
# revoked without rotating everyone's. Both variables may be set; the shared key's principal is
# "shared-key".
#
# Still not the destination: there is no per-user budget, no expiry and no SSO. It is the
# identity the cross-session budget filter (docs/design/USER_FACING_SYSTEM.md §2.3) would key on.
#
# Unset by default so the local demo keeps working. `/api/health` reports which mode is
# active, because a service that is open and does not say so is worse than one that is open.
API_KEY = os.environ.get("SYNTHPROOF_API_KEY", "").strip()
SHARED_PRINCIPAL = "shared-key"


def _parse_named_keys(raw: str) -> Dict[str, str]:
    """Parses "name=key,name=key". A malformed value stops the service rather than half-working."""
    keys: Dict[str, str] = {}
    for part in (p.strip() for p in raw.split(",")):
        if not part:
            continue
        name, sep, key = part.partition("=")
        name, key = name.strip(), key.strip()
        if not sep or not name or not key:
            raise ValueError(
                f"SYNTHPROOF_API_KEYS entry {part.split('=')[0]!r} is not of the form name=key."
            )
        if name in keys or name == SHARED_PRINCIPAL:
            raise ValueError(f"SYNTHPROOF_API_KEYS names {name!r} twice or uses a reserved name.")
        if key in keys.values():
            raise ValueError("Two SYNTHPROOF_API_KEYS entries share a key; keys must be unique.")
        keys[name] = key
    return keys


API_KEYS: Dict[str, str] = _parse_named_keys(os.environ.get("SYNTHPROOF_API_KEYS", ""))
if API_KEY:
    API_KEYS[SHARED_PRINCIPAL] = API_KEY
AUTH_ENABLED = bool(API_KEYS)
AUTH_MODE = (
    "per-user"
    if any(n != SHARED_PRINCIPAL for n in API_KEYS)
    else ("shared" if AUTH_ENABLED else "disabled")
)
ANONYMOUS = "anonymous"


def require_api_key(
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None),
) -> str:
    """Returns the caller's principal name, or rejects the request. "anonymous" when auth is off.

    Accepts either `Authorization: Bearer <key>` or `X-API-Key: <key>`. Every configured key is
    compared, in constant time, whichever one matches: stopping at the first match would leak
    through timing which position the caller's key holds.
    """
    if not AUTH_ENABLED:
        return ANONYMOUS
    supplied = x_api_key or ""
    if authorization and authorization.lower().startswith("bearer "):
        supplied = authorization[7:].strip()
    matched: Optional[str] = None
    for name, key in API_KEYS.items():
        if hmac.compare_digest(supplied.encode("utf-8"), key.encode("utf-8")) and supplied:
            matched = name
    if matched is None:
        raise HTTPException(
            status_code=401,
            detail=(
                "This service requires an API key. Send it as `Authorization: Bearer <key>` "
                "or `X-API-Key: <key>`."
            ),
            headers={"WWW-Authenticate": "Bearer"},
        )
    return matched


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


def demo_dataset_dirs() -> "list[Path]":
    """Where the demo CSVs are looked for, in order.

    The repository's own `demo_datasets/` comes first. It used to be absent from this list, which
    only searched a `04_Demo_CSV_Datasets/` folder OUTSIDE the repository -- so in a fresh clone,
    in CI and in the Docker image every console demo preset silently fell back to the toy table.
    """
    here = Path(__file__).resolve()
    return [
        here.parents[2] / "demo_datasets",
        here.parents[3] / "04_Demo_CSV_Datasets",
        here.parents[2] / "04_Demo_CSV_Datasets",
        Path("demo_datasets"),
        Path("04_Demo_CSV_Datasets"),
        Path("../04_Demo_CSV_Datasets"),
    ]


def _init_demo_datasets() -> None:
    """Discovers and caches the pre-verified demo CSV datasets if present."""
    if _DEMO_DATASETS:
        return
    for d in demo_dataset_dirs():
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


def domain_source_for(name: str) -> str:
    """How this dataset's column bounds / category domains were obtained.

    This is the value the release-boundary RB6 check reads (`boundary.py::_domain`), and the
    honest answer matters: Ganev et al. (arXiv:2504.08254, 2504.06923) show that reading the
    data domain from the input breaks end-to-end DP. Demo datasets and uploads are built with
    ``Schema.infer_nonprivate`` -- their bounds come straight from the sensitive data, so they
    are ``inferred-nonprivate`` (an open channel the auditor must flag). The built-in ``toy``
    and ``adult`` datasets ship declared/public schemas.
    """
    _init_demo_datasets()
    if name in _UPLOADS or name in _DEMO_DATASETS:
        return "inferred-nonprivate"
    return "declared"


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
