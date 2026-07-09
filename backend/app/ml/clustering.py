"""Кластеризација на огласи по embedding (KMeans; лесно се менува со HDBSCAN)."""
import numpy as np
from sklearn.cluster import KMeans
from sqlalchemy.orm import Session

from app.models.listing import Listing


def cluster_listings(db: Session, max_clusters: int = 20) -> int:
    listings = (
        db.query(Listing)
        .filter(Listing.embedding.isnot(None), Listing.is_duplicate.is_(False))
        .all()
    )
    if len(listings) < 10:
        return 0

    X = np.array([l.embedding for l in listings], dtype=float)
    k = min(max_clusters, max(2, len(listings) // 15))

    kmeans = KMeans(n_clusters=k, n_init="auto", random_state=42)
    labels = kmeans.fit_predict(X)

    for l, label in zip(listings, labels):
        l.cluster_id = int(label)
    db.commit()
    return k
