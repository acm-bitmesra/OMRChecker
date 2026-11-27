# Product requirements document

**Status:** MVP implemented; institutional features remain planned.  
**Product:** OMR Checker  
**Users:** Exam administrators, teachers, evaluators, and institution operators.

## Current working MVP
- Create exams with 1–100 questions and 2–4 choices.
- Configure correct, incorrect, and blank marks.
- Generate a single-page A4 answer sheet with four ArUco registration markers.
- Upload PNG/JPG or PDFs of up to 50 pages (each PDF page is an independent sheet).
- Align each scan with OpenCV and measure bubble fill.
- Classify each question as blank, single, multiple, or uncertain.
- Route multiple/uncertain detections to manual review.
- Save a complete answer key, deterministically score approved responses, and export CSV.

## Still planned
- Production authentication and organization tenancy.
- Student identity bubble recognition / QR roster assignment.
- Native mobile application and offline capture.
- Distributed queue and independently autoscaled workers.
- Cloud object storage, retention automation, rich analytics, XLSX/PDF reporting.
- Expanded templates, paper sets, and advanced marking policies.

## Product principles
- Correctness and traceability take priority over throughput.
- Original uploads are preserved during processing.
- Templates and recognition algorithms are versioned.
- Scoring is separate from image recognition.
- Uncertain marks must be reviewed; the system must not guess.

## Quality metrics
Measure per-bubble precision/recall, per-question exact match, whole-sheet exact match, false acceptance of uncertain marks, manual review rate, recapture rate, and throughput. Do not claim an accuracy target until a representative ground-truth dataset exists.
