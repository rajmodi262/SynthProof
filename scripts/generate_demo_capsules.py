"""Builds the demo capsules from REAL pipeline runs.

WHY THIS WAS REWRITTEN (2026-09-13). The previous version constructed both PrivacyDataSheets by
hand and signed them with a real Ed25519 key. Every number in them was typed, not computed:

  * the Adult sheet declared a one_run audit with 60 canaries at alpha 0.05 and a ceiling of
    3.50 -- that audit can certify at most 2.972;
  * the ACS sheet declared 100 canaries and a ceiling of 4.00 -- at most 3.493;
  * TRTR F1 0.865 on Adult, where this project measures 0.66;
  * a ledger hash equal to SHA-256 of the empty string, and another reading "1a2b3c4d...";
  * an "ACS California Income 2018" table of five hand-typed rows.

Both capsules verified as authentic, because a signature covers what was written rather than
whether it is true. They were what OPEN_OFFLINE_CAPSULE.bat opened, and the rehearsal pack calls
the capsule the best artefact in the project. Standing rule 2: never report a number that was
not computed.

Now every capsule is produced by `synthproof run --sign` on 3,000 real UCI Adult rows, so each
field -- proved epsilon, audit ceiling, ledger head, input fingerprint -- comes from the
pipeline. Two releases are built on purpose, one per honest verdict:

  eps = 1.0 -> the audit's reach covers the claim         (IN RANGE)
  eps = 8.0 -> the claim is beyond what the audit can see (CLAIM EXCEEDS AUDIT RANGE)

The second is the more useful demo: the capsule itself says, in amber, that its own audit could
not have certified the epsilon it proves -- the finding this project is about.

The ACS capsule is not rebuilt: there is no real ACS release in this script, and a capsule is
not worth shipping with a label it cannot honour.

Usage:
    python scripts/generate_demo_capsules.py
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from synthproof.capsule.generator import generate_capsule_html, verify_capsule  # noqa: E402
from synthproof.data.datasets import load_adult  # noqa: E402
from synthproof.ledger import signing  # noqa: E402

OUT_DIR = ROOT / "demo_capsules"
KEY_DIR = ROOT / ".keys"
N_ROWS = 3000
SEED = 0
# The capsule embeds a sample of the synthetic table to keep the file small. The full release
# size is still recorded in the signed sheet, and the page states both numbers.
RECORDS_IN_CAPSULE = 250

RELEASES = [
    ("uci_adult_verified_capsule.html", 1.0),
    ("uci_adult_eps8_claim_exceeds_audit_range_capsule.html", 8.0),
]


def _cli(env, *args):
    proc = subprocess.run(
        [sys.executable, "-m", "synthproof.cli", *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout + proc.stderr)
        raise SystemExit(f"synthproof {' '.join(args[:1])} failed with exit {proc.returncode}")
    return proc


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "SYNTHPROOF_KEY_DIR": str(KEY_DIR), "PYTHONIOENCODING": "utf-8"}
    if not (KEY_DIR / signing.PRIVATE_KEY_NAME).exists():
        _cli(env, "keygen", "--key-dir", str(KEY_DIR))

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        src = tmp_dir / "uci_adult_sample.csv"
        load_adult().df.sample(n=N_ROWS, random_state=SEED).to_csv(src, index=False)

        for filename, eps in RELEASES:
            sheet_path = tmp_dir / f"sheet_eps{eps:g}.json"
            synth_path = tmp_dir / f"synthetic_eps{eps:g}.csv"
            print(f"\nReleasing UCI Adult ({N_ROWS} rows) at eps = {eps:g} ...", flush=True)
            _cli(
                env,
                "run",
                "--input", str(src),
                "--out", str(sheet_path),
                "--eps", str(eps),
                "--mechanism", "pairwise",
                "--seed", str(SEED),
                "--sign",
                "--synthetic-out", str(synth_path),
            )  # fmt: skip

            sheet = json.loads(sheet_path.read_text(encoding="utf-8"))
            synthetic = pd.read_csv(synth_path).head(RECORDS_IN_CAPSULE)

            out = OUT_DIR / filename
            generate_capsule_html(
                sheet,
                synthetic,
                output_path=out,
                curator_name="SynthProof demo release (real pipeline run)",
            )
            report = verify_capsule(out)
            print(f"  saved     {out.relative_to(ROOT)}", flush=True)
            print(
                f"  proved    {report['proved_eps']:.3f}   audited {report['audited_eps']:.3f}"
                f"   ceiling {report['audit_ceiling']:.3f}",
                flush=True,
            )
            print(f"  signature {'VALID' if report['verified'] else 'INVALID'}", flush=True)
            print(f"  verdict   {report['lod_status']}  [{report['range_code']}]", flush=True)


if __name__ == "__main__":
    main()
