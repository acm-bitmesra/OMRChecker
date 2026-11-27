# Testing strategy

## Test layers

### Unit tests
- Bubble fill ratio and edge cases.
- Blank / single / multiple / uncertain classification.
- Template bounds and overlap validation.
- Coordinate transforms.
- Scoring rules, rounding, dropped and bonus questions.
- Idempotency and state transitions.

### Integration tests
- API authorization and tenant isolation.
- Upload validation and object metadata.
- Queue publication and retry behavior.
- Database transaction boundaries.
- Result revision and audit events.
- Export generation.

### Golden dataset

Maintain an access-controlled dataset with ground-truth labels and permission to use the scans. Include scanner images at multiple resolutions; phone perspective, rotation, shadows, glare; different printers/photocopies; pen, pencil, light and erased marks; blank, single, multiple, ambiguous; damaged, cropped, and blurred pages; invalid/mismatched template IDs.

Never commit real student records or unredacted scans. Use synthetic or consented de-identified samples.

## Metrics

Report per-bubble precision/recall, per-question exact match, full-sheet exact match, false acceptance of uncertain marks, manual review rate, recapture rate, and throughput. Segment by template version and capture path.

## Acceptance

Every test scan has ground truth and expected page outcome. Changes to preprocessing/thresholds require golden-set evaluation. Published results must not silently change after engine updates. Benchmarks record hardware, resolution, and batch size.

## CI

Run formatting/linting and unit tests on every PR. Add integration and golden-dataset jobs as implementations and licensed fixtures become available.
