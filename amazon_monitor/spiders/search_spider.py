from __future__ import annotations

from datetime import datetime
from urllib.parse import urlencode

import scrapy
from bs4 import BeautifulSoup

from amazon_monitor.items import ProductSnapshotItem
from config.settings import get_settings


class SearchSpider(scrapy.Spider):
    name = "amazon_search"
    allowed_domains = ["amazon.in"]

    def start_requests(self):
        settings = get_settings()
        for query in settings.scrape_queries:
            params = urlencode({"k": query})
            for location in settings.location_pincodes:
                url = f"https://www.amazon.in/s?{params}"
                yield scrapy.Request(
                    url,
                    callback=self.parse_search,
                    meta={
                        "query": query,
                        "location": location,
                        "playwright": True,
                    },
                )

    def parse_search(self, response):
        products = response.css("div[data-component-type='s-search-result']")
        for product in products:
            asin = product.attrib.get("data-asin")
            if not asin:
                continue

            yield response.follow(
                f"/dp/{asin}",
                callback=self.parse_product,
                meta={
                    "asin": asin,
                    "location": response.meta["location"],
                    "query": response.meta["query"],
                    "playwright": True,
                },
            )

        next_page = response.css("a.s-pagination-next::attr(href)").get()
        if next_page:
            yield response.follow(next_page, callback=self.parse_search, meta=response.meta)

    def parse_product(self, response):
        asin = response.meta["asin"]
        location = response.meta["location"]
        soup = BeautifulSoup(response.text, "html.parser")

        title = self._text_or_none(response.css("#productTitle::text").get()) or self._soup_text(soup, id_="productTitle")
        price = response.css(".a-price.aok-align-center .a-offscreen::text").get() or response.css(".a-price .a-offscreen::text").get()
        seller_name = self._clean_buy_box_text(response.css("#merchant-info::text").get()) or self._soup_text(soup, id_="merchant-info")
        rating = response.css("span[data-hook='rating-out-of-text']::text").re_first(r"([\d.]+)")
        review_count = response.css("#acrCustomerReviewText::text").re_first(r"([\d,]+)")
        availability = self._text_or_none(response.css("#availability span::text").get()) or "Unknown"
        buy_box_seller = self._clean_buy_box_text(response.css("#merchant-info *::text").getall())
        is_fba = "fulfilled by amazon" in " ".join(response.css("#merchant-info *::text").getall()).lower()

        item = ProductSnapshotItem(
            asin=asin,
            title=title or f"Amazon Product {asin}",
            brand=self._extract_brand(response, soup),
            category="Bearings",
            price=price,
            seller_name=seller_name,
            availability=availability,
            rating=rating,
            review_count=review_count,
            buy_box_seller=buy_box_seller or seller_name,
            is_fba=is_fba,
            location=location,
            captured_at=datetime.utcnow(),
            offers=[],
        )

        offers_url = f"https://www.amazon.in/gp/offer-listing/{asin}/ref=dp_olp_NEW_mbc?condition=new"
        yield response.follow(offers_url, callback=self.parse_offers, meta={"item": item, "location": location})

    def parse_offers(self, response):
        item = response.meta["item"]
        soup = BeautifulSoup(response.text, "html.parser")
        offers = []

        cards = response.css("div[data-csa-c-content-id='olpOffer']")
        if not cards:
            cards = response.css(".olpOffer")

        for card in cards:
            seller_name = self._text_or_none(card.css("h3 *::text").get()) or self._text_or_none(card.css(".olpSellerName::text").get())
            price = card.css(".a-price .a-offscreen::text").get()
            availability = self._text_or_none(card.css(".olpAvailability::text").get()) or "Unknown"
            offer_text = " ".join(card.css("*::text").getall()).lower()
            offers.append(
                {
                    "seller_name": seller_name or "Unknown Seller",
                    "price": price,
                    "availability": availability,
                    "is_buy_box": item.get("buy_box_seller", "").lower() in (seller_name or "").lower(),
                    "is_fba": "fulfilled by amazon" in offer_text,
                    "seller_rating": self._extract_rating_from_offer_text(offer_text),
                }
            )

        if not offers:
            for seller_block in soup.select(".olpOffer"):
                seller_name = seller_block.select_one("h3")
                price = seller_block.select_one(".a-price .a-offscreen")
                offers.append(
                    {
                        "seller_name": seller_name.get_text(strip=True) if seller_name else "Unknown Seller",
                        "price": price.get_text(strip=True) if price else None,
                        "availability": "Unknown",
                        "is_buy_box": False,
                        "is_fba": False,
                        "seller_rating": None,
                    }
                )

        item["offers"] = offers
        yield item

    @staticmethod
    def _text_or_none(value):
        if value is None:
            return None
        text = value.strip()
        return text if text else None

    @staticmethod
    def _soup_text(soup: BeautifulSoup, id_: str) -> str | None:
        node = soup.find(id=id_)
        return node.get_text(" ", strip=True) if node else None

    @staticmethod
    def _extract_brand(response, soup: BeautifulSoup) -> str | None:
        detail_rows = response.css("#detailBullets_feature_div li")
        for row in detail_rows:
            label = " ".join(row.css("span::text").getall()).lower()
            if "brand" in label:
                text = " ".join(part.strip() for part in row.css("span::text").getall() if part.strip())
                return text.split(":")[-1].strip()
        byline = soup.select_one("#bylineInfo")
        return byline.get_text(strip=True).replace("Visit the ", "").replace(" Store", "") if byline else None

    @staticmethod
    def _clean_buy_box_text(raw_text) -> str | None:
        if not raw_text:
            return None
        if isinstance(raw_text, list):
            raw_text = " ".join(part.strip() for part in raw_text if part and part.strip())
        text = " ".join(str(raw_text).split())
        return text or None

    @staticmethod
    def _extract_rating_from_offer_text(text: str) -> float | None:
        for token in text.split():
            cleaned = token.replace("/5", "")
            try:
                value = float(cleaned)
                if 0 <= value <= 5:
                    return value
            except ValueError:
                continue
        return None
