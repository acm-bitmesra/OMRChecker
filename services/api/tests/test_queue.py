from fastapi import BackgroundTasks

from app.services import queue


def test_enqueue_uses_background_tasks_by_default(monkeypatch) -> None:
    monkeypatch.delenv("USE_CELERY_WORKER", raising=False)
    tasks = BackgroundTasks()
    mode = queue.enqueue_scan_processing("scan-abc", tasks)
    assert mode == "background"
    assert len(tasks.tasks) == 1


def test_enqueue_runs_inline_without_background_tasks(monkeypatch) -> None:
    monkeypatch.delenv("USE_CELERY_WORKER", raising=False)
    seen: list[str] = []
    monkeypatch.setattr(queue, "process_scan_record", lambda sid: seen.append(sid))

    mode = queue.enqueue_scan_processing("scan-inline")
    assert mode == "inline"
    assert seen == ["scan-inline"]


def test_enqueue_dispatches_to_celery_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("USE_CELERY_WORKER", "true")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/9")
    dispatched: list[tuple[str, list[str]]] = []

    class FakeCelery:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def send_task(self, name: str, args: list[str]) -> None:
            dispatched.append((name, args))

    monkeypatch.setattr("celery.Celery", FakeCelery)
    mode = queue.enqueue_scan_processing("scan-celery")
    assert mode == "celery"
    assert dispatched == [("omr.process_scan", ["scan-celery"])]
