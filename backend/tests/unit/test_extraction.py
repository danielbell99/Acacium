from acacium.pipeline.extract import _is_substantive


def test_rejects_a_generic_agency_reference() -> None:
    assert not _is_substantive(
        "Feedback to the employing agency regarding the locum's performance."
    )


def test_accepts_evidenced_temporary_staffing_context() -> None:
    assert _is_substantive("Agency spend was £380k and above the cap in the current month.")


def test_accepts_a_specific_recruitment_context() -> None:
    assert _is_substantive("The consultant vacancy remains open despite active recruitment.")
