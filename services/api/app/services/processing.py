from pathlib import Path

from app.database import SessionLocal
from app.models import Exam, Scan
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
        scan.detections_json = detections
        scan.approved_answers_json = approved
        scan.error_message = ""

        if unresolved:
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
