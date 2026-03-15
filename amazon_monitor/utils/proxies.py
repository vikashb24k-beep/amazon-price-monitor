from __future__ import annotations

import random

from config.settings import get_settings


class ProxyPool:
    def __init__(self) -> None:
        self.settings = get_settings()

    def get_proxy(self) -> str | None:
        if not self.settings.proxy_pool:
            return None
        return random.choice(self.settings.proxy_pool)
