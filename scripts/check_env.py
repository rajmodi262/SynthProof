"""Environment check script for SynthProof platform."""

import sys
import platform

def check_environment():
    print("=" * 60)
    print("SynthProof Environment Diagnostics")
    print("=" * 60)
    print(f"Python Version: {platform.python_version()}")
    print(f"Platform: {platform.platform()}")
    print(f"Executable: {sys.executable}")
    print("-" * 60)

    packages = [
        "numpy",
        "pandas",
        "scipy",
        "sklearn",
        "cryptography",
        "fastapi",
        "click",
        "pytest",
        "hypothesis",
    ]

    print("Dependency Status:")
    for pkg in packages:
        try:
            mod = __import__(pkg)
            version = getattr(mod, "__version__", "Installed (no __version__)")
            print(f"  [OK] {pkg:<16} : {version}")
        except Exception as err:
            print(f"  [ERROR/MISSING] {pkg:<12} : {type(err).__name__}: {err}")

    print("-" * 60)
    print("SynthProof is CPU-only. No GPU dependency is required or declared.")
    print("=" * 60)

if __name__ == "__main__":
    check_environment()
