# OMR Checker

> Create, scan, recognize, review, and evaluate OMR answer sheets using a scanner or a phone camera.

OMR Checker is an ACM BIT Mesra project for examination teams, schools, colleges, coaching institutes, and event organizers. The product is designed around **standardized printable templates, deterministic computer vision, transparent scoring, and human review for uncertain marks**.

## Project status

**Foundation scaffold.** This commit establishes product requirements, architecture, engineering contracts, and starter services. It is not yet a production-ready OMR application. Full recognition, authentication, database persistence, PDF generation, phone scanning, and exports remain implementation milestones.

## Product workflow

1. Create an exam; configure sections, options, paper sets, and marking rules.
2. Generate a versioned printable template with registration markers and a sheet identifier.
3. Capture sheets using a phone camera or scanner, or upload a multipage PDF.
4. Align each page and measure bubble fill using OpenCV.
5. Route uncertain, multiple-mark, or low-quality responses to examiner review.
6. Evaluate approved responses against a versioned answer key.
7. Publish analytics and export CSV, XLSX, or PDF reports.

## Stack

| Layer | Initial choice |
| --- | --- |
| Web | Next.js App Router, React, TypeScript |
| API | FastAPI, Pydantic |
| Recognition | Python, OpenCV, NumPy |
| Jobs | Celery, Redis |
| Database | PostgreSQL, SQLAlchemy, Alembic |
| Object storage | Cloudflare R2 / S3-compatible storage |
| Deployment | Docker; web, API, and workers deployed independently |

## Repository layout

```text
apps/web/                    Next.js examiner and admin UI
services/api/                FastAPI application
services/worker/             Asynchronous processing workers
packages/omr-engine/          Recognition and scoring primitives
packages/template-engine/    Versioned template models and generation boundary
docs/                        Product, architecture, data, security and operations
tests/                        Cross-service and golden-dataset strategy
infra/                        Local development infrastructure
```

## Local development

Prerequisites: Python 3.12+, Node.js 22+, pnpm, and Docker Compose.

1. Copy `.env.example` to `.env` and review all values.
2. Start dependencies: `docker compose up -d postgres redis`.
3. API: from `services/api`, run `pip install -e .` then `uvicorn app.main:app --reload`.
4. Worker: from `services/worker`, run `pip install -e .` then `celery -A app.celery_app.celery_app worker --loglevel=INFO`.
5. Web: from `apps/web`, run `pnpm install && pnpm dev`.

API health check: `GET /api/v1/health`. The web page and worker task are starter scaffolds; core product routes and workflows are subsequent milestones.

## Engineering principles

- Uncertain recognition must be reviewed; never silently guess.
- Preserve original uploads and record processing metadata.
- Version templates, answer keys, scoring rules, and recognition engines.
- Keep deterministic scoring separate from image recognition.
- Enforce organization-level data isolation.
- Publish accuracy and throughput only after representative ground-truth testing.

## Documentation

Start at [docs/README.md](docs/README.md). Key documents: [PRD](docs/product/PRD.md), [architecture](docs/architecture/overview.md), [recognition pipeline](docs/architecture/omr-pipeline.md), [database model](docs/data/database-schema.md), [template format](docs/omr/template-format.md), [security](docs/security/privacy.md), [testing](docs/testing/strategy.md), and [roadmap](docs/roadmap/implementation-plan.md).

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md). Security issues should be reported privately as described in [SECURITY.md](SECURITY.md).

Maintained by the ACM BIT Mesra community. Initial repository foundation authored through [@SH20RAJ](https://github.com/SH20RAJ).
