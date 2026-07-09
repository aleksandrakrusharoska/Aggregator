BOT_NAME = 'ads_scraper'

SPIDER_MODULES = ['ads_scraper.spiders']
NEWSPIDER_MODULE = 'ads_scraper.spiders'

# Be polite and obey robots.txt
ROBOTSTXT_OBEY = True
DOWNLOAD_DELAY = 1  # seconds between requests
CONCURRENT_REQUESTS = 8

# Persist items to JSON Lines via pipeline
ITEM_PIPELINES = {
    'ads_scraper.pipelines.JsonWriterPipeline': 300,
}
