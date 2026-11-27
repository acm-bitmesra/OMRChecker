# OMR recognition pipeline

## Stages

1. **Ingest:** validate extension, MIME signature, byte size, image dimensions, PDF page count, and checksum.
2. **Decode:** rasterize PDF pages at configured resolution; retain original bytes.
3. **Quality assessment:** detect blur, glare, low contrast, clipping, and extreme skew.
4. **Locate sheet:** detect printed registration marks and verify geometry.
5. **Align:** estimate page transform and warp into the template's canonical coordinate plane.
6. **Normalize:** grayscale, denoise conservatively, and compensate for uneven illumination.
7. **Locate fields:** resolve question and option regions from the exact immutable template version.
8. **Measure marks:** compute fill metrics inside bubble interiors, excluding printed outlines.
9. **Classify:** blank, single, multiple, or uncertain; retain per-option measurements and algorithm version.
10. **Resolve identity:** decode sheet ID and configured student identifier; route unresolved identity to review.
11. **Evaluate:** compare examiner-approved responses with answer-key and marking-rule versions.
12. **Persist:** store status, detections, evaluation, and provenance.

## Geometry

Template coordinates are normalized to the canonical page, measured from the top-left. Width and height are fractions of page dimensions. All measurements are mapped onto the aligned page, never directly onto the raw camera frame.

## Bubble measurement

A basic measurement is:

`fill_ratio = dark_pixel_count / sampled_pixel_count`

Use an inset measurement region to avoid counting the printed bubble outline. Thresholds must be calibrated per supported template/print profile using labeled samples. Local/adaptive measurements may be needed for uneven illumination.

## Question classifications

- **blank:** no option exceeds the calibrated mark threshold.
- **single:** exactly one option crosses the threshold confidently.
- **multiple:** more than one option crosses the threshold.
- **uncertain:** quality checks fail, measurements fall in an ambiguity band, or required geometry/identity is unreliable.

Never convert uncertain to blank or single by default. A page that cannot be aligned must not be evaluated using guessed coordinates.

## Versioned evidence

Persist file checksum/object key, page number, sheet ID, template version, engine/preprocessing version, quality metrics, per-option measurements, classification, review corrections, answer-key version, and scoring-rule version.
