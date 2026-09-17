"""Conformance runner for the DP Release Label spec (docs/design/DP_RELEASE_LABEL_SPEC.md).

This is the EXECUTABLE definition of conformance. It composes three checks that already exist in
the codebase and reports one verdict:

  1. Signature      -- Ed25519 over the label's canonical bytes (synthproof.ledger.signing /
                       synthproof.frontier.croissant.verify_croissant).
  2. Operating range -- the (proved, audited, ceiling) triple is present and coherent, so an
                       audited epsilon is never read as reassurance when the instrument could not
                       have detected the proved budget.
  3. Boundary       -- boundary-audit RB1..RB10 reports NO `leak`.

For a Croissant record, the full claim also needs the OFFICIAL MLCommons validator, which runs out
of band in scripts/validate_croissant.py (its deps conflict with the numpy AIM needs). This runner
points at it rather than re-implementing it.

CONFORMANCE IS NOT PRIVACY. By the asymmetry principle (see the spec, section 1) the checker reads
only the artefact, so it can prove a channel is OPEN but never that one is CLOSED. A conformant
label is a release whose openable channels cannot be hidden from a reader who runs this -- not a
release that is private.

Usage:
    python scripts/validate_release_label.py LABEL.json [--pubkey KEY.pub] [--json]

Exit codes (deliberately distinct so an un-run check never reads as a pass):
    0  conformant       -- signature verified, operating range coherent, no leak
    1  non-conformant   -- a leak, a broken/altered/missing-when-required signature, or a bad range
    2  not fully checked -- signature present but --pubkey not pinned, or the audit is uninformative
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Import from the installed package. The runner is a thin composition layer; the logic lives in
# the modules it calls, which are themselves tested.
from synthproof.audit import boundary
from synthproof.frontier import croissant as croissant_mod
from synthproof.ledger import signing

OK, WARN, FAIL = "ok", "warn", "fail"


def _is_croissant(doc: Dict[str, Any]) -> bool:
    return isinstance(doc.get("dp:privacyDataSheet"), dict) or "@context" in doc


def _sheet_of(doc: Dict[str, Any]) -> Dict[str, Any]:
    sheet = doc.get("dp:privacyDataSheet")
    return sheet if isinstance(sheet, dict) else doc


# --------------------------------------------------------------------------- check 1: signature


def check_signature(doc: Dict[str, Any], pubkey: Optional[Path]) -> Tuple[str, str]:
    """Returns (tone, message). tone ok=verified/pinned, warn=self-consistent-but-unpinned,
    fail=broken/altered/missing-when-required."""
    sheet = _sheet_of(doc)
    if not sheet.get("signature"):
        return FAIL, "unsigned: the label carries no Ed25519 signature (spec 4.2a requires one)"

    if pubkey is not None:
        try:
            if _is_croissant(doc):
                croissant_mod.verify_croissant(doc, key_path=pubkey)
            else:
                signing.verify_datasheet(sheet, key_path=pubkey)
        except (signing.SignatureError, croissant_mod.CroissantError) as exc:
            return FAIL, f"signature does NOT verify against {pubkey.name}: {exc}"
        return OK, f"signature verified against pinned key {pubkey.name}"

    # No pinned key. Do an INTEGRITY-ONLY check against the embedded key: this proves the bytes
    # were not altered after signing, but NOT who signed them. The spec calls this exit code 2.
    embedded = sheet.get("public_key")
    if not embedded:
        return WARN, "signed, but no public_key embedded and no --pubkey given: trust unestablished"
    try:
        key = signing.public_key_from_hex(embedded)
        signing.verify_datasheet(sheet, public_key=key)
    except (signing.SignatureError, ValueError) as exc:
        return FAIL, f"signature is present but does not verify even against its own key: {exc}"
    return (
        WARN,
        "signature is self-consistent with its embedded key, but that key is not pinned. "
        "Supply --pubkey to establish trust (a sheet that carries its own key proves only that "
        "it signed itself).",
    )


# --------------------------------------------------------------------------- check 2: range


def check_operating_range(doc: Dict[str, Any]) -> Tuple[str, str]:
    sheet = _sheet_of(doc)
    proved = sheet.get("total_proved_eps")
    audited = sheet.get("total_audited_eps")
    ceiling = sheet.get("audit_ceiling")
    missing = [
        name
        for name, val in (
            ("total_proved_eps", proved),
            ("total_audited_eps", audited),
            ("audit_ceiling", ceiling),
        )
        if val is None
    ]
    if missing:
        return FAIL, f"operating range incomplete: missing {', '.join(missing)} (spec 4.2b)"
    if audited > ceiling + 1e-9:
        return (
            FAIL,
            f"incoherent range: audited eps {audited:.3f} exceeds the audit ceiling "
            f"{ceiling:.3f} -- the audit reported more than it could provably detect",
        )
    if ceiling + 1e-9 < proved:
        return (
            WARN,
            f"range coherent but audit is UNINFORMATIVE: ceiling {ceiling:.3f} < proved "
            f"{proved:.3f}, so audited eps {audited:.3f} means the instrument could not have "
            "detected the proved budget -- not that nothing leaked",
        )
    return (
        OK,
        f"operating range coherent: audited {audited:.3f} <= ceiling {ceiling:.3f}, "
        f"proved {proved:.3f}",
    )


# --------------------------------------------------------------------------- check 3: boundary


def check_boundary(doc: Dict[str, Any]) -> Tuple[str, str, List[Dict[str, str]]]:
    report = boundary.audit_release(doc)
    leaks = report.leaks
    unver = report.unverifiable
    findings = [f.to_dict() for f in report.findings]
    if leaks:
        codes = ", ".join(f"{f.code} ({f.field})" for f in leaks)
        return FAIL, f"{len(leaks)} open channel(s) leak outside epsilon: {codes}", findings
    # Unverifiable channels do NOT fail conformance: every honest label has them (a declared row
    # count is always unverifiable). Conformance = no leak (spec section 5). They are reported, not
    # penalised -- the asymmetry principle means the checker can never settle them.
    if unver:
        return (
            OK,
            f"no leak; {len(unver)} channel(s) rest on producer honesty (unverifiable, reported)",
            findings,
        )
    return OK, "no open channel found (RB1-RB14 clean)", findings


# --------------------------------------------------------------------------- compose


def validate(doc: Dict[str, Any], pubkey: Optional[Path]) -> Dict[str, Any]:
    sig_tone, sig_msg = check_signature(doc, pubkey)
    rng_tone, rng_msg = check_operating_range(doc)
    bnd_tone, bnd_msg, findings = check_boundary(doc)

    # Verdict: FAIL on any fail -> exit 1. Otherwise WARN present (untrusted sig / uninformative
    # audit) -> exit 2 (not fully checked). All ok -> exit 0.
    tones = (sig_tone, rng_tone, bnd_tone)
    if FAIL in tones:
        verdict, exit_code = "non-conformant", 1
    elif WARN in tones:
        verdict, exit_code = "not-fully-checked", 2
    else:
        verdict, exit_code = "conformant", 0

    return {
        "artefact": "croissant" if _is_croissant(doc) else "privacy-data-sheet",
        "verdict": verdict,
        "exit_code": exit_code,
        "checks": {
            "signature": {"tone": sig_tone, "message": sig_msg},
            "operating_range": {"tone": rng_tone, "message": rng_msg},
            "boundary": {"tone": bnd_tone, "message": bnd_msg},
        },
        "boundary_findings": findings,
    }


def render(result: Dict[str, Any]) -> str:
    mark = {OK: "  ok  ", WARN: " warn ", FAIL: " FAIL "}
    lines = [
        f"DP Release Label conformance -- {result['artefact']}",
        "",
    ]
    for name, key in (
        ("signature      ", "signature"),
        ("operating range", "operating_range"),
        ("boundary       ", "boundary"),
    ):
        c = result["checks"][key]
        lines.append(f"  [{mark[c['tone']]}] {name}  {c['message']}")
    lines.append("")
    verdict = result["verdict"]
    banner = {
        "conformant": "CONFORMANT (exit 0). NOT a proof of privacy -- see the asymmetry principle.",
        "not-fully-checked": "NOT FULLY CHECKED (exit 2): a signature is unpinned or the audit is "
        "uninformative. Nothing failed, but trust is not established.",
        "non-conformant": "NON-CONFORMANT (exit 1): the label leaks, is unsigned/altered, or its "
        "operating range is incoherent.",
    }[verdict]
    lines.append(banner)
    if result["artefact"] == "croissant":
        lines.append(
            "  For the full claim also run scripts/validate_croissant.py (official MLCommons "
            "validator, isolated env)."
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("label", type=Path, help="Privacy Data Sheet or Croissant record JSON.")
    parser.add_argument(
        "--pubkey",
        type=Path,
        default=None,
        help="Expected Ed25519 public key. Without it, a present signature is reported "
        "self-consistent-but-unpinned (exit 2), never as trusted.",
    )
    parser.add_argument("--json", dest="as_json", action="store_true", help="Emit JSON.")
    args = parser.parse_args()

    if not args.label.exists():
        print(f"No such file: {args.label}")
        return 2
    try:
        doc = json.loads(args.label.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"{args.label} is not JSON: {exc}")
        return 2
    if not isinstance(doc, dict):
        print(f"{args.label} is not a sheet or a Croissant record.")
        return 2

    result = validate(doc, args.pubkey)
    if getattr(args, "as_json", False):
        print(json.dumps(result, indent=2))
    else:
        print(render(result))
    return result["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
