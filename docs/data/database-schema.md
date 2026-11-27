# Database model

This is the logical schema for initial migrations. Final column types, indexes, constraints, and deletion policies belong in SQLAlchemy models and Alembic migrations.

## Core entities

| Entity | Important fields / relationships |
| --- | --- |
| organizations | id, name, slug, status, created_at |
| users | id, email, display_name, status |
| organization_members | organization_id, user_id, role, membership_status |
| exams | id, organization_id, title, status, scheduled_at |
| exam_sections | id, exam_id, title, position, question range |
| paper_sets | id, exam_id, code, title |
| questions | id, section_id, number, option_count, type |
| marking_rules | id, exam_id, version, correct/incorrect/blank marks |
| answer_key_versions | id, exam_id, paper_set_id, version, status |
| answer_key_items | answer_key_version_id, question_id, correct_options |
| omr_templates | id, exam_id, name |
| template_versions | id, template_id, version, schema_version, config_json, artifact_key |
| students | id, organization_id, external_identifier, display_name |
| scan_batches | id, organization_id, exam_id, template_version_id, status |
| scan_files | id, batch_id, object_key, checksum, content_type, byte_size |
| scan_pages | id, scan_file_id, page_number, sheet_identifier, status |
| processing_attempts | id, scan_page_id, engine_version, status, timestamps |
| detected_responses | id, scan_page_id, question_id, status, selected_options, measurements_json |
| review_events | id, scan_page_id, reviewer_user_id, before_json, after_json, reason, created_at |
| evaluation_results | id, scan_page_id, student_id, answer_key_version_id, rules_version, score, status |
| result_revisions | id, evaluation_result_id, revision, snapshot_json, created_at |
| exports | id, exam_id, requested_by, format, status, object_key |

## Constraints and indexes
- Unique organization slug and membership per organization/user.
- Unique section position within exam and question number within its scope.
- Unique template version number per template.
- Unique answer-key version per exam/paper set.
- Unique page number per uploaded file.
- Unique idempotency key per page/engine version.
- Unique evaluation revision per result.
- Index common filters such as organization_id, exam_id, batch_id, status, and created_at.

Keep frequently queried attributes relational. Use JSON only for versioned configuration or evidence payloads.

## Tenant isolation

Tenant-owned records must carry or be reachable through an organization ID. Every API query and worker task must verify organization scope. PostgreSQL row-level security may add defense in depth but does not replace application authorization tests.

## Data lifecycle

Originals are immutable until retention deletion. Derived overlays and exports may have shorter retention. Deletion is auditable and follows documented policy. Finalized result snapshots retain enough information to reproduce a score, subject to institutional retention rules. Avoid student personal data in object names or public URLs.
