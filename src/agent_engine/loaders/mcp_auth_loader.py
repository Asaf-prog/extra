from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path


class MCPAuthLoader:
    """Loads per-MCP auth functions from plugins/mcp_auth/{mcp_id}.py.

    Each file must export an async callable ``get_headers() -> dict[str, str]``.
    If the file does not exist, get_headers() returns {} — no auth is the default.
    Loads plugins/resolvers/shared.py into sys.modules["shared"] before each
    plugin so auth functions can do ``from shared import ...``.
    """

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir
        self._shared_loaded = False

    async def get_headers(self, mcp_id: str) -> dict[str, str]:
        path = self._base_dir / "plugins" / "mcp_auth" / f"{mcp_id}.py"
        if not path.is_file():
            return {}
        self._ensure_shared()
        module = _import_from_path(path)
        fn = getattr(module, "get_headers", None)
        if fn is None or not callable(fn):
            return {}
        return await fn()

    def _ensure_shared(self) -> None:
        if self._shared_loaded:
            return
        self._shared_loaded = True
        shared_path = self._base_dir / "plugins" / "resolvers" / "shared.py"
        if shared_path.is_file():
            module = _import_from_path(shared_path)
            sys.modules.setdefault("shared", module)


def _import_from_path(path: Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
