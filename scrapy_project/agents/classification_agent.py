"""
Ad classification agent.

Labels each ad as one of:
  'product'  — item for sale (default)
  'service'  — repair, installation, social media services, buyback, etc.
  'wanted'   — someone looking to buy something

Uses keyword matching on title + description. No LLM needed — fast and deterministic.
"""
import logging
import re

logger = logging.getLogger(__name__)

# ── Wanted / looking-to-buy patterns ─────────────────────────────────────────
_WANTED_TITLE_STARTS = [
    r'^барам\b', r'^baram\b',
    r'^тражам\b', r'^trazam\b',
    r'^купувам\b', r'^kupuvam\b',
    r'^побарувам\b', r'^pobaruvam\b',
    r'^sakam da kupam\b', r'^сакам да купам\b',
    r'^looking for\b', r'^wanted\b',
    r'^kupu[ji]em\b', r'^tra[zž]im\b',
]

_WANTED_ANYWHERE = [
    'барам', 'baram', 'тражам', 'trazam',
    'купувам', 'kupuvam', 'побарувам', 'pobaruvam',
    'looking for', 'wanted to buy',
    'sakam da kupam', 'сакам да купам',
]

# ── Service patterns ──────────────────────────────────────────────────────────
_SERVICE_KEYWORDS = [
    # Repair / maintenance
    'сервис', 'servis', 'servisiranje', 'сервисирање',
    'поправка', 'popravka', 'ремонт', 'remont',
    'поправување', 'popravuvanje',
    # Unlock / software
    'отклучување', 'otklucuvanje', 'unlock', 'отклучи',
    'инсталација', 'instalacija', 'installation', 'reinstalacija',
    'форматирање', 'formatiranje',
    # Buyback / pawn
    'otkup', 'откуп', 'откупувам', 'otkupuvam',
    # Social media / digital services
    'следачи', 'sledaci', 'followers', 'pratilci',
    'likes', 'претплатници', 'subscribers', 'views', 'pregledi',
    'glasovi', 'гласови', 'votes',
    # General service words
    'услуга', 'usluga', 'услуги', 'uslugi',
    'изнајмување', 'iznajmuvanje', 'rental', 'rent', 'под наем',
    'рекламирање', 'reklamiranje', 'advertising', 'promotion',
    'дизајн', 'dizajn', 'design', 'printing', 'печатење',
    'transport', 'транспорт', 'dostava', 'достава на',
    'osiguruvanje', 'осигурување', 'insurance',
    # Recovery / data
    'data recovery', 'обнова на', 'враќање на податоци',
]

# Service ads where the word appears in the title (stronger signal)
_SERVICE_TITLE_STRONG = [
    'сервис', 'servis', 'поправка', 'popravka', 'ремонт', 'remont',
    'otkup', 'откуп', 'unlock', 'следачи', 'followers', 'услуга',
    'изнајмување', 'rental',
]


def _clean(text: str) -> str:
    return (text or '').lower().strip()


def _classify(title: str, description: str = '') -> str:
    t = _clean(title)
    d = _clean(description or '')
    combined = t + ' ' + d

    # ── Wanted check (title-first, strong signal) ─────────────────────────────
    for pattern in _WANTED_TITLE_STARTS:
        if re.search(pattern, t):
            return 'wanted'

    # Wanted keywords anywhere in title (still a strong signal)
    for kw in _WANTED_ANYWHERE:
        if re.search(r'\b' + re.escape(kw) + r'\b', t):
            return 'wanted'

    # ── Service check ─────────────────────────────────────────────────────────
    # Strong: service keyword in title
    for kw in _SERVICE_TITLE_STRONG:
        if re.search(r'\b' + re.escape(kw) + r'\b', t):
            return 'service'

    # Weaker: service keyword in description (require two signals or strong match)
    service_hits_desc = sum(
        1 for kw in _SERVICE_KEYWORDS
        if re.search(r'\b' + re.escape(kw) + r'\b', d)
    )
    if service_hits_desc >= 2:
        return 'service'

    return 'product'


def classify_ads(ads: list[dict]) -> list[dict]:
    """
    Classify a list of ads by type.

    Input dicts need: ad_url, title, description (optional).
    Returns list of {ad_url, ad_type}.
    """
    counts = {'product': 0, 'service': 0, 'wanted': 0}
    results = []

    for ad in ads:
        ad_type = _classify(ad.get('title', ''), ad.get('description', ''))
        counts[ad_type] += 1
        results.append({'ad_url': ad['ad_url'], 'ad_type': ad_type})

    total = len(results)
    logger.info(
        'Classification done: %d product (%.1f%%), %d service (%.1f%%), %d wanted (%.1f%%)',
        counts['product'], 100 * counts['product'] / total if total else 0,
        counts['service'], 100 * counts['service'] / total if total else 0,
        counts['wanted'],  100 * counts['wanted']  / total if total else 0,
    )
    return results
