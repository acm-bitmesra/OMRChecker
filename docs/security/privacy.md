# Security and privacy baseline

OMR scans and result reports may contain personally identifiable educational records. Treat them as sensitive institutional data.

## Authentication and authorization
- Use a maintained authentication integration; do not invent password storage.
- Enforce organization membership and roles on every tenant-owned resource.
- Use least privilege: owner, administrator, examiner, reviewer, read-only viewer.
- Re-check access in background tasks so queued work cannot bypass revoked permissions.
- Rate-limit authentication, upload creation, and exports.

## Upload security
- Validate extension, MIME signature, size, dimensions, page count, and decompression limits.
- Generate object keys server-side; never use user-controlled paths.
- Treat PDFs, images, QR content, and metadata as untrusted input.
- Keep buckets private and issue short-lived signed URLs.
- Prevent cross-tenant object enumeration and public bucket access.

## Data protection
- Use TLS and managed encryption at rest.
- Store secrets in deployment secret managers, never Git.
- Avoid logging student names, IDs, answers, signed URLs, or file contents.
- Define retention with participating institutions.
- Support audited export and deletion workflows.
- Prefer opaque random sheet identifiers over personal data in QR codes.

## Auditability

Record exam/answer-key changes, reviewer corrections, result finalization, exports, and privileged access.

## Incident response

Report vulnerabilities privately to maintainers. Do not publish student data, credentials, or exploit details in public issues. See [SECURITY.md](../../SECURITY.md).

## Compliance note

Legal and institutional obligations depend on deployment jurisdiction and policy. Obtain appropriate review before processing real student records. This document is an engineering baseline, not legal advice.
