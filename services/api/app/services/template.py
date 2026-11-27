from io import BytesIO

import cv2
import numpy as np
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

PAGE_W, PAGE_H = A4
PAGE_W_MM, PAGE_H_MM = 210.0, 297.0
MARKER_SIZE_MM = 10.0
MARKER_CENTERS = {
    0: (12.0, 12.0),       # top-left
    1: (198.0, 12.0),      # top-right
    2: (198.0, 285.0),     # bottom-right
    3: (12.0, 285.0),      # bottom-left
}
ROWS_PER_COLUMN = 50
ROW_START_MM = 55.0
ROW_STEP_MM = 4.45
COLUMN_STARTS_MM = (18.0, 112.0)
OPTION_OFFSET_MM = 18.0
OPTION_STEP_MM = 7.2
BUBBLE_RADIUS_MM = 1.75


def bubble_center_mm(question_number: int, option_index: int) -> tuple[float, float]:
    """Return a question/option center in the canonical A4 top-left coordinate plane."""
    if question_number < 1 or question_number > 100:
        raise ValueError("question_number must be between 1 and 100")
    if option_index < 0 or option_index > 3:
        raise ValueError("option_index must be between 0 and 3")
    column = (question_number - 1) // ROWS_PER_COLUMN
    row = (question_number - 1) % ROWS_PER_COLUMN
    x = COLUMN_STARTS_MM[column] + OPTION_OFFSET_MM + option_index * OPTION_STEP_MM
    y = ROW_START_MM + row * ROW_STEP_MM
    return x, y


def _marker_image(marker_id: int) -> BytesIO:
    if not hasattr(cv2, "aruco"):
        raise RuntimeError("OpenCV contrib ArUco support is required to generate OMR templates")
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    image = cv2.aruco.generateImageMarker(dictionary, marker_id, 240)
    success, encoded = cv2.imencode(".png", image)
    if not success:
        raise RuntimeError("Could not generate registration marker")
    return BytesIO(encoded.tobytes())


def _draw_top_text(pdf: canvas.Canvas, value: str, x_mm: float, y_mm: float) -> None:
    pdf.drawString(x_mm * mm, PAGE_H - y_mm * mm, value)


def generate_omr_pdf(exam) -> bytes:
    """Generate one A4 page with up to 100 questions and four-corner ArUco markers."""
    if exam.total_questions > 100:
        raise ValueError("A single OMR sheet supports up to 100 questions")
    if len(exam.options_json) > 4:
        raise ValueError("A single OMR sheet supports up to four options")

    output = BytesIO()
    pdf = canvas.Canvas(output, pagesize=A4, pageCompression=1)
    pdf.setTitle(f"OMR Checker - {exam.name}")
    pdf.setAuthor("OMR Checker")

    pdf.setFont("Helvetica-Bold", 16)
    _draw_top_text(pdf, "OMR CHECKER  |  ANSWER SHEET", 18, 24)
    pdf.setFont("Helvetica", 8)
    _draw_top_text(pdf, f"Exam: {exam.name[:70]}", 18, 31)
    _draw_top_text(
        pdf,
        "Fill one bubble completely using a dark pen. Do not tick, cross, or mark outside the circles.",
        18,
        37,
    )
    _draw_top_text(pdf, "Student name:", 18, 45)
    pdf.line(39 * mm, PAGE_H - 45.8 * mm, 91 * mm, PAGE_H - 45.8 * mm)
    _draw_top_text(pdf, "Roll / student ID:", 112, 45)
    pdf.line(139 * mm, PAGE_H - 45.8 * mm, 190 * mm, PAGE_H - 45.8 * mm)

    pdf.setFont("Helvetica-Bold", 7)
    _draw_top_text(pdf, "QUESTION", 18, 51)
    _draw_top_text(pdf, "OPTIONS", 37, 51)
    _draw_top_text(pdf, "QUESTION", 112, 51)
    _draw_top_text(pdf, "OPTIONS", 131, 51)

    for marker_id, (center_x, center_y) in MARKER_CENTERS.items():
        marker = ImageReader(_marker_image(marker_id))
        pdf.drawImage(
            marker,
            (center_x - MARKER_SIZE_MM / 2) * mm,
            PAGE_H - (center_y + MARKER_SIZE_MM / 2) * mm,
            width=MARKER_SIZE_MM * mm,
            height=MARKER_SIZE_MM * mm,
            mask="auto",
        )

    option_labels = exam.options_json
    pdf.setLineWidth(0.6)
    pdf.setFont("Helvetica", 6.8)
    for question_number in range(1, exam.total_questions + 1):
        column = (question_number - 1) // ROWS_PER_COLUMN
        row = (question_number - 1) % ROWS_PER_COLUMN
        base_x = COLUMN_STARTS_MM[column]
        y = ROW_START_MM + row * ROW_STEP_MM
        _draw_top_text(pdf, str(question_number), base_x, y + 1.1)
        for option_index, option in enumerate(option_labels):
            x, bubble_y = bubble_center_mm(question_number, option_index)
            pdf.circle(x * mm, PAGE_H - bubble_y * mm, BUBBLE_RADIUS_MM * mm, stroke=1, fill=0)
            _draw_top_text(pdf, option, x - 1.0, bubble_y + 0.8)

    pdf.setFont("Helvetica", 7)
    _draw_top_text(pdf, f"Template: OMR-A4-100  |  Exam ID: {exam.id}", 18, 282)
    _draw_top_text(pdf, "Keep all four black registration markers visible. Scan the complete page.", 18, 289)
    pdf.showPage()
    pdf.save()
    return output.getvalue()
