"""Service hardening (W7): trusted network, per-principal budgets, rate limiting, headers.

Each test is the evidence for one row of docs/threat_model.md.
"""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from synthproof.api.main import create_app
from synthproof.api.security import (
    RateLimiter,
    client_is_trusted,
    parse_budgets,
)

RUN = {"dataset": "toy", "mechanism": "independent", "target_eps": 1.0, "rows": 200}


def _client(env, addr=("127.0.0.1", 50000)):
    return TestClient(create_app(env=env), client=addr)


# ---------------------------------------------------------------- T1: open service, remote caller


def test_an_open_service_refuses_a_remote_caller():
    remote = _client({}, ("203.0.113.9", 4000))
    assert remote.get("/api/ledger").status_code == 403
    assert remote.post("/api/run", json=RUN).status_code == 403
    assert remote.get("/api/health").status_code == 200  # readiness stays answerable


def test_an_open_service_still_answers_this_machine():
    assert _client({}).get("/api/ledger").status_code == 200


def test_the_container_setting_admits_the_docker_bridge_but_not_the_internet():
    env = {"SYNTHPROOF_TRUSTED_NETWORK": "private"}
    assert _client(env, ("172.17.0.1", 4000)).get("/api/ledger").status_code == 200
    assert _client(env, ("198.51.100.4", 4000)).get("/api/ledger").status_code == 403
    assert _client(env, ("8.8.8.8", 4000)).get("/api/ledger").status_code == 403


def test_with_a_key_the_key_is_the_control_not_the_address():
    env = {"SYNTHPROOF_API_KEYS": "alice=k-alice"}
    remote = _client(env, ("203.0.113.9", 4000))
    assert remote.get("/api/ledger").status_code == 401
    assert remote.get("/api/ledger", headers={"X-API-Key": "k-alice"}).status_code == 200


def test_trust_classification():
    assert client_is_trusted("127.0.0.1", "loopback")
    assert client_is_trusted("::1", "loopback")
    assert not client_is_trusted("10.0.0.5", "loopback")
    assert client_is_trusted("10.0.0.5", "private")
    assert not client_is_trusted("8.8.8.8", "private")
    assert not client_is_trusted("203.0.113.9", "private")  # documentation range, not local
    assert client_is_trusted("8.8.8.8", "any")
    assert not client_is_trusted("not-an-ip", "private")
    assert not client_is_trusted(None, "loopback")


def test_an_unknown_trusted_network_setting_stops_the_service():
    with pytest.raises(ValueError, match="TRUSTED_NETWORK"):
        create_app(env={"SYNTHPROOF_TRUSTED_NETWORK": "everyone"})


# ---------------------------------------------------- T2: one principal drains the budget


def test_a_release_past_the_principals_cap_is_refused_before_it_runs():
    env = {"SYNTHPROOF_API_KEYS": "alice=k-a,bob=k-b", "SYNTHPROOF_BUDGETS": "alice=1.5,*=10"}
    c = _client(env)
    alice, bob = {"X-API-Key": "k-a"}, {"X-API-Key": "k-b"}
    assert c.post("/api/run", json={**RUN, "seed": 1}, headers=alice).status_code == 200
    before = c.get("/api/ledger", headers=alice).json()["count"]
    refused = c.post("/api/run", json={**RUN, "seed": 2}, headers=alice)
    assert refused.status_code == 403 and "Budget exceeded" in refused.json()["detail"]
    assert c.get("/api/ledger", headers=alice).json()["count"] == before  # nothing was charged
    # The cap is per principal: bob falls under '*' and is unaffected.
    assert c.post("/api/run", json={**RUN, "seed": 3}, headers=bob).status_code == 200


@pytest.mark.parametrize("raw", ["alice", "alice=", "alice=-1", "alice=0", "=3", "alice=x"])
def test_a_malformed_budget_stops_the_service(raw):
    with pytest.raises(ValueError, match="SYNTHPROOF_BUDGETS"):
        parse_budgets(raw)


def test_budgets_parse():
    assert parse_budgets("alice=10, *=2.5") == {"alice": 10.0, "*": 2.5}


# ---------------------------------------------------------------- T3: flooding


def test_the_rate_limiter_windows_per_key():
    rl = RateLimiter(2)
    rl.check("a", now=0.0)
    rl.check("a", now=1.0)
    with pytest.raises(HTTPException) as err:
        rl.check("a", now=2.0)
    assert err.value.status_code == 429 and err.value.headers["Retry-After"] == "59"
    rl.check("b", now=2.0)  # another principal has its own window
    rl.check("a", now=61.0)  # the window slid


def test_releases_beyond_the_rate_limit_get_429():
    c = _client({"SYNTHPROOF_RATE_LIMIT": "2"})
    codes = [c.post("/api/run", json={**RUN, "seed": s}).status_code for s in range(3)]
    assert codes == [200, 200, 429]


def test_rate_limiting_is_on_by_default_for_a_durable_ledger(tmp_path, monkeypatch):
    monkeypatch.setenv("SYNTHPROOF_KEY_DIR", str(tmp_path / "keys"))
    from synthproof.api.context import build_context

    ctx = build_context({"SYNTHPROOF_LEDGER_DB": str(tmp_path / "l.db")})
    assert ctx.rate_limiter.per_minute == 30
    assert build_context({}).rate_limiter.per_minute == 0


# ---------------------------------------------------------------- T4: browser-side attacks


def test_every_response_carries_the_security_headers():
    r = _client({}).get("/api/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["Referrer-Policy"] == "no-referrer"


def test_the_console_gets_a_content_security_policy_without_inline_scripts():
    csp = _client({}).get("/").headers["Content-Security-Policy"]
    assert (
        "script-src 'self'" in csp
        and "unsafe-inline" not in csp.split("script-src")[1].split(";")[0]
    )
    assert "frame-ancestors 'none'" in csp


# ---------------------------------------------------------------- transport (W8)


def test_large_responses_are_compressed():
    r = _client({}).get("/openapi.json", headers={"Accept-Encoding": "gzip"})
    assert r.status_code == 200 and r.headers.get("content-encoding") == "gzip"


def test_the_run_stream_is_never_compressed():
    # A gzipped event stream is buffered until enough bytes accumulate, which would deliver the
    # pipeline log all at once at the end -- the defect the Vite proxy note also guards against.
    with _client({}).stream("POST", "/api/run", json=RUN, headers={"Accept-Encoding": "gzip"}) as r:
        assert r.headers["content-type"].startswith("text/event-stream")
        assert "content-encoding" not in r.headers


def test_hashed_assets_are_cached_but_the_index_is_not():
    from starlette.applications import Starlette
    from starlette.responses import PlainTextResponse
    from starlette.routing import Route

    from synthproof.api.security import ASSET_CACHE, SecurityHeadersMiddleware

    app = Starlette(routes=[
        Route("/", lambda r: PlainTextResponse("index")),
        Route("/assets/index-abc123.js", lambda r: PlainTextResponse("js")),
    ])
    app.add_middleware(SecurityHeadersMiddleware)
    c = TestClient(app)
    assert c.get("/assets/index-abc123.js").headers["Cache-Control"] == ASSET_CACHE
    assert "immutable" not in c.get("/").headers.get("Cache-Control", "")
    assert c.get("/assets/missing.js").status_code == 404
