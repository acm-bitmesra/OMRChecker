import pytest

from omr_engine.scoring import ScoringRule, score_responses


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
