from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"


class ReviewStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Evidence(BaseModel):
    document_id: str
    filename: str
    physical_page: int = Field(ge=1)
    excerpt: str = Field(min_length=1)
    scope_title: str


class Signal(BaseModel):
    id: str
    organisation: str
    category: str
    service: str
    source_fact: str
    interpretation: str
    reporting_period: str | None = None
    score: float = Field(ge=0, le=100)
    score_reasons: list[str]
    proposed_next_action: str
    evidence: Evidence
    review_status: ReviewStatus = ReviewStatus.PENDING
    review_reason: str | None = None
    caveats: list[str] = []


class DocumentScope(BaseModel):
    title: str = Field(validation_alias="report_title")
    first_physical_page: int
    last_physical_page: int
    page_count: int
    reporting_period: str
    layout: str


class SourceDocument(BaseModel):
    id: str
    organisation: str
    meeting_date: str
    filename: str
    source_url: str
    listing_url: str
    sha256: str
    page_count: int
    scope: DocumentScope
    reference_pages: list[int]


class DocumentList(BaseModel):
    manifest_version: str
    selected_report_page_count: int
    documents: list[SourceDocument]


class RunRequest(BaseModel):
    document_ids: list[str] = Field(min_length=1)
    as_of_date: str = "2026-09-16"


class ReviewRequest(BaseModel):
    decision: ReviewStatus
    reason: str = Field(min_length=3, max_length=500)


class RunProgress(BaseModel):
    selected_pages: int = 0
    processed_pages: int = 0
    candidates_found: int = 0


class Run(BaseModel):
    id: str
    status: RunStatus
    created_at: datetime
    completed_at: datetime | None = None
    document_ids: list[str]
    progress: RunProgress
    error: str | None = None


class ConfigResponse(BaseModel):
    demo_mode: bool
    rubric_version: str
    source_manifest_version: str
    score_formula: str
