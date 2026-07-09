"""Ценовни аномалии: Z-score во рамки на кластер (fallback: категорија)."""
import numpy as np
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.listing import Listing


def compute_price_anomalies(db: Session) -> int:
    settings = get_settings()
    threshold = settings.price_anomaly_zscore

    listings = (
        db.query(Listing)
        .filter(Listing.price.isnot(None), Listing.is_duplicate.is_(False))
        .all()
    )

    # групирање по кластер (или категорија ако нема кластер)
    groups: dict[str, list[Listing]] = {}
    for l in listings:
        key = f"c{l.cluster_id}" if l.cluster_id is not None else f"cat:{l.category}"
        groups.setdefault(key, []).append(l)

    anomalies = 0
    for group in groups.values():
        if len(group) < 5:  # премалку податоци за статистика
            continue
        prices = np.array([l.price for l in group], dtype=float)
        std = prices.std()
        if std == 0:
            continue
        mean = prices.mean()
        for l in group:
            z = (l.price - mean) / std
            l.price_zscore = round(float(z), 3)
            l.is_anomaly = abs(z) >= threshold
            if l.is_anomaly:
                anomalies += 1

    db.commit()
    return anomalies
