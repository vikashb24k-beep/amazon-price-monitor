import scrapy

class ProductItem(scrapy.Item):
    asin = scrapy.Field()
    title = scrapy.Field()
    seller = scrapy.Field()
    price = scrapy.Field()
    buybox_seller = scrapy.Field()
    timestamp = scrapy.Field()