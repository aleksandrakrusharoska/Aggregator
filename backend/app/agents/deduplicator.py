"""De-duplication Agent — семантичка дедупликација со embeddings.

1. Генерира embedding за секој нов оглас (наслов + опис)
2. Бара најсличен постоечки оглас преку pgvector cosine similarity
3. Ако сличноста ≥ праг → го означува како дупликат
"""
from sqlalchemy import select

from app.core.agent_log import log_activity
from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.ml.embeddings import embed_texts
from app.models.listing import Listing

settings = get_settings()


@celery_app.task(name="agents.deduplicator.deduplicate")
def deduplicate(prev: dict | None = None) -> dict:
    new_ids = (prev or {}).get("new_listing_ids", [])
    if not new_ids:
        log_activity("De-duplicator", "Нема нови огласи за обработка", target="PriceAnalyst")
        return {"new_listing_ids": [], "duplicates": 0}

    db = SessionLocal()
    duplicates = 0
    try:
        listings = db.query(Listing).filter(Listing.id.in_(new_ids)).all()

        # 1) embeddings
        texts = [f"{l.title}. {l.description or ''}" for l in listings]
        vectors = embed_texts(texts)
        for listing, vec in zip(listings, vectors):
            listing.embedding = vec
        db.commit()

        # 2) similarity search (cosine distance = 1 - similarity)
        max_distance = 1.0 - settings.dedup_similarity_threshold
        for listing in listings:
            stmt = (
                select(Listing.id, Listing.embedding.cosine_distance(listing.embedding).label("dist"))
                .where(Listing.id != listing.id, Listing.is_duplicate.is_(False), Listing.embedding.isnot(None))
                .order_by("dist")
                .limit(1)
            )
            row = db.execute(stmt).first()
            if row and row.dist is not None and row.dist <= max_distance:
                listing.is_duplicate = True
                listing.duplicate_of = row.id
                duplicates += 1
        db.commit()

        log_activity(
            "De-duplicator",
            f"Обработени {len(listings)} огласи, {duplicates} дупликати",
            target="PriceAnalyst",
        )
    finally:
        db.close()

    return {"new_listing_ids": new_ids, "duplicates": duplicates}
