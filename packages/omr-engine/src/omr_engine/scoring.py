from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping, Sequence


@dataclass(frozen=True, slots=True)
class ScoringRule:
    correct: float = 1.0
    incorrect: float = 0.0
    blank: float = 0.0


class QuestionPolicy(StrEnum):
    STANDARD = "standard"
    DROPPED = "dropped"
    BONUS = "bonus"


class QuestionOutcome(StrEnum):
    CORRECT = "correct"
    INCORRECT = "incorrect"
    BLANK = "blank"
    DROPPED = "dropped"
    BONUS = "bonus"


@dataclass(frozen=True, slots=True)
class QuestionScoringConfig:
    """Per-question override for weights, dropped/bonus policies, and section grouping."""

    rule: ScoringRule | None = None
    policy: QuestionPolicy = QuestionPolicy.STANDARD
    section: str | None = None


@dataclass(frozen=True, slots=True)
class QuestionScoreDetail:
    question_number: int
    outcome: QuestionOutcome
    actual: tuple[str, ...]
    expected: tuple[str, ...]
    points_awarded: float
    max_points: float
    section: str | None = None


@dataclass(frozen=True, slots=True)
class ScoreSummary:
    correct_count: int
    incorrect_count: int
    blank_count: int
    score: float
    maximum_score: float


@dataclass(frozen=True, slots=True)
class DetailedScoreSummary:
    correct_count: int
    incorrect_count: int
    blank_count: int
    dropped_count: int
    bonus_count: int
    score: float
    maximum_score: float
    question_results: tuple[QuestionScoreDetail, ...]
    section_scores: dict[str, ScoreSummary]


def score_responses(
    responses: Mapping[int, Sequence[str] | None],
    answer_key: Mapping[int, Sequence[str]],
    rule: ScoringRule = ScoringRule(),
) -> ScoreSummary:
    """Score approved responses; uncertain recognition must be resolved first.

    A non-empty response is incorrect unless its normalized option set exactly
    matches the answer key. For dropped, bonus, weighted, or section-level rules,
    use :func:`evaluate_sheet`.
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


def evaluate_sheet(
    responses: Mapping[int, Sequence[str] | None],
    answer_key: Mapping[int, Sequence[str]],
    *,
    default_rule: ScoringRule = ScoringRule(),
    question_configs: Mapping[int, QuestionScoringConfig] | None = None,
    decimal_places: int = 2,
) -> DetailedScoreSummary:
    """Evaluate approved sheet responses with weighted, dropped, bonus, and section rules."""
    if set(responses) != set(answer_key):
        raise ValueError("responses and answer_key must contain the same question numbers")
    if decimal_places < 0:
        raise ValueError("decimal_places must be non-negative")

    configs = question_configs or {}
    unknown_questions = set(configs) - set(answer_key)
    if unknown_questions:
        raise ValueError(
            f"question_configs references unknown questions: {sorted(unknown_questions)}"
        )

    correct_count = incorrect_count = blank_count = dropped_count = bonus_count = 0
    total_score = 0.0
    total_max = 0.0
    details: list[QuestionScoreDetail] = []
    section_buckets: dict[str, list[QuestionScoreDetail]] = defaultdict(list)

    for question_number in sorted(answer_key):
        expected = tuple(answer_key[question_number])
        raw_actual = responses[question_number]
        actual = tuple(raw_actual) if raw_actual else ()
        cfg = configs.get(question_number, QuestionScoringConfig())
        rule = cfg.rule or default_rule

        if cfg.policy == QuestionPolicy.DROPPED:
            dropped_count += 1
            outcome = QuestionOutcome.DROPPED
            awarded = 0.0
            q_max = 0.0
        elif cfg.policy == QuestionPolicy.BONUS:
            bonus_count += 1
            outcome = QuestionOutcome.BONUS
            awarded = rule.correct
            q_max = max(rule.correct, 0.0)
        elif not actual:
            blank_count += 1
            outcome = QuestionOutcome.BLANK
            awarded = rule.blank
            q_max = max(rule.correct, 0.0)
        elif set(actual) == set(expected):
            correct_count += 1
            outcome = QuestionOutcome.CORRECT
            awarded = rule.correct
            q_max = max(rule.correct, 0.0)
        else:
            incorrect_count += 1
            outcome = QuestionOutcome.INCORRECT
            awarded = rule.incorrect
            q_max = max(rule.correct, 0.0)

        total_score += awarded
        total_max += q_max
        detail = QuestionScoreDetail(
            question_number=question_number,
            outcome=outcome,
            actual=actual,
            expected=expected,
            points_awarded=round(awarded, decimal_places),
            max_points=round(q_max, decimal_places),
            section=cfg.section,
        )
        details.append(detail)
        if cfg.section is not None:
            section_buckets[cfg.section].append(detail)

    section_scores: dict[str, ScoreSummary] = {}
    for section_name, items in section_buckets.items():
        section_scores[section_name] = ScoreSummary(
            correct_count=sum(1 for d in items if d.outcome == QuestionOutcome.CORRECT),
            incorrect_count=sum(1 for d in items if d.outcome == QuestionOutcome.INCORRECT),
            blank_count=sum(1 for d in items if d.outcome == QuestionOutcome.BLANK),
            score=round(sum(d.points_awarded for d in items), decimal_places),
            maximum_score=round(sum(d.max_points for d in items), decimal_places),
        )

    return DetailedScoreSummary(
        correct_count=correct_count,
        incorrect_count=incorrect_count,
        blank_count=blank_count,
        dropped_count=dropped_count,
        bonus_count=bonus_count,
        score=round(total_score, decimal_places),
        maximum_score=round(total_max, decimal_places),
        question_results=tuple(details),
        section_scores=section_scores,
    )
