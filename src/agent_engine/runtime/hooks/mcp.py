"""Bridges ``before_mcp_request`` hooks into the httpx transport layer.

The platform talks to remote MCP servers through ``langchain-mcp-adapters`` /
the MCP SDK, which accept an ``httpx.Auth`` for per-request header injection
(this is the same seam :class:`MCPAuthLoader` uses). :class:`HookedMCPAuth`
runs the ``before_mcp_request`` hooks on every outgoing request and applies the
headers they produce.

Why per-request instead of per-session: an MCP client is created once at build
time and shared across runs, but each run has its own identity/auth. Reading the
active :class:`RunContext` from a context var at request time means a single
shared client can serve many tenants without the engine holding request state.

Transport limitation: at the HTTP layer the JSON-RPC ``operation``/``tool_name``
are inside the request body and not cheaply available, so ``operation`` defaults
to ``"request"``. Headers are applied for every MCP operation (connect,
list_tools, call_tool) which is what enterprise auth needs.

Response seam: ``httpx.Auth.async_auth_flow`` resumes after ``yield request``
with the response (``response = yield request``). This is a clean place to run
``after_mcp_response`` hooks with the HTTP status and latency — never the body or
headers. There is **no** clean ``on_mcp_error`` seam here: when the transport
itself raises (connection error), httpx propagates the exception *without*
throwing it back into this generator, so the error is not observable at the auth
layer. MCP *tool-call* failures are instead surfaced via ``on_tool_error`` at the
tool-execution seam. See docs/RUNTIME_HOOKS.md.
"""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncGenerator

import httpx

from agent_engine.runtime.hooks.context import current_run_context
from agent_engine.runtime.hooks.manager import HookManager
from agent_engine.runtime.hooks.models import McpRequestContext, McpResponseContext

logger = logging.getLogger(__name__)


class HookedMCPAuth(httpx.Auth):
    """An ``httpx.Auth`` that runs ``before_mcp_request`` hooks per request.

    ``base`` is an optional underlying auth (e.g. a per-MCP ``MCPAuthLoader``
    plugin) applied first; the hooks then add their headers on top. Header names
    and values are never logged — only the count.
    """

    def __init__(
        self, manager: HookManager, server_id: str, base: httpx.Auth | None = None
    ) -> None:
        self._manager = manager
        self._server_id = server_id
        self._base = base

    async def async_auth_flow(
        self, request: httpx.Request
    ) -> AsyncGenerator[httpx.Request, httpx.Response]:
        if self._base is not None:
            # Apply the underlying plugin auth's headers first. Header-injection
            # auth yields the request exactly once; multi-step response-driven
            # auth is out of scope for MCP header enrichment.
            async for prepared in self._base.async_auth_flow(request):
                request = prepared
                break

        run_context = current_run_context.get()
        mcp_request = McpRequestContext(
            server_id=self._server_id,
            url=str(request.url),
            operation="request",
        )
        mcp_request = await self._manager.run_before_mcp_request(run_context, mcp_request)

        for key, value in mcp_request.headers.items():
            request.headers[key] = value
        if mcp_request.headers:
            logger.debug(
                "before_mcp_request applied headers server=%s count=%d",
                self._server_id,
                len(mcp_request.headers),
            )

        start = time.perf_counter()
        response = yield request
        # Resumed by httpx with the response; observe-only. Body/headers are
        # never read or logged — only status and latency.
        latency_ms = int((time.perf_counter() - start) * 1000)
        if self._manager.has("after_mcp_response"):
            await self._manager.run_after_mcp_response(
                run_context,
                McpResponseContext(
                    server_id=self._server_id,
                    url=str(request.url),
                    status_code=response.status_code,
                    latency_ms=latency_ms,
                ),
            )
            logger.debug(
                "after_mcp_response server=%s status=%d ms=%d",
                self._server_id,
                response.status_code,
                latency_ms,
            )
