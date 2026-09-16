from __future__ import annotations

from csv import DictWriter
from io import StringIO
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response

from acacium.catalogue import find_document, load_manifest, load_service_catalogue
from acacium.integrity import SourceIntegrityError, verify_sha256
from acacium.pipeline.extract import extract_document
from acacium.review_store import ReviewStore
from acacium.run_store import RunStore
from acacium.schemas import (
    ConfigResponse,
    DocumentList,
    ReviewRequest,
    Run,
    RunRequest,
    Signal,
)
from acacium.settings import get_settings

settings = get_settings()
manifest = load_manifest(settings.manifest_path)
service_catalogue = load_service_catalogue(settings.service_catalogue_path)
store = RunStore(ReviewStore(settings.review_database_path))
RUBRIC_VERSION = "2026-09-16"

app = FastAPI(title="Acacium Board Paper Intelligence", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/api/health/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/health/ready")
def ready() -> dict[str, str]:
    try:
        for document in manifest.documents:
            source_path = settings.documents_dir / document.filename
            if not source_path.is_file():
                raise FileNotFoundError(document.filename)
            verify_sha256(source_path, document.sha256)
    except (FileNotFoundError, SourceIntegrityError) as error:
        raise HTTPException(
            status_code=503,
            detail="The declared local evidence corpus is not ready.",
        ) from error
    return {"status": "ready"}


@app.get("/api/config", response_model=ConfigResponse)
def config() -> ConfigResponse:
    return ConfigResponse(
        demo_mode=settings.demo_mode,
        rubric_version=RUBRIC_VERSION,
        source_manifest_version=manifest.manifest_version,
        score_formula="(35*fit + 25*need + 25*timing + 15*specificity) / 2",
    )


@app.get("/api/documents", response_model=DocumentList)
def documents() -> DocumentList:
    return manifest


@app.get("/api/documents/{document_id}/content")
def document_content(document_id: str) -> FileResponse:
    try:
        document = find_document(manifest, document_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Document not found") from error

    source_path = settings.documents_dir / document.filename
    if not source_path.is_file():
        raise HTTPException(status_code=404, detail="Local document copy is unavailable")
    try:
        verify_sha256(source_path, document.sha256)
    except SourceIntegrityError as error:
        raise HTTPException(
            status_code=409,
            detail="Local document copy fails source-integrity validation",
        ) from error
    return FileResponse(source_path, media_type="application/pdf", filename=document.filename)


@app.get("/api/signals", response_model=list[Signal])
def signals() -> list[Signal]:
    return store.signals()


@app.get("/api/shortlist/export")
def export_shortlist() -> Response:
    buffer = StringIO()
    fields = [
        "rank",
        "organisation",
        "category",
        "service",
        "score",
        "period",
        "source_document",
        "source_page",
        "source_url",
        "evidence_excerpt",
        "review_reason",
        "next_action",
    ]
    writer = DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for rank, signal in enumerate(store.approved_signals(), start=1):
        document = find_document(manifest, signal.evidence.document_id)
        writer.writerow(
            {
                "rank": rank,
                "organisation": signal.organisation,
                "category": signal.category,
                "service": signal.service,
                "score": signal.score,
                "period": signal.reporting_period or "",
                "source_document": signal.evidence.filename,
                "source_page": signal.evidence.physical_page,
                "source_url": document.source_url,
                "evidence_excerpt": signal.evidence.excerpt,
                "review_reason": signal.review_reason or "",
                "next_action": signal.proposed_next_action,
            }
        )
    return Response(
        buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=acacium-approved-shortlist.csv"},
    )


@app.post("/api/signals/{signal_id}/review", response_model=Signal)
def review_signal(signal_id: str, request: ReviewRequest) -> Signal:
    reviewed = store.review(signal_id, request)
    if reviewed is None:
        raise HTTPException(status_code=404, detail="Signal not found")
    return reviewed


@app.get("/api/jobs", response_model=list[Run])
def jobs() -> list[Run]:
    return store.list_runs()


@app.get("/api/jobs/{run_id}", response_model=Run)
def job(run_id: str) -> Run:
    stored = store.get(run_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return stored


@app.get("/api/jobs/{run_id}/signals", response_model=list[Signal])
def job_signals(run_id: str) -> list[Signal]:
    extracted = store.signals_for_run(run_id)
    if extracted is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return extracted


@app.post("/api/jobs", response_model=Run, status_code=202)
def start_job(request: RunRequest, background_tasks: BackgroundTasks) -> Run:
    unknown = set(request.document_ids) - {document.id for document in manifest.documents}
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown document IDs: {sorted(unknown)}")
    run = store.create(
        request.document_ids,
        as_of_date=request.as_of_date,
        rubric_version=RUBRIC_VERSION,
        source_manifest_version=manifest.manifest_version,
        service_catalogue_version=service_catalogue.version,
    )
    background_tasks.add_task(_run_extraction, run.id, request.document_ids)
    return run


def _run_extraction(run_id: str, document_ids: list[str]) -> None:
    try:
        sources = [find_document(manifest, document_id) for document_id in document_ids]
        store.begin(run_id, sum(source.scope.page_count for source in sources))
        extracted: list[Signal] = []
        for source in sources:
            document_signals = extract_document(
                source,
                Path(settings.documents_dir),
                service_catalogue,
            )
            extracted.extend(document_signals)
            for page_index in range(source.scope.page_count):
                store.record_page(run_id, document_signals if page_index == 0 else [])
        store.complete(run_id, extracted)
    except Exception as exc:
        store.fail(run_id, f"Extraction failed safely: {type(exc).__name__}")
