import scrapy
from ads_scraper.items import AdItem


class Reklama5Spider(scrapy.Spider):
    name = 'reklama5'
    allowed_domains = ['reklama5.mk']
    start_urls = ['https://reklama5.mk/Search?city=&cat=580&q=&sell=0&sell=1&buy=0&buy=1&trade=0&trade=1&includeOld=0&includeOld=1&includeNew=0&includeNew=1&cargoReady=0&DDVIncluded=0&private=0&company=0&page=1&SortByPrice=0&zz=1&pageView=']

    def __init__(self, start_url=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if start_url:
            self.start_urls = [start_url]

    def parse(self, response):
        from urllib.parse import urlparse, parse_qs

        # Extract items from listing page (uses site classes observed in saved HTML)
        for block in response.css('div.row.ad-top-div'):
            item = AdItem()
            item['source'] = 'reklama5'
            link = block.css('a.SearchAdTitle::attr(href)').get()
            item['ad_url'] = response.urljoin(link) if link else response.url
            item['title'] = block.css('a.SearchAdTitle::text').get()
            item['description'] = block.css('p.searchAdDesc::text').get()

            price = block.css('span.search-ad-price::text').get()
            if price:
                item['price'] = price.strip()

            city = block.css('span.city-span::text').get()
            if city:
                item['location'] = city.strip()

            # image is in a style attribute like: background-image:url(//reklama5.mk/photos/....jpg)
            img_style = block.css('.ad-image::attr(style)').get()
            images = []
            if img_style:
                import re
                m = re.search(r"url\(([^)]+)\)", img_style)
                if m:
                    src = m.group(1).strip().strip('"\'')
                    if src.startswith('//'):
                        src = 'https:' + src
                    elif src.startswith('/'):
                        src = response.urljoin(src)
                    images.append(src)
            item['images'] = images

            item['specs'] = {}
            yield item

        # pagination: look for "Следна" (Next in Macedonian) or any page link with page= param
        next_page = response.css('a.page-link[title*="Следна"]::attr(href), a[rel="next"]::attr(href)').get()
        if not next_page:
            current = int(parse_qs(urlparse(response.url).query).get('page', ['1'])[0])
            for href in response.css('li.page-item a.page-link::attr(href)').getall():
                if not href:
                    continue
                page_no = parse_qs(urlparse(response.urljoin(href)).query).get('page', [''])[0]
                if str(page_no) == str(current + 1):
                    next_page = href
                    break
        if next_page:
            yield response.follow(next_page, callback=self.parse)

    def parse_ad(self, response):
        item = AdItem()
        item['ad_url'] = response.url
        item['source'] = 'reklama5'
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
