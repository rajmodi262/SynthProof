"""SynthProof prototype launcher.

Starts the web application and opens the browser to the console.

WHAT THE BANNER USED TO SAY, AND WHY IT CHANGED (2026-09-13). It listed three "pre-seeded
releases in ledger" with audited epsilons (0.384, 0.712, 0.180) and "Verified" beside each,
including a "Texas Inpatient Health" release. None of that existed. The ledger is seeded with
three budget CHARGES (see synthproof/api/state.py) so the tamper studio has a chain to attack:
no synthesis ran for them, they carry no audit result, and no Texas dataset exists anywhere in
this repository. The audited values were the fabricated demo-capsule numbers. It also announced
"CORE ARCHITECTURAL NOVELTIES" over a novelty verdict that killed eight of the project's claims,
and a gauge that "prevents false certifications" while computing its verdict backwards.
"""

import os
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Demo mode with an in-memory ledger: the destructive tamper/reset endpoints are only enabled
# here, and nothing written during a demo survives the process.
os.environ.setdefault("SYNTHPROOF_DEMO", "1")
os.environ.setdefault("SYNTHPROOF_LEDGER_DB", ":memory:")


def check_prerequisites() -> None:
    """Builds the console bundle and the demo capsules if they are missing."""
    console_index = ROOT_DIR / "synthproof" / "api" / "console" / "index.html"
    if not console_index.exists():
        # `npm` is `npm.cmd` on Windows, which subprocess cannot resolve from a bare name --
        # the previous version raised FileNotFoundError here on exactly the OS the double-click
        # launcher targets.
        npm = shutil.which("npm") or shutil.which("npm.cmd")
        if npm is None:
            print("[-] The web console is not built and Node.js/npm is not on PATH.")
            print("    Install Node.js LTS, then run:  cd web && npm install && npm run build")
            sys.exit(1)
        print("[*] Building the web console (npm run build)...")
        subprocess.run([npm, "run", "build"], cwd=str(ROOT_DIR / "web"), check=True)

    capsules_dir = ROOT_DIR / "demo_capsules"
    if not capsules_dir.exists() or not list(capsules_dir.glob("*.html")):
        print("[*] Building demo capsules from real pipeline releases...")
        subprocess.run(
            [sys.executable, str(ROOT_DIR / "scripts" / "generate_demo_capsules.py")], check=True
        )


BANNER = """
==========================================================================================
  SynthProof -- synthetic data that ships with its proof
  B.Tech capstone prototype, running locally
==========================================================================================

  WHAT TO TRY
  ----------------------------------------------------------------------------------------
  1. Run a release    Pick a dataset and an epsilon, then Run. Every number shown is computed.
  2. Tamper studio    Attack the ledger four ways and watch the hash chain report the break.
  3. Verifier         Check a signed sheet or capsule without trusting this server.
  4. Audit range      Each release states whether its audit could have certified its epsilon.
  5. Guided tour      A scripted walkthrough of the pipeline.

  THE LEDGER AT START
  ----------------------------------------------------------------------------------------
  Three ILLUSTRATIVE budget charges (run ids begin "illustrative-") so the tamper studio has
  a chain to attack. They are spend records only: no synthesis ran for them and they carry no
  audit result. Real releases appear after you click Run.

  LOCAL ACCESS
  ----------------------------------------------------------------------------------------
  Console          http://127.0.0.1:{port}/
  API docs         http://127.0.0.1:{port}/docs
  Offline capsule  demo_capsules/uci_adult_verified_capsule.html            (eps = 1, in range)
                   demo_capsules/uci_adult_eps8_claim_exceeds_audit_range_capsule.html
==========================================================================================
"""


def main() -> None:
    check_prerequisites()

    port = int(os.environ.get("PORT", 8000))
    host = "127.0.0.1"
    url = f"http://{host}:{port}/"
    print(BANNER.format(port=port))
    print(f"[*] Starting SynthProof server on {url} ...")

    def open_browser() -> None:
        time.sleep(1.2)
        try:
            webbrowser.open(url)
        except Exception:
            pass

    threading.Thread(target=open_browser, daemon=True).start()

    import uvicorn

    from synthproof.api.main import app

    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
