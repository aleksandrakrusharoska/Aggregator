"""Alert Agent — известувања за релевантни нови огласи/аномалии.

Скелет: тука се приклучува email/push логика или зачувување
на нотификации во базата за прикажување во UI.
"""
from app.core.agent_log import log_activity
from app.core.celery_app import celery_app


@celery_app.task(name="agents.alerts.notify")
def notify(prev: dict | None = None) -> dict:
    anomalies = (prev or {}).get("anomalies", 0)
    new_count = len((prev or {}).get("new_listing_ids", []))
    if anomalies or new_count:
        log_activity("AlertAgent", f"Известување: {new_count} нови огласи, {anomalies} аномалии", target="Client")
    return {"notified": bool(anomalies or new_count)}
