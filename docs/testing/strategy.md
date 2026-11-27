# Testing strategy

## Automated tests
- Unit tests for bubble and question classification.
- Unit tests for deterministic scoring and unresolved answer handling.
- PDF generation and A4 page dimensions.
- Synthetic blank-sheet round trip: generate PDF, rasterize at 200 DPI, detect ArUco markers, align, and verify blank responses.
- FastAPI smoke test for exam creation and answer-key persistence.

## Golden dataset before real use

Build an access-controlled labeled dataset with scanner and phone captures, perspective distortion, rotation, uneven lighting, different printers and photocopies, pen/pencil marks, erasures, blanks, multiple marks, and low-quality pages. Use synthetic or consented de-identified samples only.

## Metrics

Report per-bubble precision/recall, per-question exact match, full-sheet exact match, false acceptance of ambiguous marks, manual review rate, recapture rate, and throughput. Segment by template version and capture path.

## CI

Run engine, template, and API tests for every pull request. Recognition threshold changes require a golden-dataset report. Never silently change a finalized result after an engine update.
