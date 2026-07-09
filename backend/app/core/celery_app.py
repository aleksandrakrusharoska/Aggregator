"""Celery инстанца + распоред (beat) за периодичните агенти."""
from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "ad_aggregator",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.agents.scraper",
        "app.agents.deduplicator",
        "app.agents.price_analyst",
        "app.agents.recommender",
        "app.agents.alerts",
        "app.agents.orchestrator",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Skopje",
    enable_utc=True,
)

# Периодичен распоред — Scraper-от го стартува целиот pipeline
celery_app.conf.beat_schedule = {
    "run-scrape-pipeline": {
        "task": "agents.orchestrator.run_pipeline",
        "schedule": settings.scrape_interval_minutes * 60,
    },
    "run-recommendations": {
        "task": "agents.recommender.generate",
        "schedule": crontab(minute=0),  # на секој полн час
    },
}
