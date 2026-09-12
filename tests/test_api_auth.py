"""API authentication.

Before this, anyone who could reach the port could upload a sensitive table, spend the privacy
budget attached to someone else's dataset, and read the ledger. `grep -c Depends` over the API
returned 0.

The tests that matter here are the negative ones. An auth mechanism that is present but does
not actually block is worse than none, because it invites the belief that the service is
protected — so most of what follows checks that requests WITHOUT a key are refused, on every
endpoint that touches data or budget.

Auth is configured by environment variable and read at import, so each case re-imports the
module under a patched environment rather than mutating a live app.
"""

import importlib
import io

import pytest
from fastapi.testclient import TestClient

KEY = "test-key-4f2b"

# Endpoints that must refuse an unauthenticated caller: they read uploaded data, spend budget,
# or expose the spend history.
GUARDED = [
    ("get", "/api/mechanisms", None),
    ("get", "/api/datasets", None),
    ("get", "/api/ledger", None),
    ("post", "/api/run", {"dataset": "toy", "eps": 1.0, "mechanism": "independent"}),
    ("post", "/api/ledger/reset", {}),
    ("post", "/api/ledger/tamper", {"entry_id": "x", "eps_spent": 0.1}),
]


def _app(monkeypatch, key=None, **env):
    """Re-imports the API with a patched environment and returns a client.

    `state` is reloaded FIRST and `main` second, and the order matters. API_KEY, AUTH_ENABLED
    and the CORS origins are read from the environment at import time, and since the 2026-09-13
    split they live in `synthproof.api.state` while the routes that depend on them live in
    `main` and under `routes/`. Reloading only `main` would rebind its re-exported names to
    values `state` computed under the OLD environment, and every auth assertion here would
    silently test the wrong thing.

    That import-time read is itself a trap -- the same one `ledger/signing.py` documents and
    fixed by resolving per call. It is left alone here deliberately: changing how
    authentication resolves its key does not belong in a structural refactor.
    """
    import synthproof.api.main as m
    import synthproof.api.state as st

    monkeypatch.setenv("SYNTHPROOF_API_KEY", key or "")
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    importlib.reload(st)
    importlib.reload(m)
    return TestClient(m.app), m


@pytest.fixture(autouse=True)
def _restore():
    """Leaves the module in its default (open) state for other test files."""
    yield
    import synthproof.api.main as m
    import synthproof.api.state as st

    importlib.reload(st)
    importlib.reload(m)


# ------------------------------------------------------------------ auth disabled (default)


def test_without_a_key_configured_the_service_is_open(monkeypatch):
    """The local demo must keep working with no configuration."""
    client, m = _app(monkeypatch)
    assert m.AUTH_ENABLED is False
    assert client.get("/api/mechanisms").status_code == 200


def test_an_open_service_says_so_loudly_on_health(monkeypatch):
    """An open service that does not announce it is worse than one that does. This is the
    field an operator checks before exposing the port."""
    client, _ = _app(monkeypatch)
    body = client.get("/api/health").json()
    assert body["auth"] == "disabled"
    assert "NO AUTHENTICATION" in body["auth_note"]


# ------------------------------------------------------------------ auth enabled


@pytest.mark.parametrize("method,path,payload", GUARDED)
def test_a_guarded_endpoint_refuses_a_request_with_no_key(monkeypatch, method, path, payload):
    """THE test. Everything else here is secondary to endpoints actually refusing."""
    client, _ = _app(monkeypatch, key=KEY)
    resp = getattr(client, method)(path, json=payload) if payload is not None else client.get(path)
    assert resp.status_code == 401, f"{path} answered {resp.status_code} without a key"


@pytest.mark.parametrize("method,path,payload", GUARDED)
def test_a_guarded_endpoint_refuses_a_wrong_key(monkeypatch, method, path, payload):
    client, _ = _app(monkeypatch, key=KEY)
    h = {"X-API-Key": "not-the-key"}
    resp = (
        getattr(client, method)(path, json=payload, headers=h)
        if payload is not None
        else client.get(path, headers=h)
    )
    assert resp.status_code == 401


def test_upload_refuses_without_a_key(monkeypatch):
    """The most important single endpoint: it accepts sensitive data by definition."""
    client, _ = _app(monkeypatch, key=KEY)
    csv = io.BytesIO(b"age,grp\n30,a\n40,b\n")
    resp = client.post("/api/upload", files={"file": ("t.csv", csv, "text/csv")})
    assert resp.status_code == 401


def test_a_correct_key_is_accepted_in_the_bearer_header(monkeypatch):
    client, _ = _app(monkeypatch, key=KEY)
    resp = client.get("/api/mechanisms", headers={"Authorization": f"Bearer {KEY}"})
    assert resp.status_code == 200


def test_a_correct_key_is_accepted_in_the_x_api_key_header(monkeypatch):
    client, _ = _app(monkeypatch, key=KEY)
    assert client.get("/api/mechanisms", headers={"X-API-Key": KEY}).status_code == 200


def test_the_bearer_scheme_is_matched_case_insensitively(monkeypatch):
    client, _ = _app(monkeypatch, key=KEY)
    assert (
        client.get("/api/mechanisms", headers={"Authorization": f"bearer {KEY}"}).status_code == 200
    )


def test_a_401_tells_the_caller_how_to_authenticate(monkeypatch):
    """An error that does not say what to do is a dead end."""
    client, _ = _app(monkeypatch, key=KEY)
    resp = client.get("/api/ledger")
    assert "Bearer" in resp.headers.get("WWW-Authenticate", "")
    assert "X-API-Key" in resp.json()["detail"]


# ------------------------------------------------------------------ health stays reachable


def test_health_is_reachable_without_a_key_even_when_auth_is_on(monkeypatch):
    """A readiness probe must not need a secret, and this endpoint is how an operator
    discovers the service is protected at all."""
    client, _ = _app(monkeypatch, key=KEY)
    body = client.get("/api/health").json()
    assert body["auth"] == "required"
    assert "NO AUTHENTICATION" not in body["auth_note"]


def test_health_does_not_leak_the_key(monkeypatch):
    client, _ = _app(monkeypatch, key=KEY)
    assert KEY not in client.get("/api/health").text


# ------------------------------------------------------------------ CORS


def test_cors_stops_being_a_wildcard_once_a_key_is_set(monkeypatch):
    """With a key configured, a wildcard origin would let any page on the internet drive the
    API from a browser that happens to hold the key."""
    _, m = _app(monkeypatch, key=KEY)
    assert "*" not in m._ALLOWED_ORIGINS


def test_cors_origins_can_be_configured_explicitly(monkeypatch):
    _, m = _app(monkeypatch, key=KEY, SYNTHPROOF_CORS_ORIGINS="https://a.example,https://b.example")
    assert m._ALLOWED_ORIGINS == ["https://a.example", "https://b.example"]


def test_cors_stays_open_for_the_unauthenticated_local_demo(monkeypatch):
    _, m = _app(monkeypatch)
    assert m._ALLOWED_ORIGINS == ["*"]
