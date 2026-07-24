"""
Price anomaly detection agent.

Groups ads by normalised product title, computes Z-score of price_eur
within each group, and flags outliers (|z| > Z_THRESHOLD).

Only ads with a known price_eur are considered.
Groups with fewer than MIN_GROUP_SIZE ads are skipped (too little data).
"""
import logging
import re

import numpy as np

logger = logging.getLogger(__name__)

Z_THRESHOLD = 2.0       # flag if price deviates > 2 std from group mean
MIN_GROUP_SIZE = 3      # need at least 3 ads to compute meaningful stats

_NOISE = [
    'se prodava', 'prodavam', 'itno', 'hitno', 'kako nov', 'kako nova',
    'zachuvan', 'zacuvan', 'polovno', 'koristeno', 'novo', 'nov', 'nova',
    'for sale', 'like new', 'used', 'brand new',
    'се продава', 'продавам', 'итно', 'како нов', 'како ново',
    'зачуван', 'користено', 'ново', 'нов',
]


def _normalise(title: str) -> str:
    """Normalise title to a product group key."""
    if not title:
        return ''
    t = title.lower()
    for phrase in _NOISE:
        t = t.replace(phrase, ' ')
    t = re.sub(r'(\d+)\s*(gb|tb|mb)', r'\1\2', t)
    t = re.sub(r'[^\w\s]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def detect_anomalies(ads: list[dict]) -> list[dict]:
    """
    Given a list of ads with ad_url, title, price_eur, source:
    - groups by normalised title
    - computes Z-score within each group
    - returns list of dicts with ad_url, price_zscore, is_anomaly
    """
    # Filter to ads with valid prices
    priced = [a for a in ads if a.get('price_eur') and float(a['price_eur']) > 0]
    logger.info('Ads with price: %d / %d', len(priced), len(ads))

    # Group by normalised title
    groups: dict[str, list[dict]] = {}
    for ad in priced:
        key = _normalise(ad.get('title', ''))
        if not key:
            continue
        groups.setdefault(key, []).append(ad)

    logger.info('Product groups: %d', len(groups))

    results = []
    anomaly_count = 0

    for key, group in groups.items():
        if len(group) < MIN_GROUP_SIZE:
            # Not enough data — assign neutral zscore
            for ad in group:
                results.append({
                    'ad_url': ad['ad_url'],
                    'price_zscore': None,
                    'is_anomaly': False,
                })
            continue

        prices = np.array([float(a['price_eur']) for a in group])
        mean = prices.mean()
        std = prices.std()

        for ad, price in zip(group, prices):
            if std == 0:
                zscore = 0.0
            else:
                zscore = float((price - mean) / std)

            is_anomaly = abs(zscore) > Z_THRESHOLD
            if is_anomaly:
                anomaly_count += 1
                logger.debug(
                    'ANOMALY: %s | price=%.2f | mean=%.2f | z=%.2f | group=%s',
                    ad.get('title', '')[:50], price, mean, zscore, key[:40]
                )

            results.append({
                'ad_url': ad['ad_url'],
                'price_zscore': round(zscore, 4),
                'is_anomaly': is_anomaly,
            })

    logger.info('Anomalies detected: %d / %d priced ads', anomaly_count, len(priced))
    return results
