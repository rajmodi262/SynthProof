"""The API is built by `create_app(ctx)`, and importing it does nothing.

Until 2026-10-16 importing `synthproof.api.state` opened the ledger database, could write a
signing key into SYNTHPROOF_KEY_DIR and seeded the demo ledger; configuration could only be
changed by reloading modules in the right order. These tests pin the replacement.
"""

import os
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from synthproof.api.context import build_context
from synthproof.api.main import create_app

ROOT = Path(__file__).resolve().parents[1]


def test_importing_the_api_creates_no_ledger_and_no_key(tmp_path):
    db, keys = tmp_path / "ledger.db", tmp_path / "keys"
    env = {**os.environ, "SYNTHPROOF_LEDGER_DB": str(db), "SYNTHPROOF_KEY_DIR": str(keys)}
    code = "import synthproof.api.main, synthproof.api.state, synthproof.api.routes.run"
    subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, check=True)
    assert not db.exists(), "importing the API opened the ledger database"
    assert not keys.exists(), "importing the API wrote a signing key"


def test_two_apps_in_one_process_do_not_share_state():
    a = TestClient(create_app(build_context({})))
    b = TestClient(create_app(build_context({})))
    before = b.get("/api/ledger").json()["count"]
    body = {"dataset": "toy", "mechanism": "independent", "target_eps": 1.0, "rows": 200}
    a.post("/api/run", json={**body, "seed": 1})
    assert a.get("/api/ledger").json()["count"] == before + 1
    assert b.get("/api/ledger").json()["count"] == before


def test_configuration_comes_from_the_environment_passed_in_no_reload_needed():
    open_app = TestClient(create_app(env={}))
    locked = TestClient(create_app(env={"SYNTHPROOF_API_KEYS": "alice=k-alice,bob=k-bob"}))
    assert open_app.get("/api/health").json()["auth"] == "disabled"
    health = locked.get("/api/health").json()
    assert (health["auth"], health["auth_mode"]) == ("required", "per-user")
    assert locked.get("/api/ledger").status_code == 401
    assert locked.get("/api/ledger", headers={"X-API-Key": "k-bob"}).status_code == 200


def test_named_keys_also_narrow_cors():
    """CORS used to narrow only for the shared SYNTHPROOF_API_KEY; named keys left it at '*'."""
    from synthproof.api.main import allowed_origins

    assert allowed_origins({}) == ["*"]
    assert "*" not in allowed_origins({"SYNTHPROOF_API_KEYS": "alice=k"})
    assert allowed_origins({"SYNTHPROOF_CORS_ORIGINS": "https://a.example"}) == [
        "https://a.example"
    ]
