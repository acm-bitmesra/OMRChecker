from pathlib import Path
from types import SimpleNamespace

import fitz
import numpy as np
import cv2

from app.services.recognition import recognize_sheet
from app.services.template import generate_omr_pdf


def test_generated_blank_sheet_is_aligned_and_recognized(tmp_path: Path) -> None:
    exam = SimpleNamespace(
        id="recognition-test",
        name="Recognition test",
        total_questions=8,
        options_json=["A", "B", "C", "D"],
    )
    pdf = fitz.open(stream=generate_omr_pdf(exam), filetype="pdf")
    pixmap = pdf[0].get_pixmap(dpi=200, alpha=False)
    image_path = tmp_path / "blank-sheet.png"
    image_path.write_bytes(pixmap.tobytes("png"))

    result = recognize_sheet(image_path, 8, ["A", "B", "C", "D"])
    assert len(result["questions"]) == 8
    assert all(item["state"] == "blank" for item in result["questions"].values())
