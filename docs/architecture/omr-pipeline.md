# OMR recognition pipeline

## Implemented path

1. Validate PNG/JPG/PDF extension, signature, upload size, and PDF page count.
2. Decode raster images; rasterize PDF pages with PyMuPDF at 200 DPI.
3. Detect all four ArUco registration markers (IDs 0–3).
4. Estimate a perspective transform and warp to canonical A4 dimensions.
5. Compute per-bubble interior dark-pixel ratio relative to nearby paper brightness.
6. Classify each option and then each question as blank, single, multiple, or uncertain.
7. Store per-option fill ratios and engine version.
8. Auto-approve only blank and single detections; route multiple and uncertain responses to review.
9. Apply marking rules only after every question has an approved response.

## Geometry and template

The canonical page is A4 portrait. Bubble positions are shared by the PDF generator and recognition service through `bubble_center_mm`. Template markers use the OpenCV ArUco DICT_4X4_50 dictionary. Marker IDs identify their page corners, so a rotated camera frame can still be rectified.

## Measurement

For each option, the engine measures dark pixels inside an inset circle and estimates local paper brightness in a surrounding annulus:

`fill_ratio = dark_pixels_inside / sampled_interior_pixels`

The default blank and filled thresholds in code are provisional. The intermediate band is deliberately uncertain. Calibration is required for supported printer/pen/camera combinations.

## Safety behavior

A scan missing any registration marker fails recognition instead of using guessed coordinates. Multiple and uncertain marks do not receive an automatic score. Reprocessing/version history, confidence calibration, and a visual original/overlay review are production-hardening items.
