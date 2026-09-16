from __future__ import annotations

from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from acacium.catalogue import find_document, load_manifest
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
store = RunStore(ReviewStore(settings.review_database_path))

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


@app.get("/api/config", response_model=ConfigResponse)
def config() -> ConfigResponse:
    return ConfigResponse(
        demo_mode=settings.demo_mode,
        rubric_version="2026-09-16",
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
    return FileResponse(source_path, media_type="application/pdf", filename=document.filename)


@app.get("/api/signals", response_model=list[Signal])
def signals() -> list[Signal]:
    return store.signals()


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


@app.post("/api/jobs", response_model=Run, status_code=202)
def start_job(request: RunRequest, background_tasks: BackgroundTasks) -> Run:
    unknown = set(request.document_ids) - {document.id for document in manifest.documents}
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown document IDs: {sorted(unknown)}")
    run = store.create(request.document_ids)
    background_tasks.add_task(_run_extraction, run.id, request.document_ids)
    return run


def _run_extraction(run_id: str, document_ids: list[str]) -> None:
    try:
        sources = [find_document(manifest, document_id) for document_id in document_ids]
        store.begin(run_id, sum(source.scope.page_count for source in sources))
        extracted: list[Signal] = []
        for source in sources:
            document_signals = extract_document(source, Path(settings.documents_dir))
            extracted.extend(document_signals)
            for page_index in range(source.scope.page_count):
                store.record_page(run_id, document_signals if page_index == 0 else [])
        store.complete(run_id, extracted)
    except Exception as exc:
        store.fail(run_id, f"Extraction failed safely: {type(exc).__name__}")
