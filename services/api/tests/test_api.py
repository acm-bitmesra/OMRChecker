from pathlib import Path

import cv2
import fitz
from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
import pytest
from pydantic import ValidationError

from app.main import app, finalize_scan_if_ready
from app.models import Exam, Scan, SheetToken
from app.schemas import ReviewInput, StudentSheetCreate
from app.services.processing import resolve_scan_identity


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



def test_candidate_sheet_and_review_ids_reject_whitespace_only_values() -> None:
    with pytest.raises(ValidationError):
        StudentSheetCreate(student_id="   ")
    with pytest.raises(ValidationError):
        ReviewInput(answers={}, student_id="   ")


def test_worker_rejects_token_record_with_blank_candidate_id() -> None:
    scan = type("ScanStub", (), {"student_id": "", "student_name": ""})()
    token_record = type(
        "TokenStub",
        (),
        {"exam_id": "exam-1", "student_id": "   ", "student_name": "Nobody"},
    )()
    reason = resolve_scan_identity(scan, token_record, "exam-1", "opaque-token")
    assert "blank student ID" in reason
    assert scan.student_id == ""


def test_worker_rejects_candidate_token_from_another_exam() -> None:
    scan = type("ScanStub", (), {"student_id": "", "student_name": ""})()
    token_record = type(
        "TokenStub",
        (),
        {"exam_id": "exam-other", "student_id": "BIT-001", "student_name": "Candidate"},
    )()
    reason = resolve_scan_identity(scan, token_record, "exam-1", "opaque-token")
    assert "different examination" in reason
    assert scan.student_id == ""


def test_worker_normalizes_valid_candidate_identity() -> None:
    scan = type("ScanStub", (), {"student_id": "  MANUAL-01  ", "student_name": "  Name  "})()
    reason = resolve_scan_identity(scan, None, "exam-1", None)
    assert reason == ""
    assert scan.student_id == "MANUAL-01"
    assert scan.student_name == "Name"


def test_scan_image_reprocess_analytics_and_delete(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OMR_STORAGE_DIR", str(tmp_path))
    Base.metadata.create_all(bind=engine)
    client = TestClient(app)

    exam = client.post(
        "/api/v1/exams",
        json={
            "name": "Analytics & Preview Exam",
            "total_questions": 2,
            "options": ["A", "B", "C", "D"],
            "correct_marks": 4,
            "incorrect_marks": -1,
            "blank_marks": 0,
        },
    ).json()
    client.put(
        f"/api/v1/exams/{exam['id']}/answer-key",
        json={"answers": {"1": "A", "2": "B"}},
    )

    uploads_dir = tmp_path / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    img_path = uploads_dir / "sample-page.png"
    img_path.write_bytes(b"\x89PNG\r\n\x1a\nfake-png-bytes")

    with SessionLocal() as session:
        scan = Scan(
            exam_id=exam["id"],
            student_id="STU-101",
            student_name="Alice",
            original_filename="sample.png",
            source_path=str(img_path),
            image_path=str(img_path),
            page_number=1,
            total_pages=1,
            status="evaluated",
            approved_answers_json={"1": "A", "2": "C"},
            result_json={"correct": 1, "incorrect": 1, "unattempted": 0, "score": 3.0, "maximum_score": 8.0, "percentage": 37.5},
        )
        outside_scan = Scan(
            exam_id=exam["id"],
            student_id="STU-999",
            student_name="Outside",
            original_filename="outside.png",
            source_path="/etc/passwd",
            image_path="/etc/passwd",
            page_number=1,
            total_pages=1,
            status="failed",
        )
        session.add_all([scan, outside_scan])
        session.commit()
        scan_id = scan.id
        outside_id = outside_scan.id

    img_res = client.get(f"/api/v1/scans/{scan_id}/image")
    assert img_res.status_code == 200
    assert img_res.headers["content-type"] == "image/png"

    traversal_res = client.get(f"/api/v1/scans/{outside_id}/image")
    assert traversal_res.status_code == 403

    analytics_res = client.get(f"/api/v1/exams/{exam['id']}/analytics")
    assert analytics_res.status_code == 200
    analytics = analytics_res.json()
    assert analytics["evaluated"] == 1
    assert analytics["average_score"] == 3.0
    assert analytics["question_stats"][0]["accuracy"] == 1.0
    assert analytics["question_stats"][1]["accuracy"] == 0.0

    monkeypatch.setattr("app.main.process_scan_record", lambda _sid: None)
    reprocess_res = client.post(f"/api/v1/scans/{scan_id}/reprocess")
    assert reprocess_res.status_code == 202
    assert reprocess_res.json()["status"] == "queued"

    del_scan = client.delete(f"/api/v1/scans/{scan_id}")
    assert del_scan.status_code == 200
    assert not img_path.exists()

    del_exam = client.delete(f"/api/v1/exams/{exam['id']}")
    assert del_exam.status_code == 200
    assert client.get(f"/api/v1/exams/{exam['id']}").status_code == 404
