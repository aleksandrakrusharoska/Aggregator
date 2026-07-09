"""Заедничко логирање на агентска активност.

Секој агент вика log_activity(); записот оди во базата (за историја)
и се објавува на Redis pub/sub канал за WebSocket live feed-от.
"""
import json
from datetime import datetime, timezone

import redis

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.agent_log import AgentLog

settings = get_settings()
CHANNEL = "agent-activity"

_redis = redis.Redis.from_url(settings.redis_url, decode_responses=True)


def log_activity(agent: str, message: str, target: str | None = None, level: str = "info") -> None:
    payload = {
        "agent": agent,
        "target": target,
        "message": message,
        "level": level,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # 1) Историја во базата
    db = SessionLocal()
    try:
        db.add(AgentLog(agent=agent, target=target, message=message, level=level))
        db.commit()
    finally:
        db.close()

    # 2) Live feed преку Redis pub/sub → WebSocket
    _redis.publish(CHANNEL, json.dumps(payload))
