from __future__ import annotations

import hmac
from hashlib import sha256
from pathlib import Path


class SourceIntegrityError(ValueError):
    """Raised when a local source file no longer matches its tracked digest."""


def verify_sha256(source_path: Path, expected_digest: str) -> None:
    """Reject local source material whose content differs from the source manifest."""
    digest = sha256()
    with source_path.open("rb") as source_file:
        for chunk in iter(lambda: source_file.read(1024 * 1024), b""):
            digest.update(chunk)

    if not hmac.compare_digest(digest.hexdigest(), expected_digest):
        raise SourceIntegrityError("Source file digest does not match the tracked manifest.")
