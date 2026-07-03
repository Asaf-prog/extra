"""Plugin import roots — make package-path plugin refs importable robustly.

Managed hooks (and any future import-path plugins) ultimately resolve to full
Python import paths from ``plugins.toml``, e.g.
``plugins.hooks.mcp_auth:McpAuthHook``. Such refs only resolve if their
top-level package is on ``sys.path``. Relying on the shell's current working
directory is fragile: launching the CLI from another directory breaks the
import.

This module centralizes the fix. A spec may declare ``plugins.import_roots``;
the engine resolves each root **relative to the agent YAML file** (not the CWD)
and registers it on ``sys.path`` exactly once, before any plugin is imported.
This is the single place that touches ``sys.path`` for plugins — callers must
not scatter their own manipulation.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Iterable
from pathlib import Path

logger = logging.getLogger(__name__)


class ImportRootError(RuntimeError):
    """A declared plugin import root could not be resolved to a directory."""


def resolve_import_roots(base_dir: Path, roots: Iterable[str]) -> list[Path]:
    """Resolve declared roots relative to ``base_dir`` (the YAML file's dir).

    Returns absolute, de-duplicated paths in declaration order. Raises
    :class:`ImportRootError` with a clear message if a root does not exist or is
    not a directory. Resolution is anchored on ``base_dir``, never the CWD.
    """
    resolved: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        path = (base_dir / root).resolve()
        if not path.is_dir():
            raise ImportRootError(
                f"plugin import root not found: {root!r} "
                f"(resolved to {path} relative to {base_dir})"
            )
        if path not in seen:
            seen.add(path)
            resolved.append(path)
    return resolved


def register_import_roots(base_dir: Path, roots: Iterable[str]) -> list[Path]:
    """Resolve and prepend plugin import roots to ``sys.path`` (idempotent).

    Roots already present on ``sys.path`` are not added again, so repeated
    builds do not grow it. With no roots this is a no-op, preserving existing
    behavior. Returns the resolved roots. Paths are not secrets and are safe to
    log at DEBUG.
    """
    resolved = resolve_import_roots(base_dir, roots)
    new = [str(p) for p in resolved if str(p) not in sys.path]
    if new:
        sys.path[:0] = new  # prepend, preserving declared order and precedence
        logger.debug("registered plugin import roots: %s", new)
    return resolved
