def evaluate_answers(
    approved_answers: dict[str, str | None],
    answer_key: dict[str, str],
    *,
    correct_marks: float,
    incorrect_marks: float,
    blank_marks: float,
) -> dict:
    """Compute a deterministic score from examiner-approved answers only."""
    if set(approved_answers) != set(answer_key):
        raise ValueError("Every question must have an approved response before evaluation")

    correct = incorrect = blank = 0
    score = 0.0

    for question_number, expected in answer_key.items():
        actual = approved_answers[question_number]
        if actual is None:
            blank += 1
            score += blank_marks
        elif actual == expected:
            correct += 1
            score += correct_marks
        else:
            incorrect += 1
            score += incorrect_marks

    maximum = len(answer_key) * correct_marks
    percentage = (score / maximum * 100.0) if maximum > 0 else 0.0
    return {
        "correct": correct,
        "incorrect": incorrect,
        "unattempted": blank,
        "score": round(score, 4),
        "maximum_score": round(maximum, 4),
        "percentage": round(percentage, 2),
    }


def build_approved_answers(detections: dict[str, dict]) -> tuple[dict[str, str | None], list[str]]:
    approved: dict[str, str | None] = {}
    unresolved: list[str] = []
    for question_number, detection in detections.items():
        state = detection["state"]
        if state == "single":
            approved[question_number] = detection["selected_options"][0]
        elif state == "blank":
            approved[question_number] = None
        else:
            unresolved.append(question_number)
    return approved, unresolved
