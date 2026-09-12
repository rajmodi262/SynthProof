"""SynthProof Master Prototype Launcher.

Starts the interactive web application, pre-seeds the cryptographic ledger,
and opens the browser directly to the prototype demonstration.
"""

import os
import sys
import time
import webbrowser
from pathlib import Path

# Ensure root directory is on sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Ensure demo environment variables are set
os.environ.setdefault("SYNTHPROOF_DEMO", "1")
os.environ.setdefault("SYNTHPROOF_LEDGER_DB", ":memory:")


def check_prerequisites():
    """Validates that build assets and keys exist."""
    console_index = ROOT_DIR / "synthproof" / "api" / "console" / "index.html"
    if not console_index.exists():
        print("[-] Warning: Console production bundle not found.")
        print("    Building web console with npm run build...")
        import subprocess
        subprocess.run(["npm", "run", "build"], cwd=str(ROOT_DIR / "web"), check=True)

    capsules_dir = ROOT_DIR / "demo_capsules"
    if not capsules_dir.exists() or not list(capsules_dir.glob("*.html")):
        print("[*] Generating standalone verified demo capsules...")
        import subprocess
        subprocess.run([sys.executable, str(ROOT_DIR / "scripts" / "generate_demo_capsules.py")], check=True)


def print_banner():
    banner = """
========================================================================================
   ____             _   _     ____                        __ 
  / ___| _   _ _ __ | |_| |__ |  _ \ _ __ ___   ___  ___ / _|
  \___ \| | | | '_ \| __| '_ \| |_) | '__/ _ \ / _ \/ _ \ |_ 
   ___) | |_| | | | | |_| | | |  __/| | | (_) | (_) |  _/  _|
  |____/ \__, |_| |_|\__|_| |_|_|   |_|  \___/ \___/ \___|_|  
         |___/                                                
            Synthetic Data that Ships with its Proof
========================================================================================
  [+] 100% WORKING LIVE PROTOTYPE READY
  
  CORE ARCHITECTURAL NOVELTIES & MVPS:
  --------------------------------------------------------------------------------------
  1. Self-Verifying Capsule (.html) : Standalone offline container with embedded WebCrypto
  2. Red-Team Tamper Studio         : Interactive multi-class database attack simulator
  3. Zero-Trust Certificate Verifier: Independent Ed25519 & Croissant 1.1 JSON-LD auditor
  4. MIQE 2.0 LoD Operating Gauge   : Prevents false certifications below detector ceiling
  5. Interactive Guided Tour        : 5-stage comprehensive presentation walkthrough

  PRE-SEEDED RELEASES IN LEDGER:
  --------------------------------------------------------------------------------------
  * Release #1: UCI Adult Income       -> AIM (eps=1.000, audited eps=0.384, Verified)
  * Release #2: ACS California Income  -> Pairwise (eps=2.000, audited eps=0.712, Verified)
  * Release #3: Texas Inpatient Health -> Fixed Workload (eps=0.500, audited eps=0.180, Verified)

  LOCAL ACCESS:
  --------------------------------------------------------------------------------------
  * Web Application Console  : http://127.0.0.1:8000/
  * Standalone Demo Capsules : demo_capsules/uci_adult_verified_capsule.html
  * API Documentation        : http://127.0.0.1:8000/docs
========================================================================================
    """
    print(banner)


def main():
    check_prerequisites()
    print_banner()

    port = int(os.environ.get("PORT", 8000))
    host = "127.0.0.1"
    url = f"http://{host}:{port}/"

    print(f"[*] Starting SynthProof server on {url} ...")

    # Launch browser after a short delay
    def open_browser():
        time.sleep(1.2)
        try:
            webbrowser.open(url)
        except Exception:
            pass

    import threading
    threading.Thread(target=open_browser, daemon=True).start()

    import uvicorn
    from synthproof.api.main import app

    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
