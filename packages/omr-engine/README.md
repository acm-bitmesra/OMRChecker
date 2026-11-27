# OMR engine

Python package for deterministic image measurements, bubble classification, and scoring primitives.

## Current foundation
- Typed outcomes: blank, single, multiple, uncertain.
- Calibrated-threshold bubble classification helper.
- Pure scoring function with positive, negative, and blank marks.
- Unit tests for deterministic primitives.

## Planned modules
- Image decode and PDF rasterization.
- Sheet quality checks.
- Registration marker detection and perspective correction.
- Normalization and illumination compensation.
- Template-driven bubble ROI extraction.
- Fill measurement and calibrated classification.
- Diagnostic overlays and golden-dataset evaluation.

This package does not yet implement a complete OMR pipeline. Do not use these primitives to grade real examinations without integration, calibration, and validation.
