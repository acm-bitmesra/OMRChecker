# Phone and scanner capture

## Input paths

### Flatbed/document scanner
- Accept multipage PDF and supported raster formats.
- Prefer consistent DPI and avoid destructive scanner enhancement.
- Validate orientation, page size, cropping, and page count.
- Keep source bytes unchanged.

### Phone camera (PWA first)
- Request camera permission after a user gesture.
- Show live preview and alignment guide.
- Detect page boundary and perspective; allow manual correction.
- Warn about blur, glare, shadow, clipped corners, and low resolution.
- Offer recapture before upload.
- Use retryable uploads for poor connectivity.
- Add continuous capture only after single-page capture is reliable.

## Capture flow
1. User selects exam and scan batch.
2. Browser requests camera permission.
3. Preview shows alignment guidance.
4. Capture and run lightweight client-side quality checks.
5. User reviews crop and retakes if needed.
6. Upload original capture and register against batch.
7. Worker performs authoritative alignment and recognition.

## Browser notes

`navigator.mediaDevices.getUserMedia()` requires a secure context and permission. Request an environment-facing camera when available, but support camera selection and varying browser constraints. Keep client processing bounded. Browser-side quality/recognition is not the final grading authority.

## Offline and privacy

Offline capture is a later milestone. If implemented, protect locally stored pending images, provide explicit cleanup controls, and never silently retain student scans after batch submission.
