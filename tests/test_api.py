"""Tests for the console's API surface.

The rule these enforce is the one the console depends on: **the API reports only what the
pipeline measured, and names what it cannot do.** A previous console rendered four hardcoded
"PASSED" attack verdicts, one of them for an attack that was never written, so the absence of
fabrication is asserted here rather than assumed.
"""

import io
import json

import pytest
from fastapi.testclient import TestClient

from synthproof.api.main import app

client = TestClient(app)


def _sse_events(text: str):
    """Parses an SSE response body into (event, payload) pairs."""
    out = []
    for frame in text.split("\n\n"):
        event, data = None, []
        for line in frame.split("\n"):
            if line.startswith("event: "):
                event = line[7:].strip()
            elif line.startswith("data: "):
                data.append(line[6:])
        if event and data:
            out.append((event, json.loads("\n".join(data))))
    return out


def _run(**overrides):
    body = {"dataset": "toy", "mechanism": "independent", "target_eps": 1.0,
            "rows": 400, "num_canaries": 15, "seed": 0}
    body.update(overrides)
    res = client.post("/api/run", json=body)
    assert res.status_code == 200
    return _sse_events(res.text)


# ------------------------------------------------------------------ discovery

def test_health_reports_real_ledger_state():
    data = client.get("/api/health").json()
    assert data["status"] == "ok"
    assert data["ledger_verified"] is True
    assert len(data["ledger_head"]) == 64
    assert "independent" in data["mechanisms_available"]


def test_mechanisms_marks_availability_rather_than_hiding_it():
    data = client.get("/api/mechanisms").json()
    keys = {m["key"] for m in data["mechanisms"]}
    assert {"independent", "copula", "pairwise", "aim"} <= keys

    # Every mechanism carries an availability flag, and an unavailable one must explain why
    # instead of silently disappearing from the list.
    for m in data["mechanisms"]:
        assert isinstance(m["available"], bool)
        if not m["available"]:
            assert m["unavailable_reason"]

    # Attacks the project does not implement are advertised as absent.
    names = {a["name"] for a in data["attacks_not_implemented"]}
    assert {"LiRA", "DOMIAS", "Attribute inference"} <= names


def test_datasets_flags_the_toy_table_as_structureless():
    data = client.get("/api/datasets").json()
    toy = next(d for d in data["datasets"] if d["id"] == "toy")
    assert "INDEPENDENT" in (toy["note"] or "")


# ------------------------------------------------------------------ run stream

def test_run_streams_every_stage_in_order():
    events = _run()
    stages = [p["stage"] for e, p in events if e == "stage"]
    assert stages == ["split", "budget", "canaries", "profile", "fit",
                      "generate", "audit", "utility", "attack"]


def test_run_never_charges_more_than_the_requested_budget():
    """The headline claim: a requested epsilon is the epsilon you are charged."""
    events = _run(target_eps=2.0)
    done = next(p for e, p in events if e == "done")
    proved = done["measurements"]["proved_eps"]
    assert 0.0 < proved <= 2.0 * 1.02
    assert proved > 2.0 * 0.7, "calibration is leaving most of the budget unspent"


def test_run_returns_measured_clouds_not_placeholders():
    events = _run()
    done = next(p for e, p in events if e == "done")
    cloud = done["cloud"]

    assert cloud["method"] in ("pca", "columns")
    assert len(cloud["real"]) > 0 and len(cloud["synthetic"]) > 0
    assert len(cloud["canaries"]) == 15
    assert all(len(p) == 3 for p in cloud["real"])
    # Real and synthetic must be distinct clouds; identical ones would mean the projection
    # is echoing its input rather than projecting the generator's output.
    assert cloud["real"] != cloud["synthetic"]


def test_run_reports_every_accountant_charge():
    events = _run()
    done = next(p for e, p in events if e == "done")
    assert len(done["spends"]) >= 2
    for s in done["spends"]:
        assert s["marginal_eps"] >= 0.0
        assert s["mechanism"] in ("gaussian", "laplace")


def test_run_result_carries_no_fabricated_attack_verdicts():
    events = _run()
    done = next(p for e, p in events if e == "done")
    assert done["attack"]["name"] == "Distance MIA baseline"
    assert "NOT LiRA" in done["attack"]["note"]
    assert done["attacks_not_implemented"]
    # The sheet must not claim a signature it does not have.
    assert done["ledger"]["signed"] is False


def test_run_appends_to_the_ledger_and_keeps_it_verifiable():
    before = client.get("/api/ledger").json()["count"]
    events = _run()
    done = next(p for e, p in events if e == "done")
    after = client.get("/api/ledger").json()

    assert after["count"] == before + 1
    assert after["verified"] is True
    assert done["ledger"]["hash"] == after["head"]


def test_run_rejects_an_unavailable_mechanism_over_the_stream():
    events = _run(mechanism="does_not_exist")
    kinds = [e for e, _ in events]
    assert "error" in kinds
    assert "done" not in kinds


def test_run_rejects_an_unknown_dataset():
    events = _run(dataset="nope")
    err = next(p for e, p in events if e == "error")
    assert "Unknown dataset" in err["message"]


# ------------------------------------------------------------------ upload

def test_upload_accepts_a_csv_and_warns_that_inferred_bounds_leak():
    csv = "age,income,grp\n" + "".join(
        f"{20 + i % 40},{30000 + i * 7},{'a' if i % 2 else 'b'}\n" for i in range(200)
    )
    res = client.post(
        "/api/upload",
        files={"file": ("people.csv", io.BytesIO(csv.encode()), "text/csv")},
    )
    assert res.status_code == 200
    data = res.json()

    assert data["id"].startswith("upload:")
    assert data["dataset"]["rows"] == 200
    assert data["schema_inferred"] is True
    # The leak has to be stated, not buried: bounds read from the data are not safe.
    assert "leak" in (data["warning"] or "").lower()

    # It must then be selectable as a dataset and actually runnable.
    ids = {d["id"] for d in client.get("/api/datasets").json()["datasets"]}
    assert data["id"] in ids

    events = _run(dataset=data["id"], rows=200, num_canaries=10)
    assert any(e == "done" for e, _ in events)


def test_upload_rejects_non_csv():
    res = client.post(
        "/api/upload",
        files={"file": ("model.bin", io.BytesIO(b"\x00\x01"), "application/octet-stream")},
    )
    assert res.status_code == 400


def test_upload_rejects_a_table_with_no_complete_rows():
    res = client.post(
        "/api/upload",
        files={"file": ("empty.csv", io.BytesIO(b"a,b\n,\n"), "text/csv")},
    )
    assert res.status_code == 400


# ------------------------------------------------------------------ ledger demo

def test_tampering_breaks_the_chain_from_that_entry_onward():
    """The demo's central claim: the chain is tamper-EVIDENT."""
    client.post("/api/ledger/reset")
    _run(seed=1)
    _run(seed=2)
    _run(seed=3)

    state = client.get("/api/ledger").json()
    assert state["verified"] is True
    assert state["count"] == 3

    target = state["entries"][1]["entry_id"]
    res = client.post("/api/ledger/tamper", json={"entry_id": target, "eps_spent": 0.01}).json()

    assert res["verified"] is False
    assert res["broken_from_index"] == 1
    assert res["broken_count"] == 2, "the altered entry and every later one must be invalid"
    assert client.get("/api/ledger").json()["verified"] is False

    client.post("/api/ledger/reset")
    assert client.get("/api/ledger").json()["verified"] is True


def test_tampering_an_unknown_entry_is_a_404():
    assert client.post("/api/ledger/tamper",
                       json={"entry_id": "nope", "eps_spent": 0.1}).status_code == 404


def test_ledger_accumulates_spend_across_releases():
    """Budget erosion across releases is the threat the ledger exists to make visible."""
    client.post("/api/ledger/reset")
    _run(target_eps=1.0, seed=1)
    _run(target_eps=1.0, seed=2)

    state = client.get("/api/ledger").json()
    assert state["count"] == 2
    # Two releases at eps=1 each cost roughly 2 in total, not 1.
    assert state["total_eps_spent"] > 1.5
    client.post("/api/ledger/reset")


@pytest.mark.parametrize("bad", [
    {"target_eps": -1.0},
    {"target_eps": 0},
    {"num_canaries": 0},
    {"rows": 10},
])
def test_run_request_validation_rejects_nonsense(bad):
    body = {"dataset": "toy", "mechanism": "independent", "target_eps": 1.0,
            "rows": 400, "num_canaries": 15, "seed": 0}
    body.update(bad)
    assert client.post("/api/run", json=body).status_code == 422


def test_index_serves_a_pointer_when_the_console_is_not_built():
    res = client.get("/")
    assert res.status_code == 200
    assert "SynthProof" in res.text
