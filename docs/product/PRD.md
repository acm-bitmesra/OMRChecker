# Product requirements document

**Status:** Draft for implementation planning  
**Product:** OMR Checker  
**Users:** Exam administrators, teachers, evaluators, and institution operators.

## Problem and outcome

Manual checking of multiple-choice answer sheets takes time and can introduce arithmetic and transcription errors. Dedicated OMR hardware can be inaccessible to smaller institutions. OMR Checker aims to make structured OMR evaluation usable with ordinary scanners and phone cameras while keeping every uncertain decision reviewable.

An examiner should be able to define an exam, generate a sheet, capture or upload responses, review uncertain marks, calculate marks from configured rules, and export auditable results.

## Personas

| Persona | Need |
| --- | --- |
| Exam administrator | Configure exams, templates, answer keys, and access |
| Evaluator | Process batches and resolve uncertain responses |
| Teacher | Understand student and question-level performance |
| Organization owner | Manage members, retention, and institutional settings |

## MVP scope

### P0 — first usable release
- Organization/user foundation and role-aware access.
- Exam creation with question count, options, sections, and scoring rules.
- Versioned template generation for a small set of A4 layouts.
- Answer-key entry and paper-set association.
- JPG, PNG, and multipage PDF ingestion.
- Page-level processing queue and status.
- Registration-marker alignment.
- Bubble measurement and blank / single / multiple / uncertain classification.
- Examiner review and corrections with audit events.
- Deterministic score calculation.
- CSV export and processing provenance.

### P1 — quality and usability
- Phone-camera capture and continuous scanning.
- Blur, glare, cropping, and lighting checks.
- XLSX/PDF exports and question analytics.
- Multiple paper sets, sections, bonus/dropped questions, cutoffs.
- Bulk batch monitoring, retry, and reprocess controls.

### P2 — institutional scale
- Native mobile app and offline capture.
- Multi-institution administration and advanced roles.
- SSO, integrations, public API, configurable retention.
- Worker autoscaling and operational SLOs.

## Out of scope for MVP
- Arbitrary handwritten-text OCR.
- Descriptive-answer grading.
- LLM-based bubble decisions.
- Universal support for third-party OMR layouts.
- Automatic publication of low-confidence results.

## Functional requirements

| ID | Requirement | Acceptance condition |
| --- | --- | --- |
| FR-01 | Exam creation | Authorized user can save exam metadata and status |
| FR-02 | Marking rules | Correct, incorrect, blank, and special-question policies are explicit |
| FR-03 | Template generation | PDF carries template/version identity and registration marks |
| FR-04 | Batch upload | Files are validated and stored before processing |
| FR-05 | Recognition | Every question has a typed status and traceable measurements |
| FR-06 | Manual review | Examiner sees source crop, detected options, and can correct with an audit event |
| FR-07 | Evaluation | Same inputs and versions produce the same score |
| FR-08 | Export | Export includes stable student IDs and clear score fields |

## Non-functional requirements
- Correctness and traceability take priority over throughput.
- Original uploads are immutable.
- Every state-changing request is authenticated and authorized.
- Cross-organization access is denied by default.
- Jobs are idempotent and retry-safe.
- States distinguish queued, processing, review-required, evaluated, failed, and finalized.
- Supported print/capture conditions and limitations are explicit.

## Metrics

Do not claim an accuracy target before building a labeled dataset. Establish a baseline and track per-bubble precision/recall, per-question exact match, full-sheet exact match, false acceptance of uncertain marks, review rate, recapture rate, and throughput by capture method.

## Risks

Poor print quality, erasures, shadows, identity mismatch, template mismatch, duplicate pages, and incorrect answer-key configuration can all invalidate results. Mitigate with versioned templates, source preservation, review, auditability, and representative testing.
