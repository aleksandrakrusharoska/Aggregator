"""Историја на агентска активност (за Agent Status страницата)."""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agent: Mapped[str] = mapped_column(String(50), index=True)
    target: Mapped[str | None] = mapped_column(String(50))
    message: Mapped[str] = mapped_column(Text)
    level: Mapped[str] = mapped_column(String(20), default="info")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
