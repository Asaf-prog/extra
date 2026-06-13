from __future__ import annotations

import importlib.util
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from agent_engine.core.spec import GraphNode


class RouteFilter(ABC):
    """Filters routing candidates before the orchestrator LLM makes a decision.

    Implement this interface to add cross-cutting concerns (access control,
    feature flags, rate limiting, etc.) without touching the engine core.
    Filters run in order; each receives the list returned by the previous one.
    """

    @abstractmethod
    def filter(self, ctx: dict[str, Any], candidates: list[GraphNode]) -> list[GraphNode]: ...


class AccessFilter(RouteFilter):
    """Removes protected nodes the caller is not allowed to reach."""

    def __init__(self, base_dir: Path) -> None:
        self._resolver = _load_access_resolver(base_dir)

    def filter(self, ctx: dict[str, Any], candidates: list[GraphNode]) -> list[GraphNode]:
        return [
            n for n in candidates
            if not n.node.protected or self._resolver.can_access(ctx, n.node.id)
        ]


def _load_access_resolver(base_dir: Path) -> Any:
    path = base_dir / "plugins" / "access.py"
    spec = importlib.util.spec_from_file_location("access", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cls = getattr(module, "AccessResolver", None)
    if cls is None:
        raise ImportError(f"{path} must define class AccessResolver")
    return cls()
