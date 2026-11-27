from dataclasses import dataclass
import math
from enum import StrEnum
from typing import Mapping, Sequence

from omr_engine.classification import (
    QuestionDecision,
    QuestionState,
    classify_bubble,
    classify_question,
)


class QualityIssue(StrEnum):
    LOW_CONTRAST = "low_contrast"
    EXCESSIVE_GLARE = "excessive_glare"
    CLIPPED_SHADOWS = "clipped_shadows"
    ALIGNMENT_MISSING = "alignment_missing"
    EXTREME_SKEW = "extreme_skew"


@dataclass(frozen=True, slots=True)
class QualityReport:
    """Page-level scan/capture quality metrics and deterministic pass/fail gate."""

    is_valid: bool
    contrast_span: int
    glare_ratio: float
    dark_clip_ratio: float
    skew_degrees: float
    issues: tuple[QualityIssue, ...]
    sample_stride: int
    samples_used: int


@dataclass(frozen=True, slots=True)
class SheetRecognitionResult:
    """Full-sheet question classifications paired with quality and review routing."""

    engine_version: str
    quality: QualityReport
    questions: dict[int, QuestionDecision]
    review_question_numbers: tuple[int, ...]
    needs_review: bool


def assess_page_quality(
    image: Sequence[Sequence[int]],
    *,
    alignment_ok: bool = True,
    skew_degrees: float = 0.0,
    max_skew_degrees: float = 10.0,
    min_contrast_span: int = 60,
    max_glare_ratio: float = 0.85,
    glare_threshold: int = 250,
    max_dark_clip_ratio: float = 0.75,
    dark_clip_threshold: int = 15,
    max_sample_pixels: int = 100_000,
) -> QualityReport:
    """Evaluate page quality using a deterministic, bounded grid sample.

    Sampling the page at a regular stride avoids materializing and sorting millions
    of Python pixel objects for full-resolution phone-camera or scanner images.
    The same input and sample limit always produce the same report.
    """
    if len(image) == 0 or len(image[0]) == 0:
        raise ValueError("image must be non-empty")
    if max_sample_pixels < 1:
        raise ValueError("max_sample_pixels must be positive")

    height = len(image)
    width = len(image[0])
    stride = max(1, math.ceil(math.sqrt((width * height) / max_sample_pixels)))

    pixels: list[int] = []
    for y, row in enumerate(image):
        if len(row) != width:
            raise ValueError("image rows must all have equal width")
        if y % stride != 0:
            continue
        for x in range(0, width, stride):
            pixel = int(row[x])
            if not 0 <= pixel <= 255:
                raise ValueError(f"pixel intensity {pixel} out of range [0, 255]")
            pixels.append(pixel)

    if not pixels:
        raise ValueError("image sample is empty")

    pixels.sort()
    n = len(pixels)
    p5 = pixels[min(n - 1, int(0.05 * (n - 1)))]
    p95 = pixels[min(n - 1, int(0.95 * (n - 1)))]
    contrast_span = p95 - p5

    glare_count = sum(1 for p in pixels if p >= glare_threshold)
    dark_clip_count = sum(1 for p in pixels if p <= dark_clip_threshold)
    glare_ratio = glare_count / n
    dark_clip_ratio = dark_clip_count / n

    issues: list[QualityIssue] = []
    if not alignment_ok:
        issues.append(QualityIssue.ALIGNMENT_MISSING)
    if abs(skew_degrees) > max_skew_degrees:
        issues.append(QualityIssue.EXTREME_SKEW)
    if contrast_span < min_contrast_span:
        issues.append(QualityIssue.LOW_CONTRAST)
    if glare_ratio > max_glare_ratio:
        issues.append(QualityIssue.EXCESSIVE_GLARE)
    if dark_clip_ratio > max_dark_clip_ratio:
        issues.append(QualityIssue.CLIPPED_SHADOWS)

    return QualityReport(
        is_valid=len(issues) == 0,
        contrast_span=contrast_span,
        glare_ratio=glare_ratio,
        dark_clip_ratio=dark_clip_ratio,
        skew_degrees=skew_degrees,
        issues=tuple(issues),
        sample_stride=stride,
        samples_used=n,
    )


def classify_sheet_questions(
    question_measurements: Mapping[int, Sequence[tuple[str, float]]],
    quality: QualityReport,
    *,
    engine_version: str = "0.1.0",
    blank_threshold: float = 0.25,
    filled_threshold: float = 0.55,
    route_multiple_to_review: bool = True,
) -> SheetRecognitionResult:
    """Classify every question on a sheet and route uncertain/invalid pages to review."""
    if not question_measurements:
        raise ValueError("question_measurements must not be empty")

    questions: dict[int, QuestionDecision] = {}
    review_numbers: list[int] = []

    for q_num in sorted(question_measurements):
        measurements = question_measurements[q_num]
        if not quality.is_valid:
            options = [option for option, _ in measurements]
            if len(options) != len(set(options)):
                raise ValueError("option identifiers must be unique")
            bubbles = tuple(
                classify_bubble(
                    option,
                    ratio,
                    blank_threshold=blank_threshold,
                    filled_threshold=filled_threshold,
                )
                for option, ratio in measurements
            )
            decision = QuestionDecision(
                state=QuestionState.UNCERTAIN,
                selected_options=(),
                bubbles=bubbles,
            )
            questions[q_num] = decision
            review_numbers.append(q_num)
            continue

        decision = classify_question(
            measurements,
            blank_threshold=blank_threshold,
            filled_threshold=filled_threshold,
        )
        questions[q_num] = decision
        if decision.state == QuestionState.UNCERTAIN or (
            route_multiple_to_review and decision.state == QuestionState.MULTIPLE
        ):
            review_numbers.append(q_num)

    return SheetRecognitionResult(
        engine_version=engine_version,
        quality=quality,
        questions=questions,
        review_question_numbers=tuple(review_numbers),
        needs_review=len(review_numbers) > 0 or not quality.is_valid,
    )
