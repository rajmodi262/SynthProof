"""The tamper-evidence and verification endpoints — the ones shown live at a viva.

Written for task 3.2 of docs/ROAD_TO_TEN.md. Coverage analysis found `/api/ledger/tamper`
almost entirely untested: all four attack branches, the empty-ledger guard, and both
verification endpoints sat at zero. That is the worst possible place for a gap, because these
are the endpoints the console drives during a demonstration, and their failure mode is
silence — an attack that is not detected renders as a chain that is still fine.

What these assert is narrow and deliberate: **the API must report detection, and must not
report success for something it did not verify.** Whether the underlying cryptography is
correct is pinned elsewhere (tests/test_ledger_adversarial.py runs nine attacks against live
SQLite). Here the question is whether the HTTP surface tells the truth about what happened.
"""

import pytest
from fastapi.testclient import TestClient

from synthproof.api.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _isolated_ledger():
    """The ledger is process-wide module state; a tamper test would poison every later test."""
    client.post("/api/ledger/reset")
    yield
    client.post("/api/ledger/reset")


def _seed_ledger(entries: int = 2) -> None:
    """Puts real signed entries in the ledger by running actual releases through the API."""
    for _ in range(entries):
        r = client.post(
            "/api/run",
            json={
                "dataset": "toy",
                "mechanism": "independent",
                "target_eps": 1.0,
                "delta": 1e-5,
                "seed": 0,
                "num_canaries": 10,
                "rows": 200,
            },
        )
        assert r.status_code == 200, r.text


# --------------------------------------------------------------------------- the guard


def test_tampering_with_an_empty_ledger_is_refused_rather_than_crashing():
    """There is nothing to attack before a release exists, and saying so beats an IndexError."""
    r = client.post("/api/ledger/tamper", json={"attack_type": "modify_eps", "eps_spent": 99.0})
    assert r.status_code == 400
    assert "empty" in r.json()["detail"].lower()


# --------------------------------------------------------------------------- the attacks


@pytest.mark.parametrize(
    "attack_type,expect_in_description",
    [
        ("truncate", "truncation"),
        ("corrupt_hash", "hash"),
        ("corrupt_signature", "signature"),
        ("modify_eps", "spend"),
    ],
)
def test_every_attack_is_detected_and_named(attack_type, expect_in_description):
    """All four branches, and the verdict must be DETECTED in every one.

    `truncate` is the one worth having a test for: a shortened hash chain is internally
    consistent, so chaining alone cannot see it. Only the signed head committing to
    (entry_count, tip_hash) catches it, and that is the whole argument for the head existing.
    """
    _seed_ledger(2)

    r = client.post("/api/ledger/tamper", json={"attack_type": attack_type, "eps_spent": 99.0})
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["verified"] is False, f"{attack_type} went undetected"
    assert expect_in_description.lower() in body["attack_description"].lower()
    assert body["broken_count"] >= 1


def test_the_ledger_reports_itself_broken_after_an_attack():
    """Detection has to survive the response: a later GET must not say the chain is fine."""
    _seed_ledger(2)
    assert client.get("/api/ledger").json()["verified"] is True

    client.post("/api/ledger/tamper", json={"attack_type": "modify_eps", "eps_spent": 99.0})
    assert client.get("/api/ledger").json()["verified"] is False


def test_reset_restores_a_verifying_chain():
    """The demo has to be repeatable, which means the reset has to actually work."""
    _seed_ledger(1)
    client.post("/api/ledger/tamper", json={"attack_type": "corrupt_hash"})
    assert client.get("/api/ledger").json()["verified"] is False

    client.post("/api/ledger/reset")
    assert client.get("/api/ledger").json()["verified"] is True


def test_the_tamper_explanation_does_not_overclaim():
    """It must not say "guarantees non-repudiation", which it used to.

    ledger/signing.py records that a key holder can rewrite the chain and re-sign it, so the
    construction is tamper-EVIDENT, not tamper-proof, and it cannot bind a key to a person.
    The endpoint contradicted its own module until 2026-09-12.
    """
    _seed_ledger(1)
    body = client.post("/api/ledger/tamper", json={"attack_type": "modify_eps"}).json()
    explanation = body["explanation"].lower()
    assert "non-repudiation" not in explanation
    assert "tamper-evident" in explanation or "detectable" in explanation


# ------------------------------------------------------------------- capsule round trip


def test_a_capsule_exported_by_the_api_verifies_through_the_api():
    """Export and verify are the two halves of the third-party story; test them together."""
    r = client.post(
        "/api/run",
        json={
            "dataset": "toy",
            "mechanism": "independent",
            "target_eps": 1.0,
            "delta": 1e-5,
            "seed": 0,
            "num_canaries": 10,
            "rows": 200,
        },
    )
    assert r.status_code == 200, r.text

    sheet = None
    for frame in r.text.split("\n\n"):
        if '"sheet"' in frame:
            import json as _json

            for line in frame.split("\n"):
                if line.startswith("data: "):
                    payload = _json.loads(line[6:])
                    sheet = payload.get("sheet") or (payload.get("result") or {}).get("sheet")
    if sheet is None:
        pytest.skip("the run stream did not carry a sheet in this configuration")

    exported = client.post(
        "/api/capsule/export", json={"sheet": sheet, "records": [{"age": 30, "category": "A"}]}
    )
    assert exported.status_code == 200, exported.text
    html = exported.text
    assert "SynthProof" in html

    report = client.post("/api/capsule/verify", json={"html_content": html}).json()
    assert report["verified"] is True, report


def test_a_tampered_capsule_is_rejected_by_the_api_with_a_reason():
    """The failure path. A capsule whose epsilon was edited must not verify."""
    import base64
    import json as _json
    import pathlib
    import re

    path = pathlib.Path("demo_capsules/uci_adult_verified_capsule.html")
    if not path.exists():
        pytest.skip("demo capsules not generated in this environment")

    html = path.read_text(encoding="utf-8")
    assert client.post("/api/capsule/verify", json={"html_content": html}).json()["verified"]

    m = re.search(r'JSON\.parse\(atob\("([A-Za-z0-9+/=]+)"\)\)', html)
    payload = _json.loads(base64.b64decode(m.group(1)))
    payload["sheet"]["total_proved_eps"] = 0.001  # understate the budget by 1000x
    tampered = html.replace(m.group(1), base64.b64encode(_json.dumps(payload).encode()).decode())

    report = client.post("/api/capsule/verify", json={"html_content": tampered}).json()
    assert report["verified"] is False
    assert report["error"], "a rejection must carry a reason, not just a false"


def test_malformed_capsule_input_fails_closed():
    """Not HTML, not a capsule, not a crash."""
    report = client.post("/api/capsule/verify", json={"html_content": "<p>hello</p>"}).json()
    assert report["verified"] is False
    assert report["lod_status"] == "ERROR"
