"""Endpoints за огласи: листање, филтрирање, препораки."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.schemas import ListingOut
from app.core.database import get_db
from app.models.listing import Listing

router = APIRouter(prefix="/api/listings", tags=["listings"])


@router.get("", response_model=list[ListingOut])
def list_listings(
    db: Session = Depends(get_db),
    q: str | None = Query(None, description="Пребарување по наслов"),
    category: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    anomalies_only: bool = False,
    limit: int = Query(50, le=200),
    offset: int = 0,
):
    query = db.query(Listing).filter(Listing.is_duplicate.is_(False))
    if q:
        query = query.filter(Listing.title.ilike(f"%{q}%"))
    if category:
        query = query.filter(Listing.category == category)
    if min_price is not None:
        query = query.filter(Listing.price >= min_price)
    if max_price is not None:
        query = query.filter(Listing.price <= max_price)
    if anomalies_only:
        query = query.filter(Listing.is_anomaly.is_(True))
    return query.order_by(Listing.scraped_at.desc()).offset(offset).limit(limit).all()


@router.get("/{listing_id}/similar", response_model=list[ListingOut])
def similar_listings(listing_id: int, db: Session = Depends(get_db), limit: int = 5):
    """Препораки: најслични огласи по embedding (pgvector)."""
    listing = db.get(Listing, listing_id)
    if not listing or listing.embedding is None:
        raise HTTPException(404, "Огласот не постои или нема embedding")

    return (
        db.query(Listing)
        .filter(
            Listing.id != listing_id,
            Listing.is_duplicate.is_(False),
            Listing.embedding.isnot(None),
        )
        .order_by(Listing.embedding.cosine_distance(listing.embedding))
        .limit(limit)
        .all()
    )
