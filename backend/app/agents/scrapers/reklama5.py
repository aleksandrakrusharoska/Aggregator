"""Reklama5.mk адаптер — класифициран портал, претежно server-side рендериран.

Стратегија: прво обичен HTTP (брзо, лесно за серверот); ако не најде
ништо, fallback на Playwright.

ВАЖНО: URL шаблоните подолу се појдовна точка — отвори ја категоријата
„Техника" на reklama5.mk во прелистувач и потврди ги точните патеки
(и параметарот за страница). Екстракцијата е хеуристичка и ќе преживее
разлики во HTML-от, ама URL-ата мора да се точни.
"""
import logging

from app.agents.scrapers.common import crawl_pages, extract_cards, fetch_html, fetch_rendered

logger = logging.getLogger(__name__)

BASE_URL = "https://www.reklama5.mk"

# TODO: потврди ги вистинските URL-а од прелистувач (категорија Техника)
CATEGORY_URLS = [
    f"{BASE_URL}/Search?q=laptop&page={{page}}",
    f"{BASE_URL}/Search?q=telefon&page={{page}}",
    f"{BASE_URL}/Search?q=televizor&page={{page}}",
]
MAX_PAGES = 3


def _extract(html: str) -> list[dict]:
    return extract_cards(
        html,
        source="reklama5",
        base_url=BASE_URL,
        require_domain="reklama5.mk",
        link_hint="/ad/",           # огласите на Reklama5 обично се на /AdDetails или /ad/ — потврди!
        skip_url_parts=("/Search", "/search", "/login", "/register"),
    )


def _fetch(url: str) -> str:
    html = fetch_html(url)
    if not _extract(html):  # можеби е JS-рендерирано → пробај со browser
        logger.info("Reklama5: HTTP не врати картички, пробувам со Playwright: %s", url)
        html = fetch_rendered(url)
    return html


def scrape_reklama5() -> list[dict]:
    items = crawl_pages(CATEGORY_URLS, max_pages=MAX_PAGES, fetch=_fetch, extract=_extract)
    logger.info("Reklama5: собрани %d уникатни огласи", len(items))
    return items
