import scrapy

class SearchSpider(scrapy.Spider):
    name = "amazon_search"

    start_urls = [
        "https://www.amazon.in/s?k=skf+bearing"
    ]

    def parse(self, response):
        products = response.css("div.s-result-item")

        for product in products:
            asin = product.attrib.get("data-asin")

            if asin:
                url = f"https://www.amazon.in/dp/{asin}"

                yield scrapy.Request(
                    url,
                    callback=self.parse_product,
                    meta={"asin": asin}
                )

    def parse_product(self, response):
        asin = response.meta["asin"]

        title = response.css("#productTitle::text").get()
        price = response.css(".a-price-whole::text").get()
        buybox = response.css("#merchant-info::text").get()

        yield {
            "asin": asin,
            "title": title,
            "price": price,
            "buybox_seller": buybox
        }

        offers_url = f"https://www.amazon.in/gp/offer-listing/{asin}"

        yield scrapy.Request(
            offers_url,
            callback=self.parse_offers,
            meta={"asin": asin}
        )

    def parse_offers(self, response):
        asin = response.meta["asin"]

        offers = response.css(".olpOffer")

        for offer in offers:
            seller = offer.css("h3::text").get()
            price = offer.css(".a-price-whole::text").get()

            yield {
                "asin": asin,
                "seller": seller,
                "price": price
            }