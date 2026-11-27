from dataclasses import dataclass
from typing import Mapping, Sequence

from omr_engine.classification import MarkState, QuestionDecision, QuestionState


@dataclass(frozen=True, slots=True)
class GroundTruthQuestion:
    """Ground-truth recognition expectation for one question on a labeled sheet."""

    expected_state: QuestionState
    expected_options: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SheetGroundTruth:
    """Labeled ground truth for a single OMR sheet."""

    sheet_id: str
    questions: Mapping[int, GroundTruthQuestion]


@dataclass(frozen=True, slots=True)
class SheetPrediction:
    """Engine prediction for a single OMR sheet."""

    sheet_id: str
    questions: Mapping[int, QuestionDecision]
    needs_recapture: bool = False


@dataclass(frozen=True, slots=True)
class RecognitionBenchmarkMetrics:
    """Aggregate recognition quality metrics for golden-dataset evaluation."""

    total_sheets: int
    total_questions: int
    bubble_precision: float
    bubble_recall: float
    question_exact_match_rate: float
    full_sheet_exact_match_rate: float
    false_acceptance_rate: float
    manual_review_rate: float
    recapture_rate: float


def evaluate_recognition_batch(
    predictions: Sequence[SheetPrediction],
    ground_truths: Sequence[SheetGroundTruth],
    *,
    include_multiple_in_review: bool = True,
) -> RecognitionBenchmarkMetrics:
    """Compute bubble, question, sheet, review, and false-acceptance metrics."""
    if not predictions or not ground_truths:
        raise ValueError("predictions and ground_truths must not be empty")
    if len(predictions) != len(ground_truths):
        raise ValueError("predictions and ground_truths must have equal length")
    if any(not prediction.questions for prediction in predictions):
        raise ValueError("every prediction sheet must contain at least one question")
    if any(not truth.questions for truth in ground_truths):
        raise ValueError("every ground-truth sheet must contain at least one question")

    truth_by_id = {gt.sheet_id: gt for gt in ground_truths}
    if len(truth_by_id) != len(ground_truths):
        raise ValueError("ground_truths must have unique sheet_id values")

    seen_predictions: set[str] = set()
    true_positives = false_positives = false_negatives = 0
    total_questions = 0
    exact_questions = 0
    exact_sheets = 0
    uncertain_gt_count = 0
    falsely_accepted_uncertain = 0
    review_questions = 0
    recapture_sheets = 0

    for pred in predictions:
        if pred.sheet_id in seen_predictions:
            raise ValueError(f"Duplicate prediction sheet_id: {pred.sheet_id}")
        seen_predictions.add(pred.sheet_id)

        gt = truth_by_id.get(pred.sheet_id)
        if gt is None:
            raise ValueError(f"Missing ground truth for sheet_id: {pred.sheet_id}")
        if set(pred.questions) != set(gt.questions):
            raise ValueError(
                f"Question numbers mismatch for sheet_id {pred.sheet_id}"
            )

        if pred.needs_recapture:
            recapture_sheets += 1

        sheet_exact = True
        for q_num, expected in gt.questions.items():
            total_questions += 1
            decision = pred.questions[q_num]

            if decision.state == QuestionState.UNCERTAIN or (
                include_multiple_in_review and decision.state == QuestionState.MULTIPLE
            ):
                review_questions += 1

            if expected.expected_state == QuestionState.UNCERTAIN:
                uncertain_gt_count += 1
                if decision.state != QuestionState.UNCERTAIN:
                    falsely_accepted_uncertain += 1

            pred_set = {
                b.option for b in decision.bubbles if b.state == MarkState.FILLED
            }
            if not pred_set and decision.selected_options:
                pred_set = set(decision.selected_options)
            gt_set = set(expected.expected_options)

            if expected.expected_state != QuestionState.UNCERTAIN:
                true_positives += len(pred_set & gt_set)
                false_positives += len(pred_set - gt_set)
                false_negatives += len(gt_set - pred_set)

            is_question_exact = (
                decision.state == expected.expected_state
                and set(decision.selected_options) == gt_set
            )
            if is_question_exact:
                exact_questions += 1
            else:
                sheet_exact = False

        if sheet_exact:
            exact_sheets += 1

    precision = (
        true_positives / (true_positives + false_positives)
        if (true_positives + false_positives) > 0
        else 1.0
    )
    recall = (
        true_positives / (true_positives + false_negatives)
        if (true_positives + false_negatives) > 0
        else 1.0
    )
    false_acceptance_rate = (
        falsely_accepted_uncertain / uncertain_gt_count
        if uncertain_gt_count > 0
        else 0.0
    )

    total_sheets = len(predictions)
    return RecognitionBenchmarkMetrics(
        total_sheets=total_sheets,
        total_questions=total_questions,
        bubble_precision=precision,
        bubble_recall=recall,
        question_exact_match_rate=exact_questions / total_questions,
        full_sheet_exact_match_rate=exact_sheets / total_sheets,
        false_acceptance_rate=false_acceptance_rate,
        manual_review_rate=review_questions / total_questions,
        recapture_rate=recapture_sheets / total_sheets,
    )
