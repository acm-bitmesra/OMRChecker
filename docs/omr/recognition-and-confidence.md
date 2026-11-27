# Recognition, classification, and confidence

## Core rule

The OMR engine measures marks; it does not decide examination policy. It returns evidence and a recognition state. Evaluation applies the answer key and marking rules only after responses are approved.

## Bubble measurement

A basic metric is:

`fill_ratio = dark_pixels / sampled_pixels`

Use an inset region to avoid counting printed outlines. Store the measurement method and calibration profile.

## Question states

| State | Meaning | Default action |
| --- | --- | --- |
| blank | No option crosses calibrated fill threshold | Accept as blank only when page quality is valid |
| single | One option crosses threshold confidently | Candidate response |
| multiple | More than one option crosses threshold | Review or configured multiple-mark policy |
| uncertain | Quality or measurement is ambiguous | Human review |

## Confidence is not correctness

A high-confidence detection means the signal is clear under the current calibration; it does not prove intent. Track recognition confidence separately from scoring correctness. Do not claim a confidence percentage as a measure of accuracy unless calibrated against representative data.

## Calibration protocol
- Capture representative samples from supported printers, paper, pen/pencil, and input modes.
- Label bubble states independently.
- Select thresholds on calibration data and evaluate on held-out samples.
- Report precision, recall, false acceptance, and review rate.
- Recalibrate after preprocessing, geometry, or print-profile changes.

## Review evidence

Show aligned/source crop, option labels, fill measurements, detected state/reason, student ID, editable response, explicit confirmation, and correction history.

## Algorithm changes

Every release has an engine version. Reprocessing creates a new attempt and preserves previous evidence. Finalized results require an explicit revision workflow.
