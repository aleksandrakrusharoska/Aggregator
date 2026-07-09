"""Endpoints за агентски статус и историја на активност."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas import AgentLogOut
from app.core.celery_app import celery_app
from app.core.database import get_db
from app.models.agent_log import AgentLog

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("/logs", response_model=list[AgentLogOut])
def recent_logs(db: Session = Depends(get_db), limit: int = 50):
    return db.query(AgentLog).order_by(AgentLog.created_at.desc()).limit(limit).all()


@router.post("/run-pipeline")
def trigger_pipeline():
    """Рачно тригерирање на целиот pipeline (корисно за демо/одбрана)."""
    celery_app.send_task("agents.orchestrator.run_pipeline")
    return {"status": "pipeline triggered"}
