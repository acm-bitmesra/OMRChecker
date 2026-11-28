import sys
from pathlib import Path

import pytest

import app as root_app

_WORKER_ROOT = Path(__file__).resolve().parents[1]
_WORKER_APP = _WORKER_ROOT / "app"
if str(_WORKER_ROOT) not in sys.path:
    sys.path.append(str(_WORKER_ROOT))
if hasattr(root_app, "__path__") and str(_WORKER_APP) not in root_app.__path__:
    root_app.__path__.append(str(_WORKER_APP))

from app.tasks import health_check, process_scan  # noqa: E402


def test_health_check_task_returns_ok() -> None:
    assert health_check() == "worker-ok"


def test_process_scan_rejects_empty_scan_id() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        process_scan("   ")


def test_process_scan_delegates_to_processing_service(monkeypatch) -> None:
    called: list[str] = []
    monkeypatch.setattr(
        "app.services.processing.process_scan_record",
        lambda scan_id: called.append(scan_id),
    )

    result = process_scan("scan-123")
    assert called == ["scan-123"]
    assert result == {"status": "processed", "scan_id": "scan-123"}
