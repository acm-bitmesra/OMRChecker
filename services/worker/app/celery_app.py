import os

from celery import Celery

broker_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "omr_checker",
    broker=broker_url,
    backend=broker_url,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
)
