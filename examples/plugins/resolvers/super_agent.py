"""Resolver implementation surface for super_agent."""

from __future__ import annotations

from agentplatform.runtime import ExecutionContext
from plugins.resolvers.base import BaseResolver


class SuperAgentResolver(BaseResolver):
    """Resolver implementation surface for super_agent."""

    def subscription(self, ctx: ExecutionContext) -> str:
        """Return the current user's subscription tier."""
        import os

        return os.environ.get("DEMO_SUBSCRIPTION", "Free")
