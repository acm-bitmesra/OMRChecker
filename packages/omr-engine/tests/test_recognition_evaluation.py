import pytest

from omr_engine.classification import QuestionState, classify_question
from omr_engine.evaluation import (
    GroundTruthQuestion,
    SheetGroundTruth,
    SheetPrediction,
    evaluate_recognition_batch,
)


def test_evaluate_recognition_batch_computes_exact_and_review_metrics() -> None:
    pred_sheet_1 = SheetPrediction(
        sheet_id="sheet-1",
        questions={
            1: classify_question([("A", 0.05), ("B", 0.90), ("C", 0.05), ("D", 0.05)]),
            2: classify_question([("A", 0.05), ("B", 0.05), ("C", 0.05), ("D", 0.05)]),
        },
    )
    pred_sheet_2 = SheetPrediction(
        sheet_id="sheet-2",
        needs_recapture=True,
        questions={
            1: classify_question([("A", 0.90), ("B", 0.88), ("C", 0.05), ("D", 0.05)]),
            # Ground truth is UNCERTAIN, but engine falsely classified as SINGLE ("A")
            2: classify_question([("A", 0.80), ("B", 0.05), ("C", 0.05), ("D", 0.05)]),
        },
    )

    gt_sheet_1 = SheetGroundTruth(
        sheet_id="sheet-1",
        questions={
            1: GroundTruthQuestion(QuestionState.SINGLE, ("B",)),
            2: GroundTruthQuestion(QuestionState.BLANK, ()),
        },
    )
    gt_sheet_2 = SheetGroundTruth(
        sheet_id="sheet-2",
        questions={
            1: GroundTruthQuestion(QuestionState.MULTIPLE, ("A", "B")),
            2: GroundTruthQuestion(QuestionState.UNCERTAIN, ()),
        },
    )

    metrics = evaluate_recognition_batch(
        [pred_sheet_1, pred_sheet_2],
        [gt_sheet_1, gt_sheet_2],
    )

    assert metrics.total_sheets == 2
    assert metrics.total_questions == 4
    assert metrics.bubble_precision == pytest.approx(1.0)
    assert metrics.bubble_recall == pytest.approx(1.0)
    assert metrics.question_exact_match_rate == pytest.approx(0.75)
    assert metrics.full_sheet_exact_match_rate == pytest.approx(0.5)
    assert metrics.false_acceptance_rate == pytest.approx(1.0)
    assert metrics.manual_review_rate == pytest.approx(0.25)
    assert metrics.recapture_rate == pytest.approx(0.5)


def test_evaluate_recognition_batch_rejects_mismatched_sheets_or_questions() -> None:
    pred = SheetPrediction(
        sheet_id="s1",
        questions={1: classify_question([("A", 0.9), ("B", 0.05)])},
    )
    gt = SheetGroundTruth(
        sheet_id="s2",
        questions={1: GroundTruthQuestion(QuestionState.SINGLE, ("A",))},
    )
    with pytest.raises(ValueError, match="Missing ground truth"):
        evaluate_recognition_batch([pred], [gt])
