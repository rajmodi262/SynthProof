import json
from pathlib import Path

import pandas as pd
import pytest

from synthproof.capsule.generator import generate_capsule_html
from synthproof.frontier.certificate import PrivacyDataSheet
from synthproof.ledger import signing


def test_generate_capsule_html_basic(tmp_path: Path):
    sk, pk = signing.generate_keypair(key_dir=tmp_path)
    df = pd.DataFrame(
        {
            "age": [25, 45, 65, 30],
            "workclass": ["Private", "Self-emp", "Private", "Federal-gov"],
            "income": ["<=50K", ">50K", "<=50K", ">50K"],
        }
    )

    sheet = PrivacyDataSheet(
        dataset_name="TestAdult",
        num_rows=len(df),
        target_column="income",
        total_proved_eps=1.0,
        delta=1e-5,
        total_audited_eps=0.2,
        audit_ceiling=2.5,
        mechanism="pairwise",
        mechanism_available=True,
        seed=42,
        frontier_curve=[],
        ledger_hash="a" * 64,
    )
    signing.sign_datasheet(sheet, key_path=sk)

    out_file = tmp_path / "test_capsule.html"
    html = generate_capsule_html(sheet, df, output_path=out_file)

    assert out_file.exists()
    assert "SynthProof Verified Capsule" in html
    assert "TestAdult" in html
    assert "pairwise" in html
    assert "Limit of Detection" in html
    assert "NOT DETECTED (< LoD)" in html
    assert sheet.public_key in html


def test_generate_capsule_from_dict(tmp_path: Path):
    df = pd.DataFrame({"x": [1, 2, 3], "y": ["A", "B", "A"]})
    sheet_dict = {
        "dataset_name": "ToyDict",
        "num_rows": 3,
        "target_column": "y",
        "total_proved_eps": 2.0,
        "delta": 1e-5,
        "total_audited_eps": 3.0,
        "audit_ceiling": 2.5,
        "mechanism": "independent",
        "signature": "fake_sig",
        "public_key": "fake_key",
        "signing_payload": "fake_payload",
    }

    out_file = tmp_path / "dict_capsule.html"
    html = generate_capsule_html(sheet_dict, df, output_path=out_file)

    assert out_file.exists()
    assert "CEILING REACHED (>= LoD)" in html
    assert "independent" in html


def test_verify_capsule_offline(tmp_path: Path):
    from synthproof.capsule.generator import extract_capsule_payload, verify_capsule

    sk, pk = signing.generate_keypair(key_dir=tmp_path)
    df = pd.DataFrame({"colA": [10, 20, 30], "colB": ["cat", "dog", "bird"]})

    sheet = PrivacyDataSheet(
        dataset_name="OfflineCapsuleTest",
        num_rows=len(df),
        target_column="colB",
        total_proved_eps=1.5,
        delta=1e-5,
        total_audited_eps=0.5,
        audit_ceiling=2.0,
        mechanism="aim",
        mechanism_available=True,
        seed=123,
        frontier_curve=[],
        ledger_hash="b" * 64,
    )
    signing.sign_datasheet(sheet, key_path=sk)

    capsule_file = tmp_path / "offline_verified.html"
    generate_capsule_html(sheet, df, output_path=capsule_file)

    # 1. Test payload extraction
    extracted = extract_capsule_payload(capsule_file)
    assert extracted["sheet"]["dataset_name"] == "OfflineCapsuleTest"
    assert len(extracted["records"]) == 3

    # 2. Test independent verification
    report = verify_capsule(capsule_file)
    assert report["verified"] is True
    assert report["lod_safe"] is True
    assert report["lod_status"] == "NOT DETECTED (< LoD)"
    assert report["dataset_name"] == "OfflineCapsuleTest"
    assert report["proved_eps"] == 1.5

    # 3. Verification with explicit key path
    report_pk = verify_capsule(capsule_file, key_path=pk)
    assert report_pk["verified"] is True


def test_verify_capsule_tampered(tmp_path: Path):
    from synthproof.capsule.generator import verify_capsule

    sk, pk = signing.generate_keypair(key_dir=tmp_path)
    df = pd.DataFrame({"val": [1, 2, 3]})

    sheet = PrivacyDataSheet(
        dataset_name="TamperTest",
        num_rows=len(df),
        target_column="val",
        total_proved_eps=1.0,
        delta=1e-5,
        total_audited_eps=0.1,
        audit_ceiling=2.0,
        mechanism="pairwise",
        mechanism_available=True,
        seed=99,
        frontier_curve=[],
        ledger_hash="c" * 64,
    )
    signing.sign_datasheet(sheet, key_path=sk)

    capsule_file = tmp_path / "tamper_test.html"
    generate_capsule_html(sheet, df, output_path=capsule_file)

    # Tamper with the HTML content (change total_proved_eps in base64 payload)
    content = capsule_file.read_text(encoding="utf-8")
    import base64
    import re

    m = re.search(r'JSON\.parse\(atob\("([^"]+)"\)\)', content)
    assert m is not None
    payload = json.loads(base64.b64decode(m.group(1).encode("ascii")).decode("utf-8"))
    payload["sheet"]["total_proved_eps"] = 0.01  # Altered!
    tampered_b64 = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
    tampered_html = content.replace(m.group(1), tampered_b64)
    capsule_file.write_text(tampered_html, encoding="utf-8")

    with pytest.raises(signing.SignatureError):
        verify_capsule(capsule_file)
