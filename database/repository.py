from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, sessionmaker

from database.models import AlertEvent, BuyBoxHistory, Location, Offer, PriceHistory, Product, Seller


PINCODE_CITY_MAP = {
    "600001": ("Chennai", "Tamil Nadu"),
    "560001": ("Bangalore", "Karnataka"),
    "110001": ("Delhi", "Delhi"),
}


class MonitoringRepository:
    def __init__(self, session_factory: sessionmaker) -> None:
        self.session_factory = session_factory

    def record_product_snapshot(self, snapshot: dict) -> None:
        with self.session_factory() as session:
            product = self._get_or_create_product(session, snapshot)
            location = self._get_or_create_location(session, snapshot.get("location"))

            observed_seller_name = snapshot.get("seller_name") or snapshot.get("buy_box_seller")
            observed_seller = self._get_or_create_seller(
                session,
                observed_seller_name,
                snapshot.get("rating"),
                "FBA" if snapshot.get("is_fba") else "Merchant",
            ) if observed_seller_name else None

            session.add(
                PriceHistory(
                    product=product,
                    seller=observed_seller,
                    location=location,
                    price=snapshot.get("price"),
                    availability=snapshot.get("availability"),
                    rating=snapshot.get("rating"),
                    review_count=snapshot.get("review_count"),
                    is_fba=bool(snapshot.get("is_fba")),
                    captured_at=snapshot.get("captured_at", datetime.utcnow()),
                )
            )

            buy_box_seller_name = snapshot.get("buy_box_seller")
            if buy_box_seller_name:
                buy_box_seller = self._get_or_create_seller(
                    session,
                    buy_box_seller_name,
                    None,
                    "FBA" if snapshot.get("is_fba") else "Merchant",
                )
                session.add(
                    BuyBoxHistory(
                        product=product,
                        seller=buy_box_seller,
                        location=location,
                        price=snapshot.get("price"),
                        captured_at=snapshot.get("captured_at", datetime.utcnow()),
                    )
                )

            for offer in snapshot.get("offers", []):
                offer_seller = self._get_or_create_seller(
                    session,
                    offer.get("seller_name"),
                    offer.get("seller_rating"),
                    "FBA" if offer.get("is_fba") else "Merchant",
                )
                session.add(
                    Offer(
                        product=product,
                        seller=offer_seller,
                        location=location,
                        offer_price=offer.get("price"),
                        availability=offer.get("availability"),
                        is_buy_box=bool(offer.get("is_buy_box")),
                        is_fba=bool(offer.get("is_fba")),
                        seller_rating=offer.get("seller_rating"),
                        captured_at=snapshot.get("captured_at", datetime.utcnow()),
                    )
                )

            session.commit()

    def create_alert(
        self,
        alert_type: str,
        asin: str,
        message: str,
        severity: str = "info",
        seller_name: str | None = None,
        location: str | None = None,
    ) -> None:
        with self.session_factory() as session:
            session.add(
                AlertEvent(
                    alert_type=alert_type,
                    asin=asin,
                    seller_name=seller_name,
                    location=location,
                    message=message,
                    severity=severity,
                )
            )
            session.commit()

    def list_products(self, query: str | None = None) -> list[dict]:
        with self.session_factory() as session:
            stmt = select(Product).order_by(Product.updated_at.desc())
            if query:
                term = f"%{query.lower()}%"
                stmt = stmt.where(
                    func.lower(Product.asin).like(term) | func.lower(Product.title).like(term)
                )
            products = session.scalars(stmt).all()
            return [
                {
                    "asin": product.asin,
                    "title": product.title,
                    "brand": product.brand,
                    "category": product.category,
                    "updated_at": product.updated_at.isoformat() if product.updated_at else None,
                }
                for product in products
            ]

    def get_product_details(self, asin: str) -> dict | None:
        with self.session_factory() as session:
            product = (
                session.execute(
                    select(Product)
                    .options(joinedload(Product.price_history), joinedload(Product.buy_box_history))
                    .where(Product.asin == asin)
                )
                .unique()
                .scalar_one_or_none()
            )
            if product is None:
                return None

            latest_price = None
            if product.price_history:
                latest_entry = max(product.price_history, key=lambda row: row.captured_at)
                latest_price = latest_entry.price

            return {
                "asin": product.asin,
                "title": product.title,
                "brand": product.brand,
                "category": product.category,
                "latest_price": latest_price,
                "buy_box_events": len(product.buy_box_history),
            }

    def get_price_history(self, asin: str, location: str | None = None) -> list[dict]:
        with self.session_factory() as session:
            stmt = (
                select(PriceHistory, Product, Seller, Location)
                .join(Product, PriceHistory.product_id == Product.id)
                .outerjoin(Seller, PriceHistory.seller_id == Seller.id)
                .outerjoin(Location, PriceHistory.location_id == Location.id)
                .where(Product.asin == asin)
                .order_by(PriceHistory.captured_at.asc())
            )
            if location:
                stmt = stmt.where(Location.pincode == location)

            rows = session.execute(stmt).all()
            return [
                {
                    "asin": product.asin,
                    "seller_name": seller.seller_name if seller else None,
                    "location": loc.pincode if loc else None,
                    "price": price.price,
                    "availability": price.availability,
                    "captured_at": price.captured_at.isoformat(),
                }
                for price, product, seller, loc in rows
            ]

    def get_buy_box_history(self, asin: str) -> list[dict]:
        with self.session_factory() as session:
            stmt = (
                select(BuyBoxHistory, Product, Seller, Location)
                .join(Product, BuyBoxHistory.product_id == Product.id)
                .join(Seller, BuyBoxHistory.seller_id == Seller.id)
                .outerjoin(Location, BuyBoxHistory.location_id == Location.id)
                .where(Product.asin == asin)
                .order_by(BuyBoxHistory.captured_at.asc())
            )
            rows = session.execute(stmt).all()
            return [
                {
                    "asin": product.asin,
                    "seller_name": seller.seller_name,
                    "location": loc.pincode if loc else None,
                    "price": event.price,
                    "captured_at": event.captured_at.isoformat(),
                }
                for event, product, seller, loc in rows
            ]

    def list_sellers(self) -> list[dict]:
        with self.session_factory() as session:
            sellers = session.scalars(select(Seller).order_by(Seller.seller_name.asc())).all()
            return [
                {
                    "seller_name": seller.seller_name,
                    "rating": seller.rating,
                    "fulfillment_type": seller.fulfillment_type,
                }
                for seller in sellers
            ]

    def list_alerts(self, limit: int = 100) -> list[dict]:
        with self.session_factory() as session:
            alerts = session.scalars(
                select(AlertEvent).order_by(AlertEvent.created_at.desc()).limit(limit)
            ).all()
            return [
                {
                    "alert_type": alert.alert_type,
                    "asin": alert.asin,
                    "seller_name": alert.seller_name,
                    "location": alert.location,
                    "severity": alert.severity,
                    "message": alert.message,
                    "created_at": alert.created_at.isoformat(),
                }
                for alert in alerts
            ]

    def has_recent_alert(
        self,
        alert_type: str,
        asin: str,
        seller_name: str | None,
        location: str | None,
        cooldown_minutes: int,
    ) -> bool:
        threshold = datetime.utcnow() - timedelta(minutes=cooldown_minutes)
        with self.session_factory() as session:
            stmt = (
                select(AlertEvent.id)
                .where(AlertEvent.alert_type == alert_type, AlertEvent.asin == asin)
                .where(AlertEvent.created_at >= threshold)
            )
            if seller_name is None:
                stmt = stmt.where(AlertEvent.seller_name.is_(None))
            else:
                stmt = stmt.where(AlertEvent.seller_name == seller_name)
            if location is None:
                stmt = stmt.where(AlertEvent.location.is_(None))
            else:
                stmt = stmt.where(AlertEvent.location == location)
            return session.scalar(stmt.limit(1)) is not None

    def price_history_frame(self, asin: str | None = None) -> pd.DataFrame:
        with self.session_factory() as session:
            stmt = (
                select(
                    Product.asin,
                    Product.title,
                    Seller.seller_name,
                    Location.pincode,
                    PriceHistory.price,
                    PriceHistory.availability,
                    PriceHistory.captured_at,
                )
                .join(Product, PriceHistory.product_id == Product.id)
                .outerjoin(Seller, PriceHistory.seller_id == Seller.id)
                .outerjoin(Location, PriceHistory.location_id == Location.id)
                .order_by(PriceHistory.captured_at.asc())
            )
            if asin:
                stmt = stmt.where(Product.asin == asin)
            rows = session.execute(stmt).all()
            frame = pd.DataFrame(
                rows,
                columns=[
                    "asin",
                    "title",
                    "seller_name",
                    "location",
                    "price",
                    "availability",
                    "captured_at",
                ],
            )
            if not frame.empty:
                frame["captured_at"] = pd.to_datetime(frame["captured_at"])
            return frame

    def offers_frame(self, asin: str | None = None) -> pd.DataFrame:
        with self.session_factory() as session:
            stmt = (
                select(
                    Product.asin,
                    Product.title,
                    Seller.seller_name,
                    Location.pincode,
                    Offer.offer_price,
                    Offer.is_buy_box,
                    Offer.is_fba,
                    Offer.availability,
                    Offer.captured_at,
                )
                .join(Product, Offer.product_id == Product.id)
                .join(Seller, Offer.seller_id == Seller.id)
                .outerjoin(Location, Offer.location_id == Location.id)
                .order_by(Offer.captured_at.desc())
            )
            if asin:
                stmt = stmt.where(Product.asin == asin)
            rows = session.execute(stmt).all()
            frame = pd.DataFrame(
                rows,
                columns=[
                    "asin",
                    "title",
                    "seller_name",
                    "location",
                    "offer_price",
                    "is_buy_box",
                    "is_fba",
                    "availability",
                    "captured_at",
                ],
            )
            if not frame.empty:
                frame["captured_at"] = pd.to_datetime(frame["captured_at"])
            return frame

    def buy_box_frame(self, asin: str | None = None) -> pd.DataFrame:
        with self.session_factory() as session:
            stmt = (
                select(
                    Product.asin,
                    Seller.seller_name,
                    Location.pincode,
                    BuyBoxHistory.price,
                    BuyBoxHistory.captured_at,
                )
                .join(Product, BuyBoxHistory.product_id == Product.id)
                .join(Seller, BuyBoxHistory.seller_id == Seller.id)
                .outerjoin(Location, BuyBoxHistory.location_id == Location.id)
                .order_by(BuyBoxHistory.captured_at.asc())
            )
            if asin:
                stmt = stmt.where(Product.asin == asin)
            rows = session.execute(stmt).all()
            frame = pd.DataFrame(
                rows,
                columns=["asin", "seller_name", "location", "price", "captured_at"],
            )
            if not frame.empty:
                frame["captured_at"] = pd.to_datetime(frame["captured_at"])
            return frame

    def latest_market_snapshot(self) -> pd.DataFrame:
        frame = self.offers_frame()
        if frame.empty:
            return frame

        frame = frame.sort_values("captured_at")
        latest = frame.groupby(["asin", "seller_name", "location"], as_index=False).tail(1)
        return latest.sort_values(["asin", "offer_price", "seller_name"])

    def ensure_seed_data(self) -> None:
        if not self.list_products():
            snapshots: Iterable[dict] = (
                {
                    "asin": "B0SKF6205",
                    "title": "SKF 6205 Deep Groove Ball Bearing",
                    "brand": "SKF",
                    "category": "Bearings",
                    "price": 420.0,
                    "seller_name": "Industrial Hub",
                    "buy_box_seller": "Industrial Hub",
                    "availability": "In stock",
                    "rating": 4.4,
                    "review_count": 126,
                    "is_fba": True,
                    "location": "600001",
                    "captured_at": datetime(2026, 3, 15, 10, 0),
                    "offers": [
                        {
                            "seller_name": "Industrial Hub",
                            "price": 420.0,
                            "availability": "In stock",
                            "is_buy_box": True,
                            "is_fba": True,
                            "seller_rating": 4.4,
                        },
                        {
                            "seller_name": "Bearing World",
                            "price": 428.0,
                            "availability": "In stock",
                            "is_buy_box": False,
                            "is_fba": False,
                            "seller_rating": 4.1,
                        },
                    ],
                },
                {
                    "asin": "B0SKF6205",
                    "title": "SKF 6205 Deep Groove Ball Bearing",
                    "brand": "SKF",
                    "category": "Bearings",
                    "price": 408.0,
                    "seller_name": "Bearing World",
                    "buy_box_seller": "Bearing World",
                    "availability": "In stock",
                    "rating": 4.4,
                    "review_count": 129,
                    "is_fba": False,
                    "location": "560001",
                    "captured_at": datetime(2026, 3, 15, 11, 0),
                    "offers": [
                        {
                            "seller_name": "Industrial Hub",
                            "price": 420.0,
                            "availability": "In stock",
                            "is_buy_box": False,
                            "is_fba": True,
                            "seller_rating": 4.4,
                        },
                        {
                            "seller_name": "Bearing World",
                            "price": 408.0,
                            "availability": "In stock",
                            "is_buy_box": True,
                            "is_fba": False,
                            "seller_rating": 4.1,
                        },
                    ],
                },
                {
                    "asin": "B0SKF6203",
                    "title": "SKF 6203 Deep Groove Ball Bearing",
                    "brand": "SKF",
                    "category": "Bearings",
                    "price": 295.0,
                    "seller_name": "Precision Traders",
                    "buy_box_seller": "Precision Traders",
                    "availability": "In stock",
                    "rating": 4.3,
                    "review_count": 87,
                    "is_fba": True,
                    "location": "110001",
                    "captured_at": datetime(2026, 3, 15, 10, 30),
                    "offers": [
                        {
                            "seller_name": "Precision Traders",
                            "price": 295.0,
                            "availability": "In stock",
                            "is_buy_box": True,
                            "is_fba": True,
                            "seller_rating": 4.3,
                        },
                        {
                            "seller_name": "National Bearings",
                            "price": 301.0,
                            "availability": "In stock",
                            "is_buy_box": False,
                            "is_fba": False,
                            "seller_rating": 4.0,
                        },
                    ],
                },
                {
                    "asin": "B0SKF6202",
                    "title": "SKF 6202 Deep Groove Ball Bearing",
                    "brand": "SKF",
                    "category": "Bearings",
                    "price": 252.0,
                    "seller_name": "National Bearings",
                    "buy_box_seller": "National Bearings",
                    "availability": "Low stock",
                    "rating": 4.2,
                    "review_count": 54,
                    "is_fba": False,
                    "location": "600001",
                    "captured_at": datetime(2026, 3, 15, 9, 45),
                    "offers": [
                        {
                            "seller_name": "National Bearings",
                            "price": 252.0,
                            "availability": "Low stock",
                            "is_buy_box": True,
                            "is_fba": False,
                            "seller_rating": 4.2,
                        },
                        {
                            "seller_name": "Industrial Hub",
                            "price": 260.0,
                            "availability": "In stock",
                            "is_buy_box": False,
                            "is_fba": True,
                            "seller_rating": 4.4,
                        },
                    ],
                },
            )
            for snapshot in snapshots:
                self.record_product_snapshot(snapshot)

    def _get_or_create_product(self, session: Session, snapshot: dict) -> Product:
        product = session.scalar(select(Product).where(Product.asin == snapshot["asin"]))
        if product is None:
            product = Product(
                asin=snapshot["asin"],
                title=snapshot.get("title", snapshot["asin"]),
                brand=snapshot.get("brand"),
                category=snapshot.get("category"),
            )
            session.add(product)
            session.flush()
        else:
            product.title = snapshot.get("title", product.title)
            product.brand = snapshot.get("brand", product.brand)
            product.category = snapshot.get("category", product.category)
        return product

    def _get_or_create_seller(
        self,
        session: Session,
        seller_name: str | None,
        rating: float | None,
        fulfillment_type: str | None,
    ) -> Seller:
        if not seller_name:
            seller_name = "Unknown Seller"

        seller = session.scalar(select(Seller).where(Seller.seller_name == seller_name))
        if seller is None:
            seller = Seller(
                seller_name=seller_name,
                rating=rating,
                fulfillment_type=fulfillment_type,
            )
            session.add(seller)
            session.flush()
        else:
            if rating is not None:
                seller.rating = rating
            if fulfillment_type:
                seller.fulfillment_type = fulfillment_type
        return seller

    def _get_or_create_location(self, session: Session, pincode: str | None) -> Location | None:
        if not pincode:
            return None

        location = session.scalar(select(Location).where(Location.pincode == pincode))
        if location is None:
            city, state = PINCODE_CITY_MAP.get(pincode, (None, None))
            location = Location(pincode=pincode, city=city, state=state)
            session.add(location)
            session.flush()
        return location
