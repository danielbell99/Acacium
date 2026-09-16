from pathlib import Path

from acacium.review_store import ReviewStore
from acacium.run_store import RunStore
from acacium.schemas import Evidence, ReviewRequest, ReviewStatus, Signal


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
        run = store.create(["example"])
        store.begin(run.id, selected_pages=1)
        candidates = [_signal(f"signal-{index}", float(index)) for index in range(25)]
        store.record_page(run.id, candidates)
        store.complete(run.id, candidates)

        completed = store.get(run.id)
        assert completed is not None
        assert completed.progress.candidates_found == 25
        assert len(store.signals()) == 20
        assert store.signals()[0].score == 24
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
    finally:
        first_store.close()
        second_store.close()


def _complete(store: RunStore, signal: Signal) -> None:
    run = store.create(["example"])
    store.begin(run.id, selected_pages=1)
    store.record_page(run.id, [signal])
    store.complete(run.id, [signal])
