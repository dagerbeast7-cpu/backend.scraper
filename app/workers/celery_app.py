from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "leadzen_scraper",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# Automated Nightly Scraping Schedule (8:00 PM - 6:00 AM IST)
# Callers operate 9:00 AM - 7:00 PM IST, so all automated web scraping runs at night.
celery_app.conf.beat_schedule = {
    "nightly-delhi-ncr-scrape": {
        "task": "app.workers.tasks.run_nightly_region_scrape",
        "schedule": crontab(hour=20, minute=0),  # 8:00 PM IST daily
        "kwargs": {"region_key": "delhi_ncr"},
    },
    "nightly-mumbai-scrape": {
        "task": "app.workers.tasks.run_nightly_region_scrape",
        "schedule": crontab(hour=23, minute=30),  # 11:30 PM IST daily
        "kwargs": {"region_key": "mumbai"},
    },
    "nightly-bangalore-scrape": {
        "task": "app.workers.tasks.run_nightly_region_scrape",
        "schedule": crontab(hour=2, minute=30),  # 2:30 AM IST daily
        "kwargs": {"region_key": "bangalore"},
    },
}

