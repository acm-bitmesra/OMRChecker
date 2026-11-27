from pathlib import Path

from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


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
