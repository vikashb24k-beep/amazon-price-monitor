from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from typing import Any

from config.settings import get_settings
from database.connection import init_database
from database.repository import MonitoringRepository


LOGGER = logging.getLogger(__name__)


class AmazonMonitoringPipeline:
    def __init__(self) -> None:
        self.repository: MonitoringRepository | None = None
        self.settings = get_settings()

    def open_spider(self, spider: Any) -> None:
        session_factory = init_database(self.settings.database_url)
        self.repository = MonitoringRepository(session_factory)

    def close_spider(self, spider: Any) -> None:
        self.repository = None

    def process_item(self, item: dict[str, Any], spider: Any) -> dict[str, Any]:
        if self.repository is None:
            raise RuntimeError("Database repository is not initialized")

        normalized = self._normalize_item(dict(item))
        self.repository.record_product_snapshot(normalized)
        return normalized

    def _normalize_item(self, item: dict[str, Any]) -> dict[str, Any]:
        item["price"] = self._normalize_price(item.get("price"))
        item["rating"] = self._to_float(item.get("rating"))
        item["review_count"] = self._to_int(item.get("review_count"))

        offers = item.get("offers", [])
        normalized_offers = []
        for offer in offers:
            normalized_offers.append(
                {
                    **offer,
                    "price": self._normalize_price(offer.get("price")),
                    "seller_rating": self._to_float(offer.get("seller_rating")),
                    "review_count": self._to_int(offer.get("review_count")),
                    "is_fba": bool(offer.get("is_fba")),
                    "is_buy_box": bool(offer.get("is_buy_box")),
                }
            )
        item["offers"] = normalized_offers
        return item

    @staticmethod
    def _normalize_price(value: Any) -> float | None:
        if value in (None, "", "Currently unavailable"):
            return None

        text = str(value).replace(",", "").replace("₹", "").strip()
        filtered = "".join(ch for ch in text if ch.isdigit() or ch == ".")
        if not filtered:
            return None

        try:
            return float(Decimal(filtered))
        except (InvalidOperation, ValueError):
            LOGGER.warning("Could not parse price value %r", value)
            return None

    @staticmethod
    def _to_float(value: Any) -> float | None:
        if value in (None, ""):
            return None
        try:
            return float(str(value).strip())
        except ValueError:
            return None

    @staticmethod
    def _to_int(value: Any) -> int | None:
        if value in (None, ""):
            return None
        digits = "".join(ch for ch in str(value) if ch.isdigit())
        return int(digits) if digits else None
