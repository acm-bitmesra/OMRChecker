"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { CameraCapture } from "./components/CameraCapture";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

type Exam = {
  id: string;
  name: string;
  description: string;
  total_questions: number;
  options: string[];
  correct_marks: number;
  incorrect_marks: number;
  blank_marks: number;
  has_answer_key: boolean;
};

type Detection = {
  state: "single" | "blank" | "multiple" | "uncertain";
  selected_options: string[];
  fill_ratios: Record<string, number>;
};

type Scan = {
  id: string;
  exam_id: string;
  student_id: string;
  student_name: string;
  original_filename: string;
  page_number: number;
  status: string;
  detections?: { questions: Record<string, Detection>; engine: string };
  approved_answers?: Record<string, string | null>;
  result?: {
    correct: number;
    incorrect: number;
    unattempted: number;
    score: number;
    maximum_score: number;
    percentage: number;
  };
  error_message: string;
};

type ExamAnalytics = {
  total_scans: number;
  evaluated: number;
  average_score: number | null;
  min_score: number | null;
  max_score: number | null;
  question_stats: Array<{
    question: string;
    attempts: number;
    correct: number;
    incorrect: number;
    blank: number;
    accuracy: number;
  }>;
};

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, init);
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = body?.detail;
    throw new Error(typeof detail === "string" ? detail : detail?.message ?? `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export default function HomePage() {
  const [exams, setExams] = useState<Exam[]>([]);
  const [selectedExamId, setSelectedExamId] = useState("");
  const [scans, setScans] = useState<Scan[]>([]);
  const [selectedScan, setSelectedScan] = useState<Scan | null>(null);
  const [reviewValues, setReviewValues] = useState<Record<string, string>>({});
  const [examName, setExamName] = useState("");
  const [questionCount, setQuestionCount] = useState(50);
  const [optionCount, setOptionCount] = useState(4);
  const [correctMarks, setCorrectMarks] = useState(4);
  const [incorrectMarks, setIncorrectMarks] = useState(-1);
  const [blankMarks, setBlankMarks] = useState(0);
  const [analytics, setAnalytics] = useState<ExamAnalytics | null>(null);
  const [previewAvailable, setPreviewAvailable] = useState(true);
  const [studentId, setStudentId] = useState("");
  const [studentName, setStudentName] = useState("");
  const [sheetStudentId, setSheetStudentId] = useState("");
  const [sheetStudentName, setSheetStudentName] = useState("");
  const [reviewStudentId, setReviewStudentId] = useState("");
  const [reviewStudentName, setReviewStudentName] = useState("");
  const [answerKeyText, setAnswerKeyText] = useState("");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [cameraOpen, setCameraOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const selectedExam = useMemo(
    () => exams.find((exam) => exam.id === selectedExamId) ?? null,
    [exams, selectedExamId],
  );

  const loadExams = useCallback(async () => {
    const data = await api<Exam[]>("/exams");
    setExams(data);
    setSelectedExamId((current) => current || data[0]?.id || "");
  }, []);

  const loadScans = useCallback(async (examId: string) => {
    if (!examId) {
      setScans([]);
      setAnalytics(null);
      return;
    }
    const data = await api<Scan[]>(`/exams/${examId}/scans`);
    setScans(data);
    try {
      const stats = await api<ExamAnalytics>(`/exams/${examId}/analytics`);
      setAnalytics(stats);
    } catch {
      setAnalytics(null);
    }
  }, []);

  useEffect(() => {
    let active = true;
    api<Exam[]>("/exams")
      .then((data) => {
        if (!active) return;
        setExams(data);
        setSelectedExamId((current) => current || data[0]?.id || "");
      })
      .catch((err: Error) => {
        if (active) setError(err.message);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!selectedExamId) return;
    let active = true;
    const refresh = () => {
      loadScans(selectedExamId).catch((err: Error) => {
        if (active) setError(err.message);
      });
    };
    const initialTimer = window.setTimeout(refresh, 0);
    const timer = window.setInterval(() => {
      loadScans(selectedExamId).catch(() => undefined);
    }, 4000);
    return () => {
      active = false;
      window.clearTimeout(initialTimer);
      window.clearInterval(timer);
    };
  }, [selectedExamId, loadScans]);

  async function createExam(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    const optionLabels = ["A", "B", "C", "D"].slice(0, optionCount);
    try {
      const exam = await api<Exam>("/exams", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: examName,
          total_questions: questionCount,
          options: optionLabels,
          correct_marks: correctMarks,
          incorrect_marks: incorrectMarks,
          blank_marks: blankMarks,
        }),
      });
      await loadExams();
      setSelectedExamId(exam.id);
      setExamName("");
      setNotice("Examination created. Download its printable OMR sheet next.");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function saveAnswerKey() {
    if (!selectedExam) return;
    const allowedOptions = new Set(selectedExam.options.map((opt) => opt.toUpperCase()));
    const answers: Record<string, string> = {};
    for (const line of answerKeyText.split("\n")) {
      const match = line.trim().match(/^(\d+)\s*[:,-]\s*([A-Za-z0-9]+)$/i);
      if (match) {
        const option = match[2].toUpperCase();
        if (allowedOptions.has(option)) {
          answers[match[1]] = option;
        }
      }
    }
    if (Object.keys(answers).length !== selectedExam.total_questions) {
      setError(
        `Enter one valid answer (${selectedExam.options.join("/")}) for all ${selectedExam.total_questions} questions, e.g. 1:A.`,
      );
      return;
    }
    setBusy(true);
    setError("");
    try {
      await api(`/exams/${selectedExam.id}/answer-key`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ answers }),
      });
      await loadExams();
      await loadScans(selectedExam.id);
      setNotice("Answer key saved. Eligible scans have been evaluated.");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function uploadScan(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedExam || !uploadFile) return;
    setBusy(true);
    setError("");
    const form = new FormData();
    form.append("file", uploadFile);
    form.append("student_id", studentId);
    form.append("student_name", studentName);
    try {
      const response = await api<{ scans: Scan[] }>(`/exams/${selectedExam.id}/scans`, {
        method: "POST",
        body: form,
      });
      setUploadFile(null);
      setStudentId("");
      setStudentName("");
      await loadScans(selectedExam.id);
      setNotice(`Accepted ${response.scans.length} page(s). Recognition is running; ambiguous marks will appear in Review.`);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function downloadStudentSheet() {
    if (!selectedExam || !sheetStudentId.trim()) {
      setError("Enter a student ID before creating a personalized sheet.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const response = await fetch(`${API}/exams/${selectedExam.id}/student-sheets`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ student_id: sheetStudentId.trim(), student_name: sheetStudentName.trim() }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail ?? `Request failed (${response.status})`);
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `omr-${sheetStudentId.trim().replace(/[^a-zA-Z0-9_-]/g, "-")}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      setNotice("Personalized QR answer sheet generated. The scanned page will be matched to this candidate.");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function openReview(scan: Scan) {
    try {
      const detail = await api<Scan>(`/scans/${scan.id}`);
      const values: Record<string, string> = {};
      for (const [number, detection] of Object.entries(detail.detections?.questions ?? {})) {
        if (detection.state === "single") values[number] = detection.selected_options[0] ?? "__review__";
        else if (detection.state === "blank") values[number] = "__blank__";
        else values[number] = "__review__";
      }
      setReviewValues(values);
      setReviewStudentId(detail.student_id ?? "");
      setReviewStudentName(detail.student_name ?? "");
      setPreviewAvailable(true);
      setSelectedScan(detail);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function reprocessScan(scanId: string) {
    if (!selectedExam) return;
    setBusy(true);
    setError("");
    try {
      await api(`/scans/${scanId}/reprocess`, { method: "POST" });
      await loadScans(selectedExam.id);
      setNotice("Scan re-queued for OMR recognition.");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function deleteSelectedExam() {
    if (!selectedExam) return;
    if (!window.confirm(`Delete examination "${selectedExam.name}" and all its scans?`)) {
      return;
    }
    setBusy(true);
    setError("");
    try {
      await api(`/exams/${selectedExam.id}`, { method: "DELETE" });
      setSelectedScan(null);
      setSelectedExamId("");
      await loadExams();
      setNotice("Examination deleted.");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function saveReview() {
    if (!selectedScan || !selectedExam) return;
    if (!reviewStudentId.trim()) {
      setError("Enter the candidate's student ID before finalizing this result.");
      return;
    }
    const answers: Record<string, string | null> = {};
    for (let q = 1; q <= selectedExam.total_questions; q += 1) {
      const value = reviewValues[String(q)] ?? "__review__";
      if (value === "__review__") {
        setError(`Choose an answer or mark blank for question ${q} before saving.`);
        return;
      }
      answers[String(q)] = value === "__blank__" ? null : value;
    }
    setBusy(true);
    setError("");
    try {
      const updated = await api<Scan>(`/scans/${selectedScan.id}/review`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          answers,
          student_id: reviewStudentId.trim(),
          student_name: reviewStudentName.trim(),
        }),
      });
      setSelectedScan(updated);
      await loadScans(selectedExam.id);
      setNotice("Reviewed responses saved and score recalculated.");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function downloadTemplate() {
    if (selectedExam) window.open(`${API}/exams/${selectedExam.id}/template.pdf`, "_blank", "noopener,noreferrer");
  }

  const statusLabel = (status: string) => status.replaceAll("_", " ");

  return (
    <main className="app-shell">
      <header className="topbar">
        <Link className="brand" href="/">
          <span className="brand-icon">O</span>
          <span>OMR Checker</span>
        </Link>
        <span className="topbar-note">ACM BIT Mesra · Examination workspace</span>
      </header>

      <section className="hero">
        <div className="eyebrow">SCAN · RECOGNIZE · REVIEW · EVALUATE</div>
        <h1>Exams, evaluated<br /><span>with confidence.</span></h1>
        <p>Create printable OMR sheets, scan them with a phone or document scanner, and review uncertain marks before publishing scores.</p>
        <div className="hero-meta"><span className="pulse" /> Local MVP · OpenCV recognition · Human review</div>
      </section>

      {(error || notice) && (
        <div className={error ? "alert error" : "alert success"} role="status">
          {error || notice}
          <button className="alert-close" onClick={() => { setError(""); setNotice(""); }} aria-label="Dismiss">×</button>
        </div>
      )}

      <section className="workspace">
        <aside className="sidebar">
          <div className="section-label">WORKSPACE</div>
          <label className="field-label" htmlFor="exam-select">Selected examination</label>
          <select id="exam-select" value={selectedExamId} onChange={(event) => { setSelectedExamId(event.target.value); setSelectedScan(null); }} disabled={!exams.length}>
            {!exams.length && <option value="">No examinations yet</option>}
            {exams.map((exam) => <option key={exam.id} value={exam.id}>{exam.name}</option>)}
          </select>

          <form className="panel-form" onSubmit={createExam}>
            <div className="section-label">NEW EXAMINATION</div>
            <label className="field-label" htmlFor="exam-name">Exam name</label>
            <input id="exam-name" value={examName} onChange={(event) => setExamName(event.target.value)} placeholder="e.g. Mathematics Midterm" minLength={2} required />
            <div className="form-grid">
              <div>
                <label className="field-label" htmlFor="question-count">Questions (1–100)</label>
                <input id="question-count" type="number" min={1} max={100} value={questionCount} onChange={(event) => setQuestionCount(Number(event.target.value))} required />
              </div>
              <div>
                <label className="field-label" htmlFor="option-count">Options</label>
                <select id="option-count" value={optionCount} onChange={(event) => setOptionCount(Number(event.target.value))}>
                  <option value={2}>2 (A–B)</option>
                  <option value={3}>3 (A–C)</option>
                  <option value={4}>4 (A–D)</option>
                </select>
              </div>
            </div>
            <div className="marking-grid">
              <div>
                <label className="field-label" htmlFor="correct-marks">Correct</label>
                <input id="correct-marks" type="number" step="0.25" min={0.25} max={100} value={correctMarks} onChange={(event) => setCorrectMarks(Number(event.target.value))} required />
              </div>
              <div>
                <label className="field-label" htmlFor="incorrect-marks">Wrong</label>
                <input id="incorrect-marks" type="number" step="0.25" min={-100} max={100} value={incorrectMarks} onChange={(event) => setIncorrectMarks(Number(event.target.value))} required />
              </div>
              <div>
                <label className="field-label" htmlFor="blank-marks">Blank</label>
                <input id="blank-marks" type="number" step="0.25" min={-100} max={100} value={blankMarks} onChange={(event) => setBlankMarks(Number(event.target.value))} required />
              </div>
            </div>
            <button className="button primary full" type="submit" disabled={busy}>{busy ? "Working…" : "Create examination"}</button>
          </form>

          {selectedExam && (
            <div className="exam-settings">
              <div className="section-label">EXAM SETTINGS</div>
              <div className="mini-stat"><span>Questions</span><strong>{selectedExam.total_questions}</strong></div>
              <div className="mini-stat"><span>Options</span><strong>{selectedExam.options.join(" · ")}</strong></div>
              <div className="mini-stat"><span>Marking</span><strong>+{selectedExam.correct_marks} / {selectedExam.incorrect_marks} / {selectedExam.blank_marks}</strong></div>
              <button className="button secondary full" onClick={downloadTemplate}>↓ Download generic OMR sheet</button>
              <div className="personal-sheet">
                <div className="section-label">PERSONALIZED SHEET</div>
                <label className="field-label" htmlFor="sheet-student-id">Student ID / roll number</label>
                <input id="sheet-student-id" value={sheetStudentId} onChange={(event) => setSheetStudentId(event.target.value)} placeholder="e.g. BIT-2026-001" />
                <label className="field-label" htmlFor="sheet-student-name">Student name</label>
                <input id="sheet-student-name" value={sheetStudentName} onChange={(event) => setSheetStudentName(event.target.value)} placeholder="Candidate name" />
                <button className="button secondary full" onClick={downloadStudentSheet} disabled={busy || !sheetStudentId.trim()}>↓ Generate QR answer sheet</button>
                <p className="helper">Each PDF contains an opaque QR token linked to this candidate. Mixed-student PDF batches can be scanned together.</p>
              </div>
              <a className="export-link" href={`${API}/exams/${selectedExam.id}/results.csv`} target="_blank" rel="noreferrer">Export evaluated results ↗</a>
              <button className="button ghost danger full" type="button" onClick={deleteSelectedExam} disabled={busy}>Delete examination</button>
            </div>
          )}
        </aside>

        <div className="main-column">
          {selectedExam ? (
            <>
              <div className="section-heading">
                <div><div className="section-label">OVERVIEW</div><h2>{selectedExam.name}</h2></div>
                <span className={selectedExam.has_answer_key ? "key-state ready" : "key-state"}>{selectedExam.has_answer_key ? "Answer key ready" : "Answer key needed"}</span>
              </div>

              <div className="metrics">
                <div className="metric-card"><span>Total sheets</span><strong>{scans.length}</strong></div>
                <div className="metric-card"><span>Evaluated</span><strong>{scans.filter((scan) => scan.status === "evaluated").length}</strong></div>
                <div className="metric-card"><span>Needs review</span><strong>{scans.filter((scan) => scan.status === "needs_review").length}</strong></div>
                <div className="metric-card"><span>Processing</span><strong>{scans.filter((scan) => ["queued", "processing"].includes(scan.status)).length}</strong></div>
              </div>

              <div className="content-card">
                <div className="card-head"><div><div className="section-label">STEP 01</div><h3>Set the answer key</h3></div><span className="step-number">01</span></div>
                <p className="helper">Enter one answer per line using the format <code>1:A</code>. Every question needs an answer.</p>
                <textarea value={answerKeyText} onChange={(event) => setAnswerKeyText(event.target.value)} placeholder={"1:A\n2:C\n3:B\n4:D"} rows={5} />
                <div className="form-footer"><span className="muted">Scoring: +{selectedExam.correct_marks} correct · {selectedExam.incorrect_marks} incorrect · {selectedExam.blank_marks} blank</span><button className="button primary" onClick={saveAnswerKey} disabled={busy}>Save answer key</button></div>
              </div>

              <div className="content-card">
                <div className="card-head"><div><div className="section-label">STEP 02</div><h3>Scan answer sheets</h3></div><span className="step-number">02</span></div>
                <p className="helper">Upload a PNG, JPG or multipage PDF. For PDFs, each page is processed as one answer sheet. Enter the candidate ID/name for the uploaded file.</p>
                <form onSubmit={uploadScan}>
                  <div className="form-grid">
                    <div><label className="field-label" htmlFor="student-id">Student ID / roll number</label><input id="student-id" value={studentId} onChange={(event) => setStudentId(event.target.value)} placeholder="e.g. 2201001" /></div>
                    <div><label className="field-label" htmlFor="student-name">Student name</label><input id="student-name" value={studentName} onChange={(event) => setStudentName(event.target.value)} placeholder="Candidate name" /></div>
                  </div>
                  <button className="button secondary camera-open-button" type="button" onClick={() => setCameraOpen(true)}>
                    Open phone camera
                  </button>
                  {cameraOpen && (
                    <CameraCapture
                      onClose={() => setCameraOpen(false)}
                      onCapture={(file, warning) => {
                        setUploadFile(file);
                        setCameraOpen(false);
                        setNotice(warning || "Photo captured. Review the selected image before uploading.");
                      }}
                    />
                  )}
                  <label className="upload-zone">
                    <input type="file" accept=".png,.jpg,.jpeg,.pdf,image/png,image/jpeg,application/pdf" onChange={(event) => setUploadFile(event.target.files?.[0] ?? null)} />
                    <span className="upload-icon">↑</span>
                    <strong>{uploadFile ? uploadFile.name : "Choose a scan or drop it here"}</strong>
                    <span>PNG, JPG or PDF · Up to 20 MB</span>
                  </label>
                  <div className="form-footer"><span className="muted">Tip: keep all four registration markers visible.</span><button className="button primary" type="submit" disabled={busy || !uploadFile}>{busy ? "Uploading…" : "Upload & evaluate"}</button></div>
                </form>
              </div>

              <div className="content-card">
                <div className="card-head"><div><div className="section-label">STEP 03</div><h3>Scanned sheets</h3></div><button className="button ghost" onClick={() => loadScans(selectedExam.id)}>Refresh ↻</button></div>
                {scans.length ? (
                  <div className="scan-list">
                    {scans.map((scan) => (
                      <div className="scan-row" key={scan.id}>
                        <div className="scan-file-icon">▤</div>
                        <div className="scan-info">
                          <strong>{scan.student_name || scan.student_id || scan.original_filename}</strong>
                          <span>{scan.student_id ? `ID ${scan.student_id} · ` : ""}{scan.original_filename} · page {scan.page_number}</span>
                        </div>
                        <span className={`status status-${scan.status}`}>{statusLabel(scan.status)}</span>
                        <div className="scan-score">{scan.result ? `${scan.result.score} / ${scan.result.maximum_score}` : "—"}</div>
                        {["needs_review", "failed", "awaiting_key"].includes(scan.status) && (
                          <button className="button ghost small" type="button" onClick={() => reprocessScan(scan.id)} disabled={busy}>Reprocess</button>
                        )}
                        {["needs_review", "failed", "awaiting_key", "evaluated"].includes(scan.status) && (
                          <button className="button small secondary" type="button" onClick={() => openReview(scan)}>{scan.status === "needs_review" ? "Review" : "Inspect"}</button>
                        )}
                      </div>
                    ))}
                  </div>
                ) : <div className="empty-state"><span>▤</span><strong>No sheets uploaded yet</strong><p>Upload your first completed OMR sheet to see recognition results here.</p></div>}
              </div>

              {analytics && analytics.evaluated > 0 && (
                <div className="content-card">
                  <div className="card-head"><div><div className="section-label">ANALYTICS</div><h3>Score &amp; question breakdown</h3></div><span className="muted">Avg {analytics.average_score ?? "—"} · Range {analytics.min_score ?? "—"}–{analytics.max_score ?? "—"}</span></div>
                  <div className="analytics-grid">
                    {analytics.question_stats.slice(0, 20).map((item) => (
                      <div className="analytics-pill" key={item.question}>
                        <span>Q{item.question}</span>
                        <strong>{Math.round(item.accuracy * 100)}%</strong>
                        <small>{item.correct}✓ {item.incorrect}✗ {item.blank}–</small>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {selectedScan && (
                <div className="content-card review-card">
                  <div className="card-head"><div><div className="section-label">MANUAL REVIEW</div><h3>Confirm detected responses</h3></div><button className="button ghost" onClick={() => setSelectedScan(null)}>Close ×</button></div>
                  <p className="helper">Clear single marks and blanks are prefilled. Resolve every item marked “Choose…” before saving.</p>
                  {selectedScan.error_message && <div className="alert error">{selectedScan.error_message}</div>}
                  {previewAvailable && (
                    <div className="scan-preview-wrap">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        className="scan-preview"
                        src={`${API}/scans/${selectedScan.id}/image`}
                        alt={`Scanned answer sheet for ${selectedScan.student_id || selectedScan.original_filename}`}
                        onError={() => setPreviewAvailable(false)}
                      />
                    </div>
                  )}
                  <div className="form-grid">
                    <div><label className="field-label" htmlFor="review-student-id">Student ID / roll number</label><input id="review-student-id" value={reviewStudentId} onChange={(event) => setReviewStudentId(event.target.value)} placeholder="Required to finalize result" /></div>
                    <div><label className="field-label" htmlFor="review-student-name">Student name</label><input id="review-student-name" value={reviewStudentName} onChange={(event) => setReviewStudentName(event.target.value)} placeholder="Candidate name" /></div>
                  </div>
                  <div className="review-grid">
                    {Array.from({ length: selectedExam.total_questions }, (_, index) => {
                      const q = String(index + 1);
                      const detection = selectedScan.detections?.questions?.[q];
                      const ratioText = detection?.fill_ratios
                        ? Object.entries(detection.fill_ratios)
                            .map(([opt, val]) => `${opt}:${Math.round(val * 100)}%`)
                            .join(" ")
                        : "";
                      return (
                        <label className="review-item" key={q}>
                          <span>Q{q}</span>
                          <select value={reviewValues[q] ?? "__review__"} onChange={(event) => setReviewValues((current) => ({ ...current, [q]: event.target.value }))}>
                            <option value="__review__">Choose…</option>
                            <option value="__blank__">Blank</option>
                            {selectedExam.options.map((option) => <option key={option} value={option}>{option}</option>)}
                          </select>
                          <small title={ratioText}>{detection?.state ?? "not detected"}{ratioText ? ` · ${ratioText}` : ""}</small>
                        </label>
                      );
                    })}
                  </div>
                  <div className="form-footer"><span className="muted">Changes are recorded as approved responses and scores are recalculated.</span><button className="button primary" onClick={saveReview} disabled={busy}>Save reviewed answers</button></div>
                  {selectedScan.result && <div className="result-banner"><strong>{selectedScan.result.score} / {selectedScan.result.maximum_score}</strong><span>{selectedScan.result.percentage}% · {selectedScan.result.correct} correct · {selectedScan.result.incorrect} incorrect · {selectedScan.result.unattempted} blank</span></div>}
                </div>
              )}
            </>
          ) : (
            <div className="content-card empty-workspace"><div className="empty-state"><span>✳</span><strong>Create your first examination</strong><p>Start with an exam, generate a printable sheet, and upload completed responses.</p></div></div>
          )}
        </div>
      </section>

      <footer className="footer">OMR Checker · A dependable workflow from paper to results. Recognition thresholds must be calibrated for production exams.</footer>
    </main>
  );
}
