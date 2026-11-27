# End-to-end data flow

## Create and print
1. Authorized examiner creates an exam.
2. Questions, sections, paper sets, and scoring rules are saved.
3. An immutable template version is generated.
4. PDF includes registration marks, template/version identity, and unique sheet ID.
5. Generated artifact is stored and made downloadable.

## Upload and queue
1. Examiner creates a scan batch bound to an exam and template version.
2. Files are uploaded through validated API or short-lived signed URLs.
3. API records checksum, size, MIME type, and page count.
4. Duplicate content may be flagged within the appropriate tenant scope.
5. Each page gets an idempotent processing job.

## Recognition and review
1. Worker downloads and decodes the original page.
2. Pipeline checks quality and aligns to the template.
3. Bubble measurements and classifications are stored.
4. Low-quality, uncertain, multiple-mark, or unresolved-identity pages enter review.
5. Examiner reviews source image/overlays and confirms or corrects answers.
6. Every correction creates a review event.

## Evaluation and publication
1. Evaluator resolves exact answer-key and marking-rule versions.
2. Scoring function computes results from approved responses.
3. Result is saved with reproducible calculation snapshot.
4. Examiner finalizes the batch.
5. Exports are generated from finalized snapshots.

## State transitions

Page: `queued -> processing -> review_required | evaluated | failed`

Review: `pending -> in_review -> resolved`

Publication: `draft -> ready_for_publication -> finalized`

Finalized results must not be silently overwritten. A correction or re-evaluation creates a traceable new revision.
