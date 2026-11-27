# Deployment and operations

## Environments
- **Local:** Docker Compose for PostgreSQL and Redis; app processes run locally.
- **Preview:** isolated synthetic data and non-production credentials.
- **Production:** private database and object storage, authenticated API, independent worker, TLS, backups, and monitoring.

## Initial topology
- Next.js frontend on managed web platform or container runtime.
- FastAPI in Docker.
- Celery worker in separate Docker process.
- Managed PostgreSQL and Redis/Valkey.
- Private S3-compatible storage such as Cloudflare R2.
- Error monitoring and metrics, for example Sentry.

## Configuration

See `.env.example`. Production secrets come from the platform secret manager. Never commit a real `.env`.

## Operational controls
- Health/readiness endpoints.
- Structured logs with request/job correlation IDs.
- Queue depth, retry, failure, and processing-duration metrics.
- Database backups and periodic restore tests.
- Object lifecycle and retention rules.
- Worker concurrency limits based on CPU and memory.
- Alerts for sustained backlog, failures, and storage errors.

## Deployment sequence
1. Apply backward-compatible migrations.
2. Deploy compatible API and worker images.
3. Deploy web app.
4. Verify health, queue, storage permissions, and synthetic end-to-end scan.
5. Monitor error rate and queue latency.
6. Roll back application images if necessary; database rollback requires an explicit migration plan.

## Resource and cost safety

Bound upload size, page count, image dimensions, worker concurrency, memory, and processing time. Measure file size, derived artifact volume, CPU time per page, and retention before choosing instance sizes or quoting costs.
