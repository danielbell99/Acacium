from __future__ import annotations

from datetime import UTC, datetime
from threading import Lock
from uuid import uuid4

from acacium.review_store import ReviewStore
from acacium.schemas import ReviewRequest, ReviewStatus, Run, RunProgress, RunStatus, Signal


class RunStore:
    """Coordinates active extraction with a durable local evidence snapshot."""

    def __init__(self, review_store: ReviewStore) -> None:
        self._lock = Lock()
        self._review_store = review_store
        recovered_runs = review_store.load_runs()
        self._runs: dict[str, Run] = {run.id: run for run in recovered_runs}
        completed_runs = [run for run in recovered_runs if run.status is RunStatus.COMPLETED]
        latest = max(
            completed_runs,
            key=lambda run: run.completed_at or run.created_at,
            default=None,
        )
        self._signals = (
            {signal.id: signal for signal in review_store.load_signals(latest.id)}
            if latest is not None
            else {}
        )

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
            self._review_store.save_run(run)
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
            self._review_store.save_run(run)

    def record_page(self, run_id: str, candidates: list[Signal]) -> None:
        with self._lock:
            run = self._runs[run_id]
            run.progress.processed_pages += 1
            run.progress.candidates_found += len(candidates)
            self._review_store.save_run(run)

    def complete(self, run_id: str, signals: list[Signal]) -> None:
        with self._lock:
            run = self._runs[run_id]
            shortlisted = sorted(signals, key=lambda signal: (-signal.score, signal.id))[:20]
            reviewed = self._review_store.apply(shortlisted)
            self._signals = {signal.id: signal for signal in reviewed}
            self._review_store.replace_signals(run_id, reviewed)
            run.status = RunStatus.COMPLETED
            run.completed_at = datetime.now(UTC)
            self._review_store.save_run(run)

    def fail(self, run_id: str, message: str) -> None:
        with self._lock:
            run = self._runs[run_id]
            run.status = RunStatus.FAILED
            run.error = message
            run.completed_at = datetime.now(UTC)
            self._review_store.save_run(run)

    def signals(self) -> list[Signal]:
        with self._lock:
            return sorted(self._signals.values(), key=lambda signal: (-signal.score, signal.id))

    def approved_signals(self) -> list[Signal]:
        return [
            signal for signal in self.signals() if signal.review_status is ReviewStatus.APPROVED
        ]

    def review(self, signal_id: str, request: ReviewRequest) -> Signal | None:
        with self._lock:
            signal = self._signals.get(signal_id)
            if signal is None:
                return None
            signal.review_status = request.decision
            signal.review_reason = request.reason
            self._review_store.save(signal_id, request)
            self._review_store.update_signal(signal)
            return signal

    def close(self) -> None:
        self._review_store.close()
