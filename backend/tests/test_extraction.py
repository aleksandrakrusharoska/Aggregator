"""Тестови за хеуристичката екстракција — врз реалистичен HTML fixture.

Ова докажува дека логиката работи без мрежа; живите портали се
тестираат со scripts/test_scraper.py.
"""
from app.agents.scrapers.common import clean_title, extract_cards, extract_price, guess_brand

FIXTURE = """
<html><body>
<main>
  <div class="grid">
    <div class="product-item">
      <a href="/oglas/12345/laptop-lenovo-thinkpad-t14">
        <img src="/images/thinkpad.jpg" alt="Lenovo ThinkPad T14">
      </a>
      <h3 class="title">Lenovo ThinkPad T14 i5 16GB</h3>
      <span class="price">Редовна цена 32.999 ден. Клуб цена 28.500 ден.</span>
    </div>
    <div class="product-item">
      <a href="/oglas/67890/samsung-galaxy-s23">
        <img data-src="/images/s23.jpg" alt="Samsung Galaxy S23">
      </a>
      <h3 class="title">Samsung Galaxy S23 128GB 24.999 ден</h3>
      <span class="price">24.999 ден</span>
    </div>
    <!-- дупликат линк — треба да се игнорира -->
    <div class="product-item">
      <a href="/oglas/12345/laptop-lenovo-thinkpad-t14"><img src="/x.jpg" alt="Lenovo ThinkPad T14"></a>
      <span class="price">28.500 ден</span>
    </div>
    <!-- навигациски линк без слика/цена — не е картичка -->
    <div class="item"><a href="/kontakt">Контактирајте нè за повеќе информации</a></div>
    <!-- надворешен домен — треба да се исфрли -->
    <div class="product-item">
      <a href="https://evil.example.com/oglas/999"><img src="/y.jpg" alt="Фејк"></a>
      <span class="price">9.999 ден</span>
    </div>
  </div>
</main>
</body></html>
"""


def _cards():
    return extract_cards(
        FIXTURE,
        source="test",
        base_url="https://www.test.mk",
        require_domain="test.mk",
        link_hint="/oglas",
    )


def test_extracts_only_valid_cards():
    cards = _cards()
    urls = [c["source_url"] for c in cards]
    assert len(cards) == 2, f"Очекувани 2, добиени {len(cards)}: {urls}"


def test_deduplicates_by_url():
    urls = [c["source_url"] for c in _cards()]
    assert len(urls) == len(set(urls))


def test_filters_foreign_domains():
    assert all("test.mk" in c["source_url"] for c in _cards())


def test_price_takes_lower_of_regular_and_club():
    thinkpad = next(c for c in _cards() if "ThinkPad" in c["title"])
    assert thinkpad["price"] == 28500.0


def test_price_ignores_noise_below_100():
    assert extract_price("Гаранција 24 месеци, испорака за 3 дена") is None
    assert extract_price("Гаранција 24 месеци — само 15.999 ден") == 15999.0


def test_relative_urls_become_absolute():
    for c in _cards():
        assert c["source_url"].startswith("https://www.test.mk/")


def test_title_cleanup_strips_price_suffix():
    galaxy = next(c for c in _cards() if "Galaxy" in c["title"])
    assert "ден" not in galaxy["title"]
    assert "24.999" not in galaxy["title"]


def test_clean_title_cyrillic():
    assert clean_title("iPhone 15 Pro Редовна цена 89.999") == "iPhone 15 Pro"


def test_guess_brand():
    assert guess_brand("Lenovo ThinkPad T14") == "LENOVO"
    assert guess_brand("") is None
