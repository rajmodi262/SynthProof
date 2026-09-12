"""Comprehensive verification that all demo CSV datasets run 100% cleanly through the SynthProof pipeline.
"""

from pathlib import Path
import io
import json
import pytest
from starlette.testclient import TestClient

from synthproof.api.main import app

client = TestClient(app)

DATASETS_DIR = Path(__file__).resolve().parent.parent / "demo_datasets"


def _parse_sse(text: str):
    out = []
    for block in text.strip().split("\r\n\r\n" if "\r\n\r\n" in text else "\n\n"):
        if not block.strip():
            continue
        event = None
        data = []
        for line in block.splitlines():
            if line.startswith("event: "):
                event = line[7:].strip()
            elif line.startswith("data: "):
                data.append(line[6:])
        if event and data:
            out.append((event, json.loads("\n".join(data))))
    return out


DEMO_FILES = [
    "01_healthcare_patient_outcomes.csv",
    "02_financial_credit_risk.csv",
    "03_telecom_customer_churn.csv",
    "04_hr_employee_attrition.csv",
    "05_quick_demo_demographics.csv",
]


@pytest.mark.parametrize("filename", DEMO_FILES)
def test_demo_csv_uploads_and_runs_successfully(filename: str):
    filepath = DATASETS_DIR / filename
    assert filepath.exists(), f"Missing demo CSV: {filepath}"
    
    # 1. Upload CSV to API
    with open(filepath, "rb") as f:
        upload_res = client.post(
            "/api/upload",
            files={"file": (filename, f, "text/csv")},
        )
    assert upload_res.status_code == 200, f"Upload failed: {upload_res.text}"
    data = upload_res.json()
    upload_id = data["id"]
    assert upload_id.startswith("upload:")
    assert data["dataset"]["rows"] > 0
    assert len(data["dataset"]["numerical"]) >= 2
    assert len(data["dataset"]["categorical"]) >= 1

    # 2. Run Release with pairwise mechanism on uploaded dataset
    run_res = client.post(
        "/api/run",
        json={
            "dataset": upload_id,
            "mechanism": "pairwise",
            "target_eps": 1.0,
            "num_canaries": 20,
            "rows": 400,
            "seed": 42,
        },
    )
    assert run_res.status_code == 200, f"Run failed: {run_res.text}"
    
    events = _parse_sse(run_res.text)
    event_names = [e for e, _ in events]
    
    assert "stage" in event_names
    assert "done" in event_names
    assert "error" not in event_names
    
    done_payload = next(p for e, p in events if e == "done")
    assert "measurements" in done_payload
    assert "evaluation" in done_payload
    assert "ledger" in done_payload
    assert done_payload["measurements"]["proved_eps"] > 0
    assert "tstr_f1" in done_payload["measurements"]
    assert done_payload["sheet"]["evaluation"]["tstr_f1"] >= 0
    assert done_payload["sheet"]["evaluation"]["mia_auc"] >= 0.4
