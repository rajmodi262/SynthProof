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

import hashlib
import json
import os
import secrets
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

DEFAULT_KEY_DIR = Path(os.environ.get("SYNTHPROOF_KEY_DIR", ".keys"))
PRIVATE_KEY_NAME = "synthproof_ed25519"
PUBLIC_KEY_NAME = "synthproof_ed25519.pub"
# The curator's secret for keyed input fingerprints. Held beside the signing key and, like it,
# never published. See `load_fingerprint_key`.
FINGERPRINT_KEY_NAME = "fingerprint.key"
# Where a rotated-out key's PUBLIC half is kept (its private half is destroyed), and the log.
RETIRED_DIR_NAME = "retired"
ROTATION_LOG_NAME = "ROTATIONS.jsonl"


def key_passphrase() -> Optional[bytes]:
    """The passphrase that encrypts the private key at rest, if one is configured.

    SYNTHPROOF_KEY_PASSPHRASE, or SYNTHPROOF_KEY_PASSPHRASE_FILE (a path, e.g. a Docker secret,
    so the passphrase need not sit in the environment). Unset: keys are written unencrypted, as
    before, and the file permissions are the only protection.
    """
    path = os.environ.get("SYNTHPROOF_KEY_PASSPHRASE_FILE")
    if path:
        value = Path(path).read_text(encoding="utf-8").strip()
    else:
        value = os.environ.get("SYNTHPROOF_KEY_PASSPHRASE", "")
    return value.encode("utf-8") if value else None


def _private_pem(key: ed25519.Ed25519PrivateKey) -> bytes:
    passphrase = key_passphrase()
    encryption = (
        serialization.BestAvailableEncryption(passphrase)
        if passphrase
        else serialization.NoEncryption()
    )
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=encryption,
    )


def key_fingerprint(key: ed25519.Ed25519PublicKey) -> str:
    """A short, stable name for a public key: the first 16 hex digits of SHA-256 of its bytes."""
    raw = key.public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )
    return hashlib.sha256(raw).hexdigest()[:16]


def resolve_key_dir() -> Path:
    """Where keys live, resolved at CALL time rather than at import.

    `DEFAULT_KEY_DIR` is evaluated when this module is first imported, so anything that sets
    SYNTHPROOF_KEY_DIR afterwards — a test, an embedding application, a notebook — was
    silently ignored and the process went on using `.keys/`. Reading the variable per call
    removes that trap. `DEFAULT_KEY_DIR` is kept as the documented default and as the value
    used when the variable is unset.
    """
    override = os.environ.get("SYNTHPROOF_KEY_DIR")
    return Path(override) if override else DEFAULT_KEY_DIR


class SignatureError(Exception):
    """Raised when a signature is absent, malformed, or does not verify."""


# --------------------------------------------------------------------------- key management


def generate_keypair(key_dir: Optional[Path] = None, overwrite: bool = False) -> Tuple[Path, Path]:
    """Creates a persistent Ed25519 keypair and returns (private_path, public_path).

    `key_dir` defaults to `resolve_key_dir()` — resolved at call time, so SYNTHPROOF_KEY_DIR is
    honoured however late it is set. It used to default to the import-time constant, which
    meant writing the key somewhere the loaders would not look.

    The private key is encrypted at rest with the passphrase from `key_passphrase()` when one is
    configured (SYNTHPROOF_KEY_PASSPHRASE or _FILE), and written unencrypted otherwise. A
    production holder would still prefer an HSM or a secrets manager. `.keys/` is gitignored; the
    permission tightening below is a further line of defence.
    """
    key_dir = Path(key_dir) if key_dir is not None else resolve_key_dir()
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
    priv_path.write_bytes(_private_pem(private_key))
    pub_path.write_bytes(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )

    # Owner read/write only. A no-op on Windows, hence "second line of defence".
    try:
        os.chmod(priv_path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:  # pragma: no cover - platform dependent
        pass

    return priv_path, pub_path


def load_private_key(path: Optional[Path] = None) -> ed25519.Ed25519PrivateKey:
    """Loads the persistent signing key, with an actionable error when it is absent."""
    path = Path(path) if path else resolve_key_dir() / PRIVATE_KEY_NAME
    if not path.exists():
        raise FileNotFoundError(
            f"No signing key at {path}. Create one with:\n"
            "    synthproof keygen\n"
            "Then publish the .pub file so a third party can verify your data sheets."
        )
    data = path.read_bytes()
    encrypted = b"ENCRYPTED" in data.split(b"\n", 1)[0]
    passphrase = key_passphrase()
    if encrypted and passphrase is None:
        raise SignatureError(
            f"{path} is encrypted. Set SYNTHPROOF_KEY_PASSPHRASE (or _FILE) to the passphrase it "
            "was written with."
        )
    try:
        key = serialization.load_pem_private_key(data, password=passphrase if encrypted else None)
    except ValueError as exc:  # wrong passphrase, or a corrupt file
        raise SignatureError(f"Could not decrypt {path}: wrong passphrase or corrupt key.") from exc
    if not isinstance(key, ed25519.Ed25519PrivateKey):
        raise SignatureError(f"{path} is not an Ed25519 private key.")
    return key


def rotate_keypair(key_dir: Optional[Path] = None) -> Tuple[str, str]:
    """Replaces the signing key, keeping the old PUBLIC key so earlier signatures still verify.

    The old public key moves to `retired/<fingerprint>.pub`; the old private key is overwritten
    and deleted, so nothing can sign as it again; the event is appended to ROTATIONS.jsonl. A
    sheet signed before the rotation carries its own public key and verifies against the retired
    `.pub`. A file-backed ledger must be re-signed under the new key -- `Ledger.rotate_key`, which
    `synthproof keygen --rotate --ledger PATH` runs -- because it verifies against one key.

    Returns (retired_fingerprint, new_fingerprint).
    """
    key_dir = Path(key_dir) if key_dir is not None else resolve_key_dir()
    priv_path, pub_path = key_dir / PRIVATE_KEY_NAME, key_dir / PUBLIC_KEY_NAME
    old_private = load_private_key(priv_path)
    old_fp = key_fingerprint(old_private.public_key())
    retired = key_dir / RETIRED_DIR_NAME
    retired.mkdir(exist_ok=True)
    (retired / f"{old_fp}.pub").write_bytes(pub_path.read_bytes())
    # Overwrite before deleting, so the retired private key is not trivially recoverable.
    priv_path.write_bytes(secrets.token_bytes(len(priv_path.read_bytes())))
    priv_path.unlink()
    pub_path.unlink()
    new_priv_path, _ = generate_keypair(key_dir)
    new_fp = key_fingerprint(load_private_key(new_priv_path).public_key())
    with open(key_dir / ROTATION_LOG_NAME, "a", encoding="utf-8") as fh:
        fh.write(
            json.dumps(
                {
                    "rotated_at": datetime.now(timezone.utc).isoformat(),
                    "retired": old_fp,
                    "current": new_fp,
                }
            )
            + "\n"
        )
    return old_fp, new_fp


def load_public_key(path: Optional[Path] = None) -> ed25519.Ed25519PublicKey:
    """Loads a public key for verification."""
    path = Path(path) if path else resolve_key_dir() / PUBLIC_KEY_NAME
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


def load_fingerprint_key(key_dir: Optional[Path] = None, create: bool = False) -> Optional[bytes]:
    """The curator's secret for keyed input fingerprints, or None when there is none.

    An UNKEYED hash of the input table is a deterministic membership test: an adversary who knows
    every other record hashes both candidate tables and compares
    (docs/design/PUBLIC_RELEASE_BOUNDARY.md, D3). Keyed with a secret that never leaves the
    curator, the fingerprint still lets the curator recognise a repeat release of the same table
    and gives nobody else anything to test.

    Args:
        key_dir: Defaults to `resolve_key_dir()`, resolved at call time.
        create: Write a new 32-byte key when none exists. An existing key is never replaced: a new
            key makes every earlier fingerprint unmatchable, which is the one thing it is for.
    """
    key_dir = Path(key_dir) if key_dir is not None else resolve_key_dir()
    path = key_dir / FINGERPRINT_KEY_NAME
    if not path.exists():
        if not create:
            return None
        key_dir.mkdir(parents=True, exist_ok=True)
        try:
            # "x": fail rather than overwrite if another process created it in the meantime.
            with open(path, "xb") as fh:
                fh.write(secrets.token_bytes(32))
        except FileExistsError:
            pass
        try:
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
        except OSError:  # pragma: no cover - platform dependent
            pass
    key = path.read_bytes()
    if len(key) < 32:
        raise ValueError(
            f"{path} holds {len(key)} bytes; a fingerprint key needs at least 32. Refusing to "
            "fingerprint with a key short enough to guess."
        )
    return key


def canonical_sheet_payload(sheet_dict: dict) -> bytes:
    """Canonical bytes of a data sheet covered by the signature.

    Normalizes whole-number floats to ints (e.g. 1.0 -> 1, 0.0 -> 0) so that JSON
    roundtripping through JavaScript (where 1.0 and 1 serialize identically as 1)
    does not alter the canonical byte sequence.
    """
    import json

    def _norm(v):
        if isinstance(v, dict):
            return {k: _norm(val) for k, val in sorted(v.items())}
        if isinstance(v, list):
            return [_norm(val) for val in v]
        if isinstance(v, float) and v.is_integer():
            return int(v)
        return v

    payload = dict(sheet_dict)
    payload.pop("signature", None)
    payload.pop("public_key", None)
    return json.dumps(_norm(payload), sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign_datasheet(
    sheet, private_key: Optional[ed25519.Ed25519PrivateKey] = None, key_path: Optional[Path] = None
):
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


def verify_datasheet(
    sheet_dict: dict,
    public_key: Optional[ed25519.Ed25519PublicKey] = None,
    key_path: Optional[Path] = None,
) -> bool:
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

    canonical_norm = canonical_sheet_payload(payload)
    canonical_raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")

    sig_bytes = bytes.fromhex(signature)
    verified = False
    for c in (canonical_norm, canonical_raw):
        try:
            public_key.verify(sig_bytes, c)
            verified = True
            break
        except Exception:
            continue

    if not verified:
        raise SignatureError(
            "Signature does not verify. Either the sheet was altered after signing, or it "
            "was not signed by this key."
        )
    return True
