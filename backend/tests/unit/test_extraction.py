from acacium.pipeline.extract import _deduplicate_and_rank, _is_substantive, _service_name
from acacium.schemas import Evidence, ServiceCatalogue, ServiceDefinition, Signal


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


def test_service_selection_prefers_the_more_specific_catalogue_match() -> None:
    services = ServiceCatalogue(
        version="test",
        services=[
            ServiceDefinition(
                id="permanent-recruitment",
                name="Permanent recruitment",
                matches=["recruitment"],
                priority=40,
            ),
            ServiceDefinition(
                id="staff-bank-rpo",
                name="Managed staff bank / RPO",
                matches=["agency"],
                priority=80,
            ),
        ],
    )

    assert (
        _service_name("Agency spend increased despite recruitment activity.", services)
        == "Managed staff bank / RPO"
    )


def test_service_selection_covers_plural_vacancies_and_locums() -> None:
    services = ServiceCatalogue(
        version="test",
        services=[
            ServiceDefinition(
                id="permanent-recruitment",
                name="Permanent recruitment",
                matches=["vacanc"],
                priority=40,
            ),
            ServiceDefinition(
                id="temporary-staffing",
                name="Temporary staffing",
                matches=["locum"],
                priority=60,
            ),
        ],
    )

    assert _service_name("Nursing vacancies are increasing.", services) == "Permanent recruitment"
    assert _service_name("The rota uses locums.", services) == "Temporary staffing"


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
