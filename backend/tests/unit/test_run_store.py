import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from acacium.review_store import ReviewStore
from acacium.run_store import RunStore
from acacium.schemas import (
    Evidence,
    ReviewRequest,
    ReviewStatus,
    Run,
    RunProgress,
    RunStatus,
    Signal,
)

RUN_PROVENANCE = {
    "as_of_date": "2026-09-16",
    "rubric_version": "2026-09-16",
    "source_manifest_version": "1.0",
    "service_catalogue_version": "2026-09-16",
}


def _signal(identifier: str, score: float) -> Signal:
    return Signal(
        id=identifier,
        organisation="Example Trust",
        category="vacancy pressure",
        service="Permanent recruitment",
        source_fact="A dated workforce vacancy was reported.",
        interpretation="Requires reviewer validation.",
        score=score,
        score_reasons=["Test score"],
        proposed_next_action="Validate the position.",
        evidence=Evidence(
            document_id="example",
            filename="example.pdf",
            physical_page=1,
            excerpt="A dated workforce vacancy was reported.",
            scope_title="Example scope",
        ),
    )


def test_run_store_counts_candidates_and_keeps_top_twenty(tmp_path: Path) -> None:
    store = RunStore(ReviewStore(tmp_path / "reviews.sqlite3"))
    try:
        run = store.create(["example"], **RUN_PROVENANCE)
        store.begin(run.id, selected_pages=1)
        candidates = [_signal(f"signal-{index}", float(index)) for index in range(25)]
        store.record_page(run.id, candidates)
        store.complete(run.id, candidates)

        completed = store.get(run.id)
        assert completed is not None
        assert completed.progress.candidates_found == 25
        assert completed.as_of_date == "2026-09-16"
        assert completed.source_manifest_version == "1.0"
        assert completed.service_catalogue_version == "2026-09-16"
        assert len(store.signals()) == 20
        assert len(store.signals_for_run(run.id) or []) == 20
        assert store.signals()[0].score == 24
        assert store.approved_signals() == []
    finally:
        store.close()


def test_review_decision_is_reapplied_to_a_fresh_extraction(tmp_path: Path) -> None:
    reviews = ReviewStore(tmp_path / "reviews.sqlite3")
    first_store = RunStore(reviews)
    first = _signal("stable-signal", 92.5)
    _complete(first_store, first)
    first_store.review(
        first.id,
        ReviewRequest(decision=ReviewStatus.APPROVED, reason="Evidence checked."),
    )

    second_store = RunStore(ReviewStore(tmp_path / "reviews.sqlite3"))
    rerun = _signal("stable-signal", 92.5)
    _complete(second_store, rerun)

    try:
        assert second_store.signals()[0].review_status is ReviewStatus.APPROVED
        assert second_store.signals()[0].review_reason == "Evidence checked."
        assert len(second_store.approved_signals()) == 1
    finally:
        first_store.close()
        second_store.close()


def test_completed_run_and_shortlist_survive_a_restart(tmp_path: Path) -> None:
    database_path = tmp_path / "reviews.sqlite3"
    first_store = RunStore(ReviewStore(database_path))
    signal = _signal("persisted-signal", 91.0)
    _complete(first_store, signal)
    run = first_store.list_runs()[0]
    first_store.close()

    second_store = RunStore(ReviewStore(database_path))
    try:
        recovered = second_store.get(run.id)
        assert recovered is not None
        assert recovered.status is RunStatus.COMPLETED
        assert [stored.id for stored in second_store.signals()] == [signal.id]
    finally:
        second_store.close()


def test_in_progress_run_is_marked_failed_after_a_restart(tmp_path: Path) -> None:
    database_path = tmp_path / "reviews.sqlite3"
    first_store = RunStore(ReviewStore(database_path))
    run = first_store.create(["example"], **RUN_PROVENANCE)
    first_store.begin(run.id, selected_pages=1)
    first_store.close()

    second_store = RunStore(ReviewStore(database_path))
    try:
        recovered = second_store.get(run.id)
        assert recovered is not None
        assert recovered.status is RunStatus.FAILED
        assert recovered.error == "Local process restarted before extraction completed."
    finally:
        second_store.close()


def test_unknown_run_has_no_retained_signal_snapshot(tmp_path: Path) -> None:
    store = RunStore(ReviewStore(tmp_path / "reviews.sqlite3"))
    try:
        assert store.signals_for_run("unknown-run") is None
    finally:
        store.close()


def test_identical_signals_are_retained_for_each_completed_run(tmp_path: Path) -> None:
    store = RunStore(ReviewStore(tmp_path / "reviews.sqlite3"))
    first = _signal("stable-signal", 91.0)
    second = _signal("stable-signal", 91.0)
    try:
        first_run = _complete(store, first)
        second_run = _complete(store, second)

        assert [signal.id for signal in store.signals_for_run(first_run.id) or []] == [
            "stable-signal"
        ]
        assert [signal.id for signal in store.signals_for_run(second_run.id) or []] == [
            "stable-signal"
        ]
    finally:
        store.close()


def test_legacy_signal_key_is_migrated_without_losing_the_latest_snapshot(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "reviews.sqlite3"
    signal = _signal("legacy-signal", 91.0)
    run = Run(
        id="legacy-run",
        status=RunStatus.COMPLETED,
        created_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        document_ids=["example"],
        progress=RunProgress(selected_pages=1, processed_pages=1, candidates_found=1),
        **RUN_PROVENANCE,
    )
    connection = sqlite3.connect(database_path)
    connection.executescript(
        """
        CREATE TABLE extraction_runs (
            run_id TEXT PRIMARY KEY,
            payload_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE extracted_signals (
            signal_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(run_id) REFERENCES extraction_runs(run_id)
        );
        """
    )
    connection.execute(
        "INSERT INTO extraction_runs VALUES (?, ?, ?)",
        (run.id, run.model_dump_json(), datetime.now(UTC).isoformat()),
    )
    connection.execute(
        "INSERT INTO extracted_signals VALUES (?, ?, ?, ?)",
        (signal.id, run.id, signal.model_dump_json(), datetime.now(UTC).isoformat()),
    )
    connection.commit()
    connection.close()

    store = RunStore(ReviewStore(database_path))
    try:
        assert [stored.id for stored in store.signals_for_run(run.id) or []] == [signal.id]
    finally:
        store.close()

    connection = sqlite3.connect(database_path)
    try:
        primary_key = {
            row[1]: row[5] for row in connection.execute("PRAGMA table_info(extracted_signals)")
        }
        assert primary_key == {
            "signal_id": 2,
            "run_id": 1,
            "payload_json": 0,
            "created_at": 0,
        }
    finally:
        connection.close()


def _complete(store: RunStore, signal: Signal) -> Run:
    run = store.create(["example"], **RUN_PROVENANCE)
    store.begin(run.id, selected_pages=1)
    store.record_page(run.id, [signal])
    store.complete(run.id, [signal])
    return run
