# Phone and scanner capture

## Input paths

### Flatbed/document scanner
- Accept multipage PDF and supported raster formats.
- Prefer consistent DPI and avoid destructive scanner enhancement.
- Validate orientation, page size, cropping, and page count.
- Keep source bytes unchanged.

### Phone camera (browser capture implemented)
- Open the camera from the scan form after an explicit user gesture.
- Prefer the environment-facing camera, request a high-resolution preview, and provide a visible page guide.
- Capture one JPEG frame and hand it to the same upload/evaluation pipeline as a scanner image.
- Provide basic frame-size and average-brightness guidance; the operator must still inspect the entire page and all four registration markers.
- Stop camera tracks when the capture panel closes or unmounts.
- Browser camera access requires a secure context (HTTPS or localhost) and user permission.
- This workflow does not yet detect page boundaries, measure focus, correct perspective in the browser, or work offline. Server-side OMR alignment remains authoritative.
- Continuous capture and retryable offline uploads remain future work.

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
