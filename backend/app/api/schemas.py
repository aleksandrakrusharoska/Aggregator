"""Pydantic шеми за API одговори."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ListingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    source_url: str
    title: str
    description: str | None = None
    category: str | None = None
    brand: str | None = None
    location: str | None = None
    image_url: str | None = None
    price: float | None = None
    currency: str
    cluster_id: int | None = None
    is_anomaly: bool
    price_zscore: float | None = None
    scraped_at: datetime


class AgentLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    agent: str
    target: str | None = None
    message: str
    level: str
    created_at: datetime
