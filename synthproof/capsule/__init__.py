"""SynthProof Self-Verifying Capsule package."""

from synthproof.capsule.generator import (
    extract_capsule_payload,
    generate_capsule_html,
    verify_capsule,
)

__all__ = ["generate_capsule_html", "extract_capsule_payload", "verify_capsule"]
