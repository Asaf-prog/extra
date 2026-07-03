"""Shared by-path plugin loading, used by tool/resolver/MCP-auth loaders.

Client plugin files (a tool, a per-agent resolver, an MCP-auth function) live
under the YAML spec's `plugins/` directory, which is never added to `sys.path`.
They are loaded by file path instead of by import path. This is the one place
that implements that loading — `ToolLoader`, `ResolverLoader`, and
`MCPAuthLoader` all call into it rather than each re-implementing it.

Import-path plugins (e.g. hooks resolved from `plugins.toml` refs) are a
different, deliberate mechanism — see `runtime/hooks/loader.py` and
`import_roots.py` — and do not use this module.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path


def import_from_path(path: Path) -> types.ModuleType:
    """Load and execute the module at ``path``, independent of ``sys.path``."""
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def register_shared_module(resolvers_dir: Path) -> None:
    """Load ``resolvers_dir/shared.py`` (if present) into ``sys.modules["shared"]``.

    Lets plugin files do ``from shared import SharedResolver`` (or similar)
    without ``shared.py`` needing to be on the Python path. A no-op if
    ``shared.py`` does not exist, or if ``"shared"`` is already registered.
    """
    shared_path = resolvers_dir / "shared.py"
    if shared_path.is_file():
        module = import_from_path(shared_path)
        sys.modules.setdefault("shared", module)
