from pathlib import Path
from types import SimpleNamespace

import cv2
import fitz
import numpy as np
import pytest

from app.services.evaluation import build_approved_answers, evaluate_answers
from app.services.recognition import CANONICAL_HEIGHT, CANONICAL_WIDTH, RecognitionError, recognize_sheet
from app.services.template import BUBBLE_RADIUS_MM, PAGE_H_MM, PAGE_W_MM, bubble_center_mm, generate_omr_pdf


def _paint_bubble(image: np.ndarray, question_number: int, option_index: int, *, fill_ratio: float = 1.0, intensity: int = 18) -> None:
    x_mm, y_mm = bubble_center_mm(question_number, option_index)
    cx = round(x_mm / PAGE_W_MM * CANONICAL_WIDTH)
    cy = round(y_mm / PAGE_H_MM * CANONICAL_HEIGHT)
    radius_px = round(BUBBLE_RADIUS_MM * 0.72 * (CANONICAL_WIDTH / PAGE_W_MM) * fill_ratio)
    if radius_px > 0:
        cv2.circle(image, (cx, cy), radius_px, (intensity, intensity, intensity), thickness=-1)


def _render_exam_sheet(total_questions: int = 8, sheet_token: str | None = None) -> np.ndarray:
    exam = SimpleNamespace(
        id="filled-e2e-exam",
        name="Synthetic Filled E2E Test",
        total_questions=total_questions,
        options_json=["A", "B", "C", "D"],
    )
    pdf = fitz.open(stream=generate_omr_pdf(exam, sheet_token=sheet_token), filetype="pdf")
    pixmap = pdf[0].get_pixmap(dpi=200, alpha=False)
    buffer = np.frombuffer(pixmap.tobytes("png"), dtype=np.uint8)
    image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    assert image is not None
    return cv2.resize(image, (CANONICAL_WIDTH, CANONICAL_HEIGHT))


def test_filled_single_blank_multiple_and_qr_token_roundtrip(tmp_path: Path) -> None:
    token = "candidate-token-2026-0042"
    image = _render_exam_sheet(total_questions=6, sheet_token=token)

    _paint_bubble(image, 1, 0)  # A
    _paint_bubble(image, 2, 2)  # C
    # Q3 left blank
    _paint_bubble(image, 4, 3)  # D
    _paint_bubble(image, 5, 1)  # B
    # Q6 multiple marks (A and D)
    _paint_bubble(image, 6, 0)
    _paint_bubble(image, 6, 3)

    sheet_path = tmp_path / "filled-sheet.png"
    cv2.imwrite(str(sheet_path), image)

    result = recognize_sheet(sheet_path, total_questions=6, options=["A", "B", "C", "D"])
    assert result["sheet_token"] == token

    questions = result["questions"]
    assert questions["1"]["state"] == "single" and questions["1"]["selected_options"] == ["A"]
    assert questions["2"]["state"] == "single" and questions["2"]["selected_options"] == ["C"]
    assert questions["3"]["state"] == "blank"
    assert questions["4"]["state"] == "single" and questions["4"]["selected_options"] == ["D"]
    assert questions["5"]["state"] == "single" and questions["5"]["selected_options"] == ["B"]
    assert questions["6"]["state"] == "multiple" and set(questions["6"]["selected_options"]) == {"A", "D"}

    approved, unresolved = build_approved_answers(questions)
    assert unresolved == ["6"]
    approved["6"] = "D"  # examiner resolves multiple mark

    score = evaluate_answers(
        approved,
        {"1": "A", "2": "C", "3": "A", "4": "D", "5": "A", "6": "D"},
        correct_marks=4.0,
        incorrect_marks=-1.0,
        blank_marks=0.0,
    )
    # 4 correct (Q1, Q2, Q4, Q6) = 16, 1 blank (Q3) = 0, 1 incorrect (Q5) = -1 => 15
    assert score["correct"] == 4
    assert score["incorrect"] == 1
    assert score["unattempted"] == 1
    assert score["score"] == 15.0


def test_rotated_and_padded_camera_scan_aligns_via_aruco(tmp_path: Path) -> None:
    image = _render_exam_sheet(total_questions=4)
    _paint_bubble(image, 1, 1)  # B
    _paint_bubble(image, 2, 3)  # D

    padded = cv2.copyMakeBorder(image, 140, 140, 140, 140, cv2.BORDER_CONSTANT, value=(210, 210, 210))
    center = (padded.shape[1] / 2, padded.shape[0] / 2)
    matrix = cv2.getRotationMatrix2D(center, angle=4.5, scale=0.92)
    rotated = cv2.warpAffine(padded, matrix, (padded.shape[1], padded.shape[0]), borderValue=(180, 180, 180))

    scan_path = tmp_path / "rotated-camera-scan.png"
    cv2.imwrite(str(scan_path), rotated)

    result = recognize_sheet(scan_path, total_questions=4, options=["A", "B", "C", "D"])
    assert result["questions"]["1"]["selected_options"] == ["B"]
    assert result["questions"]["2"]["selected_options"] == ["D"]
    assert result["questions"]["3"]["state"] == "blank"
    assert result["questions"]["4"]["state"] == "blank"


def test_sheet_without_registration_markers_raises_recognition_error(tmp_path: Path) -> None:
    blank_canvas = np.full((800, 600, 3), 245, dtype=np.uint8)
    bad_path = tmp_path / "missing-markers.png"
    cv2.imwrite(str(bad_path), blank_canvas)

    with pytest.raises(RecognitionError, match="(?i)registration markers"):
        recognize_sheet(bad_path, total_questions=4, options=["A", "B", "C", "D"])
