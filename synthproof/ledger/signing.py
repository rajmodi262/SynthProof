"""Ed25519 keys that survive a restart, and signatures over a Privacy Data Sheet.

This closes the gap between the project's title — "synthetic data that ships with its proof" —
and what it actually shipped. Two things were missing:

  * The ledger generated a fresh signing key in memory per process and never persisted it, so
    every signature became permanently unverifiable the moment the process exited. For a
    file-backed ledger that meant the chain could be verified structurally but not
    attributed to anyone.
  * The data sheet carried no signature at all, so the central claim was an assertion by the
    party with the strongest interest in it being believed.

WHAT A SIGNATURE HERE DOES AND DOES NOT MEAN. It proves that whoever holds the private key
produced this exact sheet, and that no field has been altered since. It does NOT prove the
epsilon is correct, that the mechanism is sound, or that the audit was run honestly — a key
holder can sign a sheet full of wrong numbers. It converts "trust our claim" into "verify
that this claim came from us and has not been edited", which is a smaller but checkable thing.

Key custody is an organisational control. Anyone with the private key can rewrite the ledger
and re-sign it, so the chain is tamper-EVIDENT, not tamper-proof.
"""

import os
import stat
from pathlib import Path
from typing import Optional, Tuple

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

DEFAULT_KEY_DIR = Path(os.environ.get("SYNTHPROOF_KEY_DIR", ".keys"))
PRIVATE_KEY_NAME = "synthproof_ed25519"
PUBLIC_KEY_NAME = "synthproof_ed25519.pub"


class SignatureError(Exception):
    """Raised when a signature is absent, malformed, or does not verify."""


# --------------------------------------------------------------------------- key management

def generate_keypair(key_dir: Path = DEFAULT_KEY_DIR,
                     overwrite: bool = False) -> Tuple[Path, Path]:
    """Creates a persistent Ed25519 keypair and returns (private_path, public_path).

    The private key is written unencrypted, which is appropriate for a capstone artefact and
    NOT for a real deployment — a production holder would keep it in an HSM or a secrets
    manager. `.keys/` is gitignored; the permission tightening below is a second line of
    defence rather than the primary one.
    """
    key_dir = Path(key_dir)
    key_dir.mkdir(parents=True, exist_ok=True)
    priv_path = key_dir / PRIVATE_KEY_NAME
    pub_path = key_dir / PUBLIC_KEY_NAME

    if priv_path.exists() and not overwrite:
        raise FileExistsError(
            f"{priv_path} already exists. Refusing to overwrite a signing key — every "
            "signature ever made with it would become unverifiable. Pass overwrite=True "
            "only if you are certain."
        )

    private_key = ed25519.Ed25519PrivateKey.generate()
    priv_path.write_bytes(private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ))
    pub_path.write_bytes(private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ))

    # Owner read/write only. A no-op on Windows, hence "second line of defence".
    try:
        os.chmod(priv_path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:  # pragma: no cover - platform dependent
        pass

    return priv_path, pub_path


def load_private_key(path: Optional[Path] = None) -> ed25519.Ed25519PrivateKey:
    """Loads the persistent signing key, with an actionable error when it is absent."""
    path = Path(path) if path else DEFAULT_KEY_DIR / PRIVATE_KEY_NAME
    if not path.exists():
        raise FileNotFoundError(
            f"No signing key at {path}. Create one with:\n"
            "    synthproof keygen\n"
            "Then publish the .pub file so a third party can verify your data sheets."
        )
    key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    if not isinstance(key, ed25519.Ed25519PrivateKey):
        raise SignatureError(f"{path} is not an Ed25519 private key.")
    return key


def load_public_key(path: Optional[Path] = None) -> ed25519.Ed25519PublicKey:
    """Loads a public key for verification."""
    path = Path(path) if path else DEFAULT_KEY_DIR / PUBLIC_KEY_NAME
    if not path.exists():
        raise FileNotFoundError(f"No public key at {path}.")
    key = serialization.load_pem_public_key(path.read_bytes())
    if not isinstance(key, ed25519.Ed25519PublicKey):
        raise SignatureError(f"{path} is not an Ed25519 public key.")
    return key


def public_key_hex(key: ed25519.Ed25519PublicKey) -> str:
    """Raw public key as hex, for embedding in a data sheet."""
    return key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ).hex()


def public_key_from_hex(value: str) -> ed25519.Ed25519PublicKey:
    return ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(value))


# --------------------------------------------------------------------------- sign / verify

def sign_datasheet(sheet, private_key: Optional[ed25519.Ed25519PrivateKey] = None,
                   key_path: Optional[Path] = None):
    """Signs a `PrivacyDataSheet` in place and returns it.

    The signature covers `sheet.signing_payload()` — every field except the signature and the
    embedded public key, serialised with sorted keys. The public key is embedded so a
    verifier can identify WHICH key signed, but it is deliberately not trusted on its own:
    `verify_datasheet` requires the expected key to be supplied separately, because a sheet
    that carries its own key proves only that it was signed by somebody.
    """
    key = private_key or load_private_key(key_path)
    sheet.signature = key.sign(sheet.signing_payload()).hex()
    sheet.public_key = public_key_hex(key.public_key())
    return sheet


def verify_datasheet(sheet_dict: dict,
                     public_key: Optional[ed25519.Ed25519PublicKey] = None,
                     key_path: Optional[Path] = None) -> bool:
    """Verifies a data sheet loaded from JSON. Raises `SignatureError` on any failure.

    Args:
        sheet_dict: The parsed sheet.
        public_key: The key the verifier expects. If omitted, `key_path` is loaded.
        key_path: Path to the expected public key.

    Returns:
        True. Failure raises rather than returning False, so a caller cannot mistake a
        falsy return for a passing check.
    """
    signature = sheet_dict.get("signature")
    if not signature:
        raise SignatureError(
            "This data sheet is unsigned. It is a record of a claim, not evidence for one — "
            "any field in it could have been edited by anyone."
        )

    if public_key is None:
        if key_path is None:
            raise SignatureError(
                "A public key is required. Verifying against the key embedded in the sheet "
                "would prove only that the sheet signed itself."
            )
        public_key = load_public_key(key_path)

    embedded = sheet_dict.get("public_key")
    if embedded and embedded != public_key_hex(public_key):
        raise SignatureError(
            "This sheet was signed by a different key than the one supplied.\n"
            f"  sheet says: {embedded}\n"
            f"  you gave:   {public_key_hex(public_key)}"
        )

    payload = dict(sheet_dict)
    payload.pop("signature", None)
    payload.pop("public_key", None)

    import json
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")

    try:
        public_key.verify(bytes.fromhex(signature), canonical)
    except Exception as exc:
        raise SignatureError(
            "Signature does not verify. Either the sheet was altered after signing, or it "
            "was not signed by this key."
        ) from exc
    return True
