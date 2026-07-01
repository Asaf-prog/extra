from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from agent_engine.loaders._import import import_from_path


class ToolLoaderError(RuntimeError):
    pass


class ToolLoader:
    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir

    def load(self, tool_id: str) -> Callable[..., Any]:
        path = self._base_dir / "plugins" / "tools" / f"{tool_id}.py"
        if not path.is_file():
            raise ToolLoaderError(
                f"Tool plugin not found: {path}\nRun `agentctl generate` to create the stub."
            )
        module = import_from_path(path)
        fn = getattr(module, tool_id, None)
        if fn is None or not callable(fn):
            raise ToolLoaderError(f"{path} must export a callable named '{tool_id}'")
        return fn
