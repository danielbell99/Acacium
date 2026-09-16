from acacium.main import app
from fastapi.testclient import TestClient


def test_documents_endpoint_returns_the_scoped_corpus() -> None:
    response = TestClient(app).get("/api/documents")

    assert response.status_code == 200
    body = response.json()
    assert body["selected_report_page_count"] == 105
    assert len(body["documents"]) == 3
