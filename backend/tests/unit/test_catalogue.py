from acacium.catalogue import load_manifest
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
