from pathlib import Path

from app.database import SessionLocal
from app.models import Exam, Scan, SheetToken
from app.services.evaluation import build_approved_answers, evaluate_answers
from app.services.recognition import RecognitionError, recognize_sheet


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
        identity_error = ""
        detected_token = detections.get("sheet_token")

        if detected_token:
            token_record = db.get(SheetToken, detected_token)
            if token_record is not None and token_record.exam_id == exam.id:
                scan.student_id = token_record.student_id
                scan.student_name = token_record.student_name
            else:
                identity_error = "The candidate QR code is unknown or belongs to a different examination."
        elif not scan.student_id.strip():
            identity_error = "Candidate identity is missing. Enter a student ID or use a personalized QR sheet."

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
