"""Integration test for the gated release pipeline (scripts/build_release.py).

Runs the whole chain on the toy table -- synthesise, sign, emit Croissant, then the three hard
gates (boundary-audit RB1-RB14, release-label conformance, signature verification) -- and asserts
every hard gate passes and the artifacts are written. Marked slow because it runs a real synthesis
+ audit (~30s). This is the test that guarantees the "runnable artifact an examiner can run" stays
runnable and green.
"""

import json
import subprocess
import sys

import pytest

pytestmark = pytest.mark.slow


def test_toy_release_passes_every_hard_gate(tmp_path):
    outdir = tmp_path / "rel"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.build_release",
            "--dataset",
            "toy",
            "--mechanism",
            "aim",
            "--eps",
            "2.0",
            "--outdir",
            str(outdir),
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"pipeline exited {proc.returncode}\n{proc.stdout}\n{proc.stderr}"

    report = json.loads((outdir / "release_report.json").read_text(encoding="utf-8"))
    assert report["all_hard_gates_pass"] is True
    assert report["gates"]["boundary_audit"]["pass"] is True
    assert report["gates"]["boundary_audit"]["leaks"] == 0
    assert report["gates"]["release_label"]["verdict"] == "conformant"
    assert report["gates"]["signature_verifies"]["pass"] is True

    # The keyed fingerprint is now DECLARED, so RB3 is a checkable note, not "unverifiable".
    assert "RB3:note" in report["gates"]["boundary_audit"]["detail"]

    # All four artifacts exist (the report stores their absolute paths) and are hashed.
    from pathlib import Path

    for key in ("privacy_data_sheet", "synthetic_csv", "croissant_record", "public_key"):
        art = report["artifacts"][key]
        assert Path(art["path"]).exists(), f"missing artifact {key}: {art['path']}"
        assert len(art["sha256"]) == 64
