from __future__ import annotations

import argparse
import subprocess
import sys

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config.settings import get_settings
from database.connection import init_database
from database.repository import MonitoringRepository
from monitoring.alerts import AlertDispatcher, AlertEngine


def run_scraper() -> None:
    subprocess.run([sys.executable, "-m", "scrapy", "crawl", "amazon_search"], check=True)


def run_alerts() -> None:
    settings = get_settings()
    repository = MonitoringRepository(init_database(settings.database_url))
    dispatcher = AlertDispatcher(settings)
    engine = AlertEngine(repository, settings, dispatcher)
    engine.evaluate()


def main() -> None:
    parser = argparse.ArgumentParser(description="Schedule Amazon monitoring runs.")
    parser.add_argument("--interval-minutes", type=int, default=30, help="Scrape cadence in minutes")
    args = parser.parse_args()

    scheduler = BlockingScheduler()
    scheduler.add_job(run_scraper, IntervalTrigger(minutes=args.interval_minutes), max_instances=1)
    scheduler.add_job(run_alerts, IntervalTrigger(minutes=args.interval_minutes), max_instances=1)
    scheduler.start()


if __name__ == "__main__":
    main()
