import sys
from pathlib import Path

from app.celery_app import celery_app


def _ensure_api_package_path() -> None:
    """Allow importing `app.services.*` when running from `services/worker`."""
    import app as root_app

    api_root = Path(__file__).resolve().parents[3] / "services" / "api"
    api_app = api_root / "app"
    if api_root.is_dir() and str(api_root) not in sys.path:
        sys.path.append(str(api_root))
    if api_app.is_dir() and hasattr(root_app, "__path__"):
        api_app_str = str(api_app)
        if api_app_str not in root_app.__path__:
            root_app.__path__.append(api_app_str)


@celery_app.task(name="omr.health_check")
def health_check() -> str:
    """Minimal task for validating worker connectivity in local development."""
    return "worker-ok"


@celery_app.task(name="omr.process_scan", bind=True, max_retries=2, default_retry_delay=5)
def process_scan(self, scan_id: str) -> dict[str, str]:
    """Execute the OMR recognition & evaluation pipeline for one queued Scan record."""
    normalized_id = (scan_id or "").strip()
    if not normalized_id:
        raise ValueError("scan_id must be a non-empty string")

    _ensure_api_package_path()
    from app.services.processing import process_scan_record

    try:
        process_scan_record(normalized_id)
    except Exception as exc:
        if getattr(self.request, "retries", 0) < self.max_retries:
            raise self.retry(exc=exc)
        raise

    return {"status": "processed", "scan_id": normalized_id}
