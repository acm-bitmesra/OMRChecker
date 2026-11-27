from dataclasses import dataclass
from enum import StrEnum
from typing import Sequence


class MarkState(StrEnum):
    BLANK = "blank"
    FILLED = "filled"
    UNCERTAIN = "uncertain"


class QuestionState(StrEnum):
    BLANK = "blank"
    SINGLE = "single"
    MULTIPLE = "multiple"
    UNCERTAIN = "uncertain"


@dataclass(frozen=True, slots=True)
class BubbleDecision:
    option: str
    fill_ratio: float
    state: MarkState


@dataclass(frozen=True, slots=True)
class QuestionDecision:
    state: QuestionState
    selected_options: tuple[str, ...]
    bubbles: tuple[BubbleDecision, ...]


def classify_bubble(
    option: str,
    fill_ratio: float,
    *,
    blank_threshold: float = 0.25,
    filled_threshold: float = 0.55,
) -> BubbleDecision:
    """Classify one measured bubble using explicit calibrated thresholds.

    Defaults are placeholders, not universal values. Calibrate by template,
    print profile, and capture path using labeled samples.
    """
    if not 0.0 <= fill_ratio <= 1.0:
        raise ValueError("fill_ratio must be between 0.0 and 1.0")
    if not 0.0 <= blank_threshold < filled_threshold <= 1.0:
        raise ValueError("thresholds must satisfy 0 <= blank < filled <= 1")

    if fill_ratio <= blank_threshold:
        state = MarkState.BLANK
    elif fill_ratio >= filled_threshold:
        state = MarkState.FILLED
    else:
        state = MarkState.UNCERTAIN

    return BubbleDecision(option=option, fill_ratio=fill_ratio, state=state)


def classify_question(
    measurements: Sequence[tuple[str, float]],
    *,
    blank_threshold: float = 0.25,
    filled_threshold: float = 0.55,
) -> QuestionDecision:
    """Convert option measurements into a question-level recognition state."""
    if not measurements:
        raise ValueError("at least one option measurement is required")

    options = [option for option, _ in measurements]
    if len(options) != len(set(options)):
        raise ValueError("option identifiers must be unique")

    bubbles = tuple(
        classify_bubble(
            option, ratio,
            blank_threshold=blank_threshold,
            filled_threshold=filled_threshold,
        )
        for option, ratio in measurements
    )

    selected = tuple(
        bubble.option for bubble in bubbles if bubble.state == MarkState.FILLED
    )
    if any(bubble.state == MarkState.UNCERTAIN for bubble in bubbles):
        state = QuestionState.UNCERTAIN
    elif len(selected) == 0:
        state = QuestionState.BLANK
    elif len(selected) == 1:
        state = QuestionState.SINGLE
    else:
        state = QuestionState.MULTIPLE

    return QuestionDecision(state=state, selected_options=selected, bubbles=bubbles)
