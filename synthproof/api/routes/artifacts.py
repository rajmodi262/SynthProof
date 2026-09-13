"""Artefact routes: emit a capsule or a Croissant record, and verify either.

This is the third-party surface -- everything here exists to hand someone who does not trust
us something they can check. So the verification endpoints fail CLOSED: a malformed or
tampered input returns `verified: false` WITH a reason, never an exception and never a pass.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

router = APIRouter()


class CapsuleExportRequest(BaseModel):
    sheet: Dict[str, Any]
    records: Optional[List[Dict[str, Any]]] = None
    curator_name: str = "SynthProof Autonomous Curator"


@router.post("/api/capsule/export")
def export_capsule_endpoint(req: CapsuleExportRequest):
    """Exports a standalone HTML capsule carrying the data, the proofs and a verifier."""
    from synthproof.capsule.generator import generate_capsule_html

    html_content = generate_capsule_html(
        req.sheet, req.records or [], curator_name=req.curator_name
    )
    return HTMLResponse(content=html_content, media_type="text/html")


class CertificateVerifyRequest(BaseModel):
    sheet: Dict[str, Any]
    public_key: Optional[str] = None


@router.post("/api/certificate/verify")
def verify_certificate_endpoint(req: CertificateVerifyRequest):
    """Independently verifies a Privacy Data Sheet or Croissant 1.1 record."""
    from synthproof.ledger import signing

    sheet = req.sheet
    pubkey = req.public_key or sheet.get("public_key")

    results = {
        "signature_valid": False,
        "claim_in_audit_range": False,
        "range_code": "UNKNOWN",
        "range_tone": "warn",
        "range_explanation": "",
        "lod_status": "UNKNOWN",
        "error": None,
        "details": {},
    }

    try:
        # Check signature
        if pubkey:
            pk = signing.public_key_from_hex(pubkey)
            signing.verify_datasheet(sheet, public_key=pk)
            results["signature_valid"] = True
        else:
            results["error"] = "Missing public key for verification."

        # Could this audit have certified this claim? One verdict, shared with the capsule
        # and the CLI -- see synthproof/audit/ceiling.py for why the old inline check was wrong.
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
        results["claim_in_audit_range"] = verdict.claim_in_audit_range
        results["range_code"] = verdict.code
        results["range_tone"] = verdict.tone
        results["range_explanation"] = verdict.explanation
        results["lod_status"] = verdict.label

        results["details"] = {
            "proved_eps": proved_eps,
            "audited_eps": audited_eps,
            "audit_ceiling": audit_ceiling,
            "mechanism": sheet.get("mechanism"),
            "dataset_name": sheet.get("dataset_name"),
            "num_rows": sheet.get("num_rows"),
            "ledger_hash": sheet.get("ledger_hash"),
        }
    except Exception as e:
        results["error"] = str(e)

    return results


class CapsuleVerifyRequest(BaseModel):
    html_content: str
    key_path: Optional[str] = None


@router.post("/api/capsule/verify")
def verify_capsule_endpoint(req: CapsuleVerifyRequest):
    """Independently verifies an uploaded HTML capsule offline."""
    from synthproof.capsule.generator import verify_capsule

    try:
        report = verify_capsule(req.html_content)
        return report
    except Exception as e:
        return {
            "verified": False,
            "claim_in_audit_range": False,
            "range_code": "ERROR",
            "range_tone": "fail",
            "range_explanation": "",
            "lod_status": "ERROR",
            "error": str(e),
        }


class CroissantExportRequest(BaseModel):
    sheet: Dict[str, Any]


@router.post("/api/croissant/export")
def export_croissant_endpoint(req: CroissantExportRequest):
    """Exports MLCommons Croissant 1.1 JSON-LD specification for a Privacy Data Sheet."""
    from synthproof.frontier.croissant import to_croissant

    try:
        return to_croissant(req.sheet)
    except Exception as e:
        raise HTTPException(400, f"Could not generate Croissant 1.1 record: {e}") from e
