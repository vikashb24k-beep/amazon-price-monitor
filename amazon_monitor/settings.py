from config.settings import get_settings


app_settings = get_settings()

BOT_NAME = "amazon_monitor"
SPIDER_MODULES = ["amazon_monitor.spiders"]
NEWSPIDER_MODULE = "amazon_monitor.spiders"

ROBOTSTXT_OBEY = False
DOWNLOAD_DELAY = 2
RANDOMIZE_DOWNLOAD_DELAY = True
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 2
AUTOTHROTTLE_MAX_DELAY = 10
CONCURRENT_REQUESTS_PER_DOMAIN = 2
RETRY_ENABLED = True
RETRY_TIMES = 5
DOWNLOAD_TIMEOUT = 30

ITEM_PIPELINES = {
    "amazon_monitor.pipelines.AmazonMonitoringPipeline": 300,
}

DOWNLOADER_MIDDLEWARES = {
    "amazon_monitor.middlewares.RandomUserAgentMiddleware": 400,
    "amazon_monitor.middlewares.ProxyRotationMiddleware": 410,
    "scrapy.downloadermiddlewares.retry.RetryMiddleware": 550,
}

DEFAULT_REQUEST_HEADERS = {
    "Accept-Language": "en-IN,en;q=0.9",
    "User-Agent": app_settings.user_agents[0],
}

PLAYWRIGHT_BROWSER_TYPE = "chromium"
