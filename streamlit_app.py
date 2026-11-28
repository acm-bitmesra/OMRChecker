from __future__ import annotations

import csv
import re
import sys
import uuid
from io import StringIO
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent
_API_DIR = _REPO_ROOT / "services" / "api"
if _API_DIR.is_dir() and str(_API_DIR) not in sys.path:
    sys.path.insert(0, str(_API_DIR))

import cv2
import fitz
import numpy as np
from sqlalchemy import select

from app.database import Base, SessionLocal, engine, ensure_local_storage
from app.models import Exam, Scan, SheetToken
from app.services.evaluation import build_approved_answers, evaluate_answers
from app.services.processing import resolve_scan_identity
from app.services.recognition import RecognitionError, recognize_sheet
from app.services.template import generate_omr_pdf

MAX_PDF_PAGES = 50
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf"}


def parse_answer_key_lines(
    raw_text: str,
    total_questions: int,
    allowed_options: list[str],
) -> tuple[dict[str, str], str | None]:
    """Parse `1:A` lines into a normalized answer key dict or return an error message."""
    allowed = {opt.strip().upper() for opt in allowed_options}
    answers: dict[str, str] = {}
    for line in raw_text.splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue
        match = re.match(r"^(\d+)\s*[:,\-\s]\s*([A-Za-z0-9]+)$", cleaned)
        if not match:
            return {}, f"Could not parse line: {cleaned!r}. Use format like 1:A."
        q_num, opt = match.group(1), match.group(2).upper()
        if opt not in allowed:
            return {}, f"Option {opt!r} for question {q_num} is not in {sorted(allowed)}."
        answers[q_num] = opt

    expected = {str(i) for i in range(1, total_questions + 1)}
    missing = sorted(expected - set(answers), key=int)
    extra = sorted(set(answers) - expected)
    if missing or extra:
        parts: list[str] = []
        if missing:
            parts.append(f"missing questions {', '.join(missing[:8])}")
        if extra:
            parts.append(f"unexpected questions {', '.join(extra[:8])}")
        return {}, f"Answer key incomplete ({'; '.join(parts)})."
    return answers, None


def build_results_csv(scans: list[Scan]) -> str:
    """Serialize evaluated scan results into a downloadable CSV report."""
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "scan_id",
            "student_id",
            "student_name",
            "source_file",
            "page",
            "correct",
            "incorrect",
            "unattempted",
            "score",
            "maximum_score",
            "percentage",
        ]
    )
    for scan in scans:
        if scan.status != "evaluated" or not scan.result_json:
            continue
        res = scan.result_json
        writer.writerow(
            [
                scan.id,
                scan.student_id,
                scan.student_name,
                scan.original_filename,
                scan.page_number,
                res.get("correct", 0),
                res.get("incorrect", 0),
                res.get("unattempted", 0),
                res.get("score", 0),
                res.get("maximum_score", 0),
                res.get("percentage", 0),
            ]
        )
    return output.getvalue()


def extract_page_images(file_bytes: bytes, filename: str, storage: Path) -> list[tuple[Path, int, int]]:
    """Validate an uploaded image/PDF and persist per-page PNG/image paths for recognition."""
    ext = Path(filename or "capture.png").suffix.lower() or ".png"
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("Upload a PNG, JPG, or PDF file.")

    upload_id = str(uuid.uuid4())
    source_path = storage / "uploads" / f"{upload_id}{ext}"
    source_path.write_bytes(file_bytes)

    if ext == ".pdf":
        if not file_bytes.startswith(b"%PDF"):
            source_path.unlink(missing_ok=True)
            raise ValueError("Invalid PDF header.")
        document = fitz.open(stream=file_bytes, filetype="pdf")
        try:
            if len(document) == 0:
                raise ValueError("The uploaded PDF has no pages.")
            if len(document) > MAX_PDF_PAGES:
                raise ValueError(f"PDF cannot exceed {MAX_PDF_PAGES} pages.")
            pages: list[tuple[Path, int, int]] = []
            for idx, page in enumerate(document, start=1):
                pixmap = page.get_pixmap(dpi=200, alpha=False)
                page_path = storage / "uploads" / f"{upload_id}-page-{idx}.png"
                page_path.write_bytes(pixmap.tobytes("png"))
                pages.append((page_path, idx, len(document)))
            return pages
        except Exception:
            source_path.unlink(missing_ok=True)
            raise
        finally:
            document.close()

    decoded = cv2.imdecode(np.frombuffer(file_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
    if decoded is None or min(decoded.shape[:2]) < 500:
        source_path.unlink(missing_ok=True)
        raise ValueError("Image is invalid or below the 500px minimum dimension.")
    return [(source_path, 1, 1)]


def init_runtime() -> Path:
    storage = ensure_local_storage()
    Base.metadata.create_all(bind=engine)
    return storage


def run_app() -> None:
    import streamlit as st

    st.set_page_config(
        page_title="OMR Checker — Scan, Review & Evaluate",
        page_icon="📝",
        layout="wide",
    )

    storage = init_runtime()

    st.title("📝 OMR Checker")
    st.caption("ACM BIT Mesra · Create printable OMR sheets, scan with camera/scanner, review uncertain marks, and export scores.")

    with SessionLocal() as db:
        exams = list(db.scalars(select(Exam).order_by(Exam.created_at.desc())).all())

    with st.sidebar:
        st.header("Workspace")
        if exams:
            exam_labels = {f"{ex.name} ({ex.total_questions}Q)": ex.id for ex in exams}
            chosen_label = st.selectbox("Selected examination", list(exam_labels.keys()))
            selected_exam_id = exam_labels[chosen_label]
        else:
            selected_exam_id = None
            st.info("Create your first examination below to begin.")

        st.divider()
        st.subheader("New Examination")
        with st.form("create_exam_form", clear_on_submit=True):
            new_name = st.text_input("Exam name", placeholder="e.g. Physics Midterm")
            new_q_count = st.number_input("Questions (1–100)", min_value=1, max_value=100, value=20)
            new_opt_count = st.selectbox("Options per question", [4, 3, 2], format_func=lambda n: f"{n} ({'ABCD'[:n]})")
            c1, c2, c3 = st.columns(3)
            new_correct = c1.number_input("Correct", min_value=0.25, max_value=100.0, value=4.0, step=0.5)
            new_incorrect = c2.number_input("Wrong", min_value=-100.0, max_value=100.0, value=-1.0, step=0.5)
            new_blank = c3.number_input("Blank", min_value=-100.0, max_value=100.0, value=0.0, step=0.5)
            submitted = st.form_submit_button("Create examination", use_container_width=True)
            if submitted:
                if len(new_name.strip()) < 2:
                    st.error("Exam name must be at least 2 characters.")
                else:
                    with SessionLocal() as db:
                        exam = Exam(
                            name=new_name.strip(),
                            total_questions=int(new_q_count),
                            options_json=["A", "B", "C", "D"][: int(new_opt_count)],
                            correct_marks=float(new_correct),
                            incorrect_marks=float(new_incorrect),
                            blank_marks=float(new_blank),
                        )
                        db.add(exam)
                        db.commit()
                    st.success("Examination created.")
                    st.rerun()

    if not selected_exam_id:
        st.info("Use the sidebar to create an examination, download printable ArUco OMR PDFs, and start scanning.")
        return

    with SessionLocal() as db:
        exam = db.get(Exam, selected_exam_id)
        if exam is None:
            st.warning("Selected exam no longer exists.")
            return
        scans = list(
            db.scalars(select(Scan).where(Scan.exam_id == exam.id).order_by(Scan.created_at.desc())).all()
        )

    m1, m2, m3, m4 = st.columns(4)
    evaluated_scans = [s for s in scans if s.status == "evaluated" and s.result_json]
    m1.metric("Questions", exam.total_questions)
    m2.metric("Uploaded sheets", len(scans))
    m3.metric("Evaluated", len(evaluated_scans))
    m4.metric("Needs review", sum(1 for s in scans if s.status == "needs_review"))

    tab_sheets, tab_key, tab_scan, tab_review = st.tabs(
        ["1. Printable Sheets", "2. Answer Key", "3. Scan & Upload", "4. Review & Export"]
    )

    with tab_sheets:
        st.subheader("Generic A4 OMR Sheet")
        st.write(f"Options: **{' · '.join(exam.options_json)}** | Marking: **+{exam.correct_marks} / {exam.incorrect_marks} / {exam.blank_marks}**")
        generic_pdf = generate_omr_pdf(exam)
        st.download_button(
            "Download generic OMR PDF",
            data=generic_pdf,
            file_name=f"omr-{exam.id[:8]}.pdf",
            mime="application/pdf",
        )

        st.divider()
        st.subheader("Personalized Candidate Sheet (QR Token)")
        p1, p2 = st.columns(2)
        cand_id = p1.text_input("Student ID / Roll Number", placeholder="e.g. BIT-2026-001")
        cand_name = p2.text_input("Student Name (optional)", placeholder="Candidate name")
        if st.button("Generate QR answer sheet PDF", disabled=not cand_id.strip()):
            token = uuid.uuid4().hex
            pdf_bytes = generate_omr_pdf(exam, sheet_token=token)
            with SessionLocal() as db:
                db.add(
                    SheetToken(
                        token=token,
                        exam_id=exam.id,
                        student_id=cand_id.strip(),
                        student_name=cand_name.strip(),
                    )
                )
                db.commit()
            st.download_button(
                "Download personalized QR PDF",
                data=pdf_bytes,
                file_name=f"omr-{cand_id.strip()}.pdf",
                mime="application/pdf",
            )

    with tab_key:
        st.subheader("Answer Key")
        existing_key = "\n".join(
            f"{q}:{exam.answer_key_json[str(q)]}"
            for q in range(1, exam.total_questions + 1)
            if exam.answer_key_json and str(q) in exam.answer_key_json
        )
        key_text = st.text_area(
            f"Enter one answer per line (e.g. 1:A) for all {exam.total_questions} questions",
            value=existing_key,
            height=220,
        )
        if st.button("Save answer key"):
            parsed, err = parse_answer_key_lines(key_text, exam.total_questions, exam.options_json)
            if err:
                st.error(err)
            else:
                with SessionLocal() as db:
                    db_exam = db.get(Exam, exam.id)
                    assert db_exam is not None
                    db_exam.answer_key_json = parsed
                    for scan in db.scalars(select(Scan).where(Scan.exam_id == exam.id)).all():
                        if scan.approved_answers_json and len(scan.approved_answers_json) == db_exam.total_questions and scan.student_id.strip():
                            scan.result_json = evaluate_answers(
                                scan.approved_answers_json,
                                parsed,
                                correct_marks=db_exam.correct_marks,
                                incorrect_marks=db_exam.incorrect_marks,
                                blank_marks=db_exam.blank_marks,
                            )
                            scan.status = "evaluated"
                    db.commit()
                st.success("Answer key saved and ready scans evaluated.")
                st.rerun()

    with tab_scan:
        st.subheader("Upload Scan or Capture from Camera")
        s1, s2 = st.columns(2)
        manual_sid = s1.text_input("Student ID (optional if using QR sheet)", key="scan_sid")
        manual_sname = s2.text_input("Student Name (optional)", key="scan_sname")
        uploaded = st.file_uploader("Upload PNG, JPG, or PDF", type=["png", "jpg", "jpeg", "pdf"])
        camera_photo = st.camera_input("Or capture answer sheet with camera")
        active_file = uploaded or camera_photo

        if st.button("Process answer sheet", disabled=active_file is None):
            assert active_file is not None
            try:
                file_bytes = active_file.getvalue()
                pages = extract_page_images(file_bytes, active_file.name, storage)
            except ValueError as exc:
                st.error(str(exc))
                pages = []

            processed_count = 0
            for page_path, page_num, total_pages in pages:
                with SessionLocal() as db:
                    db_exam = db.get(Exam, exam.id)
                    assert db_exam is not None
                    scan = Scan(
                        exam_id=exam.id,
                        student_id=manual_sid.strip(),
                        student_name=manual_sname.strip(),
                        original_filename=(active_file.name or "capture.png")[:255],
                        source_path=str(page_path),
                        image_path=str(page_path),
                        page_number=page_num,
                        total_pages=total_pages,
                        status="processing",
                    )
                    db.add(scan)
                    db.commit()
                    db.refresh(scan)

                    try:
                        detections = recognize_sheet(page_path, db_exam.total_questions, db_exam.options_json)
                        approved, unresolved = build_approved_answers(detections["questions"])
                        token = detections.get("sheet_token")
                        token_record = db.get(SheetToken, token) if token else None
                        id_err = resolve_scan_identity(scan, token_record, db_exam.id, token)
                        scan.detections_json = detections
                        scan.approved_answers_json = approved
                        scan.error_message = id_err
                        if unresolved or id_err:
                            scan.status = "needs_review"
                        elif not db_exam.answer_key_json:
                            scan.status = "awaiting_key"
                        else:
                            scan.result_json = evaluate_answers(
                                approved,
                                db_exam.answer_key_json,
                                correct_marks=db_exam.correct_marks,
                                incorrect_marks=db_exam.incorrect_marks,
                                blank_marks=db_exam.blank_marks,
                            )
                            scan.status = "evaluated"
                    except RecognitionError as exc:
                        scan.status = "failed"
                        scan.error_message = str(exc)
                    db.commit()
                    processed_count += 1

            if processed_count:
                st.success(f"Processed {processed_count} page(s). Check Review & Export.")
                st.rerun()

    with tab_review:
        st.subheader("Scans, Manual Review & CSV Export")
        if evaluated_scans:
            st.download_button(
                "Download evaluated results CSV",
                data=build_results_csv(evaluated_scans),
                file_name=f"omr-results-{exam.id[:8]}.csv",
                mime="text/csv",
            )

        if not scans:
            st.info("No sheets processed yet.")
            return

        scan_options = {
            f"{s.student_id or 'Unresolved'} · {s.original_filename} (p.{s.page_number}) [{s.status}]": s.id
            for s in scans
        }
        chosen_scan_label = st.selectbox("Select scan to inspect or review", list(scan_options.keys()))
        chosen_scan_id = scan_options[chosen_scan_label]

        with SessionLocal() as db:
            scan = db.get(Scan, chosen_scan_id)
            if scan is None:
                return

        col_img, col_form = st.columns([1, 1])
        with col_img:
            if Path(scan.image_path).is_file():
                st.image(scan.image_path, caption=f"{scan.original_filename} (page {scan.page_number})", use_container_width=True)
            if scan.error_message:
                st.warning(scan.error_message)
            if scan.result_json:
                res = scan.result_json
                st.success(f"Score: {res['score']} / {res['maximum_score']} ({res['percentage']}%) — {res['correct']}✓ / {res['incorrect']}✗ / {res['unattempted']} blank")

        with col_form:
            rev_sid = st.text_input("Student ID", value=scan.student_id, key=f"rev_sid_{scan.id}")
            rev_sname = st.text_input("Student Name", value=scan.student_name, key=f"rev_sname_{scan.id}")
            choices = ["Blank"] + exam.options_json
            overrides: dict[str, str | None] = {}
            detections_q = (scan.detections_json or {}).get("questions", {})

            for q_num in range(1, exam.total_questions + 1):
                q_key = str(q_num)
                det = detections_q.get(q_key, {})
                current = (scan.approved_answers_json or {}).get(q_key)
                if current not in exam.options_json:
                    current = "Blank"
                ratios = det.get("fill_ratios", {})
                ratio_str = " ".join(f"{k}:{int(v * 100)}%" for k, v in ratios.items())
                picked = st.selectbox(
                    f"Q{q_num} ({det.get('state', 'n/a')} · {ratio_str})",
                    choices,
                    index=choices.index(current),
                    key=f"q_{scan.id}_{q_key}",
                )
                overrides[q_key] = None if picked == "Blank" else picked

            if st.button("Save reviewed answers", key=f"save_rev_{scan.id}"):
                if not rev_sid.strip():
                    st.error("Student ID is required to finalize evaluation.")
                else:
                    with SessionLocal() as db:
                        db_scan = db.get(Scan, scan.id)
                        db_exam = db.get(Exam, exam.id)
                        assert db_scan is not None and db_exam is not None
                        db_scan.student_id = rev_sid.strip()
                        db_scan.student_name = rev_sname.strip()
                        db_scan.approved_answers_json = overrides
                        db_scan.error_message = ""
                        if db_exam.answer_key_json:
                            db_scan.result_json = evaluate_answers(
                                overrides,
                                db_exam.answer_key_json,
                                correct_marks=db_exam.correct_marks,
                                incorrect_marks=db_exam.incorrect_marks,
                                blank_marks=db_exam.blank_marks,
                            )
                            db_scan.status = "evaluated"
                        else:
                            db_scan.status = "awaiting_key"
                        db.commit()
                    st.success("Reviewed answers saved.")
                    st.rerun()


if __name__ == "__main__":
    run_app()
