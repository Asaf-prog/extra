from __future__ import annotations

import os
from datetime import date


class SharedResolver:
    def __init__(self) -> None:
        self._preferred_language = os.getenv("PREFERRED_LANGUAGE", "en")
        self._current_date = os.getenv("CURRENT_DATE")

    def current_date(self, ctx: dict) -> str:
        """Returns the value for {{current_date}}."""
        return self._current_date or date.today().isoformat()

    def preferred_language(self, ctx: dict) -> str:
        return self._preferred_language
