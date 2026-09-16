from acacium.pipeline.extract import _deduplicate_and_rank, _is_substantive
from acacium.schemas import Evidence, Signal


def test_rejects_a_generic_agency_reference() -> None:
    assert not _is_substantive(
        "Feedback to the employing agency regarding the locum's performance."
    )


def test_accepts_evidenced_temporary_staffing_context() -> None:
    assert _is_substantive("Agency spend was £380k and above the cap in the current month.")


def test_accepts_a_specific_recruitment_context() -> None:
    assert _is_substantive("The consultant vacancy remains open despite active recruitment.")


def test_keeps_the_strongest_candidate_for_each_source_page() -> None:
    weaker = _candidate("Generic agency costs were noted.")
    stronger = _candidate("Agency expenditure was £380k above cap for 4.2 WTE.")

    shortlisted = _deduplicate_and_rank([weaker, stronger])

    assert [signal.source_fact for signal in shortlisted] == [stronger.source_fact]


def _candidate(source_fact: str) -> Signal:
    return Signal(
        id=source_fact,
        organisation="Example Trust",
        category="temporary-staff expenditure",
        service="Managed staff bank / RPO",
        source_fact=source_fact,
        interpretation="Requires review.",
        score=92.5,
        score_reasons=["Test evidence"],
        proposed_next_action="Validate the position.",
        evidence=Evidence(
            document_id="example",
            filename="example.pdf",
            physical_page=1,
            excerpt=source_fact,
            scope_title="Example scope",
        ),
    )
