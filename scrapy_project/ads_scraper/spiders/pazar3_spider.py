import scrapy
from ads_scraper.items import AdItem


class Pazar3Spider(scrapy.Spider):
    name = 'pazar3'
    allowed_domains = ['pazar3.mk']
    start_urls = ['https://www.pazar3.mk/oglasi/elektronika/prodazba-kupuvanje-zamena']
    custom_settings = {
        'DOWNLOAD_DELAY': 20,
        'CONCURRENT_REQUESTS': 1,
    }

    def __init__(self, start_url=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if start_url:
            self.start_urls = [start_url]

    def parse(self, response):
        # Parse listing blocks present in server-rendered HTML
        from urllib.parse import urlparse, parse_qs

        listings = response.css('div.row-listing, div.row.row-listing')
        for l in listings:
            item = AdItem()
            title = l.css('h2 a::text').get()
            href = l.css('h2 a::attr(href)').get()
            img = l.css('img::attr(data-src)').get() or l.css('img::attr(src)').get()
            price = l.css('p.list-price::text').get()
            posted = l.css('span.pull-right::text').get()
            # location/category breadcrumbs appear as a series of links; take the last non-empty one
            crumbs = l.css('a.link-html.nobold::text').getall()
            location = crumbs[-1].strip() if crumbs else None

            item['title'] = title.strip() if title else None
            item['ad_url'] = response.urljoin(href) if href else None
            item['images'] = [response.urljoin(img)] if img else []
            item['price'] = price.strip() if price else None
            item['posted_date'] = posted.strip() if posted else None
            item['location'] = location
            item['source'] = 'pazar3'

            yield item

        # Pagination: follow explicit "next" page button when enabled
        next_btn = response.css('a.next.page-number:not(.disabled)::attr(href)').get()
        if not next_btn:
            parsed = urlparse(response.url)
            params = parse_qs(parsed.query)
            current = int(params.get('Page', ['1'])[0])
            next_btn = response.css(f'a.page-number[page-no="{current+1}"]::attr(href)').get()
        if next_btn:
            yield response.follow(next_btn, callback=self.parse)

    def parse_ad(self, response):
        item = AdItem()
        item['ad_url'] = response.url
        item['source'] = 'pazar3'
        item['title'] = response.css('h1::text').get()
        item['price'] = response.css('.price::text').get()
        item['currency'] = response.css('.price .currency::text').get()
        item['location'] = response.css('.location::text').get()
        item['description'] = ' '.join(response.css('.description p::text').getall() or []).strip()
        item['seller_name'] = response.css('.seller-name::text').get()
        item['phone'] = response.css('.phone::text').get()
        item['images'] = response.css('.gallery img::attr(src)').getall()
        item['posted_date'] = response.css('.posted::text').get()

        specs = {}
        for row in response.css('.specs tr'):
            k = row.css('th::text').get()
            v = row.css('td::text').get()
            if k and v:
                specs[k.strip().lower()] = v.strip()
        item['specs'] = specs
        yield item
