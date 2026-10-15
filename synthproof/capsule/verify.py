"""Reading an exported capsule back and verifying it: signature, key trust, and audit range."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any, Dict, Optional, Union

from synthproof.ledger import signing


def extract_capsule_payload(html_content_or_path: Union[str, Path]) -> Dict[str, Any]:
    """Extracts the embedded JSON payload from a SynthProof capsule HTML file or string."""
    import re

    if isinstance(html_content_or_path, Path):
        html_content = html_content_or_path.read_text(encoding="utf-8")
    elif isinstance(html_content_or_path, str) and not html_content_or_path.strip().startswith(
        "<!DOCTYPE"
    ):
        p = Path(html_content_or_path)
        if p.exists() and p.is_file():
            html_content = p.read_text(encoding="utf-8")
        else:
            html_content = html_content_or_path
    else:
        html_content = str(html_content_or_path)

    m = re.search(r'JSON\.parse\(atob\("([^"]+)"\)\)', html_content)
    if not m:
        raise ValueError("Not a valid SynthProof capsule: missing embedded payload.")

    b64_str = m.group(1)
    raw_json = base64.b64decode(b64_str.encode("ascii")).decode("utf-8")
    return json.loads(raw_json)


def verify_capsule(
    capsule_html_or_path: Union[str, Path],
    public_key: Optional[signing.ed25519.Ed25519PublicKey] = None,
    key_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Verifies a standalone capsule file or HTML string offline."""
    payload = extract_capsule_payload(capsule_html_or_path)
    sheet = payload.get("sheet", {})
    records = payload.get("records", [])

    embedded_pk = sheet.get("public_key")
    if public_key is not None or key_path is not None:
        key_source = "supplied"
        publisher_authenticated = True
        if public_key is None:
            public_key = signing.load_public_key(key_path)
    else:
        key_source = "embedded"
        publisher_authenticated = False
        if embedded_pk:
            public_key = signing.public_key_from_hex(embedded_pk)
        else:
            raise signing.SignatureError("Capsule sheet is unsigned or missing public key.")

    signing.verify_datasheet(sheet, public_key=public_key, key_path=key_path)

    import hashlib

    raw_pk = public_key.public_bytes(
        encoding=signing.serialization.Encoding.Raw,
        format=signing.serialization.PublicFormat.Raw,
    )
    key_fingerprint = hashlib.sha256(raw_pk).hexdigest()[:16]

    from synthproof.audit.ceiling import range_verdict

    audit_ceiling = float(sheet.get("audit_ceiling") or 0.0)
    audited_eps = float(sheet.get("total_audited_eps") or 0.0)
    proved_eps = float(sheet.get("total_proved_eps") or 0.0)
    verdict = range_verdict(
        proved_eps,
        audited_eps,
        audit_ceiling,
        estimator=sheet.get("audit_estimator"),
        budget=sheet.get("audit_budget"),
        alpha=sheet.get("audit_alpha"),
    )

    return {
        # `verified` is the SIGNATURE. Whether the claim is within the audit's reach is a
        # separate question with its own fields: a valid signature on an out-of-range or
        # internally inconsistent claim is still a valid signature.
        "verified": True,
        "publisher_authenticated": publisher_authenticated,
        "key_source": key_source,
        "key_fingerprint": key_fingerprint,
        "claim_in_audit_range": verdict.claim_in_audit_range,
        "range_code": verdict.code,
        "range_tone": verdict.tone,
        "range_explanation": verdict.explanation,
        "recomputed_ceiling": verdict.recomputed_ceiling,
        "lod_status": verdict.label,
        "proved_eps": proved_eps,
        "audited_eps": audited_eps,
        "audit_ceiling": audit_ceiling,
        "dataset_name": sheet.get("dataset_name"),
        "num_rows": sheet.get("num_rows"),
        "total_records_in_capsule": payload.get("total_records", len(records)),
        "mechanism": sheet.get("mechanism"),
        "ledger_hash": sheet.get("ledger_hash"),
        "public_key": sheet.get("public_key"),
        "signature": sheet.get("signature"),
    }
