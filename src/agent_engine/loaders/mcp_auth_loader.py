from __future__ import annotations

from collections.abc import AsyncGenerator, Awaitable, Callable
from pathlib import Path

import httpx

from agent_engine.loaders._import import import_from_path, register_shared_module


class _PluginAuth(httpx.Auth):
    """Adapts a user ``get_headers()`` function to httpx's per-request auth flow.

    ``get_headers`` is awaited on *every* request, so the plugin owns token
    refresh: short-lived credentials (OAuth, etc.) stay fresh without a restart.
    """

    def __init__(self, get_headers: Callable[[], Awaitable[dict[str, str]]]) -> None:
        self._get_headers = get_headers

    async def async_auth_flow(
        self, request: httpx.Request
    ) -> AsyncGenerator[httpx.Request, httpx.Response]:
        headers = await self._get_headers()
        for key, value in headers.items():
            request.headers[key] = value
        yield request


class MCPAuthLoader:
    """Loads per-MCP auth functions from plugins/mcp_auth/{mcp_id}.py.

    Each file must export an async callable ``get_headers() -> dict[str, str]``.
    If the file does not exist, get_auth() returns None — no auth is the default.
    Loads plugins/resolvers/shared.py into sys.modules["shared"] before each
    plugin so auth functions can do ``from shared import ...``.
    """

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir
        self._shared_loaded = False

    def get_auth(self, mcp_id: str) -> httpx.Auth | None:
        """Return an httpx.Auth for the server, or None if no auth plugin exists.

        The returned auth re-invokes the plugin's get_headers() on every request,
        so rotating credentials are resolved fresh per call rather than frozen.
        """
        path = self._base_dir / "plugins" / "mcp_auth" / f"{mcp_id}.py"
        if not path.is_file():
            return None
        self._ensure_shared()
        module = import_from_path(path)
        fn = getattr(module, "get_headers", None)
        if fn is None or not callable(fn):
            return None
        return _PluginAuth(fn)

    def _ensure_shared(self) -> None:
        if self._shared_loaded:
            return
        self._shared_loaded = True
        register_shared_module(self._base_dir / "plugins" / "resolvers")
