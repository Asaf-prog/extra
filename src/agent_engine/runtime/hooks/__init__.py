"""Runtime hooks: trusted code run automatically at fixed lifecycle points.

Hooks are distinct from tools. A *tool* is something the LLM may choose to call;
a *hook* is something the runtime executes automatically (auth, policy, audit,
context enrichment). Hooks are never exposed to the model.

See docs/RUNTIME_HOOKS.md for the full contract and enterprise MCP-auth example.
"""

from __future__ import annotations

from agent_engine.runtime.hooks.context import current_run_context
from agent_engine.runtime.hooks.errors import (
    HookError,
    HookExecutionError,
    HookLoadError,
    HookValidationError,
)
from agent_engine.runtime.hooks.loader import HookLoader
from agent_engine.runtime.hooks.manager import HookManager, LoadedHook
from agent_engine.runtime.hooks.mcp import HookedMCPAuth
from agent_engine.runtime.hooks.models import (
    HOOK_POINTS,
    AuthContext,
    EngineContext,
    HookInvocation,
    HookPoint,
    McpRequestContext,
    McpResponseContext,
    RunContext,
    RunEndContext,
    ToolCallContext,
    ToolRequestContext,
    ToolResultContext,
)

__all__ = [
    "HOOK_POINTS",
    "AuthContext",
    "EngineContext",
    "HookError",
    "HookExecutionError",
    "HookInvocation",
    "HookLoadError",
    "HookLoader",
    "HookManager",
    "HookPoint",
    "HookValidationError",
    "HookedMCPAuth",
    "LoadedHook",
    "McpRequestContext",
    "McpResponseContext",
    "RunContext",
    "RunEndContext",
    "ToolCallContext",
    "ToolRequestContext",
    "ToolResultContext",
    "current_run_context",
]
