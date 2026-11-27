# API design notes

Base path: `/api/v1`. FastAPI should publish an OpenAPI document from route and schema definitions; this file records intended resource boundaries.

## Conventions
- JSON request/response bodies except dedicated file-transfer endpoints.
- UUID identifiers for externally visible resources.
- UTC timestamps in ISO 8601.
- Pagination for list endpoints.
- Stable machine-readable error codes.
- Every query scoped to the caller's organization.
- Idempotency keys for batch creation and long-running submissions.
- Return a job/batch ID immediately for asynchronous work.

## Initial endpoint map

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/exams` | Create exam |
| GET | `/exams` | List accessible exams |
| GET | `/exams/{exam_id}` | Retrieve exam |
| POST | `/exams/{exam_id}/template-versions` | Create template version |
| POST | `/template-versions/{version_id}/generate` | Generate printable PDF |
| POST | `/exams/{exam_id}/answer-key-versions` | Create answer-key version |
| POST | `/exams/{exam_id}/scan-batches` | Create scan batch |
| POST | `/scan-batches/{batch_id}/uploads` | Register upload |
| POST | `/scan-batches/{batch_id}/process` | Queue recognition |
| GET | `/scan-batches/{batch_id}` | Read batch/page statuses |
| GET | `/scan-pages/{page_id}/detections` | Read detection evidence |
| PATCH | `/scan-pages/{page_id}/responses` | Submit examiner corrections |
| POST | `/scan-pages/{page_id}/evaluate` | Evaluate approved responses |
| POST | `/scan-batches/{batch_id}/finalize` | Finalize batch |
| GET | `/exams/{exam_id}/analytics` | Exam analytics |
| POST | `/exams/{exam_id}/exports` | Request export job |

## Response envelope

```json
{
  "data": { "id": "resource-uuid", "status": "queued" },
  "meta": { "request_id": "request-uuid" }
}
```

## Error envelope

```json
{
  "error": {
    "code": "TEMPLATE_VERSION_MISMATCH",
    "message": "The uploaded sheet does not match the selected template version.",
    "request_id": "request-uuid"
  }
}
```

Never expose stack traces, storage credentials, signed URLs, or internal filesystem paths. Validate state transitions server-side.
