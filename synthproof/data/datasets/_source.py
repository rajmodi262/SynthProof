"""Where a benchmark comes from, and fetching it with its digest verified."""

import hashlib
import os
import urllib.request
from dataclasses import dataclass

DEFAULT_DATA_DIR = os.environ.get("SYNTHPROOF_DATA_DIR", "data")


@dataclass(frozen=True)
class DatasetSource:
    """A downloadable benchmark and the digest that proves we got the right bytes."""

    name: str
    url: str
    sha256: str
    filename: str

    def __post_init__(self) -> None:
        # `urlopen` honours whatever scheme it is given, including `file:` and `ftp:`. A
        # dataset source is always a remote HTTPS artefact, so anything else is either a
        # typo or an attempt to make the loader read a local path. Rejecting it here means
        # the scheme cannot be smuggled in through a caller-constructed DatasetSource.
        if not self.url.startswith("https://"):
            raise ValueError(
                f"Dataset {self.name!r}: url must be https, got {self.url!r}. "
                "Other schemes (file:, ftp:) are refused."
            )

    def verify(self, blob: bytes) -> None:
        got = hashlib.sha256(blob).hexdigest()
        if self.sha256 and got != self.sha256:
            raise ValueError(
                f"Checksum mismatch for {self.name}.\n"
                f"  expected {self.sha256}\n  got      {got}\n"
                "Refusing to use these bytes. If the upstream file legitimately changed, "
                "update the pinned digest deliberately and record why."
            )


# UCI Adult (Becker & Kohavi, 1996). The column names are not in the CSV itself.


def _cache_path(source: DatasetSource, data_dir: str) -> str:
    return os.path.join(data_dir, source.filename)


def fetch(source: DatasetSource, data_dir: str = DEFAULT_DATA_DIR, force: bool = False) -> str:
    """Downloads `source` into `data_dir` if absent, verifying its digest.

    Returns the local path. Raises if the digest does not match a pinned value.
    """
    os.makedirs(data_dir, exist_ok=True)
    path = _cache_path(source, data_dir)

    if os.path.exists(path) and not force:
        with open(path, "rb") as f:
            source.verify(f.read())
        return path

    # Scheme is pinned to https by DatasetSource.__post_init__, so this cannot be
    # redirected to file:/ftp:. nosec B310 records that the check is deliberate.
    with urllib.request.urlopen(source.url, timeout=120) as resp:  # nosec B310
        blob = resp.read()
    source.verify(blob)

    with open(path, "wb") as f:
        f.write(blob)
    return path


def pin_checksum(source: DatasetSource, data_dir: str = DEFAULT_DATA_DIR) -> str:
    """Returns the SHA-256 of a locally cached file, for pinning into `DatasetSource`."""
    with open(_cache_path(source, data_dir), "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()
