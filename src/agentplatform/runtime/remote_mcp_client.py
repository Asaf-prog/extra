from __future__ import annotations

from contextlib import AsyncExitStack, suppress
from typing import Any, ClassVar, Protocol
from urllib.parse import urlparse

from agentplatform.runtime.mcp_manager import MCPClientProtocol
from agentplatform.runtime.tool_models import MCPToolDefinition


class RemoteMCPClientError(RuntimeError):
    """Raised when the generic remote MCP client cannot complete an operation."""


class AsyncContextManagerFactory(Protocol):
    def __call__(self, url: str) -> Any: ...


class SessionFactory(Protocol):
    def __call__(self, read_stream: Any, write_stream: Any) -> Any: ...


class GenericRemoteMCPClient(MCPClientProtocol):
    """Generic URL-based MCP client backed by the official MCP Python SDK.

    The rest of the runtime sees only ``MCPClientProtocol`` and
    ``MCPToolDefinition``. SDK-specific session, transport, and result objects
    stay inside this adapter.
    """

    _SUPPORTED_TRANSPORTS: ClassVar[set[str]] = {"streamable_http", "streamable-http"}

    def __init__(
        self,
        *,
        server_id: str,
        url: str,
        transport: str = "streamable_http",
        transport_factory: AsyncContextManagerFactory | None = None,
        session_factory: SessionFactory | None = None,
    ) -> None:
        self.server_id = server_id
        self.url = _validate_url(server_id, url)
        self.transport = _normalize_transport(server_id, transport)
        self._transport_factory = transport_factory or _streamable_http_transport
        self._session_factory = session_factory or _client_session
        self._exit_stack: AsyncExitStack | None = None
        self._session: Any | None = None

    async def connect(self) -> None:
        if self._session is not None:
            return

        stack = AsyncExitStack()
        try:
            try:
                streams = await stack.enter_async_context(self._transport_factory(self.url))
            except Exception as exc:
                raise RemoteMCPClientError(
                    f"MCP server '{self.server_id}' failed to connect to '{self.url}': {exc}"
                ) from exc

            read_stream, write_stream = _extract_transport_streams(self.server_id, streams)
            session = await stack.enter_async_context(
                self._session_factory(read_stream, write_stream)
            )

            try:
                await session.initialize()
            except Exception as exc:
                raise RemoteMCPClientError(
                    f"MCP server '{self.server_id}' failed to initialize MCP session: {exc}"
                ) from exc

            self._exit_stack = stack
            self._session = session
        except Exception:
            await _close_stack_quietly(stack)
            raise

    async def close(self) -> None:
        stack = self._exit_stack
        self._exit_stack = None
        self._session = None

        if stack is None:
            return

        try:
            await stack.aclose()
        except Exception as exc:
            raise RemoteMCPClientError(
                f"MCP server '{self.server_id}' failed to close MCP session: {exc}"
            ) from exc

    async def list_tools(self) -> list[MCPToolDefinition]:
        session = self._require_session()

        try:
            result = await session.list_tools()
        except Exception as exc:
            raise RemoteMCPClientError(
                f"MCP server '{self.server_id}' failed to discover tools: {exc}"
            ) from exc

        tools = getattr(result, "tools", None)
        if not isinstance(tools, list):
            raise RemoteMCPClientError(
                f"MCP server '{self.server_id}' returned invalid tools/list response."
            )

        return [_tool_definition_from_sdk_tool(self.server_id, tool) for tool in tools]

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, object],
    ) -> object:
        session = self._require_session()

        try:
            result = await session.call_tool(name, arguments)
        except Exception as exc:
            raise RemoteMCPClientError(
                f"MCP tool '{name}' on server '{self.server_id}' failed: {exc}"
            ) from exc

        return _normalize_call_tool_result(self.server_id, name, result)

    def _require_session(self) -> Any:
        if self._session is None:
            raise RemoteMCPClientError(
                f"MCP server '{self.server_id}' client used before connect()."
            )
        return self._session


def _validate_url(server_id: str, url: str) -> str:
    if not url:
        raise RemoteMCPClientError(f"MCP server '{server_id}' must define a non-empty URL.")

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RemoteMCPClientError(
            f"MCP server '{server_id}' has invalid URL '{url}'. "
            "Remote MCP URLs must be absolute http(s) URLs."
        )

    return url


def _normalize_transport(server_id: str, transport: str) -> str:
    if transport not in GenericRemoteMCPClient._SUPPORTED_TRANSPORTS:
        raise RemoteMCPClientError(
            f"MCP server '{server_id}' has unsupported remote MCP transport "
            f"'{transport}'. Supported transport: streamable_http."
        )
    return "streamable_http"


def _streamable_http_transport(url: str) -> Any:
    try:
        from mcp.client.streamable_http import streamable_http_client
    except ImportError as exc:  # pragma: no cover - exercised only without dependency installed.
        raise RemoteMCPClientError(
            "The official MCP Python SDK is required for remote MCP clients. "
            'Install the project with the "mcp>=1.27,<2" dependency.'
        ) from exc

    return streamable_http_client(url)


def _client_session(read_stream: Any, write_stream: Any) -> Any:
    try:
        from mcp import ClientSession
    except ImportError as exc:  # pragma: no cover - exercised only without dependency installed.
        raise RemoteMCPClientError(
            "The official MCP Python SDK is required for remote MCP clients. "
            'Install the project with the "mcp>=1.27,<2" dependency.'
        ) from exc

    return ClientSession(read_stream, write_stream)


def _extract_transport_streams(server_id: str, streams: object) -> tuple[object, object]:
    if not isinstance(streams, tuple) or len(streams) < 2:
        raise RemoteMCPClientError(f"MCP server '{server_id}' returned invalid transport streams.")

    return streams[0], streams[1]


def _tool_definition_from_sdk_tool(server_id: str, tool: object) -> MCPToolDefinition:
    name = getattr(tool, "name", None)
    if not isinstance(name, str) or not name:
        raise RemoteMCPClientError(
            f"MCP server '{server_id}' returned invalid tool metadata: missing tool name."
        )

    description = getattr(tool, "description", "") or ""
    if not isinstance(description, str):
        raise RemoteMCPClientError(
            f"MCP server '{server_id}' returned invalid metadata for tool '{name}'."
        )

    schema = getattr(tool, "inputSchema", None)
    if schema is None:
        schema = getattr(tool, "input_schema", None)
    if schema is None:
        schema = {}

    parameters_schema = _json_object(server_id, name, schema)
    return MCPToolDefinition(
        server_id=server_id,
        name=name,
        description=description,
        parameters_schema=parameters_schema,
    )


def _json_object(server_id: str, tool_name: str, value: object) -> dict[str, object]:
    if hasattr(value, "model_dump"):
        value = value.model_dump(by_alias=True, mode="json")

    if isinstance(value, dict):
        return dict(value)

    raise RemoteMCPClientError(
        f"MCP server '{server_id}' returned invalid parameters schema for tool '{tool_name}'."
    )


def _normalize_call_tool_result(server_id: str, tool_name: str, result: object) -> object:
    if bool(getattr(result, "isError", False)):
        raise RemoteMCPClientError(
            f"MCP tool '{tool_name}' on server '{server_id}' returned error."
        )

    structured = getattr(result, "structuredContent", None)
    if structured is None:
        structured = getattr(result, "structured_content", None)
    if structured is not None:
        return _json_value(structured)

    content = getattr(result, "content", None)
    if isinstance(content, list):
        normalized = [_normalize_content_block(block) for block in content]
        if len(normalized) == 1:
            return normalized[0]
        return normalized

    raise RemoteMCPClientError(
        f"MCP tool '{tool_name}' on server '{server_id}' returned an unsupported result shape."
    )


def _normalize_content_block(block: object) -> object:
    text = getattr(block, "text", None)
    if isinstance(text, str):
        return text

    return _json_value(block)


def _json_value(value: object) -> object:
    if hasattr(value, "model_dump"):
        return value.model_dump(by_alias=True, mode="json")
    return value


async def _close_stack_quietly(stack: AsyncExitStack) -> None:
    with suppress(Exception):
        await stack.aclose()
