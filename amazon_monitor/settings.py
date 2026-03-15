BOT_NAME = "amazon_monitor"

SPIDER_MODULES = ["amazon_monitor.spiders"]
NEWSPIDER_MODULE = "amazon_monitor.spiders"

ROBOTSTXT_OBEY = False

DOWNLOAD_DELAY = 3
RANDOMIZE_DOWNLOAD_DELAY = True

ITEM_PIPELINES = {
    "amazon_monitor.pipelines.AmazonPipeline": 300,
}

DEFAULT_REQUEST_HEADERS = {
"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
"Accept-Language": "en-IN,en;q=0.9"
}