"""Behaviour tests for HookManager execution semantics."""

from __future__ import annotations

import logging

import pytest

from agent_engine.core.spec import HooksConfig, HookSpec
from agent_engine.runtime.hooks.errors import HookExecutionError
from agent_engine.runtime.hooks.manager import HookManager
from agent_engine.runtime.hooks.models import (
    EngineContext,
    McpRequestContext,
    RunContext,
    ToolCallContext,
)
from tests.runtime.hooks import fixtures

_FIX = "tests.runtime.hooks.fixtures"


@pytest.fixture(autouse=True)
def _clear_calls() -> None:
    fixtures.CALLS.clear()


def _manager(*specs: HookSpec) -> HookManager:
    return HookManager.from_config(HooksConfig(hooks=specs))


async def test_executes_hooks_in_declaration_order() -> None:
    mgr = _manager(
        HookSpec("on_run_start", f"{_FIX}:sync_hook", {"n": 1}),
        HookSpec("on_run_start", f"{_FIX}:async_hook", {"n": 2}),
        HookSpec("on_run_start", f"{_FIX}:sync_hook", {"n": 3}),
    )
    await mgr.run_run_start(RunContext())
    assert [c[2]["n"] for c in fixtures.CALLS] == [1, 2, 3]


async def test_supports_sync_and_async_hooks() -> None:
    mgr = _manager(
        HookSpec("on_run_start", f"{_FIX}:sync_hook"),
        HookSpec("on_run_start", f"{_FIX}:async_hook"),
    )
    await mgr.run_run_start(RunContext())
    assert {c[0] for c in fixtures.CALLS} == {"sync", "async"}


async def test_supports_callable_class_hook() -> None:
    mgr = _manager(HookSpec("on_run_start", f"{_FIX}:CallableHook"))
    await mgr.run_run_start(RunContext())
    assert fixtures.CALLS[0][0] == "callable"


async def test_class_method_hook_receives_config_once_and_reuses_instance() -> None:
    fixtures.McpAuthHook.instances_created = 0
    mgr = _manager(
        HookSpec(
            "before_mcp_request",
            f"{_FIX}:McpAuthHook.before_mcp_request",
            {"audience": "internal-docs"},
        )
    )

    first = await mgr.run_before_mcp_request(
        RunContext(run_id="r1"), McpRequestContext(server_id="s", url="https://x/mcp")
    )
    second = await mgr.run_before_mcp_request(
        RunContext(run_id="r2"), McpRequestContext(server_id="s", url="https://x/mcp")
    )

    assert first.headers["X-Audience"] == "internal-docs"
    assert second.headers["X-Audience"] == "internal-docs"
    assert fixtures.McpAuthHook.instances_created == 1
    assert fixtures.CALLS[0][0] == "mcp_auth_method"
    assert fixtures.CALLS[1][0] == "mcp_auth_method"
    assert fixtures.CALLS[0][1] == fixtures.CALLS[1][1]
    assert [call[2] for call in fixtures.CALLS] == [1, 2]
    assert fixtures.CALLS[0][3] == {"audience": "internal-docs"}


async def test_passes_config_to_hook() -> None:
    mgr = _manager(HookSpec("on_engine_start", f"{_FIX}:sync_hook", {"audience": "mcp"}))
    await mgr.run_engine_start(EngineContext(system_name="s"))
    assert fixtures.CALLS[0][2] == {"audience": "mcp"}


async def test_run_start_returns_updated_context() -> None:
    mgr = _manager(HookSpec("on_run_start", f"{_FIX}:run_start_enrich", {"user_id": "alice"}))
    result = await mgr.run_run_start(RunContext(run_id="r1"))
    assert result.user_id == "alice"
    assert result.run_id == "r1"


async def test_before_mcp_request_returns_updated_request() -> None:
    mgr = _manager(HookSpec("before_mcp_request", f"{_FIX}:add_auth_header", {"token": "abc"}))
    req = await mgr.run_before_mcp_request(
        RunContext(), McpRequestContext(server_id="s", url="https://x/mcp")
    )
    assert req.headers["Authorization"] == "Bearer abc"


async def test_hook_failure_raises_with_point_and_ref() -> None:
    mgr = _manager(HookSpec("after_tool_call", f"{_FIX}:boom"))
    with pytest.raises(HookExecutionError) as exc:
        await mgr.run_after_tool_call(
            RunContext(), ToolCallContext(agent_id="a", tool_name="t", provider="local")
        )
    assert exc.value.point == "after_tool_call"
    assert exc.value.ref.endswith("boom")
    assert isinstance(exc.value.cause, RuntimeError)


async def test_failure_policy_warn_does_not_raise() -> None:
    mgr = _manager(HookSpec("after_tool_call", f"{_FIX}:boom", failure_policy="warn"))
    # Should swallow the error and continue.
    await mgr.run_after_tool_call(
        RunContext(), ToolCallContext(agent_id="a", tool_name="t", provider="local")
    )


async def test_run_error_hook_failure_is_swallowed() -> None:
    mgr = _manager(HookSpec("on_run_error", f"{_FIX}:boom"))
    # run_run_error must never raise — the original error is what matters.
    await mgr.run_run_error(RunContext(), ValueError("original"))


async def test_logs_do_not_leak_config_values(caplog: pytest.LogCaptureFixture) -> None:
    mgr = _manager(
        HookSpec("on_engine_start", f"{_FIX}:sync_hook", {"token_env": "SECRET_VALUE_XYZ"})
    )
    with caplog.at_level(logging.DEBUG, logger="agent_engine.runtime.hooks.manager"):
        await mgr.run_engine_start(EngineContext(system_name="s"))
    text = caplog.text
    assert "SECRET_VALUE_XYZ" not in text  # value never logged
    assert "token_env" in text  # key only, at DEBUG


def test_has_reports_declared_points() -> None:
    mgr = _manager(HookSpec("before_mcp_request", f"{_FIX}:add_auth_header"))
    assert mgr.has("before_mcp_request") is True
    assert mgr.has("after_tool_call") is False
