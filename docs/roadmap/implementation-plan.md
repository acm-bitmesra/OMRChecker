# Implementation roadmap

## Delivered in the current MVP
- [x] Product and architecture documentation.
- [x] Next.js examiner dashboard.
- [x] FastAPI exam, answer-key, upload, review, summary, and CSV routes.
- [x] SQLAlchemy models with SQLite local default and PostgreSQL URL support.
- [x] A4 PDF generator with ArUco registration markers.
- [x] OpenCV perspective alignment and bubble fill measurement.
- [x] Blank/single/multiple/uncertain question classification.
- [x] Deterministic scoring and manual review.
- [x] PNG/JPG and multipage PDF ingestion.
- [x] Unit and integration smoke tests.

## Next: production hardening
- [ ] Calibrate thresholds against a diverse labeled dataset.
- [ ] Add authentication, organization membership, and role-based access.
- [ ] Move uploads and derived artifacts to private object storage.
- [ ] Connect scan jobs to Celery/Redis with retries and idempotency.
- [ ] Implement robust audit events and result revisions.
- [ ] Add QR/student roster matching and separate candidate identity workflow.
- [ ] Add XLSX/PDF reports and question-level analytics.
- [ ] Add PWA camera capture, quality checks, and recapture guidance.
- [ ] Add containerized API/web/worker deployment and CI build checks.
- [ ] Complete security, load, and recovery testing before institutional pilots.
