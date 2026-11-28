# OMR Checker

> Create printable OMR sheets, scan them with a phone or document scanner, recognize marked answers, review uncertain responses, and evaluate results.

OMR Checker is an ACM BIT Mesra project. This repository now contains a working **single-operator MVP** with a Next.js examiner dashboard, FastAPI backend, OpenCV/ArUco alignment, bubble recognition, deterministic scoring, manual review, CSV export, and printable A4 templates.

## Current capabilities

- Create examinations with 1–100 questions and 2–4 answer options.
- Configure positive, negative, and blank marking.
- Generate generic and candidate-specific A4 OMR PDFs with four ArUco registration markers.
- Embed an opaque per-candidate QR token in personalized sheets and resolve the candidate automatically during scanning.
- Capture a page from the browser camera on supported phones or upload PNG/JPG/PDF scans; mixed-candidate batches can be identified using personalized QR sheets.
- Align perspective-distorted captures using the registration markers.
- Measure bubble fill ratios and classify answers as blank, single, multiple, or uncertain.
- Require human review for ambiguous and multiple marks.
- Save an answer key and calculate deterministic scores.
- Export evaluated scan records as CSV.
- Review detected responses and override answers in the dashboard.

## Stack

| Layer | Technology |
| --- | --- |
| Web | Next.js, React, TypeScript |
| API | FastAPI, Pydantic |
| Database | SQLAlchemy (SQLite locally; PostgreSQL via `DATABASE_URL`) |
| Recognition | OpenCV contrib ArUco, NumPy |
| PDF | ReportLab generation, PyMuPDF rasterization |
| Background processing | FastAPI background tasks in the MVP; Celery/Redis scaffold for a future queue |
| Infrastructure | Docker Compose for PostgreSQL and Redis |

## Run locally

Prerequisites: Python 3.12+, Node.js 22+, pnpm, and Docker (optional for local PostgreSQL/Redis).

### 1. Install Python packages

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The default database is a local SQLite file and the default upload directory is `./data`. To use PostgreSQL, set `DATABASE_URL` before starting the API, for example:

```bash
export DATABASE_URL='postgresql+psycopg://omr:YOUR_PASSWORD@localhost:5432/omr_checker'
```

### 2. Start the API

```cd services/api
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs  
Health: http://localhost:8000/api/v1/health

### 3. Start the web application

In a second terminal:

```bash
cd apps/web
cp .env.example .env.local
pnpm install
pnpm dev
```

Open http://localhost:3000.

### Quick free deployment (Streamlit Community Cloud)

OMR Checker includes a standalone `streamlit_app.py` and `.streamlit/config.toml` for zero-cost, one-click deployment without separate PostgreSQL, Redis, or Node.js servers:

- **Local launch:** `streamlit run streamlit_app.py`
- **Streamlit Community Cloud:** Connect the repository, keep branch `main` and main file path `streamlit_app.py`, and deploy directly using root `requirements.txt`.

### 4. Create and evaluate an exam

1. Create an exam (up to 100 questions).
2. Generate a personalized QR sheet for each candidate by entering their roll number and name; the QR contains only an opaque random token.
3. Print at 100% scale and do not crop the four registration markers.
4. Mark bubbles clearly using a dark pen.
5. Enter one answer per line in the dashboard, such as `1:A`, and save the complete key.
6. Upload a clear PNG/JPG scan or a multipage PDF. Different personalized candidate sheets can be mixed in one PDF.
7. Wait for recognition. Unknown QR tokens, missing candidate identity, and uncertain or multiple marks appear in Manual Review.
8. Confirm the candidate ID and every unresolved answer. The score is recalculated only after identity and answers are resolved.
9. Export evaluated records as CSV.

## API overview

All endpoints are under `/api/v1`.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/health` | API health |
| GET / POST | `/exams` | List / create exams |
| GET | `/exams/{id}` | Get exam |
| PUT | `/exams/{id}/answer-key` | Save complete answer key |
| GET | `/exams/{id}/template.pdf` | Download generic printable OMR |
| POST | `/exams/{id}/student-sheets` | Generate a QR-linked candidate sheet |
| POST | `/exams/{id}/scans` | Upload image/PDF |
| GET | `/exams/{id}/scans` | List scans |
| GET | `/scans/{id}` | Get one scan |
| PATCH | `/scans/{id}/review` | Save examiner-approved answers |
| GET | `/exams/{id}/results.csv` | Export evaluated results |
| GET | `/exams/{id}/summary` | Scan status summary |

Interactive OpenAPI documentation is available at `/docs`.

## Important accuracy and deployment notes

- Recognition thresholds are initial defaults. Validate and calibrate them with printed samples from supported printers, pens/pencils, scanners, and phone cameras before real exam use.
- The sheet generator currently supports one A4 page with up to 100 questions and up to four options.
- For a multipage PDF, every page is treated as an independent OMR sheet. The candidate ID/name supplied at upload applies to every page in that PDF.
- Browser camera capture requires HTTPS (or localhost) and camera permission. It provides basic resolution/brightness feedback but does not guarantee focus or page alignment; the server remains the recognition authority.
- The current web/API MVP is single-operator and does not yet include production authentication, institution tenancy, S3 storage, offline camera capture, or a distributed queue.
- The local SQLite database and upload directory are for development. Deploy with managed PostgreSQL, private object storage, authentication, retention controls, TLS, backups, and isolated workers before handling real student records.
- Never automatically accept uncertain detections. Human review is intentional.

## Repository documentation

- [Product requirements](docs/product/PRD.md)
- [Architecture](docs/architecture/overview.md)
- [OMR pipeline](docs/architecture/omr-pipeline.md)
- [API design](docs/api/openapi-notes.md)
- [Database model](docs/data/database-schema.md)
- [Template format](docs/omr/template-format.md)
- [Recognition confidence](docs/omr/recognition-and-confidence.md)
- [Phone/scanner capture](docs/scanning/mobile-scanning.md)
- [Security](docs/security/privacy.md)
- [Testing](docs/testing/strategy.md)
- [Roadmap](docs/roadmap/implementation-plan.md)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Report security issues privately as outlined in [SECURITY.md](SECURITY.md).

Maintained by the ACM BIT Mesra community. Initial implementation and repository foundation authored through [@SH20RAJ](https://github.com/SH20RAJ).
