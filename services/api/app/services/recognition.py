from pathlib import Path

import cv2
import numpy as np

from app.services.template import (
    BUBBLE_RADIUS_MM,
    MARKER_CENTERS,
    PAGE_H_MM,
    PAGE_W_MM,
    ROWS_PER_COLUMN,
    ROW_START_MM,
    ROW_STEP_MM,
    bubble_center_mm,
)

CANONICAL_WIDTH = 1654
CANONICAL_HEIGHT = 2339
DPI = 200
BLANK_THRESHOLD = 0.12
FILLED_THRESHOLD = 0.30


class RecognitionError(Exception):
    """Raised when a sheet cannot be safely aligned or measured."""


def _mm_to_pixel(x_mm: float, y_mm: float) -> tuple[int, int]:
    return (
        round(x_mm / PAGE_W_MM * CANONICAL_WIDTH),
        round(y_mm / PAGE_H_MM * CANONICAL_HEIGHT),
    )


def align_sheet(image_path: str | Path) -> np.ndarray:
    """Detect four ArUco registration markers and warp a scan into canonical A4 space."""
    if not hasattr(cv2, "aruco"):
        raise RecognitionError("OpenCV contrib ArUco support is unavailable")

    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise RecognitionError("The uploaded image could not be decoded")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    parameters = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(dictionary, parameters)
    corners, ids, _ = detector.detectMarkers(gray)

    if ids is None:
        raise RecognitionError("Registration markers were not detected; check crop and image quality")

    detected: dict[int, np.ndarray] = {}
    for marker_corners, marker_id in zip(corners, ids.flatten()):
        marker_id = int(marker_id)
        if marker_id in MARKER_CENTERS:
            detected[marker_id] = marker_corners.reshape(4, 2).mean(axis=0)

    required_ids = set(MARKER_CENTERS)
    if set(detected) != required_ids:
        missing = sorted(required_ids - set(detected))
        raise RecognitionError(f"Could not find all four registration markers (missing IDs: {missing})")

    source = np.array([detected[index] for index in range(4)], dtype=np.float32)
    destination = np.array(
        [_mm_to_pixel(*MARKER_CENTERS[index]) for index in range(4)],
        dtype=np.float32,
    )
    transform = cv2.getPerspectiveTransform(source, destination)
    aligned = cv2.warpPerspective(
        image,
        transform,
        (CANONICAL_WIDTH, CANONICAL_HEIGHT),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255),
    )
    return cv2.cvtColor(aligned, cv2.COLOR_BGR2GRAY)


def measure_bubble(gray: np.ndarray, x_mm: float, y_mm: float) -> float:
    """Measure dark ink in a bubble's interior relative to nearby paper brightness."""
    center_x, center_y = _mm_to_pixel(x_mm, y_mm)
    pixels_per_mm = CANONICAL_WIDTH / PAGE_W_MM
    outer_radius = round(3.0 * pixels_per_mm)
    inner_radius = round(1.15 * pixels_per_mm)

    y1, y2 = max(0, center_y - outer_radius), min(gray.shape[0], center_y + outer_radius + 1)
    x1, x2 = max(0, center_x - outer_radius), min(gray.shape[1], center_x + outer_radius + 1)
    crop = gray[y1:y2, x1:x2]
    yy, xx = np.ogrid[: crop.shape[0], : crop.shape[1]]
    local_x, local_y = center_x - x1, center_y - y1
    distance_squared = (xx - local_x) ** 2 + (yy - local_y) ** 2

    inner = distance_squared <= inner_radius**2
    annulus = (distance_squared >= round(2.15 * pixels_per_mm) ** 2) & (
        distance_squared <= outer_radius**2
    )
    if not np.any(inner) or not np.any(annulus):
        raise RecognitionError("Bubble region fell outside the aligned page")

    background_level = float(np.median(crop[annulus]))
    dark_cutoff = max(65.0, min(185.0, background_level - 38.0))
    return float(np.mean(crop[inner] < dark_cutoff))


def recognize_sheet(image_path: str | Path, total_questions: int, options: list[str]) -> dict:
    """Return per-question detections while preserving ambiguous cases for human review."""
    gray = align_sheet(image_path)
    questions: dict[str, dict] = {}

    for question_number in range(1, total_questions + 1):
        ratios: dict[str, float] = {}
        marked: list[str] = []
        uncertain = False

        for option_index, option in enumerate(options):
            x_mm, y_mm = bubble_center_mm(question_number, option_index)
            ratio = measure_bubble(gray, x_mm, y_mm)
            ratios[option] = round(ratio, 4)
            if ratio >= FILLED_THRESHOLD:
                marked.append(option)
            elif ratio > BLANK_THRESHOLD:
                uncertain = True

        if uncertain:
            state = "uncertain"
        elif len(marked) == 0:
            state = "blank"
        elif len(marked) == 1:
            state = "single"
        else:
            state = "multiple"

        questions[str(question_number)] = {
            "state": state,
            "selected_options": marked,
            "fill_ratios": ratios,
        }

    sheet_token, _, _ = cv2.QRCodeDetector().detectAndDecode(gray)
    return {
        "questions": questions,
        "sheet_token": sheet_token or None,
        "engine": "opencv-aruco-fill-ratio-v1",
        "canonical_size": [CANONICAL_WIDTH, CANONICAL_HEIGHT],
    }
