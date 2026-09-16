from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Self, cast
from urllib.request import Request, urlopen

from acacium.integrity import SourceIntegrityError, verify_sha256
from acacium.schemas import DocumentList


class DownloadResponse(Protocol):
    def __enter__(self) -> Self: ...

    def __exit__(self, *_args: object) -> None: ...

    def read(self, _size: int = -1) -> bytes: ...


Downloader = Callable[[Request, float], DownloadResponse]


def _download(request: Request, timeout: float) -> DownloadResponse:
    return cast(DownloadResponse, urlopen(request, timeout=timeout))


DEFAULT_DOWNLOADER: Downloader = _download


@dataclass(frozen=True)
class AcquisitionResult:
    downloaded: tuple[str, ...]
    reused: tuple[str, ...]


def fetch_documents(
    manifest: DocumentList,
    documents_dir: Path,
    *,
    force: bool = False,
    downloader: Downloader = DEFAULT_DOWNLOADER,
) -> AcquisitionResult:
    """Fetch the declared public corpus and replace only hash-validated files."""
    documents_dir.mkdir(parents=True, exist_ok=True)
    downloaded: list[str] = []
    reused: list[str] = []

    for document in manifest.documents:
        destination = documents_dir / document.filename
        if not force and _is_valid(destination, document.sha256):
            reused.append(document.filename)
            continue

        temporary = destination.with_suffix(f"{destination.suffix}.part")
        try:
            request = Request(document.source_url, headers={"User-Agent": "AcaciumPrototype/1.0"})
            with downloader(request, 120.0) as response, temporary.open("wb") as output:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
            verify_sha256(temporary, document.sha256)
            temporary.replace(destination)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
        downloaded.append(document.filename)

    return AcquisitionResult(tuple(downloaded), tuple(reused))


def _is_valid(path: Path, expected_digest: str) -> bool:
    if not path.is_file():
        return False
    try:
        verify_sha256(path, expected_digest)
    except SourceIntegrityError:
        return False
    return True
