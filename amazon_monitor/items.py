import scrapy


class ProductSnapshotItem(scrapy.Item):
    asin = scrapy.Field()
    title = scrapy.Field()
    brand = scrapy.Field()
    category = scrapy.Field()
    price = scrapy.Field()
    seller_name = scrapy.Field()
    availability = scrapy.Field()
    rating = scrapy.Field()
    review_count = scrapy.Field()
    buy_box_seller = scrapy.Field()
    is_fba = scrapy.Field()
    location = scrapy.Field()
    captured_at = scrapy.Field()
    offers = scrapy.Field()
