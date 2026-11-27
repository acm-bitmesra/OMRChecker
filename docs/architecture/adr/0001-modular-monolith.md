# ADR 0001: Start with a modular monolith

- **Status:** Accepted
- **Date:** 2026-11-27

## Context

The product needs a web UI, API, database, and CPU-intensive image processing. Early development benefits from simple local setup and shared domain contracts, while OMR jobs may need independent scaling.

## Decision

Use a modular FastAPI application for domain APIs and a separate Celery worker process for asynchronous recognition and export tasks. Keep frontend, API, worker, and reusable Python packages in one repository.

## Consequences

Benefits: small initial operational footprint, clear domain boundaries, reusable engine package, and independent worker scaling.

Trade-offs: package boundaries must be maintained deliberately; API and worker share models and database contracts; extracting services later requires explicit event/API contracts.

Revisit when separate teams, independent deployment, or measured load justify more services.
