"""Shared base class for customer-owned resolver implementations."""

from __future__ import annotations

from abc import ABC
from datetime import date
import os

from agentplatform.runtime import ExecutionContext


class BaseResolver(ABC):
    """Base class for all generated agent resolver classes."""

    def __init__(self, rest_client: object | None = None) -> None:
        self.rest_client = rest_client

    def current_date(self, ctx: ExecutionContext) -> str:
        """Return today's date in YYYY-MM-DD format."""
        return date.today().isoformat()

    def user_name(self, ctx: ExecutionContext) -> str:
        """Return the current user's display name."""
        return os.environ.get("DEMO_USER_NAME", "Amit")
