from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Exam(Base):
    __tablename__ = "exams"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False)
    options_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    correct_marks: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    incorrect_marks: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    blank_marks: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    answer_key_json: Mapped[dict[str, str] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    scans: Mapped[list["Scan"]] = relationship(
        back_populates="exam", cascade="all, delete-orphan"
    )


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    exam_id: Mapped[str] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    student_name: Mapped[str] = mapped_column(String(160), default="", nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    source_path: Mapped[str] = mapped_column(Text, nullable=False)
    image_path: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    total_pages: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    detections_json: Mapped[dict[str, dict] | None] = mapped_column(JSON, nullable=True)
    approved_answers_json: Mapped[dict[str, str | None] | None] = mapped_column(JSON, nullable=True)
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    exam: Mapped[Exam] = relationship(back_populates="scans")
