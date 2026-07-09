"""Модел за оглас + историја на цени."""
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

EMBEDDING_DIM = 384  # paraphrase-multilingual-MiniLM-L12-v2


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Извор
    source: Mapped[str] = mapped_column(String(50), index=True)          # нпр. "reklama5"
    source_url: Mapped[str] = mapped_column(String(500), unique=True)
    external_id: Mapped[str | None] = mapped_column(String(100))

    # Содржина
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(100), index=True)
    brand: Mapped[str | None] = mapped_column(String(100))               # извлечено (LLM нормализација)
    model: Mapped[str | None] = mapped_column(String(150))
    location: Mapped[str | None] = mapped_column(String(100))
    image_url: Mapped[str | None] = mapped_column(String(500))

    # Цена
    price: Mapped[float | None] = mapped_column(Float, index=True)
    currency: Mapped[str] = mapped_column(String(10), default="MKD")

    # ML полиња
    embedding = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    cluster_id: Mapped[int | None] = mapped_column(Integer, index=True)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)
    duplicate_of: Mapped[int | None] = mapped_column(ForeignKey("listings.id"))
    price_zscore: Mapped[float | None] = mapped_column(Float)
    is_anomaly: Mapped[bool] = mapped_column(Boolean, default=False)

    # Метаподатоци
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    price_history: Mapped[list["PriceHistory"]] = relationship(back_populates="listing")


class PriceHistory(Base):
    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"), index=True)
    price: Mapped[float] = mapped_column(Float)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    listing: Mapped[Listing] = relationship(back_populates="price_history")
