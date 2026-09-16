from acacium.main import app
from fastapi.testclient import TestClient


def test_documents_endpoint_returns_the_scoped_corpus() -> None:
    response = TestClient(app).get("/api/documents")

    assert response.status_code == 200
    body = response.json()
    assert body["selected_report_page_count"] == 105
    assert len(body["documents"]) == 3


def test_unknown_document_content_returns_not_found() -> None:
    response = TestClient(app).get("/api/documents/unknown/content")

    assert response.status_code == 404


def test_document_content_serves_the_hash_verified_pdf() -> None:
    response = TestClient(app).get("/api/documents/west-herts-2026-09-10/content")

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
