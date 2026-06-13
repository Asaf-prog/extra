from __future__ import annotations

import os

from shared import SharedResolver


class Resolver(SharedResolver):
    def __init__(self) -> None:
        super().__init__()

    def subscription(self, ctx: dict) -> str:
        return os.environ.get("DEMO_SUBSCRIPTION", "Free")
