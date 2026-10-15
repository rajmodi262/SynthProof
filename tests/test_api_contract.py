"""The OpenAPI document is the console's contract, and it is enforced, not just written down.

Before 2026-10-16 the console's types were hand-written and had drifted from the server. Now:
responses are validated against `synthproof/api/schemas.py`, the document is exported to
`web/src/api/openapi.json`, and the console's types are generated from it. These tests pin the
server half; CI regenerates the TypeScript and fails on a diff (the console job).
"""

import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from synthproof.api import schemas
from synthproof.api.context import build_context
from synthproof.api.main import create_app

ROOT = Path(__file__).resolve().parents[1]


def test_the_committed_openapi_document_is_current():
    out = subprocess.run(
        [sys.executable, "scripts/export_openapi.py", "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert out.returncode == 0, out.stdout + out.stderr


def test_the_run_stream_frames_are_in_the_document():
    spec = create_app(build_context({}), env={}).openapi()
    comps = spec["components"]["schemas"]
    assert {"RunStartFrame", "RunDoneFrame", "Measurements", "AuditResult"} <= set(comps)
    content = spec["paths"]["/api/run"]["post"]["responses"]["200"]["content"]
    refs = {r["$ref"] for r in content["text/event-stream"]["schema"]["oneOf"]}
    assert refs == {"#/components/schemas/RunStartFrame", "#/components/schemas/RunDoneFrame"}


def test_a_field_the_contract_does_not_know_is_rejected():
    """extra='forbid': a server-side addition must go through the schema, or it fails here."""
    good = {
        "verified": True,
        "head": "h",
        "count": 0,
        "total_eps_spent": 0.0,
        "eps_by_actor": {},
        "entries": [],
    }
    schemas.LedgerState.model_validate(good)
    with pytest.raises(ValidationError):
        schemas.LedgerState.model_validate({**good, "surprise": 1})


def test_a_cloud_point_must_be_a_triple():
    base = {"axes": ["a", "b", "c"], "method": "pca", "explained_variance": [], "canaries": []}
    schemas.Cloud.model_validate({**base, "real": [[0, 0, 0]], "synthetic": []})
    with pytest.raises(ValidationError):
        schemas.Cloud.model_validate({**base, "real": [[0, 0]], "synthetic": []})


def test_every_json_endpoint_declares_its_response_model():
    spec = create_app(build_context({}), env={}).openapi()
    for path in ("/api/health", "/api/mechanisms", "/api/datasets", "/api/ledger"):
        schema = spec["paths"][path]["get"]["responses"]["200"]["content"]["application/json"][
            "schema"
        ]
        assert "$ref" in schema, f"{path} has no response model"
