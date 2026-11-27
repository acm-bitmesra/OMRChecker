from app.services.evaluation import build_approved_answers, evaluate_answers


def test_build_approved_answers_preserves_ambiguous_questions_for_review() -> None:
    approved, unresolved = build_approved_answers({
        "1": {"state": "single", "selected_options": ["B"]},
        "2": {"state": "blank", "selected_options": []},
        "3": {"state": "multiple", "selected_options": ["A", "C"]},
        "4": {"state": "uncertain", "selected_options": []},
    })
    assert approved == {"1": "B", "2": None}
    assert unresolved == ["3", "4"]


def test_evaluation_uses_correct_negative_and_blank_marks() -> None:
    result = evaluate_answers(
        {"1": "A", "2": "C", "3": None},
        {"1": "A", "2": "B", "3": "D"},
        correct_marks=4,
        incorrect_marks=-1,
        blank_marks=0,
    )
    assert result == {
        "correct": 1,
        "incorrect": 1,
        "unattempted": 1,
        "score": 3,
        "maximum_score": 12,
        "percentage": 25.0,
    }
