import scrapy
from ads_scraper.items import AdItem
from ads_scraper.spiders.pazar3_spider import Pazar3Spider

BASE = 'https://www.pazar3.mk/oglasi/elektronika/prodazba-kupuvanje-zamena'


class Pazar3OldestSpider(Pazar3Spider):
    """
    Crawls pazar3 from the oldest page backwards to the newest.

    Use this to recover historical ads missed in earlier crawls.
    All page URLs are queued upfront so a 404 on one page skips it
    and the rest continue normally.

    Usage:
        scrapy crawl pazar3_oldest -s DOWNLOAD_DELAY=2 -s CONCURRENT_REQUESTS=1 -s LOG_LEVEL=INFO
    """
    name = 'pazar3_oldest'

    def start_requests(self):
        # Fetch page 1 first just to discover the total number of pages
        yield scrapy.Request(BASE, callback=self._discover_pages)

    def _discover_pages(self, response):
        page_nos = [
            int(p) for p in response.css('a.page-number::attr(page-no)').getall()
            if p.isdigit()
        ]
        last_page = max(page_nos) if page_nos else 1
        self.logger.info('Discovered %d pages — queuing from page %d down to 1', last_page, last_page)

        for page in range(last_page, 0, -1):
            yield scrapy.Request(
                f'{BASE}?Page={page}',
                callback=self._parse_listing_page,
                priority=page,          # higher page number = crawled first
                errback=self._on_error,
                meta={'page': page},
            )

    def _on_error(self, failure):
        page = failure.request.meta.get('page', '?')
        self.logger.warning('Page %s failed (%s) — skipping', page, failure.value)

    def _parse_listing_page(self, response):
        if response.status == 404:
            self.logger.warning('Page %s returned 404 — skipping', response.meta.get('page', '?'))
            return

        listings = response.css('div.row-listing, div.row.row-listing')
        self.logger.info('Page %s: %d listings', response.meta.get('page', '?'), len(listings))

        for l in listings:
            item = AdItem()
            title  = l.css('h2 a::text').get()
            href   = l.css('h2 a::attr(href)').get()
            img    = l.css('img::attr(data-src)').get() or l.css('img::attr(src)').get()
            price  = l.css('p.list-price::text').get()
            posted = l.css('span.pull-right::text').get()
            crumbs = l.css('a.link-html.nobold::text').getall()

            item['title']       = title.strip() if title else None
            item['ad_url']      = response.urljoin(href) if href else None
            item['images']      = [response.urljoin(img)] if img else []
            item['price']       = price.strip() if price else None
            item['posted_date'] = posted.strip() if posted else None
            item['location']    = crumbs[-1].strip() if crumbs else None
            item['source']      = 'pazar3'

            if href:
                yield response.follow(
                    href,
                    callback=self.parse_ad,   # reuse parent's detail parser
                    meta={'listing': dict(item)},
                    errback=self._on_error,
                )
            else:
                yield item
        # No next-page following — all pages are already queued from _discover_pages
