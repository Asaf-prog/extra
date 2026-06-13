# ADR 0009: Orchestrators are supervisor agents (children exposed as tools)

## Status

Accepted

## Context

The original design routed a request through the graph: each orchestrator used
LLM structured output (a `RouteDecision`) to pick exactly one child, wired as a
LangGraph **conditional edge**. Execution walked down a single path until it
reached a leaf agent, which produced the answer.

This had real limitations:

- **Single path only.** One request could reach exactly one leaf. A request that
  spans topics ("book a flight *and* add milk to my cart") could not be served.
- **Forced routing.** The router always chose *some* child, even when none
  matched, producing confidently wrong answers.
- **Routers added latency, not capability.** Intermediate orchestrators were a
  classification step, not a participant in the answer.
- **Trace conflated routing with execution.** The path taken and the tools used
  were entangled.

## Decision

Each orchestrator is itself an **LLM agent** whose children are exposed to it as
**callable tools** (the supervisor / agent-to-agent pattern).

- Every child (an agent or a nested orchestrator) becomes one `StructuredTool`
  with input schema `{message: str}`.
- The orchestrator reads its system prompt plus an engine-injected contract,
  decides which child tool(s) to call, collects their answers, and **synthesises**
  a final response. It may call several children for one request.
- The compiled LangGraph is **flat**: `START → root → END`. The whole child tree
  runs *inside* the root node's invocation; LangGraph schedules only the root.
  There are no conditional edges and no `RouteDecision`.
- **Access control** filters protected children out *before* they are exposed as
  tools — a child the caller may not reach is simply not offered to the LLM, so
  the model declines naturally instead of being blocked mid-run.
- **Trace.** `visited` records the full call-chain of node paths (merged up from
  nested calls). `used_tools` records only real tool/MCP calls (also merged up).
  Agent-to-agent calls are routing and live in `visited`, not `used_tools`.

## Consequences

- An orchestrator can fan out to multiple children and combine their results.
- A request with no matching child yields a natural "I'm not able to help with
  that" instead of forced misrouting.
- **Streaming:** only the root orchestrator streams its synthesised answer to the
  user; inner agents run silently (see RUNTIME_LIFECYCLE.md).
- **Cost scales with depth:** each orchestrator and agent uses its own chat
  model, so deep hierarchies multiply model calls. Keep hierarchies shallow.
- The LangGraph graph no longer mirrors the YAML topology one-to-one; the
  topology lives in the node tree assembled at build time.

## Alternatives Considered

1. **Structured-output routing to a single child (the previous design).**
   Rejected: single-path, forced routing, cannot combine children.
2. **Per-orchestrator LangGraph subgraphs with conditional edges.** Rejected:
   more machinery for the same single-path behaviour; combining results is hard.
3. **Hard-coded routing rules in YAML.** Rejected: brittle and not
   LLM-declarative.

## Enforcement

- The engine builds each orchestrator as an `OrchestratorNode` whose children are
  `StructuredTool`s; an injected contract instructs the model to answer only via
  tools and only within a tool's stated scope.
- Behaviour is covered by `tests/engine/test_engine_flow.py` (routing, nested
  tool-usage trace, protected-node filtering, root-only streaming).

## Related

- [ADR 0006 — Reusable node declarations and agent nodes](0006-reusable-agent-definitions-and-hierarchy-instances.md)
- [ADR 0007 — Build phase separate from runtime phase](0007-build-phase-separate-from-runtime-phase.md)
- [ADR 0008 — Model access via init_chat_model](0008-model-access-via-langchain-init-chat-model.md)
- Docs: [ARCHITECTURE.md](../ARCHITECTURE.md), [RUNTIME_LIFECYCLE.md](../RUNTIME_LIFECYCLE.md)
