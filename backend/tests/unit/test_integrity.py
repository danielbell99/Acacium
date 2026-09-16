from hashlib import sha256
from pathlib import Path

import pytest
from acacium.integrity import SourceIntegrityError, verify_sha256


def test_accepts_source_file_matching_the_manifest_digest(tmp_path: Path) -> None:
    source_path = tmp_path / "board-paper.pdf"
    contents = b"public board paper"
    source_path.write_bytes(contents)

    verify_sha256(source_path, sha256(contents).hexdigest())


def test_rejects_source_file_not_matching_the_manifest_digest(tmp_path: Path) -> None:
    source_path = tmp_path / "board-paper.pdf"
    source_path.write_bytes(b"changed board paper")

    with pytest.raises(SourceIntegrityError, match="does not match"):
        verify_sha256(source_path, sha256(b"expected board paper").hexdigest())
