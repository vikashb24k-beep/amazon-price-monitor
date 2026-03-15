from __future__ import annotations

import pandas as pd

from database.repository import MonitoringRepository


class AnalyticsService:
    def __init__(self, repository: MonitoringRepository) -> None:
        self.repository = repository

    def build_summary(self, asin: str | None = None) -> dict:
        prices = self.repository.price_history_frame(asin)
        buy_box = self.repository.buy_box_frame(asin)
        latest_offers = self.repository.latest_market_snapshot()
        if asin and not latest_offers.empty:
            latest_offers = latest_offers[latest_offers["asin"] == asin]

        if prices.empty:
            return {
                "price_points": 0,
                "products_tracked": 0,
                "average_market_price": None,
                "min_price_seller": None,
                "frequent_price_changers": [],
                "buy_box_win_rate": [],
                "undercutting_events": [],
                "seller_market_share": [],
            }

        frequent_changes = (
            prices.sort_values("captured_at")
            .assign(prev_price=lambda frame: frame.groupby(["asin", "seller_name"])["price"].shift(1))
            .assign(changed=lambda frame: frame["price"] != frame["prev_price"])
            .groupby("seller_name", dropna=True)["changed"]
            .sum()
            .sort_values(ascending=False)
            .head(10)
        )

        seller_market_share = []
        if not latest_offers.empty:
            seller_market_share = (
                latest_offers.groupby("seller_name")["asin"]
                .nunique()
                .div(latest_offers["asin"].nunique())
                .mul(100)
                .round(2)
                .reset_index(name="market_share_pct")
                .to_dict(orient="records")
            )

        buy_box_win_rate = []
        if not buy_box.empty:
            buy_box_win_rate = (
                buy_box.groupby("seller_name")["asin"]
                .count()
                .div(len(buy_box))
                .mul(100)
                .round(2)
                .reset_index(name="win_rate_pct")
                .to_dict(orient="records")
            )

        min_price_seller = None
        if not latest_offers.empty:
            min_row = latest_offers.sort_values("offer_price").iloc[0]
            min_price_seller = {
                "seller_name": min_row["seller_name"],
                "offer_price": float(min_row["offer_price"]),
                "asin": min_row["asin"],
            }

        return {
            "price_points": int(len(prices)),
            "products_tracked": int(prices["asin"].nunique()),
            "average_market_price": round(float(prices["price"].dropna().mean()), 2),
            "min_price_seller": min_price_seller,
            "frequent_price_changers": [
                {"seller_name": seller, "changes": int(changes)}
                for seller, changes in frequent_changes.items()
            ],
            "buy_box_win_rate": buy_box_win_rate,
            "undercutting_events": self._detect_undercutting(latest_offers),
            "seller_market_share": seller_market_share,
        }

    def price_heatmap(self, asin: str | None = None) -> pd.DataFrame:
        offers = self.repository.latest_market_snapshot()
        if asin and not offers.empty:
            offers = offers[offers["asin"] == asin]
        if offers.empty:
            return offers
        return offers.pivot_table(
            index="seller_name",
            columns="location",
            values="offer_price",
            aggfunc="min",
        )

    def _detect_undercutting(self, latest_offers: pd.DataFrame) -> list[dict]:
        if latest_offers.empty:
            return []

        records = []
        for asin, frame in latest_offers.groupby("asin"):
            prices = frame["offer_price"].dropna().sort_values()
            if len(prices) < 2:
                continue
            min_price = prices.iloc[0]
            second_price = prices.iloc[1]
            delta_pct = round(((second_price - min_price) / second_price) * 100, 2)
            if delta_pct > 0:
                winner = frame.loc[frame["offer_price"] == min_price].iloc[0]
                records.append(
                    {
                        "asin": asin,
                        "seller_name": winner["seller_name"],
                        "price": float(min_price),
                        "undercut_pct": delta_pct,
                    }
                )
        return sorted(records, key=lambda row: row["undercut_pct"], reverse=True)
