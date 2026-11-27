import csv
import os
import uuid
from pathlib import Path
from typing import Generator
from io import StringIO

import fitz
import numpy as np
import cv2
from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine, ensure_local_storage
from app.models import Exam, Scan
from app.schemas import AnswerKeyInput, ExamCreate, ReviewInput
from app.services.evaluation import evaluate_answers
from app.services.processing import process_scan_record
from app.services.template import generate_omr_pdf

API_PREFIX = "/api/v1"
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_PDF_PAGES = 50
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf"}

app = FastAPI(
    title="OMR Checker API",
    version="0.2.0",
    description="Create exams, generate OMR sheets, scan responses, review detections, and evaluate results.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv(
        "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    ).split(","),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    ensure_local_storage()
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def exam_payload(exam: Exam) -> dict:
    return {
        "id": exam.id,
        "name": exam.name,
        "description": exam.description,
        "total_questions": exam.total_questions,
        "options": exam.options_json,
        "correct_marks": exam.correct_marks,
        "incorrect_marks": exam.incorrect_marks,
        "blank_marks": exam.blank_marks,
        "has_answer_key": bool(exam.answer_key_json),
        "created_at": exam.created_at.isoformat() if exam.created_at else None,
    }


def scan_payload(scan: Scan) -> dict:
    return {
        "id": scan.id,
        "exam_id": scan.exam_id,
        "student_id": scan.student_id,
        "student_name": scan.student_name,
        "original_filename": scan.original_filename,
        "page_number": scan.page_number,
        "total_pages": scan.total_pages,
        "status": scan.status,
        "detections": scan.detections_json,
        "approved_answers": scan.approved_answers_json,
        "result": scan.result_json,
        "error_message": scan.error_message,
        "created_at": scan.created_at.isoformat() if scan.created_at else None,
    }


def get_exam_or_404(db: Session, exam_id: str) -> Exam:
    exam = db.get(Exam, exam_id)
    if exam is None:
        raise HTTPException(status_code=404, detail="Examination not found")
    return exam


def validate_answer_key(exam: Exam, answers: dict[str, str]) -> dict[str, str]:
    expected_questions = {str(number) for number in range(1, exam.total_questions + 1)}
    if set(answers) != expected_questions:
        missing = sorted(expected_questions - set(answers), key=int)
        extra = sorted(set(answers) - expected_questions)
        raise HTTPException(
            status_code=422,
            detail={"message": "Answer key must define every question exactly once", "missing": missing, "extra": extra},
        )
    normalized = {key: value.strip().upper() for key, value in answers.items()}
    invalid = {
        question: answer
        for question, answer in normalized.items()
        if answer not in exam.options_json
    }
    if invalid:
        raise HTTPException(
            status_code=422,
            detail={"message": "Answer key contains an unknown option", "invalid": invalid},
        )
    return normalized


def finalize_scan_if_ready(scan: Scan, exam: Exam) -> None:
    approved = scan.approved_answers_json or {}
    if len(approved) != exam.total_questions or not exam.answer_key_json:
        scan.result_json = None
        scan.status = "awaiting_key" if len(approved) == exam.total_questions else "needs_review"
        return
    scan.result_json = evaluate_answers(
        approved,
        exam.answer_key_json,
        correct_marks=exam.correct_marks,
        incorrect_marks=exam.incorrect_marks,
        blank_marks=exam.blank_marks,
    )
    scan.status = "evaluated"


def validate_upload(file_bytes: bytes, filename: str) -> str:
    extension = Path(filename or "").suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Upload a PNG, JPG, or PDF file")
    if extension == ".pdf" and not file_bytes.startswith(b"%PDF"):
        raise HTTPException(status_code=415, detail="The file does not contain a valid PDF header")
    if extension == ".png" and not file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        raise HTTPException(status_code=415, detail="The file does not contain a valid PNG signature")
    if extension in {".jpg", ".jpeg"} and not file_bytes.startswith(b"\xff\xd8\xff"):
        raise HTTPException(status_code=415, detail="The file does not contain a valid JPEG signature")
    return extension


@app.get(f"{API_PREFIX}/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "omr-checker-api", "version": "0.2.0"}


@app.get(f"{API_PREFIX}/exams", tags=["exams"])
def list_exams(db: Session = Depends(get_db)) -> list[dict]:
    exams = db.scalars(select(Exam).order_by(Exam.created_at.desc())).all()
    return [exam_payload(exam) for exam in exams]


@app.post(f"{API_PREFIX}/exams", status_code=201, tags=["exams"])
def create_exam(payload: ExamCreate, db: Session = Depends(get_db)) -> dict:
    exam = Exam(
        name=payload.name.strip(),
        description=payload.description.strip(),
        total_questions=payload.total_questions,
        options_json=payload.options,
        correct_marks=payload.correct_marks,
        incorrect_marks=payload.incorrect_marks,
        blank_marks=payload.blank_marks,
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return exam_payload(exam)


@app.get(f"{API_PREFIX}/exams/{{exam_id}}", tags=["exams"])
def get_exam(exam_id: str, db: Session = Depends(get_db)) -> dict:
    return exam_payload(get_exam_or_404(db, exam_id))


@app.put(f"{API_PREFIX}/exams/{{exam_id}}/answer-key", tags=["exams"])
def set_answer_key(
    exam_id: str,
    payload: AnswerKeyInput,
    db: Session = Depends(get_db),
) -> dict:
    exam = get_exam_or_404(db, exam_id)
    exam.answer_key_json = validate_answer_key(exam, payload.answers)

    scans = db.scalars(select(Scan).where(Scan.exam_id == exam_id)).all()
    for scan in scans:
        if scan.approved_answers_json and len(scan.approved_answers_json) == exam.total_questions:
            finalize_scan_if_ready(scan, exam)
    db.commit()
    return {"message": "Answer key saved", "exam": exam_payload(exam)}


@app.get(f"{API_PREFIX}/exams/{{exam_id}}/template.pdf", tags=["templates"])
def download_template(exam_id: str, db: Session = Depends(get_db)) -> Response:
    exam = get_exam_or_404(db, exam_id)
    try:
        pdf_bytes = generate_omr_pdf(exam)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    filename = f"omr-{exam.id[:8]}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post(f"{API_PREFIX}/exams/{{exam_id}}/scans", status_code=202, tags=["scans"])
async def upload_scan(
    exam_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    student_id: str = Form(default=""),
    student_name: str = Form(default=""),
    db: Session = Depends(get_db),
) -> dict:
    exam = get_exam_or_404(db, exam_id)
    file_bytes = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Maximum upload size is 20 MB")
    extension = validate_upload(file_bytes, file.filename or "")
    storage = ensure_local_storage()
    upload_id = str(uuid.uuid4())
    source_path = storage / "uploads" / f"{upload_id}{extension}"
    source_path.write_bytes(file_bytes)

    page_images: list[tuple[str, int, int]] = []
    if extension == ".pdf":
        try:
            document = fitz.open(stream=file_bytes, filetype="pdf")
            if len(document) > MAX_PDF_PAGES:
                source_path.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail=f"PDF cannot exceed {MAX_PDF_PAGES} pages")
            if len(document) == 0:
                raise HTTPException(status_code=422, detail="The PDF has no pages")
            for page_index, page in enumerate(document, start=1):
                pixmap = page.get_pixmap(dpi=200, alpha=False)
                page_path = storage / "uploads" / f"{upload_id}-page-{page_index}.png"
                page_path.write_bytes(pixmap.tobytes("png"))
                page_images.append((str(page_path), page_index, len(document)))
            document.close()
        except HTTPException:
            raise
        except Exception as exc:
            source_path.unlink(missing_ok=True)
            raise HTTPException(status_code=422, detail="Could not read the uploaded PDF") from exc
    else:
        image = cv2.imdecode(np.frombuffer(file_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None or min(image.shape[:2]) < 500:
            source_path.unlink(missing_ok=True)
            raise HTTPException(status_code=422, detail="Image is invalid or too small to read reliably")
        page_images.append((str(source_path), 1, 1))

    created: list[Scan] = []
    for image_path, page_number, total_pages in page_images:
        scan = Scan(
            exam_id=exam_id,
            student_id=student_id.strip(),
            student_name=student_name.strip(),
            original_filename=(file.filename or "omr-upload")[:255],
            source_path=str(source_path),
            image_path=image_path,
            page_number=page_number,
            total_pages=total_pages,
            status="queued",
        )
        db.add(scan)
        created.append(scan)

    db.commit()
    for scan in created:
        db.refresh(scan)
        background_tasks.add_task(process_scan_record, scan.id)

    return {
        "message": "Upload accepted; processing has been queued",
        "scans": [scan_payload(scan) for scan in created],
    }


@app.get(f"{API_PREFIX}/exams/{{exam_id}}/scans", tags=["scans"])
def list_scans(exam_id: str, db: Session = Depends(get_db)) -> list[dict]:
    get_exam_or_404(db, exam_id)
    scans = db.scalars(
        select(Scan).where(Scan.exam_id == exam_id).order_by(Scan.created_at.desc())
    ).all()
    return [scan_payload(scan) for scan in scans]


@app.get(f"{API_PREFIX}/scans/{{scan_id}}", tags=["scans"])
def get_scan(scan_id: str, db: Session = Depends(get_db)) -> dict:
    scan = db.get(Scan, scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan_payload(scan)


@app.patch(f"{API_PREFIX}/scans/{{scan_id}}/review", tags=["review"])
def review_scan(
    scan_id: str,
    payload: ReviewInput,
    db: Session = Depends(get_db),
) -> dict:
    scan = db.get(Scan, scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    exam = get_exam_or_404(db, scan.exam_id)

    approved = dict(scan.approved_answers_json or {})
    for question_number, answer in payload.answers.items():
        if question_number not in {str(i) for i in range(1, exam.total_questions + 1)}:
            raise HTTPException(status_code=422, detail=f"Unknown question number: {question_number}")
        if answer is not None:
            answer = answer.strip().upper()
            if answer not in exam.options_json:
                raise HTTPException(status_code=422, detail=f"Unknown option for question {question_number}")
        approved[question_number] = answer

    scan.approved_answers_json = approved
    finalize_scan_if_ready(scan, exam)
    db.commit()
    db.refresh(scan)
    return scan_payload(scan)


@app.get(f"{API_PREFIX}/exams/{{exam_id}}/results.csv", tags=["results"])
def export_results(exam_id: str, db: Session = Depends(get_db)) -> StreamingResponse:
    get_exam_or_404(db, exam_id)
    scans = db.scalars(
        select(Scan)
        .where(Scan.exam_id == exam_id, Scan.status == "evaluated")
        .order_by(Scan.student_id, Scan.page_number)
    ).all()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "scan_id", "student_id", "student_name", "source_file", "page",
        "correct", "incorrect", "unattempted", "score", "maximum_score", "percentage",
    ])
    for scan in scans:
        result = scan.result_json or {}
        writer.writerow([
            scan.id, scan.student_id, scan.student_name, scan.original_filename,
            scan.page_number, result.get("correct", 0), result.get("incorrect", 0),
            result.get("unattempted", 0), result.get("score", 0),
            result.get("maximum_score", 0), result.get("percentage", 0),
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="omr-results-{exam_id[:8]}.csv"'},
    )


@app.get(f"{API_PREFIX}/exams/{{exam_id}}/summary", tags=["results"])
def exam_summary(exam_id: str, db: Session = Depends(get_db)) -> dict:
    get_exam_or_404(db, exam_id)
    scans = db.scalars(select(Scan).where(Scan.exam_id == exam_id)).all()
    evaluated = [scan for scan in scans if scan.status == "evaluated" and scan.result_json]
    scores = [float(scan.result_json["score"]) for scan in evaluated]
    return {
        "total_scans": len(scans),
        "queued": sum(scan.status == "queued" for scan in scans),
        "processing": sum(scan.status == "processing" for scan in scans),
        "needs_review": sum(scan.status == "needs_review" for scan in scans),
        "awaiting_key": sum(scan.status == "awaiting_key" for scan in scans),
        "failed": sum(scan.status == "failed" for scan in scans),
        "evaluated": len(evaluated),
        "average_score": round(sum(scores) / len(scores), 2) if scores else None,
    }
