from __future__ import annotations

from agent_engine.core.errors import ValidationError


class ParseError(Exception):
    def __init__(self, errors: list[ValidationError]) -> None:
        self.errors = errors
        lines = "\n".join(f"  {e}" for e in errors)
        super().__init__(f"Parse failed:\n{lines}")
