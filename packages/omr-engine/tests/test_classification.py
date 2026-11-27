import pytest

from omr_engine.classification import (
    MarkState,
    QuestionState,
    classify_bubble,
    classify_question,
)


def test_clear_filled_and_blank_bubbles() -> None:
    assert classify_bubble("A", 0.05).state == MarkState.BLANK
    assert classify_bubble("B", 0.92).state == MarkState.FILLED


def test_threshold_gap_is_uncertain() -> None:
    assert classify_bubble("C", 0.40).state == MarkState.UNCERTAIN


def test_single_mark() -> None:
    result = classify_question([("A", 0.05), ("B", 0.90), ("C", 0.08), ("D", 0.06)])
    assert result.state == QuestionState.SINGLE
    assert result.selected_options == ("B",)


def test_multiple_marks() -> None:
    result = classify_question([("A", 0.91), ("B", 0.05), ("C", 0.88), ("D", 0.04)])
    assert result.state == QuestionState.MULTIPLE


def test_ambiguous_option_is_uncertain() -> None:
    result = classify_question([("A", 0.05), ("B", 0.40), ("C", 0.05), ("D", 0.05)])
    assert result.state == QuestionState.UNCERTAIN


def test_invalid_ratio_is_rejected() -> None:
    with pytest.raises(ValueError):
        classify_bubble("A", 1.2)


def test_duplicate_options_are_rejected() -> None:
    with pytest.raises(ValueError):
        classify_question([("A", 0.1), ("A", 0.9)])
