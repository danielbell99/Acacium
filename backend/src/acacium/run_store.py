from __future__ import annotations

from datetime import UTC, datetime
from threading import Lock
from uuid import uuid4

from acacium.schemas import ReviewRequest, Run, RunProgress, RunStatus, Signal


class RunStore:
    """Small, explicit in-process store. Durable persistence is the next build slice."""

    def __init__(self) -> None:
        self._runs: dict[str, Run] = {}
        self._signals: dict[str, Signal] = {}
        self._lock = Lock()

    def create(self, document_ids: list[str]) -> Run:
        run = Run(
            id=str(uuid4()),
            status=RunStatus.QUEUED,
            created_at=datetime.now(UTC),
            document_ids=document_ids,
            progress=RunProgress(),
        )
        with self._lock:
            self._runs[run.id] = run
        return run

    def get(self, run_id: str) -> Run | None:
        with self._lock:
            return self._runs.get(run_id)

    def list_runs(self) -> list[Run]:
        with self._lock:
            return sorted(self._runs.values(), key=lambda run: run.created_at, reverse=True)

    def begin(self, run_id: str, selected_pages: int) -> None:
        with self._lock:
            run = self._runs[run_id]
            run.status = RunStatus.RUNNING
            run.progress.selected_pages = selected_pages

    def record_page(self, run_id: str, candidates: list[Signal]) -> None:
        with self._lock:
            run = self._runs[run_id]
            run.progress.processed_pages += 1
            run.progress.candidates_found += len(candidates)

    def complete(self, run_id: str, signals: list[Signal]) -> None:
        with self._lock:
            run = self._runs[run_id]
            shortlisted = sorted(signals, key=lambda signal: (-signal.score, signal.id))[:20]
            self._signals.update({signal.id: signal for signal in shortlisted})
            run.status = RunStatus.COMPLETED
            run.completed_at = datetime.now(UTC)

    def fail(self, run_id: str, message: str) -> None:
        with self._lock:
            run = self._runs[run_id]
            run.status = RunStatus.FAILED
            run.error = message
            run.completed_at = datetime.now(UTC)

    def signals(self) -> list[Signal]:
        with self._lock:
            return sorted(self._signals.values(), key=lambda signal: (-signal.score, signal.id))

    def review(self, signal_id: str, request: ReviewRequest) -> Signal | None:
        with self._lock:
            signal = self._signals.get(signal_id)
            if signal is None:
                return None
            signal.review_status = request.decision
            signal.review_reason = request.reason
            return signal
