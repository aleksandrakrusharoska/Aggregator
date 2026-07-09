import scrapy


class AdItem(scrapy.Item):
    title = scrapy.Field()
    price = scrapy.Field()
    currency = scrapy.Field()
    location = scrapy.Field()
    description = scrapy.Field()
    seller_name = scrapy.Field()
    phone = scrapy.Field()
    images = scrapy.Field()
    posted_date = scrapy.Field()
    category = scrapy.Field()
    condition = scrapy.Field()
    specs = scrapy.Field()  # dict with spec name -> value
    ad_url = scrapy.Field()
    source = scrapy.Field()
