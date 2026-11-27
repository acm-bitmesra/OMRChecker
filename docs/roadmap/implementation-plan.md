# Implementation roadmap

Milestones are complete only when acceptance criteria and tests pass.

## M0 — repository foundation
- [x] Document product scope and architecture.
- [x] Establish monorepo directories and service entry points.
- [x] Add initial recognition and scoring primitives.
- [ ] Establish dependency lockfiles and complete CI.
- [ ] Confirm supported sheet layout and print calibration plan.

## M1 — deterministic OMR core
- [ ] Validate complete template schema.
- [ ] Implement PDF rasterization and page quality checks.
- [ ] Detect registration markers and correct perspective.
- [ ] Extract bubble regions and measure marks.
- [ ] Implement blank/single/multiple/uncertain classification.
- [ ] Create synthetic/consented golden dataset.
- [ ] Publish baseline recognition metrics.

## M2 — examiner MVP
- [ ] SQLAlchemy models and Alembic migrations.
- [ ] Organization and user authorization.
- [ ] Exam, section, paper-set, answer-key, and template APIs.
- [ ] Printable PDF generation.
- [ ] Private uploads and scan-batch lifecycle.
- [ ] Celery worker connected to OMR pipeline.
- [ ] Manual review and correction audit trail.
- [ ] Deterministic evaluation and CSV export.

## M3 — usability and trust
- [ ] PWA camera scanning and quality guidance.
- [ ] XLSX/PDF reports and question analytics.
- [ ] Retry/reprocess controls and result revisions.
- [ ] Security and tenant-isolation testing.
- [ ] Pilot using synthetic or institution-approved data.

## M4 — scale and integrations
- [ ] Continuous/offline phone capture.
- [ ] Native mobile app after PWA pilot.
- [ ] SSO and institution integrations.
- [ ] Worker autoscaling and operational SLOs.

## Definition of done
- Acceptance criteria documented and tested.
- No secrets or real student data committed.
- API/template contracts updated.
- Relevant docs and migration notes updated.
- Failure states are visible and recoverable.
- Recognition changes evaluated against the golden dataset.
