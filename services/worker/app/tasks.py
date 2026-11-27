from app.celery_app import celery_app


@celery_app.task(name="omr.health_check")
def health_check() -> str:
    """Minimal task for validating worker connectivity in local development."""
    return "worker-ok"
