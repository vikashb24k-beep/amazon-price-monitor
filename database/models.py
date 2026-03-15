from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asin: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    title: Mapped[str] = mapped_column(Text)
    brand: Mapped[str | None] = mapped_column(String(120), nullable=True)
    category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    price_history: Mapped[list["PriceHistory"]] = relationship(back_populates="product")
    offers: Mapped[list["Offer"]] = relationship(back_populates="product")
    buy_box_history: Mapped[list["BuyBoxHistory"]] = relationship(back_populates="product")


class Seller(Base):
    __tablename__ = "sellers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    fulfillment_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    price_history: Mapped[list["PriceHistory"]] = relationship(back_populates="seller")
    offers: Mapped[list["Offer"]] = relationship(back_populates="seller")
    buy_box_history: Mapped[list["BuyBoxHistory"]] = relationship(back_populates="seller")


class Location(Base):
    __tablename__ = "locations"
    __table_args__ = (UniqueConstraint("pincode", "city", name="uq_locations_pincode_city"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pincode: Mapped[str] = mapped_column(String(12), index=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    state: Mapped[str | None] = mapped_column(String(120), nullable=True)

    price_history: Mapped[list["PriceHistory"]] = relationship(back_populates="location")
    offers: Mapped[list["Offer"]] = relationship(back_populates="location")
    buy_box_history: Mapped[list["BuyBoxHistory"]] = relationship(back_populates="location")


class PriceHistory(Base):
    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    seller_id: Mapped[int | None] = mapped_column(ForeignKey("sellers.id"), nullable=True, index=True)
    location_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id"), nullable=True, index=True)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    availability: Mapped[str | None] = mapped_column(String(60), nullable=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    review_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_fba: Mapped[bool] = mapped_column(Boolean, default=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    product: Mapped["Product"] = relationship(back_populates="price_history")
    seller: Mapped["Seller"] = relationship(back_populates="price_history")
    location: Mapped["Location"] = relationship(back_populates="price_history")


class Offer(Base):
    __tablename__ = "offers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id"), index=True)
    location_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id"), nullable=True, index=True)
    offer_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    availability: Mapped[str | None] = mapped_column(String(60), nullable=True)
    is_buy_box: Mapped[bool] = mapped_column(Boolean, default=False)
    is_fba: Mapped[bool] = mapped_column(Boolean, default=False)
    seller_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    product: Mapped["Product"] = relationship(back_populates="offers")
    seller: Mapped["Seller"] = relationship(back_populates="offers")
    location: Mapped["Location"] = relationship(back_populates="offers")


class BuyBoxHistory(Base):
    __tablename__ = "buy_box_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("sellers.id"), index=True)
    location_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id"), nullable=True, index=True)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    product: Mapped["Product"] = relationship(back_populates="buy_box_history")
    seller: Mapped["Seller"] = relationship(back_populates="buy_box_history")
    location: Mapped["Location"] = relationship(back_populates="buy_box_history")


class AlertEvent(Base):
    __tablename__ = "alert_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alert_type: Mapped[str] = mapped_column(String(60), index=True)
    asin: Mapped[str] = mapped_column(String(32), index=True)
    seller_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(120), nullable=True)
    message: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20), default="info")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
