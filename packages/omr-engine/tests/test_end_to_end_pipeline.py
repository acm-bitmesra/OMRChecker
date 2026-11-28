import pytest

from omr_engine.classification import QuestionState
from omr_engine.evaluation import (
    GroundTruthQuestion,
    SheetGroundTruth,
    SheetPrediction,
    evaluate_recognition_batch,
)
from omr_engine.measurement import NormalizedBox, measure_question_bubbles
from omr_engine.quality import assess_page_quality, classify_sheet_questions
from omr_engine.scoring import QuestionPolicy, QuestionScoringConfig, ScoringRule, evaluate_sheet


def _build_synthetic_sheet(marked: dict[int, tuple[int, ...]]) -> list[list[int]]:
    sheet = [[248 for _ in range(120)] for _ in range(120)]
    for q_idx in range(1, 5):
        y0 = 10 + (q_idx - 1) * 25
        for opt_idx in range(4):
            x0 = 10 + opt_idx * 25
            for y in range(y0, y0 + 16):
                sheet[y][x0] = 0
                sheet[y][x0 + 15] = 0
            for x in range(x0, x0 + 16):
                sheet[y0][x] = 0
                sheet[y0 + 15][x] = 0
            if opt_idx in marked.get(q_idx, ()):
                for y in range(y0 + 2, y0 + 14):
                    for x in range(x0 + 2, x0 + 14):
                        sheet[y][x] = 15
    return sheet


def _question_regions() -> dict[int, dict[str, NormalizedBox]]:
    regions: dict[int, dict[str, NormalizedBox]] = {}
    for q_idx in range(1, 5):
        y = (10 + (q_idx - 1) * 25) / 120
        regions[q_idx] = {
            label: NormalizedBox(x=(10 + opt_idx * 25) / 120, y=y, width=16 / 120, height=16 / 120)
            for opt_idx, label in enumerate(("A", "B", "C", "D"))
        }
    return regions


def test_omr_engine_full_pipeline_measurement_quality_scoring_and_benchmark() -> None:
    sheet = _build_synthetic_sheet({1: (0,), 2: (2,), 3: (), 4: (1, 3)})
    regions = _question_regions()

    quality = assess_page_quality(sheet, alignment_ok=True, skew_degrees=0.5)
    assert quality.is_valid

    raw_measurements = {
        q_num: measure_question_bubbles(sheet, q_regions, inset_ratio=0.15)
        for q_num, q_regions in regions.items()
    }
    recognition = classify_sheet_questions(raw_measurements, quality)
    assert recognition.needs_review
    assert recognition.review_question_numbers == (4,)

    approved = {
        1: list(recognition.questions[1].selected_options),
        2: list(recognition.questions[2].selected_options),
        3: None,
        4: ["B"],
    }
    score = evaluate_sheet(
        approved,
        answer_key={1: ["A"], 2: ["D"], 3: ["C"], 4: ["B"]},
        default_rule=ScoringRule(correct=4.0, incorrect=-1.0, blank=0.0),
        question_configs={
            1: QuestionScoringConfig(section="Part A"),
            2: QuestionScoringConfig(section="Part A"),
            3: QuestionScoringConfig(policy=QuestionPolicy.BONUS, section="Part B"),
            4: QuestionScoringConfig(section="Part B"),
        },
    )
    # Q1: +4, Q2: -1, Q3 (bonus): +4, Q4: +4 => 11 / 16
    assert score.score == pytest.approx(11.0)
    assert score.maximum_score == pytest.approx(16.0)

    metrics = evaluate_recognition_batch(
        [SheetPrediction(sheet_id="s1", questions=recognition.questions)],
        [
            SheetGroundTruth(
                sheet_id="s1",
                questions={
                    1: GroundTruthQuestion(QuestionState.SINGLE, ("A",)),
                    2: GroundTruthQuestion(QuestionState.SINGLE, ("C",)),
                    3: GroundTruthQuestion(QuestionState.BLANK, ()),
                    4: GroundTruthQuestion(QuestionState.MULTIPLE, ("B", "D")),
                },
            )
        ],
    )
    assert metrics.question_exact_match_rate == 1.0
    assert metrics.full_sheet_exact_match_rate == 1.0
    assert metrics.bubble_precision == 1.0
    assert metrics.bubble_recall == 1.0
