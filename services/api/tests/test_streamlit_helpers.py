import importlib.util
from pathlib import Path
from types import SimpleNamespace

from app.models import Scan

_STREAMLIT_FILE = Path(__file__).resolve().parents[3] / "streamlit_app.py"
_SPEC = importlib.util.spec_from_file_location("streamlit_app", _STREAMLIT_FILE)
assert _SPEC and _SPEC.loader
streamlit_app = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(streamlit_app)


def test_parse_answer_key_lines_valid_and_invalid() -> None:
    parsed, err = streamlit_app.parse_answer_key_lines(
        "1:A\n2:b\n3:C\n",
        total_questions=3,
        allowed_options=["A", "B", "C", "D"],
    )
    assert err is None
    assert parsed == {"1": "A", "2": "B", "3": "C"}

    _, missing_err = streamlit_app.parse_answer_key_lines(
        "1:A",
        total_questions=3,
        allowed_options=["A", "B", "C", "D"],
    )
    assert missing_err and "missing questions" in missing_err

    _, option_err = streamlit_app.parse_answer_key_lines(
        "1:D\n2:A",
        total_questions=2,
        allowed_options=["A", "B", "C"],
    )
    assert option_err and "not in" in option_err


def test_build_results_csv_filters_to_evaluated_scans() -> None:
    evaluated = Scan(
        id="s1",
        exam_id="e1",
        student_id="BIT-001",
        student_name="Ada",
        original_filename="sheet.pdf",
        source_path="sheet.pdf",
        image_path="sheet.png",
        page_number=1,
        total_pages=1,
        status="evaluated",
        result_json={
            "correct": 3,
            "incorrect": 1,
            "unattempted": 0,
            "score": 11,
            "maximum_score": 16,
            "percentage": 68.75,
        },
    )
    pending = SimpleNamespace(status="needs_review", result_json=None)
    csv_text = streamlit_app.build_results_csv([evaluated, pending])  # type: ignore[list-item]
    lines = csv_text.strip().splitlines()
    assert len(lines) == 2
    assert "BIT-001" in lines[1]
    assert "68.75" in lines[1]
