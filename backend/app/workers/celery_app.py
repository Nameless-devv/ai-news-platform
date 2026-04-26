from celery import Celery
from celery.schedules import crontab
from app.config import settings

celery_app = Celery(
    "ai_news_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Tashkent",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.workers.tasks.fetch_and_queue_news": {"queue": "fetcher"},
        "app.workers.tasks.process_article": {"queue": "processor"},
    },
    beat_schedule={
        "fetch-news-every-5-minutes": {
            "task": "app.workers.tasks.fetch_and_queue_news",
            "schedule": settings.FETCH_INTERVAL_MINUTES * 60,
        },
    },
)
