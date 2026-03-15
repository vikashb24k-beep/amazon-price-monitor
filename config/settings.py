from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache


def _split_csv(raw_value: str, default: list[str]) -> list[str]:
    values = [entry.strip() for entry in raw_value.split(",") if entry.strip()]
    return values or default


def _env_flag(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class AppSettings:
    app_name: str = os.getenv("APP_NAME", "Amazon Bearing Monitor")
    environment: str = os.getenv("APP_ENV", "development")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///amazon_monitor.db")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8000"))
    alert_email_from: str = os.getenv("ALERT_EMAIL_FROM", "")
    alert_email_to: str = os.getenv("ALERT_EMAIL_TO", "")
    smtp_host: str = os.getenv("SMTP_HOST", "localhost")
    smtp_port: int = int(os.getenv("SMTP_PORT", "25"))
    slack_webhook_url: str = os.getenv("SLACK_WEBHOOK_URL", "")
    generic_webhook_url: str = os.getenv("GENERIC_WEBHOOK_URL", "")
    proxy_pool: list[str] = field(
        default_factory=lambda: _split_csv(os.getenv("PROXY_POOL", ""), [])
    )
    user_agents: list[str] = field(
        default_factory=lambda: _split_csv(
            os.getenv("USER_AGENT_POOL", ""),
            [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/122.0 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/122.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
                "(KHTML, like Gecko) Version/17.3 Safari/605.1.15",
            ],
        )
    )
    scrape_queries: list[str] = field(
        default_factory=lambda: _split_csv(
            os.getenv("SCRAPE_QUERIES", "SKF bearing 6205,SKF bearing 6203,SKF bearing 6202"),
            ["SKF bearing 6205", "SKF bearing 6203", "SKF bearing 6202"],
        )
    )
    location_pincodes: list[str] = field(
        default_factory=lambda: _split_csv(
            os.getenv("LOCATION_PINCODES", "600001,560001,110001"),
            ["600001", "560001", "110001"],
        )
    )
    price_drop_threshold_pct: float = float(os.getenv("PRICE_DROP_THRESHOLD_PCT", "5"))
    undercut_threshold_pct: float = float(os.getenv("UNDERCUT_THRESHOLD_PCT", "3"))
    alert_cooldown_minutes: int = int(os.getenv("ALERT_COOLDOWN_MINUTES", "60"))
    seed_demo_data: bool = field(
        default_factory=lambda: _env_flag("SEED_DEMO_DATA", os.getenv("APP_ENV", "development") != "production")
    )


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    return AppSettings()
