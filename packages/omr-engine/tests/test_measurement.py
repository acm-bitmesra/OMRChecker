import numpy as np
import pytest

from omr_engine.classification import QuestionState, classify_question
from omr_engine.measurement import (
    NormalizedBox,
    PixelBox,
    apply_inset,
    measure_bubble_fill,
    measure_question_bubbles,
    normalized_to_pixel_box,
)


def _make_blank_sheet(width: int = 100, height: int = 100, fill: int = 255) -> list[list[int]]:
    return [[fill for _ in range(width)] for _ in range(height)]


def _draw_box_outline(
    sheet: list[list[int]],
    box: PixelBox,
    border_value: int = 0,
) -> None:
    for x in range(box.left, box.right):
        sheet[box.top][x] = border_value
        sheet[box.bottom - 1][x] = border_value
    for y in range(box.top, box.bottom):
        sheet[y][box.left] = border_value
        sheet[y][box.right - 1] = border_value


def _fill_box_interior(
    sheet: list[list[int]],
    box: PixelBox,
    value: int = 20,
    margin: int = 1,
) -> None:
    for y in range(box.top + margin, box.bottom - margin):
        for x in range(box.left + margin, box.right - margin):
            sheet[y][x] = value


def test_normalized_to_pixel_box_and_inset() -> None:
    region = NormalizedBox(x=0.1, y=0.2, width=0.2, height=0.2)
    outer = normalized_to_pixel_box(region, image_width=100, image_height=100)
    assert outer == PixelBox(left=10, top=20, right=30, bottom=40)

    inner = apply_inset(outer, inset_ratio=0.15)
    assert inner == PixelBox(left=13, top=23, right=27, bottom=37)
    assert inner.area == 14 * 14


def test_inset_excludes_printed_bubble_outline() -> None:
    sheet = _make_blank_sheet(100, 100, fill=255)
    region = NormalizedBox(x=0.1, y=0.1, width=0.1, height=0.1)  # 10x10 at (10..20)
    outer = normalized_to_pixel_box(region, 100, 100)
    _draw_box_outline(sheet, outer, border_value=0)

    # Without inset, the printed 1px border inflates fill_ratio above 0.35 (uncertain!).
    no_inset = measure_bubble_fill(sheet, region, option="A", inset_ratio=0.0)
    assert no_inset.fill_ratio == pytest.approx(36 / 100)

    # With 15% inset, the printed border is excluded and the blank interior reads 0.0.
    with_inset = measure_bubble_fill(sheet, region, option="A", inset_ratio=0.15)
    assert with_inset.fill_ratio == 0.0
    assert with_inset.mean_intensity == 255.0


def test_measure_question_bubbles_integrates_with_classify_question() -> None:
    sheet = _make_blank_sheet(100, 100, fill=250)
    regions = {
        "A": NormalizedBox(x=0.1, y=0.2, width=0.1, height=0.1),
        "B": NormalizedBox(x=0.3, y=0.2, width=0.1, height=0.1),
        "C": NormalizedBox(x=0.5, y=0.2, width=0.1, height=0.1),
        "D": NormalizedBox(x=0.7, y=0.2, width=0.1, height=0.1),
    }
    for box_region in regions.values():
        _draw_box_outline(sheet, normalized_to_pixel_box(box_region, 100, 100), border_value=0)
    _fill_box_interior(sheet, normalized_to_pixel_box(regions["C"], 100, 100), value=15, margin=1)

    measurements = measure_question_bubbles(sheet, regions)
    decision = classify_question(measurements)
    assert decision.state == QuestionState.SINGLE
    assert decision.selected_options == ("C",)


def test_invalid_inputs_raise_value_errors() -> None:
    with pytest.raises(ValueError):
        NormalizedBox(x=0.9, y=0.1, width=0.2, height=0.1)
    with pytest.raises(ValueError):
        apply_inset(PixelBox(0, 0, 10, 10), inset_ratio=0.5)
    with pytest.raises(ValueError):
        measure_bubble_fill([[255, 255]], NormalizedBox(0.0, 0.0, 1.0, 1.0), dark_threshold=300)



def test_measurement_accepts_numpy_grayscale_arrays() -> None:
    image = np.full((100, 100), 255, dtype=np.uint8)
    region = NormalizedBox(x=0.1, y=0.1, width=0.1, height=0.1)
    measured = measure_bubble_fill(image, region, inset_ratio=0.15)
    assert measured.fill_ratio == 0.0
    assert measured.mean_intensity == 255.0

    with pytest.raises(ValueError, match="at least one row"):
        measure_bubble_fill(np.empty((0, 100), dtype=np.uint8), region)


def test_normalized_box_rejects_non_finite_coordinates() -> None:
    for value in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValueError, match="finite"):
            NormalizedBox(x=value, y=0.1, width=0.2, height=0.2)
