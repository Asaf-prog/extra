# MCP & Tools

This document defines how executor agents use Python plugin tools and MCP
servers. Python plugin tools are implemented; MCP client integration is planned
(task `0007`).

---

## MCP Servers

MCP servers are declared once and referenced by agents:

```yaml
mcps:
  flights_mcp:
    url: "https://company.com/mcp/flights/sse"

agents:
  domestic_flights_agent:
    description: "Search and book flights within the country."
    mcps: [flights_mcp]
```

MCP servers may be implemented in any language. The engine connects to them from
the long-lived runtime and exposes their discovered tools to configured agents.

---

## Python Plugin Tools

Tools are Python plugin methods exposed to the LLM at runtime. Each tool is
declared with a description in YAML and implemented as a callable in
`plugins/tools/{tool_id}.py`:

```yaml
tools:
  book_flight:
    description: "Search and book a flight given origin, destination and travel date"

agents:
  domestic_flights_agent:
    description: "Search and book flights within the country."
    tools: [book_flight]
```

Plugin file (`plugins/tools/book_flight.py`):

```python
def book_flight() -> str:
    """Search and book a flight given origin, destination and travel date."""
    raise NotImplementedError
```

Run `agentctl generate` to create tool stubs. The engine loads each tool once at
graph-build time and wraps it as a LangChain `StructuredTool`. At runtime, only
the agent's declared tools are bound to its LLM, and a tool-call loop runs until
the model stops requesting tools.

---

## Resolver vs. Tool Boundary

| | Resolver | Tool |
| --- | --- | --- |
| Runs | Before the node runs | During LLM execution |
| Chosen by | Engine | LLM |
| Exposed to LLM | No | Yes |
| Token cost | None | Yes |
| Purpose | Fill prompt variables | Perform actions |

Use a resolver for deterministic context such as `current_date`, `user_name`, or
`subscription`. Use a tool for model-selected actions such as `book_flight` or
`add_to_cart`.

---

## Safety

The current schema does not yet define per-tool permissions or input policies.
For the MVP:

- validate that every agent tool id exists in top-level `tools` (✅ implemented);
- validate that every agent MCP id exists in top-level `mcps` (✅ implemented);
- load tool plugins from `plugins/tools/{tool_id}.py` (✅ implemented);
- bind only the agent's declared tools per node (✅ implemented);
- pass request context through `ctx` (✅ implemented);
- redact secrets from traces (⏳ planned, task 0011);
- keep prompt wording out of the enforcement path.

Future per-tool access control should be added deliberately to the schema and
docs before implementation.
