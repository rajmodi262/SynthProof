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
        "lod_safe": False,
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

        # Check LoD
        audit_ceiling = float(sheet.get("audit_ceiling", 0.0))
        audited_eps = float(sheet.get("total_audited_eps", 0.0))
        proved_eps = float(sheet.get("total_proved_eps", 0.0))

        if audit_ceiling > 0:
            if audited_eps < audit_ceiling:
                results["lod_safe"] = True
                results["lod_status"] = "NOT DETECTED (< LoD)"
            else:
                results["lod_safe"] = False
                results["lod_status"] = "CEILING REACHED (>= LoD)"

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
            "lod_safe": False,
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
