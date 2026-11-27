# Background worker

Celery workers run CPU-heavy recognition and report-generation jobs outside HTTP handlers.

## Run locally

```bash
pip install -e .
celery -A app.celery_app.celery_app worker --loglevel=INFO
```

Only Celery app wiring and a connectivity task are scaffolded. Add idempotent page-processing tasks alongside the API job lifecycle.
