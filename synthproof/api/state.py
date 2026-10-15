"""Compatibility layer: the names routes and tests used before the app factory.

Until 2026-10-16 this module WAS the API's state -- a ledger, the auth configuration, the upload
cache and the demo datasets, all created as a side effect of importing it. That state now lives
in an explicit `AppContext` (`api/context.py`) that `create_app` receives and routes get by
dependency injection. What remains here is a lazily built DEFAULT context -- the one the default
`synthproof.api.main.app` serves -- and the old module-level names, resolved against it on
access, so existing imports keep working. Importing this module does no work.

`importlib.reload(state)` still rebuilds the default from the current environment, which is how
the auth tests switch configuration.
"""

from typing import Optional

from synthproof.api.context import (  # noqa: F401  (re-exported for older callers)
    ANONYMOUS,
    MAX_UPLOAD_BYTES,
    MAX_UPLOAD_ROWS,
    MAX_UPLOADS,
    SHARED_PRINCIPAL,
    UPLOAD_CHUNK,
    AppContext,
    build_context,
    demo_dataset_dirs,
    get_context,
    ledger_key,
    parse_named_keys,
    require_api_key,
)
from synthproof.data.dataset import TabularDataset

_DEFAULT: Optional[AppContext] = None

# Old private names for the upload limits and helpers.
_MAX_UPLOADS = MAX_UPLOADS
_MAX_UPLOAD_BYTES = MAX_UPLOAD_BYTES
_MAX_UPLOAD_ROWS = MAX_UPLOAD_ROWS
_UPLOAD_CHUNK = UPLOAD_CHUNK
_ledger_key = ledger_key
_parse_named_keys = parse_named_keys


def default_context() -> AppContext:
    """The context the default app serves, built from the environment on first use."""
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = build_context()
    return _DEFAULT


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


def _load_dataset(name: str, rows: int, seed: int = 0) -> TabularDataset:
    return default_context().load_dataset(name, rows, seed)


def domain_source_for(name: str) -> str:
    return default_context().domain_source_for(name)


def _register_upload(upload_id: str, ds: TabularDataset) -> None:
    default_context().register_upload(upload_id, ds)


def _init_demo_datasets() -> None:
    default_context().init_demo_datasets()


def _ledger_conn():
    return default_context().ledger_conn()


def _require_demo_ledger() -> None:
    default_context().require_demo_ledger()


_LAZY = {
    "GLOBAL_LEDGER": lambda c: c.ledger,
    "LEDGER_DURABLE": lambda c: c.ledger_durable,
    "DEMO_MODE": lambda c: c.demo_mode,
    "API_KEYS": lambda c: c.api_keys,
    "API_KEY": lambda c: c.api_keys.get(SHARED_PRINCIPAL, ""),
    "AUTH_ENABLED": lambda c: c.auth_enabled,
    "AUTH_MODE": lambda c: c.auth_mode,
    "_UPLOADS": lambda c: c.uploads,
    "_DEMO_DATASETS": lambda c: c.demo_datasets,
    "_LEDGER_DB": lambda c: c.ledger_db,
}


def __getattr__(name: str):
    if name in _LAZY:
        return _LAZY[name](default_context())
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
