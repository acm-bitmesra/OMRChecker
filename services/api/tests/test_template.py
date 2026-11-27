from types import SimpleNamespace

import fitz

from app.services.template import generate_omr_pdf


def make_exam(total_questions: int = 100):
    return SimpleNamespace(
        id="exam-test-123",
        name="Sample test",
        total_questions=total_questions,
        options_json=["A", "B", "C", "D"],
    )


def test_template_pdf_is_a4_and_contains_a_page() -> None:
    document = fitz.open(stream=generate_omr_pdf(make_exam()), filetype="pdf")
    assert len(document) == 1
    page = document[0]
    assert round(page.rect.width) == 595
    assert round(page.rect.height) == 842


def test_option_legend_is_printed_once_per_column_not_inside_each_bubble() -> None:
    document = fitz.open(stream=generate_omr_pdf(make_exam(total_questions=8)), filetype="pdf")
    words = document[0].get_text("words")
    labels = [word for word in words if word[4] in {"A", "B", "C", "D"}]

    # Two 50-question columns each get one A/B/C/D legend.
    # The old implementation printed these letters inside every bubble.
    assert len(labels) == 8
    assert all(word[1] < 153 for word in labels)
