"""Everything one running API instance owns, in one object, built explicitly.

WHY (W6, 2026-10-16). The ledger, the auth configuration, the upload cache and the demo datasets
used to be module globals in `api/state.py`, created as a side effect of IMPORTING it: importing
the package opened the ledger database, could write a signing key to SYNTHPROOF_KEY_DIR, and
seeded the demo ledger. Two consequences: nothing could run two isolated instances in one
process, and the tests had to `importlib.reload` modules in a particular order to change the
configuration -- a trap the auth tests document at length.

Now an `AppContext` is built by `build_context(env)` and handed to `create_app(ctx)`; routes
receive it through FastAPI dependency injection (`get_context`). Importing this module, or the
app module, does no work. `api/state.py` remains as a thin compatibility layer over a lazily
built default context, so existing imports keep working.
"""

import contextlib
import hmac
import os
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterator, Mapping, Optional

import pandas as pd
from fastapi import Header, HTTPException, Request

from synthproof.api.security import (
    TRUSTED_NETWORKS,
    RateLimiter,
    budget_for,
    enforce_trusted_network,
    parse_budgets,
)
from synthproof.data.dataset import TabularDataset
from synthproof.data.schema import Schema
from synthproof.ledger import signing
from synthproof.ledger.ledger import Ledger
from synthproof.ledger.types import LedgerEntry

SHARED_PRINCIPAL = "shared-key"
ANONYMOUS = "anonymous"

# Uploaded tables live in memory for the session. Nothing is written to disk: this service
# receives sensitive data by definition, and persisting it silently would be exactly the habit
# the project exists to argue against. Bounded and FIFO-evicting, so a long-running process does
# not keep every table ever uploaded resident.
MAX_UPLOADS = 8
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
MAX_UPLOAD_ROWS = 20_000
UPLOAD_CHUNK = 1 * 1024 * 1024


def ledger_key(db_path: str):
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


def parse_named_keys(raw: str) -> Dict[str, str]:
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


@dataclass
class AppContext:
    """The state of one API instance. Build with `build_context`; pass to `create_app`."""

    ledger: Ledger
    ledger_db: str
    demo_mode: bool
    # principal name -> key. A single shared key is NOT user authentication: every caller is
    # the same principal. Named keys attribute each spend to its key's owner in the ledger.
    api_keys: Dict[str, str]
    uploads: "OrderedDict[str, TabularDataset]" = field(default_factory=OrderedDict)
    demo_datasets: Dict[str, TabularDataset] = field(default_factory=dict)
    # Hardening (api/security.py): epsilon caps per principal ("*" = everyone else), which
    # clients an unauthenticated service answers, and releases/uploads per principal per minute.
    budgets: Dict[str, float] = field(default_factory=dict)
    trusted_network: str = "loopback"
    rate_limiter: RateLimiter = field(default_factory=lambda: RateLimiter(0))

    # ---------------------------------------------------------------- configuration

    @property
    def ledger_durable(self) -> bool:
        """True when the ledger and its key live on disk, so signatures verify after a restart."""
        return self.ledger_db != ":memory:"

    @property
    def auth_enabled(self) -> bool:
        return bool(self.api_keys)

    @property
    def auth_mode(self) -> str:
        if any(n != SHARED_PRINCIPAL for n in self.api_keys):
            return "per-user"
        return "shared" if self.auth_enabled else "disabled"

    # ---------------------------------------------------------------- the ledger

    @contextlib.contextmanager
    def ledger_conn(self) -> Iterator:
        """Yields a ledger connection and closes it if it was opened for this call.

        `Ledger._get_conn` returns the SHARED connection for an in-memory database and a NEW one
        per call for a file-backed database. Closing the shared connection would drop the whole
        in-memory database, so only per-call connections are closed -- the same rule
        `Ledger.append` and `Ledger.verify` follow internally.
        """
        conn = self.ledger._get_conn()
        try:
            yield conn
        finally:
            if conn is not self.ledger._conn:
                conn.close()

    def require_demo_ledger(self) -> None:
        """Refuses destructive ledger operations outside an in-memory demo.

        `/api/ledger/tamper` and `/api/ledger/reset` exist to demonstrate that the chain is
        tamper-EVIDENT. Against a file-backed ledger they would be remote primitives for
        destroying audit records, so they need demo mode AND an in-memory database.
        """
        if not self.demo_mode:
            raise HTTPException(
                403,
                "Destructive ledger endpoints are disabled. Set SYNTHPROOF_DEMO=1 to enable "
                "them, and only against a throwaway ledger.",
            )
        if self.ledger_durable:
            raise HTTPException(
                403,
                f"Refusing to modify a persistent ledger at {self.ledger_db!r}. These endpoints "
                "destroy audit records and are only ever appropriate against ':memory:'.",
            )

    def seed_demo_ledger(self) -> None:
        """Gives the tamper studio a chain to attack on a fresh in-memory ledger.

        These are ILLUSTRATIVE budget charges, and the run ids say so where the console displays
        them (standing rule 5). No synthesis ran for them and they carry no audit result. Until
        2026-09-13 they were indistinguishable from real releases.
        """
        if not self.demo_mode or self.ledger.get_entries():
            return
        for ds_id, run_id, mech, eps, delta, seed in (
            ("adult", "illustrative-charge-1_aim_eps1.0", "aim", 1.0, 1e-5, 42),
            ("adult", "illustrative-charge-2_pairwise_eps2.0", "pairwise", 2.0, 1e-5, 0),
            ("toy", "illustrative-charge-3_independent_eps0.5", "independent", 0.5, 1e-5, 7),
        ):
            self.ledger.append(
                LedgerEntry(
                    dataset_id=ds_id,
                    run_id=run_id,
                    mechanism_name=mech,
                    eps_spent=eps,
                    delta=delta,
                    seed=seed,
                )
            )

    # ---------------------------------------------------------------- datasets

    def register_upload(self, upload_id: str, ds: TabularDataset) -> None:
        """Stores an upload, evicting the oldest once the cap is reached."""
        self.uploads[upload_id] = ds
        while len(self.uploads) > MAX_UPLOADS:
            self.uploads.popitem(last=False)

    def init_demo_datasets(self) -> None:
        """Discovers and caches the pre-verified demo CSV datasets, once, on first use."""
        if self.demo_datasets:
            return
        for d in demo_dataset_dirs():
            if not d.is_dir():
                continue
            for p in sorted(d.glob("*.csv")):
                try:
                    df = (
                        pd.read_csv(p, skipinitialspace=True, na_values=["?", ""])
                        .dropna()
                        .reset_index(drop=True)
                    )
                except Exception:  # an unreadable demo file is skipped, not fatal
                    continue
                if not df.empty:
                    schema = Schema.infer_nonprivate(df)
                    self.demo_datasets[p.stem] = TabularDataset(df, name=p.stem, schema=schema)
            if self.demo_datasets:
                break

    def load_dataset(self, name: str, rows: int, seed: int = 0) -> TabularDataset:
        """Resolves a dataset name against uploads, demo datasets and the built-ins."""
        self.init_demo_datasets()
        if name in self.uploads:
            ds = self.uploads[name]
        elif name in self.demo_datasets:
            ds = self.demo_datasets[name]
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

    def spent_by(self, principal: str) -> float:
        """Naive sum of the epsilon this principal has spent here (an upper bound)."""
        return sum(e.eps_spent for e in self.ledger.get_entries() if e.actor == principal)

    def check_budget(self, principal: str, requested_eps: float) -> None:
        """Refuses a release that would take `principal` past its epsilon cap."""
        cap = budget_for(self.budgets, principal)
        if cap is None:
            return
        spent = self.spent_by(principal)
        if spent + requested_eps > cap + 1e-12:
            raise HTTPException(
                status_code=403,
                detail=(
                    f"Budget exceeded: {principal!r} has spent eps={spent:.4f} of a cap of "
                    f"{cap:g}, and this release requests eps={requested_eps:g}. Nothing was run."
                ),
            )

    def domain_source_for(self, name: str) -> str:
        """How this dataset's column bounds / category domains were obtained (read by RB6).

        Demo datasets and uploads are built with `Schema.infer_nonprivate` -- their bounds come
        straight from the sensitive data, so they are `inferred-nonprivate`, an open channel the
        boundary auditor must flag (Ganev et al., arXiv:2504.08254). `toy` and `adult` ship
        declared schemas.
        """
        self.init_demo_datasets()
        if name in self.uploads or name in self.demo_datasets:
            return "inferred-nonprivate"
        return "declared"


def build_context(env: Optional[Mapping[str, str]] = None) -> AppContext:
    """Builds an instance's state from an environment (defaults to os.environ).

    SYNTHPROOF_LEDGER_DB (':memory:' by default), SYNTHPROOF_KEY_DIR (read by the signing module),
    SYNTHPROOF_DEMO, SYNTHPROOF_API_KEY (one shared key) and SYNTHPROOF_API_KEYS
    ("name=key,..."). Auth is off when neither key variable is set, so the local demo needs no
    configuration; /api/health then says `auth: "disabled"` loudly.
    """
    env = os.environ if env is None else env
    db = env.get("SYNTHPROOF_LEDGER_DB", ":memory:")
    keys = parse_named_keys(env.get("SYNTHPROOF_API_KEYS", ""))
    shared = env.get("SYNTHPROOF_API_KEY", "").strip()
    if shared:
        keys[SHARED_PRINCIPAL] = shared
    network = env.get("SYNTHPROOF_TRUSTED_NETWORK", "loopback").strip() or "loopback"
    if network not in TRUSTED_NETWORKS:
        raise ValueError(f"SYNTHPROOF_TRUSTED_NETWORK must be one of {TRUSTED_NETWORKS}.")
    # Rate limiting defaults on for a durable ledger (a deployment) and off for the in-memory
    # demo, where tests and the live demo run releases back to back.
    rate = int(env.get("SYNTHPROOF_RATE_LIMIT", "30" if db != ":memory:" else "0"))
    ctx = AppContext(
        ledger=Ledger(db_path=db, private_key=ledger_key(db)),
        ledger_db=db,
        demo_mode=env.get("SYNTHPROOF_DEMO", "1" if db == ":memory:" else "0") == "1",
        api_keys=keys,
        budgets=parse_budgets(env.get("SYNTHPROOF_BUDGETS", "")),
        trusted_network=network,
        rate_limiter=RateLimiter(rate),
    )
    ctx.seed_demo_ledger()
    return ctx


def get_context(request: Request) -> AppContext:
    """FastAPI dependency: the context of the app serving this request."""
    return request.app.state.ctx


def require_api_key(
    request: Request,
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None),
) -> str:
    """Returns the caller's principal name, or rejects the request. "anonymous" when auth is off.

    Accepts either `Authorization: Bearer <key>` or `X-API-Key: <key>`. Every configured key is
    compared, in constant time, whichever one matches: stopping at the first match would leak
    through timing which position the caller's key holds.
    """
    ctx = get_context(request)
    if not ctx.auth_enabled:
        # An open service answers only its trusted network (api/security.py).
        enforce_trusted_network(request, ctx.trusted_network)
        return ANONYMOUS
    supplied = x_api_key or ""
    if authorization and authorization.lower().startswith("bearer "):
        supplied = authorization[7:].strip()
    matched: Optional[str] = None
    for name, key in ctx.api_keys.items():
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
