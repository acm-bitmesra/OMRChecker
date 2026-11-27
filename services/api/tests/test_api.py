from pathlib import Path

from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import SheetToken


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
