"""Unit tests for FastAPI endpoints."""

from fastapi.testclient import TestClient
from synthproof.api.main import app

client = TestClient(app)


def test_api_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["ledger_verified"] is True


def test_api_ledger_endpoint():
    response = client.get("/api/ledger")
    assert response.status_code == 200
    data = response.json()
    assert data["verified"] is True
    assert "entries" in data


def test_api_synthesize_endpoint():
    response = client.post(
        "/api/synthesize",
        json={"mechanism": "AIM / MST", "target_eps": 1.0, "num_samples": 50}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "datasheet" in data
    assert data["ledger_verified"] is True


def test_api_index_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert "SynthProof" in response.text
