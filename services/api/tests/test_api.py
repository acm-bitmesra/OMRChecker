from pathlib import Path

import cv2
import fitz
from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.main import app, finalize_scan_if_ready
from app.models import Exam, Scan, SheetToken


def test_exam_create_and_answer_key(tmp_path: Path, monkeypatch) -> None:
    # Use the configured local database for this smoke test; IDs are unique per test.
    Base.metadata.create_all(bind=engine)
    client = TestClient(app)
    response = client.post(
        "/api/v1/exams",
        json={
            "name": "API smoke exam",
            "total_questions": 2,
            "options": ["A", "B", "C", "D"],
            "correct_marks": 4,
            "incorrect_marks": -1,
            "blank_marks": 0,
        },
    )
    assert response.status_code == 201
    exam = response.json()
    key_response = client.put(
        f"/api/v1/exams/{exam['id']}/answer-key",
        json={"answers": {"1": "A", "2": "D"}},
    )
    assert key_response.status_code == 200
    assert key_response.json()["exam"]["has_answer_key"] is True

    sheet_response = client.post(
        f"/api/v1/exams/{exam['id']}/student-sheets",
        json={"student_id": "BIT-2026-001", "student_name": "Test Candidate"},
    )
    assert sheet_response.status_code == 200
    assert sheet_response.headers["content-type"] == "application/pdf"
    assert sheet_response.content.startswith(b"%PDF")

    with SessionLocal() as session:
        token_record = session.query(SheetToken).filter_by(exam_id=exam["id"]).one()
        assert token_record.student_id == "BIT-2026-001"
        assert token_record.student_name == "Test Candidate"
        expected_token = token_record.token

        scan = Scan(
            exam_id=exam["id"],
            student_id="",
            student_name="",
            original_filename="candidate.pdf",
            source_path="candidate.pdf",
            image_path="candidate.png",
            page_number=1,
            total_pages=1,
            status="needs_review",
            approved_answers_json={"1": "A", "2": "D"},
            error_message="The candidate QR code is unknown or belongs to a different examination.",
        )
        session.add(scan)
        session.flush()
        stored_exam = session.get(Exam, exam["id"])
        finalize_scan_if_ready(scan, stored_exam)
        assert scan.status == "needs_review"
        assert scan.result_json is None

        scan.student_id = "BIT-2026-001"
        finalize_scan_if_ready(scan, stored_exam)
        assert scan.status == "evaluated"
        assert scan.error_message == ""
        assert scan.result_json["correct"] == 2

    pdf = fitz.open(stream=sheet_response.content, filetype="pdf")
    image_path = tmp_path / "candidate-sheet.png"
    pdf[0].get_pixmap(dpi=200, alpha=False).save(image_path)
    image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    decoded, points, _ = cv2.QRCodeDetector().detectAndDecode(image)
    assert points is not None
    assert decoded == expected_token
