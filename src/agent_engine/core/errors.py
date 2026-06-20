from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationError:
    field: str
    message: str

    def __str__(self) -> str:
        return f"[{self.field}] {self.message}"
