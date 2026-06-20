"""Context and event models passed to runtime hooks.

These are the *only* objects a hook sees — hooks never receive raw graph state
or other runtime internals. Every model is an immutable (frozen) dataclass; the
two fields hooks are meant to enrich (``headers`` and ``metadata``) are plain
dicts that may be mutated in place, and convenience copy helpers are provided
for a fully immutable style.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any, Literal, TypeVar

# The supported lifecycle points. Adding a point here is the one place that
# enables a new hook kind across schema validation, loading, and execution.
HookPoint = Literal[
    "on_engine_start",
    "on_run_start",
    "before_mcp_request",
    "after_tool_call",
    "on_run_error",
]

HOOK_POINTS: tuple[HookPoint, ...] = (
    "on_engine_start",
    "on_run_start",
    "before_mcp_request",
    "after_tool_call",
    "on_run_error",
)

T = TypeVar("T")


@dataclass(frozen=True)
class AuthContext:
    """Identity and authorization facts resolved by the embedding application.

    The platform never populates ``inbound_access_token`` itself — the host app
    passes it in. Hooks may use it (e.g. to exchange it for an MCP-scoped token)
    but must never log it.
    """

    user_id: str | None = None
    organization_id: str | None = None
    inbound_access_token: str | None = None
    scopes: tuple[str, ...] = ()
    roles: tuple[str, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class RunContext:
    """Per-request context threaded through one run.

    Created once per ``Engine.run``/``Engine.stream`` call and made available to
    MCP and tool hooks for the duration of that run. It holds no graph state.
    """

    run_id: str | None = None
    conversation_id: str | None = None
    user_id: str | None = None
    organization_id: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)
    auth_context: AuthContext | None = None

    def replace(self, **changes: Any) -> RunContext:
        """Return a copy with the given fields replaced (immutable update)."""
        return dataclasses.replace(self, **changes)


@dataclass(frozen=True)
class HookInvocation:
    """Single argument passed to managed hook plugin methods.

    ``payload`` is hook-point specific: for example ``RunContext`` for
    ``on_run_start`` and ``McpRequestContext`` for ``before_mcp_request``.
    Per-request identity always comes from ``run_context`` or the payload, never
    from mutable fields on the long-lived plugin instance.
    """

    hook_point: str
    payload: object
    plugin: str | None = None
    method: str | None = None
    ref: str | None = None
    run_context: RunContext | None = None
    config: object | None = None
    metadata: dict[str, object] = field(default_factory=dict)

    def payload_as(self, expected_type: type[T]) -> T:
        if not isinstance(self.payload, expected_type):
            raise TypeError(
                f"Hook payload for {self.hook_point!r} is "
                f"{type(self.payload).__name__}, expected {expected_type.__name__}"
            )
        return self.payload


@dataclass(frozen=True)
class EngineContext:
    """What an ``on_engine_start`` hook may observe about the built system.

    Intentionally read-only and minimal: hooks validate setup and initialize
    their own clients here, they do not reconfigure the engine.
    """

    system_name: str
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class McpRequestContext:
    """The MCP request a ``before_mcp_request`` hook may enrich.

    ``headers`` starts empty for each request; hooks add the headers they want
    applied (Authorization, tenant/correlation, HMAC signatures). Existing
    transport headers are never exposed here, so hooks cannot read another
    layer's credentials.

    ``operation`` is best-effort at the HTTP transport layer and defaults to
    ``"request"``; see docs/RUNTIME_HOOKS.md for the limitation.
    """

    server_id: str
    url: str
    operation: str = "request"
    tool_name: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)

    def with_headers(self, headers: dict[str, str]) -> McpRequestContext:
        """Return a copy with ``headers`` merged on top of the current headers."""
        return dataclasses.replace(self, headers={**self.headers, **headers})


ToolProvider = Literal["local", "mcp", "unknown"]
ToolStatus = Literal["succeeded", "failed"]


@dataclass(frozen=True)
class ToolCallContext:
    """A completed tool call observed by ``after_tool_call`` hooks.

    Side-effect oriented: hooks audit or emit metrics; they do not alter the
    result in the MVP. Arguments and full results are deliberately omitted —
    they may carry sensitive user data.
    """

    agent_id: str
    tool_name: str
    provider: ToolProvider
    server_id: str | None = None
    status: ToolStatus = "succeeded"
    latency_ms: int | None = None
    error: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)
