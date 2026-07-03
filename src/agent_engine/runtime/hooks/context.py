"""Per-run context propagation for hooks.

The engine is created once and shared across requests, so it must
hold no request state. The current run's :class:`RunContext` is instead carried
in a :class:`contextvars.ContextVar`, which is copied into any task/coroutine
spawned during the run. This lets the MCP transport auth layer and tool-call
sites reach the active run's identity without the engine storing it.
"""

from __future__ import annotations

from contextvars import ContextVar

from agent_engine.runtime.hooks.models import RunContext

current_run_context: ContextVar[RunContext | None] = ContextVar("current_run_context", default=None)
