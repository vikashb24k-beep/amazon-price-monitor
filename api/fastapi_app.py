from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query

from analytics.price_analysis import AnalyticsService
from config.settings import get_settings
from database.connection import init_database
from database.repository import MonitoringRepository


settings = get_settings()
repository = MonitoringRepository(init_database(settings.database_url))
if settings.seed_demo_data:
    repository.ensure_seed_data()
analytics = AnalyticsService(repository)

app = FastAPI(title=settings.app_name, version="1.0.0")


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
        "seed_demo_data": settings.seed_demo_data,
    }


@app.get("/products")
def get_products(query: str | None = Query(default=None)) -> list[dict]:
    return repository.list_products(query)


@app.get("/product/{asin}")
def get_product(asin: str) -> dict:
    product = repository.get_product_details(asin)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.get("/price-history/{asin}")
def get_price_history(asin: str, location: str | None = Query(default=None)) -> list[dict]:
    return repository.get_price_history(asin, location)


@app.get("/buy-box-history/{asin}")
def get_buy_box_history(asin: str) -> list[dict]:
    return repository.get_buy_box_history(asin)


@app.get("/sellers")
def get_sellers() -> list[dict]:
    return repository.list_sellers()


@app.get("/alerts")
def get_alerts(limit: int = Query(default=100, ge=1, le=500)) -> list[dict]:
    return repository.list_alerts(limit)


@app.get("/analytics/summary")
def get_summary(asin: str | None = Query(default=None)) -> dict:
    return analytics.build_summary(asin)
