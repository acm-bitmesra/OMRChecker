import pytest

from omr_engine.scoring import (
    QuestionOutcome,
    QuestionPolicy,
    QuestionScoringConfig,
    ScoringRule,
    evaluate_sheet,
    score_responses,
)


def test_scores_correct_incorrect_and_blank_responses() -> None:
    result = score_responses(
        responses={1: ["A"], 2: ["C"], 3: None},
        answer_key={1: ["A"], 2: ["B"], 3: ["D"]},
        rule=ScoringRule(correct=4, incorrect=-1, blank=0),
    )
    assert result.correct_count == 1
    assert result.incorrect_count == 1
    assert result.blank_count == 1
    assert result.score == 3
    assert result.maximum_score == 12


def test_question_sets_must_match() -> None:
    with pytest.raises(ValueError):
        score_responses({1: ["A"]}, {1: ["A"], 2: ["B"]})


def test_evaluate_sheet_supports_dropped_bonus_weighted_and_sections() -> None:
    result = evaluate_sheet(
        responses={
            1: ["A"],
            2: ["B"],
            3: None,
            4: ["D"],  # wrong answer on dropped question -> 0 points, excluded from max
            5: None,   # blank on bonus question -> receives full marks
        },
        answer_key={
            1: ["A"],
            2: ["C"],
            3: ["A", "B"],
            4: ["A"],
            5: ["B"],
        },
        default_rule=ScoringRule(correct=4.0, incorrect=-1.0, blank=0.0),
        question_configs={
            1: QuestionScoringConfig(section="Physics"),
            2: QuestionScoringConfig(section="Physics"),
            3: QuestionScoringConfig(
                rule=ScoringRule(correct=2.0, incorrect=-0.5, blank=-0.25),
                section="Math",
            ),
            4: QuestionScoringConfig(policy=QuestionPolicy.DROPPED, section="Math"),
            5: QuestionScoringConfig(policy=QuestionPolicy.BONUS, section="Math"),
        },
    )

    assert result.correct_count == 1
    assert result.incorrect_count == 1
    assert result.blank_count == 1
    assert result.dropped_count == 1
    assert result.bonus_count == 1
    # Physics: +4 - 1 = 3 / 8; Math: -0.25 + 0 + 4 = 3.75 / 6
    assert result.score == pytest.approx(6.75)
    assert result.maximum_score == pytest.approx(14.0)
    assert result.section_scores["Physics"].score == pytest.approx(3.0)
    assert result.section_scores["Physics"].maximum_score == pytest.approx(8.0)
    assert result.section_scores["Math"].score == pytest.approx(3.75)
    assert result.section_scores["Math"].maximum_score == pytest.approx(6.0)
    assert result.question_results[3].outcome == QuestionOutcome.DROPPED
    assert result.question_results[4].outcome == QuestionOutcome.BONUS


def test_evaluate_sheet_rounds_fractional_floating_point_totals() -> None:
    result = evaluate_sheet(
        responses={1: ["A"], 2: ["A"], 3: ["A"]},
        answer_key={1: ["A"], 2: ["A"], 3: ["B"]},
        default_rule=ScoringRule(correct=1 / 3, incorrect=-1 / 6, blank=0.0),
        decimal_places=2,
    )
    assert result.score == 0.5
    assert result.maximum_score == 1.0


def test_evaluate_sheet_rejects_unknown_question_config() -> None:
    with pytest.raises(ValueError, match="unknown questions"):
        evaluate_sheet(
            responses={1: ["A"]},
            answer_key={1: ["A"]},
            question_configs={99: QuestionScoringConfig()},
        )
