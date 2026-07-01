from __future__ import annotations

from dataclasses import dataclass, field

from agent_engine.runtime.tool_models import ToolUsageRecord


@dataclass(frozen=True)
class RunResult:
    """The outcome of one completed run: the route taken, the answer, and the
    tools observed along the way."""

    system_name: str
    visited: list[str]
    answer: str
    used_tools: tuple[ToolUsageRecord, ...] = field(default_factory=tuple)
    input_tokens: int | None = None
    output_tokens: int | None = None
