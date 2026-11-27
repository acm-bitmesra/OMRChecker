# Cross-service and golden-dataset tests

This directory is reserved for integration tests spanning the API, queue, worker, storage, and result lifecycle.

## Planned suites
- Upload-to-worker-to-result integration tests.
- Tenant isolation and authorization regression tests.
- Idempotent queue submission and retry tests.
- Batch state transition and partial-failure tests.
- Golden-dataset evaluation across supported template and capture profiles.

Keep unit tests beside their owning Python packages. Store only synthetic or consented, de-identified sample sheets in test fixtures; never commit real student records. Large approved fixtures should use a documented artifact workflow rather than Git history.
