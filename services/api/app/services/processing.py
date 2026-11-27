from pathlib import Path

from app.database import SessionLocal
from app.models import Exam, Scan, SheetToken
from app.services.evaluation import build_approved_answers, evaluate_answers
from app.services.recognition import RecognitionError, recognize_sheet


def resolve_scan_identity(scan, token_record, exam_id: str, detected_token: str | None) -> str:
    """Resolve a scan to a candidate, returning a review reason when identity is unsafe."""
    if detected_token:
        if token_record is None or token_record.exam_id != exam_id:
            return "The candidate QR code is unknown or belongs to a different examination."
        normalized_id = token_record.student_id.strip()
        if not normalized_id:
            return "The candidate QR code is linked to a blank student ID. Assign the candidate manually."
        scan.student_id = normalized_id
        scan.student_name = (token_record.student_name or "").strip()
        return ""

    scan.student_id = (scan.student_id or "").strip()
    scan.student_name = (scan.student_name or "").strip()
    if not scan.student_id:
        return "Candidate identity is missing. Enter a student ID or use a personalized QR sheet."
    return ""


def process_scan_record(scan_id: str) -> None:
    """Background task entry point. It owns and closes its database session."""
    db = SessionLocal()
    try:
        scan = db.get(Scan, scan_id)
        if scan is None:
            return
        exam = db.get(Exam, scan.exam_id)
        if exam is None:
            scan.status = "failed"
            scan.error_message = "The associated examination no longer exists"
            db.commit()
            return

        scan.status = "processing"
        db.commit()

        detections = recognize_sheet(scan.image_path, exam.total_questions, exam.options_json)
        approved, unresolved = build_approved_answers(detections["questions"])
        detected_token = detections.get("sheet_token")
        token_record = db.get(SheetToken, detected_token) if detected_token else None
        identity_error = resolve_scan_identity(scan, token_record, exam.id, detected_token)

        scan.detections_json = detections
        scan.approved_answers_json = approved
        scan.error_message = identity_error

        if unresolved or identity_error:
            scan.status = "needs_review"
        elif not exam.answer_key_json:
            scan.status = "awaiting_key"
        else:
            scan.result_json = evaluate_answers(
                approved,
                exam.answer_key_json,
                correct_marks=exam.correct_marks,
                incorrect_marks=exam.incorrect_marks,
                blank_marks=exam.blank_marks,
            )
            scan.status = "evaluated"

        db.commit()
    except RecognitionError as exc:
        db.rollback()
        scan = db.get(Scan, scan_id)
        if scan is not None:
            scan.status = "failed"
            scan.error_message = str(exc)
            db.commit()
    except Exception:
        db.rollback()
        scan = db.get(Scan, scan_id)
        if scan is not None:
            scan.status = "failed"
            scan.error_message = "Unexpected processing error. Check server logs using the scan ID."
            db.commit()
    finally:
        db.close()
