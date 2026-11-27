import numpy as np
import pytest

from omr_engine.classification import QuestionState
from omr_engine.quality import (
    QualityIssue,
    assess_page_quality,
    classify_sheet_questions,
)


def _good_sheet() -> list[list[int]]:
    # Crisp printed dark marks (~10%) on bright paper (~90%)
    rows: list[list[int]] = []
    for y in range(20):
        row = [20 if (y in (2, 3) and x < 10) else 240 for x in range(20)]
        rows.append(row)
    return rows


def test_assess_page_quality_accepts_clear_aligned_sheet() -> None:
    report = assess_page_quality(_good_sheet(), alignment_ok=True, skew_degrees=1.5)
    assert report.is_valid
    assert report.issues == ()
    assert report.contrast_span == 220


def test_assess_page_quality_flags_low_contrast_glare_skew_and_missing_alignment() -> None:
    washed_out = [[253 for _ in range(10)] for _ in range(10)]
    report = assess_page_quality(
        washed_out,
        alignment_ok=False,
        skew_degrees=15.0,
    )
    assert not report.is_valid
    assert QualityIssue.ALIGNMENT_MISSING in report.issues
    assert QualityIssue.EXTREME_SKEW in report.issues
    assert QualityIssue.LOW_CONTRAST in report.issues
    assert QualityIssue.EXCESSIVE_GLARE in report.issues


def test_invalid_quality_forces_all_questions_to_uncertain_for_review() -> None:
    bad_quality = assess_page_quality(_good_sheet(), alignment_ok=False)
    result = classify_sheet_questions(
        {
            1: [("A", 0.05), ("B", 0.92), ("C", 0.05), ("D", 0.05)],
            2: [("A", 0.02), ("B", 0.03), ("C", 0.04), ("D", 0.05)],
        },
        bad_quality,
    )
    assert result.needs_review
    assert result.review_question_numbers == (1, 2)
    assert result.questions[1].state == QuestionState.UNCERTAIN
    assert result.questions[1].selected_options == ()
    assert result.questions[2].state == QuestionState.UNCERTAIN


def test_valid_quality_routes_only_uncertain_and_multiple_questions_to_review() -> None:
    good_quality = assess_page_quality(_good_sheet())
    result = classify_sheet_questions(
        {
            1: [("A", 0.05), ("B", 0.90), ("C", 0.05), ("D", 0.05)],  # single
            2: [("A", 0.91), ("B", 0.89), ("C", 0.05), ("D", 0.05)],  # multiple
            3: [("A", 0.05), ("B", 0.42), ("C", 0.05), ("D", 0.05)],  # uncertain
            4: [("A", 0.05), ("B", 0.05), ("C", 0.05), ("D", 0.05)],  # blank
        },
        good_quality,
        route_multiple_to_review=True,
    )
    assert result.needs_review
    assert result.review_question_numbers == (2, 3)
    assert result.questions[1].state == QuestionState.SINGLE
    assert result.questions[4].state == QuestionState.BLANK


def test_empty_measurements_raises() -> None:
    good_quality = assess_page_quality(_good_sheet())
    with pytest.raises(ValueError):
        classify_sheet_questions({}, good_quality)



def test_quality_assessment_accepts_numpy_arrays_and_uses_bounded_sampling() -> None:
    image = np.full((1000, 1000), 240, dtype=np.uint8)
    report = assess_page_quality(image, max_sample_pixels=10_000)
    assert report.samples_used <= 10_000
    assert report.sample_stride >= 1
    assert report.contrast_span == 0

    with pytest.raises(ValueError, match="image must be non-empty"):
        assess_page_quality(np.empty((0, 100), dtype=np.uint8))


def test_quality_assessment_rejects_invalid_sample_limit() -> None:
    with pytest.raises(ValueError, match="max_sample_pixels must be positive"):
        assess_page_quality(_good_sheet(), max_sample_pixels=0)
