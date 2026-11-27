"use client";

import { useEffect, useRef, useState } from "react";

type CameraCaptureProps = {
  onCapture: (file: File, qualityNotice: string) => void;
  onClose: () => void;
};

function getCameraError(error: unknown): string {
  if (error instanceof DOMException) {
    if (error.name === "NotAllowedError" || error.name === "PermissionDeniedError") {
      return "Camera access was denied. Allow camera access in your browser settings and try again.";
    }
    if (error.name === "NotFoundError" || error.name === "DevicesNotFoundError") {
      return "No camera was found on this device.";
    }
    if (error.name === "NotReadableError" || error.name === "TrackStartError") {
      return "The camera is busy in another application. Close that app and try again.";
    }
  }
  return "Could not start the camera. Use a secure HTTPS page or localhost, check browser permissions, and retry.";
}

export function CameraCapture({ onCapture, onClose }: CameraCaptureProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [error, setError] = useState("");
  const [capturing, setCapturing] = useState(false);

  useEffect(() => {
    let active = true;
    let localStream: MediaStream | null = null;

    async function startCamera() {
      if (!navigator.mediaDevices?.getUserMedia) {
        setError("Camera capture requires HTTPS (or localhost) and a browser with camera support.");
        return;
      }

      try {
        localStream = await navigator.mediaDevices.getUserMedia({
          audio: false,
          video: {
            facingMode: { ideal: "environment" },
            width: { ideal: 1920 },
            height: { ideal: 2560 },
          },
        });

        if (!active) {
          localStream.getTracks().forEach((track) => track.stop());
          return;
        }

        streamRef.current = localStream;
        const video = videoRef.current;
        if (video) {
          video.srcObject = localStream;
          await video.play();
        }
      } catch (cameraError) {
        if (active) setError(getCameraError(cameraError));
      }
    }

    void startCamera();

    return () => {
      active = false;
      localStream?.getTracks().forEach((track) => track.stop());
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
      if (videoRef.current) videoRef.current.srcObject = null;
    };
  }, []);

  async function capturePhoto() {
    const video = videoRef.current;
    if (!video || video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
      setError("The camera preview is not ready yet. Wait a moment and try again.");
      return;
    }

    const width = video.videoWidth;
    const height = video.videoHeight;
    if (!width || !height) {
      setError("The camera did not provide a usable frame. Try again or upload a scanner image.");
      return;
    }

    setCapturing(true);
    setError("");
    try {
      const canvas = document.createElement("canvas");
      canvas.width = width;
      canvas.height = height;
      const context = canvas.getContext("2d");
      if (!context) throw new Error("Could not prepare the captured image.");
      context.drawImage(video, 0, 0, width, height);

      const qualityNotes: string[] = [];
      if (Math.min(width, height) < 1200) {
        qualityNotes.push("This camera frame is relatively small; move closer or use a scanner if bubble edges look soft.");
      }

      // Sample brightness sparsely to avoid an expensive full-resolution pass.
      const sample = context.getImageData(0, 0, width, height);
      const stride = Math.max(1, Math.floor(Math.min(width, height) / 300));
      let luminanceTotal = 0;
      let sampleCount = 0;
      for (let y = 0; y < height; y += stride) {
        for (let x = 0; x < width; x += stride) {
          const index = (y * width + x) * 4;
          const luminance =
            0.2126 * sample.data[index] +
            0.7152 * sample.data[index + 1] +
            0.0722 * sample.data[index + 2];
          luminanceTotal += luminance;
          sampleCount += 1;
        }
      }
      const averageLuminance = sampleCount ? luminanceTotal / sampleCount : 128;
      if (averageLuminance < 65) {
        qualityNotes.push("The image appears dark; improve lighting and retake if the bubbles are hard to distinguish.");
      } else if (averageLuminance > 238) {
        qualityNotes.push("The image appears very bright; reduce glare and retake if the page looks washed out.");
      }
      qualityNotes.push("Check that the full page and all four black registration markers are visible before uploading.");

      const blob = await new Promise<Blob>((resolve, reject) => {
        canvas.toBlob(
          (result) => (result ? resolve(result) : reject(new Error("Could not encode the captured photo."))),
          "image/jpeg",
          0.94,
        );
      });
      const file = new File([blob], `omr-camera-${Date.now()}.jpg`, {
        type: "image/jpeg",
        lastModified: Date.now(),
      });
      onCapture(file, qualityNotes.join(" "));
    } catch (captureError) {
      setError(captureError instanceof Error ? captureError.message : "Could not capture this page.");
    } finally {
      setCapturing(false);
    }
  }

  return (
    <section className="camera-panel" role="dialog" aria-label="Phone camera scanner">
      <div className="camera-panel-heading">
        <div>
          <strong>Scan an answer sheet</strong>
          <p>Hold the phone steady and keep all four registration markers inside the frame.</p>
        </div>
        <button className="button ghost" type="button" onClick={onClose}>Close</button>
      </div>

      <div className="camera-frame">
        <video ref={videoRef} autoPlay playsInline muted aria-label="Live camera preview" />
        <div className="camera-guide" aria-hidden="true" />
      </div>

      {error && <div className="alert error" role="alert">{error}</div>}

      <div className="camera-actions">
        <button className="button primary" type="button" onClick={capturePhoto} disabled={capturing || Boolean(error)}>
          {capturing ? "Capturing…" : "Capture page"}
        </button>
        <button className="button secondary" type="button" onClick={onClose}>Cancel</button>
      </div>
      <p className="camera-footnote">Capture is a convenience, not an accuracy guarantee. Review image clarity before submitting the sheet for evaluation.</p>
    </section>
  );
}
