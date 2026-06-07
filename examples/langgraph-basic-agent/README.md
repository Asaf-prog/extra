# LangGraph Basic Agent Example

This standalone example shows a small, deterministic agent workflow built with
LangGraph and LangChain-compatible tools. It is for learning, comparison, and
future integration reference.

It is **not** the main product runtime. The project still plans to validate YAML,
compile it into its own `CompiledAgentGraph`, and execute requests through its
own long-lived `RuntimeEngine` and per-request `ExecutionContext`.

## What It Demonstrates

- How LangGraph models graph state, nodes, edges, and conditional routing.
- How a LangChain tool can wrap a deterministic local Python function.
- How execution can record trace-like steps in state.
- How a graph-based workflow can route between a general-answer path and a
  tool-backed path.

The default behavior is mock-first and local. It does not call an LLM, OpenAI,
MCP server, database, or third-party API.

## Install

```bash
cd examples/langgraph-basic-agent
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

The dependency constraints are intentionally broad and modern. If LangChain or
LangGraph release breaking changes, adjust the versions in `pyproject.toml`.

## Run

```bash
python -m langgraph_basic_agent.main
```

You can also pass your own message:

```bash
python -m langgraph_basic_agent.main "count words in this short sentence"
```

Expected output includes the input message, route, final answer, and execution
steps.

## Test

```bash
pytest
```

The tests are deterministic and do not call real external services.

## Graph Structure

```text
START
  -> route_request
  -> answer_general      when route == "general"
  -> answer_with_tool    when route == "tool"
  -> finalize_response
  -> END
```

State fields:

- `message` — user input.
- `route` — router decision (`general` or `tool`).
- `tool_result` — deterministic local tool output.
- `answer` — intermediate answer before final formatting.
- `final_response` — final user-facing response.
- `steps` — trace-like execution steps.

## How This Relates To The Main Project

LangGraph provides an existing graph execution model where Python node functions
update shared state and edges control the next node. LangChain provides common
interfaces for tools, prompts, and model integrations.

The main project remains independent: it plans to compile declarative YAML into
its own internal `CompiledAgentGraph`, create a long-lived `RuntimeEngine`, and
create a fresh `ExecutionContext` per request. This example helps contributors
compare those planned concepts with an existing ecosystem. Future integration
may be considered, but the core architecture does not depend on LangGraph unless
a formal ADR decides that later.

## Optional OpenAI Experiments

The example includes `langchain-openai` as an optional dependency group for
contributors who want to experiment later:

```bash
pip install -e ".[openai]"
cp .env.example .env
```

The checked-in code does not require an API key and does not read `.env` by
default.
