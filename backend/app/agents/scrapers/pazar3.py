"""Pazar3.mk адаптер — класифициран портал.

Иста стратегија како Reklama5: HTTP прво, Playwright fallback.

ВАЖНО: потврди ги URL шаблоните од прелистувач. Pazar3 има чисти
категориски патеки (нпр. /oglasi/tehnika/...), што е подобро од
пребарување — стабилни се и враќаат сè од категоријата.
"""
import logging

from app.agents.scrapers.common import crawl_pages, extract_cards, fetch_html, fetch_rendered

logger = logging.getLogger(__name__)

BASE_URL = "https://www.pazar3.mk"

# TODO: потврди ги вистинските категориски патеки од прелистувач
CATEGORY_URLS = [
    f"{BASE_URL}/oglasi/tehnika/kompjuteri?Page={{page}}",
    f"{BASE_URL}/oglasi/tehnika/mobilni-telefoni?Page={{page}}",
    f"{BASE_URL}/oglasi/tehnika/tv-video?Page={{page}}",
]
MAX_PAGES = 3


def _extract(html: str) -> list[dict]:
    return extract_cards(
        html,
        source="pazar3",
        base_url=BASE_URL,
        require_domain="pazar3.mk",
        link_hint="/oglas",
        skip_url_parts=("?Page=", "/login", "/register", "/oglasi/"),
    )


def _fetch(url: str) -> str:
    html = fetch_html(url)
    if not _extract(html):
        logger.info("Pazar3: HTTP не врати картички, пробувам со Playwright: %s", url)
        html = fetch_rendered(url)
    return html


def scrape_pazar3() -> list[dict]:
    items = crawl_pages(CATEGORY_URLS, max_pages=MAX_PAGES, fetch=_fetch, extract=_extract)
    logger.info("Pazar3: собрани %d уникатни огласи", len(items))
    return items
