from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True, slots=True)
class ScoringRule:
    correct: float = 1.0
    incorrect: float = 0.0
    blank: float = 0.0


@dataclass(frozen=True, slots=True)
class ScoreSummary:
    correct_count: int
    incorrect_count: int
    blank_count: int
    score: float
    maximum_score: float


def score_responses(
    responses: Mapping[int, Sequence[str] | None],
    answer_key: Mapping[int, Sequence[str]],
    rule: ScoringRule = ScoringRule(),
) -> ScoreSummary:
    """Score approved responses; uncertain recognition must be resolved first.

    A non-empty response is incorrect unless its normalized option set exactly
    matches the answer key. Bonus, dropped, and weighted questions need an
    explicit expanded rule model before being used in production.
    """
    if set(responses) != set(answer_key):
        raise ValueError("responses and answer_key must contain the same question numbers")

    correct_count = incorrect_count = blank_count = 0
    score = 0.0
    maximum_score = len(answer_key) * max(rule.correct, 0.0)

    for question_number, expected in answer_key.items():
        actual = responses[question_number]
        if actual is None or len(actual) == 0:
            blank_count += 1
            score += rule.blank
        elif set(actual) == set(expected):
            correct_count += 1
            score += rule.correct
        else:
            incorrect_count += 1
            score += rule.incorrect

    return ScoreSummary(
        correct_count=correct_count,
        incorrect_count=incorrect_count,
        blank_count=blank_count,
        score=score,
        maximum_score=maximum_score,
    )
