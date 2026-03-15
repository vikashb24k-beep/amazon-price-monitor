from __future__ import annotations

import random
from typing import Any

from amazon_monitor.utils.proxies import ProxyPool
from config.settings import get_settings


class RandomUserAgentMiddleware:
    def __init__(self) -> None:
        self.settings = get_settings()

    def process_request(self, request: Any, spider: Any) -> None:
        request.headers["User-Agent"] = random.choice(self.settings.user_agents)


class ProxyRotationMiddleware:
    def __init__(self) -> None:
        self.proxy_pool = ProxyPool()

    def process_request(self, request: Any, spider: Any) -> None:
        proxy = self.proxy_pool.get_proxy()
        if proxy:
            request.meta["proxy"] = proxy
