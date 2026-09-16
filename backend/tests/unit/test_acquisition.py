from __future__ import annotations

from hashlib import sha256
from io import BytesIO
from pathlib import Path
from urllib.request import Request

import pytest
from acacium.acquisition import fetch_documents
from acacium.integrity import SourceIntegrityError
from acacium.schemas import DocumentList


class _Response(BytesIO):
    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def _manifest(payload: bytes) -> DocumentList:
    return DocumentList.model_validate(
        {
            "manifest_version": "test",
            "selected_report_page_count": 1,
            "documents": [
                {
                    "id": "example",
                    "organisation": "Example Trust",
                    "meeting_date": "2026-09-16",
                    "filename": "example.pdf",
                    "source_url": "https://example.test/example.pdf",
                    "listing_url": "https://example.test",
                    "sha256": sha256(payload).hexdigest(),
                    "page_count": 1,
                    "scope": {
                        "report_title": "Example report",
                        "first_physical_page": 1,
                        "last_physical_page": 1,
                        "page_count": 1,
                        "reporting_period": "2026-09",
                        "layout": "Test",
                    },
                    "reference_pages": [1],
                }
            ],
        }
    )


def test_fetches_and_reuses_a_hash_verified_document(tmp_path: Path) -> None:
    payload = b"public board paper"
    calls: list[Request] = []

    def downloader(request: Request, timeout: float) -> _Response:
        assert timeout == 120.0
        calls.append(request)
        return _Response(payload)

    first = fetch_documents(_manifest(payload), tmp_path, downloader=downloader)
    second = fetch_documents(_manifest(payload), tmp_path, downloader=downloader)

    assert first.downloaded == ("example.pdf",)
    assert first.reused == ()
    assert second.downloaded == ()
    assert second.reused == ("example.pdf",)
    assert len(calls) == 1
    assert (tmp_path / "example.pdf").read_bytes() == payload


def test_rejects_a_download_when_its_hash_does_not_match(tmp_path: Path) -> None:
    def downloader(_request: Request, _timeout: float) -> _Response:
        return _Response(b"unexpected bytes")

    with pytest.raises(SourceIntegrityError, match="digest"):
        fetch_documents(_manifest(b"expected bytes"), tmp_path, downloader=downloader)

    assert not (tmp_path / "example.pdf").exists()
    assert not (tmp_path / "example.pdf.part").exists()
