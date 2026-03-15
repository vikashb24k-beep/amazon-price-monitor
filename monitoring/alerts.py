from __future__ import annotations

import json
import smtplib
from email.message import EmailMessage
from urllib import request

from config.settings import AppSettings
from database.repository import MonitoringRepository


class AlertDispatcher:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings

    def dispatch(self, subject: str, body: str) -> None:
        if self.settings.alert_email_from and self.settings.alert_email_to:
            self._send_email(subject, body)
        if self.settings.slack_webhook_url:
            self._post_json(self.settings.slack_webhook_url, {"text": f"{subject}\n{body}"})
        if self.settings.generic_webhook_url:
            self._post_json(self.settings.generic_webhook_url, {"subject": subject, "body": body})

    def _send_email(self, subject: str, body: str) -> None:
        message = EmailMessage()
        message["From"] = self.settings.alert_email_from
        message["To"] = self.settings.alert_email_to
        message["Subject"] = subject
        message.set_content(body)
        with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port) as smtp:
            smtp.send_message(message)

    @staticmethod
    def _post_json(url: str, payload: dict) -> None:
        req = request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        request.urlopen(req, timeout=10).read()


class AlertEngine:
    def __init__(self, repository: MonitoringRepository, settings: AppSettings, dispatcher: AlertDispatcher) -> None:
        self.repository = repository
        self.settings = settings
        self.dispatcher = dispatcher

    def evaluate(self) -> list[dict]:
        frame = self.repository.price_history_frame()
        if frame.empty:
            return []

        frame = frame.sort_values("captured_at")
        events = []

        for (asin, seller_name, location), group in frame.groupby(["asin", "seller_name", "location"], dropna=False):
            if len(group) < 2:
                continue

            latest = group.iloc[-1]
            previous = group.iloc[-2]

            if latest["price"] is not None and previous["price"] is not None:
                delta_pct = round(((previous["price"] - latest["price"]) / previous["price"]) * 100, 2)
                if delta_pct >= self.settings.price_drop_threshold_pct:
                    message = (
                        f"{asin} price dropped by {delta_pct}% for seller {seller_name} "
                        f"at location {location}: {previous['price']} -> {latest['price']}"
                    )
                    events.append(self._register("price_drop", asin, message, seller_name, location, "warning"))

            if latest["availability"] != previous["availability"]:
                message = (
                    f"{asin} availability changed for seller {seller_name} "
                    f"at location {location}: {previous['availability']} -> {latest['availability']}"
                )
                events.append(self._register("stock_change", asin, message, seller_name, location, "info"))

        buy_box = self.repository.buy_box_frame().sort_values("captured_at")
        for (asin, location), group in buy_box.groupby(["asin", "location"], dropna=False):
            if len(group) < 2:
                continue
            latest = group.iloc[-1]
            previous = group.iloc[-2]
            if latest["seller_name"] != previous["seller_name"]:
                message = (
                    f"{asin} Buy Box changed at location {location}: "
                    f"{previous['seller_name']} -> {latest['seller_name']}"
                )
                events.append(self._register("buy_box_change", asin, message, latest["seller_name"], location, "critical"))

        offers = self.repository.latest_market_snapshot()
        if not offers.empty:
            for asin, group in offers.groupby("asin"):
                ranked = group.dropna(subset=["offer_price"]).sort_values("offer_price")
                if len(ranked) < 2:
                    continue
                low = ranked.iloc[0]
                next_best = ranked.iloc[1]
                gap_pct = round(((next_best["offer_price"] - low["offer_price"]) / next_best["offer_price"]) * 100, 2)
                if gap_pct >= self.settings.undercut_threshold_pct:
                    message = (
                        f"{asin} undercut alert: {low['seller_name']} is {gap_pct}% below "
                        f"the next seller at {low['offer_price']}"
                    )
                    events.append(self._register("undercut", asin, message, low["seller_name"], low["location"], "warning"))

        return events

    def _register(
        self,
        alert_type: str,
        asin: str,
        message: str,
        seller_name: str | None,
        location: str | None,
        severity: str,
    ) -> dict:
        if self.repository.has_recent_alert(
            alert_type,
            asin,
            seller_name,
            location,
            self.settings.alert_cooldown_minutes,
        ):
            return {
                "alert_type": alert_type,
                "asin": asin,
                "seller_name": seller_name,
                "location": location,
                "severity": severity,
                "message": f"Suppressed duplicate alert: {message}",
            }
        self.repository.create_alert(alert_type, asin, message, severity, seller_name, location)
        self.dispatcher.dispatch(f"[{severity.upper()}] {alert_type}", message)
        return {
            "alert_type": alert_type,
            "asin": asin,
            "seller_name": seller_name,
            "location": location,
            "severity": severity,
            "message": message,
        }
