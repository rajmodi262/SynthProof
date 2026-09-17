"""Build one trustworthy DP synthetic-data release and PROVE every gate passes.

This is the runnable artifact an examiner (or a reviewer) can execute end to end:

    synthesise -> sign (Ed25519) -> emit Croissant -> and then check, from the artifacts alone:
      GATE 1  boundary-audit RB1-RB14 report NO leak
      GATE 2  the DP Release Label is CONFORMANT (signature + operating range + boundary)
      GATE 3  the Ed25519 signature verifies against the published public key
      GATE 4  (optional) the OFFICIAL MLCommons validator accepts the Croissant record

Every gate is asserted, not assumed. The script exits non-zero if any HARD gate (1-3) fails, and
writes a single `release_report.json` bundling the artifact paths, their SHA-256s, and each gate's
verdict -- so "this release is trustworthy" becomes a claim a third party can re-check rather than
take on faith. GATE 4 is soft: its "not checked" (exit 2, no isolated env) is kept distinct from a
pass, so an un-run validator never reads as green.

Nothing here is novel on its own; it is the project's existing pieces (FrontierEngine, the Ed25519
signer, the Croissant emitter, boundary-audit, validate_release_label, validate_croissant) wired
into one gated command. The value is that the whole chain is reproducible and self-checking.

Usage:
    python -m scripts.build_release --dataset toy --mechanism aim --eps 2.0
    python -m scripts.build_release --dataset diabetes --mechanism mst --outdir release/diabetes
    python -m scripts.build_release --dataset adult --mechanism aim --eps 8.0 --mlcommons
"""

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

from synthproof.audit import boundary
from synthproof.data.dataset import TabularDataset
from synthproof.frontier import croissant as croissant_mod
from synthproof.frontier.certificate import FrontierEngine
from synthproof.ledger import signing

N_ROWS = 6000  # subsample size, matching the H1 protocol so a release is comparable to the grid


def _load(name: str) -> TabularDataset:
    """Load a dataset under its public schema (domain_source stays 'declared')."""
    if name == "toy":
        return TabularDataset.create_synthetic_toy(num_rows=1000)
    if name == "adult":
        from synthproof.data.datasets import load_adult

        ds = load_adult()
    elif name == "bank":
        from synthproof.data.datasets import load_bank_marketing

        ds = load_bank_marketing()
    elif name == "diabetes":
        from synthproof.data.datasets import load_diabetes130

        ds = load_diabetes130()
    else:
        raise SystemExit(f"unknown dataset {name!r}; choose toy/adult/bank/diabetes")
    ds.df = ds.df.sample(n=min(N_ROWS, len(ds.df)), random_state=0).reset_index(drop=True)
    return ds


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset", default="toy", help="toy | adult | bank | diabetes")
    ap.add_argument("--mechanism", default="aim")
    ap.add_argument("--eps", type=float, default=2.0)
    ap.add_argument("--delta", type=float, default=1e-5)
    ap.add_argument("--canaries", type=int, default=30)
    ap.add_argument("--outdir", default="release/out")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument(
        "--mlcommons",
        action="store_true",
        help="also run GATE 4, the official MLCommons validator (needs the isolated env; see "
        "scripts/validate_croissant.py --setup).",
    )
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    key_dir = outdir / "keys"

    print(f"[setup]  dataset={args.dataset} mechanism={args.mechanism} eps={args.eps}")
    ds = _load(args.dataset)
    from synthproof.frontier.experiment import MECHANISMS

    if args.mechanism not in MECHANISMS:
        raise SystemExit(f"unknown mechanism {args.mechanism!r}; available: {sorted(MECHANISMS)}")

    # A fresh signing key for this release (real releases reuse a persistent curator key).
    priv_path, pub_path = signing.generate_keypair(key_dir=key_dir, overwrite=True)
    fingerprint_key = signing.load_fingerprint_key(key_dir=key_dir, create=True)

    print("[synth]  running the mechanism + audit (this is the slow step) ...")
    engine = FrontierEngine(seed=args.seed)
    sheet = engine.run_sweep(
        ds,
        eps_grid=[args.eps],
        delta=args.delta,
        mechanism=args.mechanism,
        num_canaries=args.canaries,
        domain_source="declared",  # the schema is public -> RB6 clean
        release_rows=ds.num_rows,  # operator-chosen public size -> RB2 clean
        retain_release=True,
        fingerprint_key=fingerprint_key,  # keyed HMAC -> RB3 not an unkeyed membership test
        skip_preflight=(args.dataset == "toy"),
    )
    signing.sign_datasheet(sheet, key_path=key_dir / signing.PRIVATE_KEY_NAME)

    # ---- write the artifacts -------------------------------------------------------------
    sheet_path = outdir / "privacy_data_sheet.json"
    csv_path = outdir / "synthetic.csv"
    croissant_path = outdir / "release.croissant.json"

    sheet_path.write_text(sheet.to_json(), encoding="utf-8")
    if engine.last_release is None:
        raise SystemExit("no retained release; this is a bug (retain_release was set).")
    engine.last_release.to_csv(csv_path, index=False)
    data_sha = _sha256(csv_path)

    record = croissant_mod.to_croissant(
        json.loads(sheet_path.read_text(encoding="utf-8")),
        columns=croissant_mod.columns_from_schema(ds.schema),
        data_url=csv_path.name,
        data_sha256=data_sha,
        date_published=date.today().isoformat(),
    )
    croissant_path.write_text(croissant_mod.to_json(record), encoding="utf-8")

    # ---- the gates -----------------------------------------------------------------------
    gates = {}

    # GATE 1: boundary-audit RB1-RB14, no leak.
    report = boundary.audit_release(json.loads(sheet_path.read_text(encoding="utf-8")))
    gates["boundary_audit"] = {
        "pass": report.passed,
        "leaks": len(report.leaks),
        "unverifiable": len(report.unverifiable),
        "detail": [f"{f.code}:{f.severity}" for f in report.findings],
    }

    # GATE 2: DP Release Label conformance (signature + operating range + boundary).
    from scripts.validate_release_label import validate as validate_label

    label = validate_label(json.loads(sheet_path.read_text(encoding="utf-8")), pub_path)
    gates["release_label"] = {
        "pass": label["exit_code"] == 0,
        "verdict": label["verdict"],
        "checks": {k: v["tone"] for k, v in label["checks"].items()},
    }

    # GATE 3: the signature verifies against the published public key.
    try:
        signing.verify_datasheet(
            json.loads(sheet_path.read_text(encoding="utf-8")), key_path=pub_path
        )
        gates["signature_verifies"] = {"pass": True}
    except signing.SignatureError as exc:
        gates["signature_verifies"] = {"pass": False, "error": str(exc)}

    # GATE 4 (soft): the official MLCommons validator, out of band.
    if args.mlcommons:
        proc = subprocess.run(
            [sys.executable, "scripts/validate_croissant.py", str(croissant_path)],
            capture_output=True,
            text=True,
        )
        gates["mlcommons_validator"] = {
            "exit_code": proc.returncode,
            "pass": proc.returncode == 0,
            "checked": proc.returncode != 2,  # 2 == isolated env absent == NOT checked
            "tail": proc.stdout.strip().splitlines()[-3:] if proc.stdout else [],
        }

    hard_gates = ["boundary_audit", "release_label", "signature_verifies"]
    all_hard_pass = all(gates[g]["pass"] for g in hard_gates)

    bundle = {
        "dataset": args.dataset,
        "mechanism": args.mechanism,
        "eps_requested": args.eps,
        "eps_proved": sheet.total_proved_eps,
        "rows": ds.num_rows,
        "artifacts": {
            "privacy_data_sheet": {"path": str(sheet_path), "sha256": _sha256(sheet_path)},
            "synthetic_csv": {"path": str(csv_path), "sha256": data_sha},
            "croissant_record": {"path": str(croissant_path), "sha256": _sha256(croissant_path)},
            "public_key": {"path": str(pub_path), "sha256": _sha256(pub_path)},
        },
        "gates": gates,
        "all_hard_gates_pass": all_hard_pass,
    }
    report_path = outdir / "release_report.json"
    report_path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")

    # ---- human summary -------------------------------------------------------------------
    def mark(ok):
        return "PASS" if ok else "FAIL"

    print("\n" + "=" * 64)
    print(f"RELEASE BUNDLE  ->  {outdir}")
    print("=" * 64)
    print(f"  eps requested {args.eps}  ->  proved {sheet.total_proved_eps:.3f}")
    print(
        f"  GATE 1 boundary-audit RB1-RB14 ... {mark(gates['boundary_audit']['pass'])}"
        f"  ({gates['boundary_audit']['leaks']} leaks, "
        f"{gates['boundary_audit']['unverifiable']} unverifiable)"
    )
    print(
        f"  GATE 2 release-label conformance . {mark(gates['release_label']['pass'])}"
        f"  ({gates['release_label']['verdict']})"
    )
    print(f"  GATE 3 signature verifies ........ {mark(gates['signature_verifies']['pass'])}")
    if "mlcommons_validator" in gates:
        g = gates["mlcommons_validator"]
        status = "PASS" if g["pass"] else ("NOT CHECKED" if not g["checked"] else "FAIL")
        print(f"  GATE 4 MLCommons validator ....... {status}")
    print("=" * 64)
    print(f"  report: {report_path}")
    print("  ALL HARD GATES PASS." if all_hard_pass else "  A HARD GATE FAILED -- see report.")
    return 0 if all_hard_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
