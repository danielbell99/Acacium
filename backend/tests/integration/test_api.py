from hashlib import sha256
from types import SimpleNamespace

import pytest
from acacium import main
from acacium.integrity import SourceIntegrityError
from acacium.main import app
from acacium.schemas import DocumentList
from fastapi.testclient import TestClient


@pytest.fixture
def prepared_local_corpus(monkeypatch: pytest.MonkeyPatch, tmp_path) -> str:
    payload = b"%PDF-1.4\n% deterministic test evidence\n"
    filename = "test-board-paper.pdf"
    document_id = "test-board-paper"
    (tmp_path / filename).write_bytes(payload)
    test_manifest = DocumentList.model_validate(
        {
            "manifest_version": "test",
            "selected_report_page_count": 1,
            "documents": [
                {
                    "id": document_id,
                    "organisation": "Test NHS Trust",
                    "meeting_date": "2026-09-16",
                    "filename": filename,
                    "source_url": "https://example.test/board-paper.pdf",
                    "listing_url": "https://example.test",
                    "sha256": sha256(payload).hexdigest(),
                    "page_count": 1,
                    "scope": {
                        "report_title": "Test Board Paper",
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
    monkeypatch.setattr(main, "manifest", test_manifest)
    monkeypatch.setattr(main, "settings", SimpleNamespace(documents_dir=tmp_path))
    return document_id


def test_documents_endpoint_returns_the_scoped_corpus() -> None:
    response = TestClient(app).get("/api/documents")

    assert response.status_code == 200
    body = response.json()
    assert body["selected_report_page_count"] == 105
    assert len(body["documents"]) == 3


def test_config_exposes_the_versioned_scoring_rubric() -> None:
    response = TestClient(app).get("/api/config")

    assert response.status_code == 200
    assert response.json()["rubric_version"] == "2026-09-16"
    assert response.json()["score_formula"] == (
        "Versioned evidence bands: fit, substantiation and reviewer validation"
    )


def test_readiness_confirms_the_local_evidence_corpus(prepared_local_corpus: str) -> None:
    response = TestClient(app).get("/api/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_readiness_rejects_a_source_integrity_failure(
    monkeypatch: pytest.MonkeyPatch, prepared_local_corpus: str
) -> None:
    def reject_source(*_args, **_kwargs) -> None:
        raise SourceIntegrityError("test source mismatch")

    monkeypatch.setattr(main, "verify_sha256", reject_source)

    response = TestClient(app).get("/api/health/ready")

    assert response.status_code == 503
    assert response.json()["detail"] == "The declared local evidence corpus is not ready."


def test_unknown_document_content_returns_not_found() -> None:
    response = TestClient(app).get("/api/documents/unknown/content")

    assert response.status_code == 404


def test_unknown_run_signals_returns_not_found() -> None:
    response = TestClient(app).get("/api/jobs/unknown-run/signals")

    assert response.status_code == 404


def test_document_content_serves_the_hash_verified_pdf(prepared_local_corpus: str) -> None:
    response = TestClient(app).get(f"/api/documents/{prepared_local_corpus}/content")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"


def test_shortlist_export_keeps_evidence_audit_columns() -> None:
    response = TestClient(app).get("/api/shortlist/export")

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert response.text.startswith(
        "rank,organisation,category,service,score,period,source_document,source_page,"
        "source_url,evidence_excerpt,review_reason,next_action\n"
    )
