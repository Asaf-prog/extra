"""Importable hook callables used by loader/manager tests.

These exist as a real module so tests can reference them by import path exactly
the way a YAML ``ref`` would (``tests.runtime.hooks.fixtures:sync_hook``).
"""

from __future__ import annotations

from typing import Any

from agent_engine.runtime.hooks.models import McpRequestContext, RunContext

# A module-level sink so side-effect hooks can be observed without globals in
# the test bodies. Tests clear it before use.
CALLS: list[Any] = []


def sync_hook(context: Any, config: dict[str, Any]) -> None:
    CALLS.append(("sync", context, config))


async def async_hook(context: Any, config: dict[str, Any]) -> None:
    CALLS.append(("async", context, config))


def run_start_enrich(context: RunContext, config: dict[str, Any]) -> RunContext:
    return context.replace(user_id=config.get("user_id", "u-1"))


def add_auth_header(
    context: RunContext | None, request: McpRequestContext, config: dict[str, Any]
) -> McpRequestContext:
    request.headers["Authorization"] = f"Bearer {config.get('token', 'static')}"
    return request


def add_tenant_header(
    context: RunContext | None, request: McpRequestContext, config: dict[str, Any]
) -> McpRequestContext:
    return request.with_headers({"X-Tenant": config.get("tenant", "acme")})


def boom(*args: Any) -> None:
    raise RuntimeError("hook exploded")


class CallableHook:
    """A class hook: instantiated by the loader, called like a function."""

    def __call__(self, context: Any, config: dict[str, Any]) -> None:
        CALLS.append(("callable", context, config))


class McpAuthHook:
    """Method-style class hook used to prove one instance is reused."""

    instances_created = 0

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        type(self).instances_created += 1
        self.config = dict(config or {})
        self.calls = 0

    async def before_mcp_request(
        self, context: RunContext | None, request: McpRequestContext
    ) -> McpRequestContext:
        self.calls += 1
        CALLS.append(
            (
                "mcp_auth_method",
                id(self),
                self.calls,
                self.config,
                context,
            )
        )
        return request.with_headers({"X-Audience": str(self.config.get("audience", "default"))})


class MissingConfigConstructorHook:
    def __init__(self, one: object, two: object) -> None:
        self.one = one
        self.two = two

    def before_mcp_request(
        self, context: RunContext | None, request: McpRequestContext
    ) -> McpRequestContext:
        return request


class NonCallableMethodHook:
    before_mcp_request = 123


not_callable = 123


# -- engine-integration recording hooks (tagged by point) -------------------


def record_engine_start(context: Any, config: dict[str, Any]) -> None:
    CALLS.append(("on_engine_start", context))


def record_run_start(context: RunContext, config: dict[str, Any]) -> RunContext:
    CALLS.append(("on_run_start", context))
    return context.replace(metadata={**context.metadata, "seen": True})


def record_after_tool_call(context: Any, call: Any, config: dict[str, Any]) -> None:
    CALLS.append(("after_tool_call", call))


def record_run_error(context: Any, error: BaseException, config: dict[str, Any]) -> None:
    CALLS.append(("on_run_error", error))
