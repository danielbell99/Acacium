from acacium.catalogue import load_manifest, load_scoring_rubric, load_service_catalogue
from acacium.pipeline.extract import (
    _deduplicate_and_rank,
    _is_substantive,
    _matching_excerpts,
    _service_name,
    _to_signal,
)
from acacium.schemas import Evidence, ServiceCatalogue, ServiceDefinition, Signal
from acacium.settings import get_settings

RUBRIC = load_scoring_rubric(get_settings().scoring_rubric_path)


def test_rejects_a_generic_agency_reference() -> None:
    assert not _is_substantive(
        "Feedback to the employing agency regarding the locum's performance.", RUBRIC
    )


def test_accepts_evidenced_temporary_staffing_context() -> None:
    assert _is_substantive("Agency spend was £380k and above the cap in the current month.", RUBRIC)


def test_accepts_a_specific_recruitment_context() -> None:
    assert _is_substantive(
        "The consultant vacancy remains open despite active recruitment.", RUBRIC
    )


def test_configured_measurable_staffing_band_drives_the_score_and_reasons() -> None:
    document = load_manifest(get_settings().manifest_path).documents[0]
    services = load_service_catalogue(get_settings().service_catalogue_path)

    signal = _to_signal(
        document,
        page=1,
        excerpt="Agency expenditure was £380k above cap for 4.2 WTE.",
        service_catalogue=services,
        scoring_rubric=RUBRIC,
    )

    assert signal.category == "temporary-staff expenditure"
    assert signal.score == 92.5
    assert signal.score_reasons == [
        "Clear workforce-service fit",
        "Explicit spend or staffing evidence",
        "Recent pack",
    ]


def test_discards_an_overlong_passage_when_its_visible_excerpt_lacks_evidence() -> None:
    page_text = f"{'x' * 920} agency spend was noted."

    assert list(_matching_excerpts(page_text, RUBRIC)) == []


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


def test_service_selection_covers_recruited_language_from_board_papers() -> None:
    services = load_service_catalogue(get_settings().service_catalogue_path)

    assert _service_name("The service has recruited a psychologist.", services) == (
        "Permanent recruitment"
    )


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
