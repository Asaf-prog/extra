from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from concurrent.futures import Future
from typing import Any, Protocol, runtime_checkable

from agent_engine.runtime.tool_models import MCPToolDefinition

logger = logging.getLogger(__name__)


class MCPManagerError(RuntimeError):
    pass


@runtime_checkable
class MCPClientProtocol(Protocol):
    async def connect(self) -> None: ...
    async def close(self) -> None: ...
    async def list_tools(self) -> list[MCPToolDefinition]: ...
    async def call_tool(self, name: str, arguments: dict[str, object]) -> object: ...


MCPClientFactory = Callable[[str, Any], MCPClientProtocol]


def _default_client_factory(server_id: str, config: Any) -> MCPClientProtocol:
    from agent_engine.runtime.remote_mcp_client import GenericRemoteMCPClient
    return GenericRemoteMCPClient(server_id=server_id, url=config.url)


class MCPManager:
    """Owns MCP clients, discovered tools, and MCP tool execution."""

    def __init__(
        self,
        mcp_configs: dict[str, Any],
        client_factory: MCPClientFactory | None = None,
    ) -> None:
        self._mcp_configs = mcp_configs
        self._client_factory = client_factory or _default_client_factory
        self._clients: dict[str, MCPClientProtocol] = {}
        self._tools_by_server: dict[str, list[MCPToolDefinition]] = {}
        self._owner_loop: asyncio.AbstractEventLoop | None = None

    async def start(self) -> None:
        self._owner_loop = asyncio.get_running_loop()
        for server_id, config in self._mcp_configs.items():
            client = self._client_factory(server_id, config)
            try:
                await client.connect()
                tools = await client.list_tools()
            except Exception as exc:
                raise MCPManagerError(
                    f"MCP server '{server_id}' failed to start: {exc}"
                ) from exc
            self._clients[server_id] = client
            self._tools_by_server[server_id] = tools
            logger.info("MCP server=%s connected, tools=%d", server_id, len(tools))

    async def stop(self) -> None:
        errors: list[str] = []
        for server_id, client in self._clients.items():
            try:
                await client.close()
            except Exception as exc:
                errors.append(f"{server_id}: {exc}")
        self._clients.clear()
        self._tools_by_server.clear()
        self._owner_loop = None
        if errors:
            raise MCPManagerError("Failed to close MCP clients: " + "; ".join(errors))

    def list_tools(self, server_id: str) -> list[MCPToolDefinition]:
        if server_id not in self._mcp_configs:
            raise MCPManagerError(f"Unknown MCP server '{server_id}'.")
        return list(self._tools_by_server.get(server_id, []))

    async def call_tool(
        self, *, server_id: str, tool_name: str, arguments: dict[str, object]
    ) -> object:
        owner_loop = self._owner_loop
        running_loop = asyncio.get_running_loop()
        if owner_loop is not None and owner_loop is not running_loop:
            future: Future[object] = asyncio.run_coroutine_threadsafe(
                self._call(server_id, tool_name, arguments), owner_loop
            )
            return await asyncio.wrap_future(future)
        return await self._call(server_id, tool_name, arguments)

    async def _call(self, server_id: str, tool_name: str, arguments: dict[str, object]) -> object:
        if server_id not in self._clients:
            raise MCPManagerError(f"MCP server '{server_id}' is not started.")
        known = {t.name for t in self.list_tools(server_id)}
        if tool_name not in known:
            raise MCPManagerError(f"Unknown MCP tool '{tool_name}' for server '{server_id}'.")
        started = time.perf_counter()
        try:
            result = await self._clients[server_id].call_tool(tool_name, arguments)
        except Exception as exc:
            raise MCPManagerError(
                f"MCP tool '{tool_name}' on server '{server_id}' failed: {exc}"
            ) from exc
        logger.info("MCP tool=%s on server=%s took %dms", tool_name, server_id,
                    int((time.perf_counter() - started) * 1000))
        return result
