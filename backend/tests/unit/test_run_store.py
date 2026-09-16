from acacium.run_store import RunStore
from acacium.schemas import Evidence, Signal


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


def test_run_store_counts_candidates_and_keeps_top_twenty() -> None:
    store = RunStore()
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
