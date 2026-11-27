# ADR 0002: Use normalized template coordinates

- **Status:** Accepted
- **Date:** 2026-11-27

## Context

The same sheet may be captured at different resolutions, scanner DPI settings, and camera distances. Pixel coordinates tied to a single raster size are fragile.

## Decision

Store field and bubble geometry as normalized fractions of a canonical page after registration-marker alignment. Page size and orientation are explicit in each immutable template version.

## Consequences

Benefits: geometry maps across raster resolutions and generated PDFs share the same coordinate contract as recognition.

Trade-offs: marker detection and perspective correction must be reliable; print scaling and non-uniform distortion still require checks; schema changes require a new version.

Do not assume the scanned page's aspect ratio is correct until alignment and page-quality checks pass.
