"""
Reference price agent.

Computes, for every ad with a matched brand+model, how its price compares
to a reference "New" price — so the frontend can show "this used phone
costs X% of a new one" instead of the old cluster/z-score anomaly badge.

Reference price comes from two tiers, in priority order:
  1. Setec's live retail catalog (retail_prices table) — real retailer
     pricing, but only covers currently-sold models.
  2. Our own marketplace's condition="New" listings (pooled across
     pazar3 + reklama5) — broader coverage, used as a fallback for older
     or discontinued models Setec doesn't carry, but less authoritative
     (a seller's asking price, not a retailer's).

Fields computed per ad:
  reference_new_price_mkd  the reference price
  reference_sample_size    how many matching listings contributed
  reference_source         "setec" or "marketplace"
  price_vs_new_ratio       price_mkd / reference_new_price_mkd
  good_price_deal          heuristic: is the ratio low enough for its
                            condition tier to call it a good deal?

Ads without a matched brand+model, or with no reference available at all,
get all fields set to None/False rather than a guess.
"""
import logging
import statistics

logger = logging.getLogger(__name__)

MIN_REFERENCE_SAMPLES = 1  # even a single reference point is useful given how sparse this data is

# Ratios below this are almost certainly a broken/garbage price_mkd value
# upstream (e.g. a placeholder or a scraping error), not a genuine deal —
# don't confidently label those "good deals".
MIN_PLAUSIBLE_RATIO = 0.10

# Heuristic: how far below the reference "New" price a used ad in a given
# condition tier should be to count as a good deal. Not statistically
# fitted — a starting point, easy to tune once real data comes in.
CONDITION_MAX_RATIO = {
    'New': 0.95,
    'Used - Like New': 0.80,
    'Used - Good': 0.68,
    'Used - Fair': 0.55,
    'Used': 0.65,
    'For parts': 0.35,
}
DEFAULT_MAX_RATIO = 0.65  # condition unknown/other


def _norm(s):
    return s.strip().lower() if s else ''


def _build_retail_index(retail_prices: list[dict]) -> dict[str, list[tuple[str, float]]]:
    """Group retail listings by normalized brand -> [(normalized title, price_mkd), ...]."""
    index: dict[str, list[tuple[str, float]]] = {}
    for r in retail_prices:
        brand = _norm(r.get('brand'))
        title = _norm(r.get('title'))
        price = r.get('price_mkd')
        if not brand or not title or not price or float(price) <= 0:
            continue
        index.setdefault(brand, []).append((title, float(price)))
    return index


def _match_retail(brand: str, model: str, retail_index: dict) -> tuple[float, int] | None:
    """Find retail listings whose title contains the model string, for this brand.
    Returns (min_price, sample_size) or None if no match."""
    candidates = retail_index.get(_norm(brand))
    if not candidates:
        return None
    model_n = _norm(model)
    if not model_n:
        return None
    matches = [price for title, price in candidates if model_n in title]
    if not matches:
        return None
    return min(matches), len(matches)


def _build_marketplace_index(ads: list[dict]) -> dict[str, tuple[float, int]]:
    """Group New-condition marketplace ads by (brand|model) -> (median_price, sample_size)."""
    groups: dict[str, list[float]] = {}
    for ad in ads:
        if ad.get('condition') != 'New':
            continue
        brand, model = ad.get('brand'), ad.get('model')
        price = ad.get('price_mkd')
        if not brand or not model or not price or float(price) <= 0:
            continue
        key = f'{_norm(brand)}|{_norm(model)}'
        groups.setdefault(key, []).append(float(price))

    index = {}
    for key, prices in groups.items():
        if len(prices) < MIN_REFERENCE_SAMPLES:
            continue
        index[key] = (statistics.median(prices), len(prices))
    return index


def compute_reference_prices(ads: list[dict], retail_prices: list[dict]) -> list[dict]:
    """
    ads: list of dicts with ad_url, brand, model, condition, price_mkd.
    retail_prices: list of dicts with brand, title, price_mkd.
    Returns list of dicts: ad_url, reference_new_price_mkd,
    reference_sample_size, reference_source, price_vs_new_ratio, good_price_deal.
    """
    retail_index = _build_retail_index(retail_prices)
    marketplace_index = _build_marketplace_index(ads)
    logger.info('Retail brands indexed: %d (%d listings)', len(retail_index),
                sum(len(v) for v in retail_index.values()))
    logger.info('Marketplace New-condition brand+model groups: %d', len(marketplace_index))

    results = []
    matched_setec = matched_marketplace = 0

    for ad in ads:
        brand, model = ad.get('brand'), ad.get('model')
        price = ad.get('price_mkd')

        ref_price = ref_size = ref_source = None
        if brand and model:
            setec_match = _match_retail(brand, model, retail_index)
            if setec_match:
                ref_price, ref_size = setec_match
                ref_source = 'setec'
                matched_setec += 1
            elif ad.get('condition') != 'New':
                # Marketplace fallback is a pool of other New-condition ads —
                # skip it for New-condition ads themselves, otherwise an ad
                # that's the only "New" listing for its model ends up being
                # compared against its own price (ratio trivially = 1.0).
                key = f'{_norm(brand)}|{_norm(model)}'
                mp_match = marketplace_index.get(key)
                if mp_match:
                    ref_price, ref_size = mp_match
                    ref_source = 'marketplace'
                    matched_marketplace += 1

        if not ref_price or not price or float(price) <= 0:
            results.append({
                'ad_url': ad['ad_url'],
                'reference_new_price_mkd': None,
                'reference_sample_size': None,
                'reference_source': None,
                'price_vs_new_ratio': None,
                'good_price_deal': False,
            })
            continue

        ratio = round(float(price) / ref_price, 4)
        max_ratio = CONDITION_MAX_RATIO.get(ad.get('condition'), DEFAULT_MAX_RATIO)

        results.append({
            'ad_url': ad['ad_url'],
            'reference_new_price_mkd': round(ref_price, 2),
            'reference_sample_size': ref_size,
            'reference_source': ref_source,
            'price_vs_new_ratio': ratio,
            'good_price_deal': MIN_PLAUSIBLE_RATIO <= ratio <= max_ratio,
        })

    logger.info('Ads matched: %d via setec, %d via marketplace fallback, %d unmatched',
                matched_setec, matched_marketplace, len(ads) - matched_setec - matched_marketplace)
    return results
