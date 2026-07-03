from __future__ import annotations

import os


class Resolver:
    def __init__(self) -> None:
        self._experience_level = os.getenv("EXPERIENCE_LEVEL", "beginner")

    def experience_level(self, ctx: dict) -> str:
        return self._experience_level
