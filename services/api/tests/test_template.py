from types import SimpleNamespace

import fitz

from app.services.template import generate_omr_pdf


def test_template_pdf_is_a4_and_contains_a_page() -> None:
    exam = SimpleNamespace(
        id="exam-test-123",
        name="Sample test",
        total_questions=100,
        options_json=["A", "B", "C", "D"],
    )
    document = fitz.open(stream=generate_omr_pdf(exam), filetype="pdf")
    assert len(document) == 1
    page = document[0]
    assert round(page.rect.width) == 595
    assert round(page.rect.height) == 842
