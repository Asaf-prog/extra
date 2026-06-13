from __future__ import annotations

import os
from datetime import date


class SharedResolver:
    def __init__(self) -> None:
        pass

    def current_date(self, ctx: dict) -> str:
        return date.today().isoformat()

    def user_name(self, ctx: dict) -> str:
        return os.environ.get("DEMO_USER_NAME", "Amit")
