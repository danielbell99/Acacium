from acacium.catalogue import load_manifest, load_scoring_rubric, load_service_catalogue
from acacium.settings import get_settings


def test_manifest_has_three_distinct_scoped_reports() -> None:
    manifest = load_manifest(get_settings().manifest_path)

    assert len(manifest.documents) == 3
    assert manifest.selected_report_page_count == 105
    assert sum(document.scope.page_count for document in manifest.documents) == 105
    assert {document.organisation for document in manifest.documents} == {
        "West Hertfordshire Teaching Hospitals NHS Trust",
        "Airedale NHS Foundation Trust",
        "The Shrewsbury and Telford Hospital NHS Trust",
    }


def test_service_catalogue_has_a_specific_temporary_staffing_service() -> None:
    services = load_service_catalogue(get_settings().service_catalogue_path)

    assert services.version == "2026-09-16"
    assert [service.id for service in services.services] == [
        "permanent-recruitment",
        "staff-bank-rpo",
        "temporary-staffing",
    ]


def test_scoring_rubric_has_explicit_evidence_bands() -> None:
    rubric = load_scoring_rubric(get_settings().scoring_rubric_path)

    assert rubric.version == "2026-09-16"
    assert rubric.rules[0].category == "temporary-staff expenditure"
    assert rubric.rules[0].score_bands[0].score == 92.5
