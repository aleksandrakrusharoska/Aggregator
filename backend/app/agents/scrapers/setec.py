"""Setec.mk адаптер — онлајн продавница, рендерира со JavaScript → Playwright.

Порт на SetecCrawlerService.java (проф. верзија), преку заедничките
алатки во common.py.
"""
import logging

from app.agents.scrapers.common import crawl_pages, extract_cards, fetch_rendered

logger = logging.getLogger(__name__)

BASE_URL = "https://setec.mk"

CATEGORY_URLS = [
    f"{BASE_URL}/search-result?q=laptop&page={{page}}",
    f"{BASE_URL}/search-result?q=telefon&page={{page}}",
    f"{BASE_URL}/search-result?q=televizor&page={{page}}",
]
MAX_PAGES = 3


def _extract(html: str) -> list[dict]:
    return extract_cards(
        html,
        source="setec",
        base_url=BASE_URL,
        require_domain="setec.mk",
        link_hint="/product",
        skip_url_parts=("/search-result",),
    )


def scrape_setec() -> list[dict]:
    items = crawl_pages(CATEGORY_URLS, max_pages=MAX_PAGES, fetch=fetch_rendered, extract=_extract)
    logger.info("Setec: собрани %d уникатни огласи", len(items))
    return items
