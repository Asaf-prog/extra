from __future__ import annotations

import importlib.util
import types
from collections.abc import Callable
from pathlib import Path
from typing import Any


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
        module = _import_from_path(path)
        fn = getattr(module, tool_id, None)
        if fn is None or not callable(fn):
            raise ToolLoaderError(f"{path} must export a callable named '{tool_id}'")
        return fn


def _import_from_path(path: Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
