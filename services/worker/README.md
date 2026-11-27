# Optional distributed worker

The first working MVP uses FastAPI background tasks to keep local setup simple. This Celery/Redis scaffold is reserved for a production queue migration when retry semantics, higher volume, or independent worker autoscaling are implemented.

Do not switch the API to Celery until task payloads are idempotent, tenant authorization is rechecked by workers, and retry/dead-letter behavior is tested.
