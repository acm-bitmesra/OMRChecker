import os

from fastapi import BackgroundTasks

from app.services.processing import process_scan_record


def _is_truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def enqueue_scan_processing(
    scan_id: str,
    background_tasks: BackgroundTasks | None = None,
) -> str:
    """Dispatch scan processing to Celery when enabled, else local BackgroundTasks."""
    if _is_truthy(os.getenv("USE_CELERY_WORKER")):
        from celery import Celery

        broker_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        client = Celery("omr_checker", broker=broker_url, backend=broker_url)
        client.send_task("omr.process_scan", args=[scan_id])
        return "celery"

    if background_tasks is not None:
        background_tasks.add_task(process_scan_record, scan_id)
        return "background"

    process_scan_record(scan_id)
    return "inline"
