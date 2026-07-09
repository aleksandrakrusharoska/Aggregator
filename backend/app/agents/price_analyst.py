"""Price Analyst Agent — детекција на ценовни аномалии.

Z-score по кластер/категорија: оглас чија цена отстапува повеќе од
PRICE_ANOMALY_ZSCORE стандардни девијации се означува како аномалија
(потенцијална зделка или сомнителен оглас).
"""
from app.core.agent_log import log_activity
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.ml.anomalies import compute_price_anomalies


@celery_app.task(name="agents.price_analyst.analyze")
def analyze(prev: dict | None = None) -> dict:
    db = SessionLocal()
    try:
        anomalies = compute_price_anomalies(db)
        log_activity("PriceAnalyst", f"Детектирани {anomalies} ценовни аномалии", target="AlertAgent")
    finally:
        db.close()
    return {**(prev or {}), "anomalies": anomalies}
