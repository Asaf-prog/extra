# MCP & Tools

This document defines how executor agents use Python plugin tools and MCP
servers. Python plugin tools, remote MCP connection via `langchain-mcp-adapters`,
and LangChain binding of both as the model's tools are implemented.

---

## MCP Servers

MCP servers are declared once and referenced by agents:

```yaml
mcps:
  flights_mcp:
    url: "https://company.com/mcp/flights"

agents:
  domestic_flights_agent:
    description: "Search and book flights within the country."
    mcps: [flights_mcp]
```

MCP servers may be implemented in any language. Users only declare the server
URL in YAML; they do not write MCP client classes. During `build()`, the engine
creates one `MultiServerMCPClient` (from `langchain-mcp-adapters`) per configured
server, connects, and discovers its tools via `get_tools()`. A server that is
unreachable is logged as a warning and skipped, so local tools keep working.

The default remote transport is the official MCP Streamable HTTP transport.
The YAML contract remains URL-based; local process / stdio MCP servers are not
supported yet.

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

## Runtime Tool Boundary

Both local plugin tools and MCP tools are presented to the model as LangChain
tools, so the model cannot tell where a tool came from. The engine assembles an
agent's tools at **build time** (`_build_agent_tools`):

- each declared local tool is loaded from `plugins/tools/{id}.py` and wrapped as
  a `StructuredTool`;
- MCP tools come only from the servers listed in the agent's `mcps`, taken from
  the `MultiServerMCPClient.get_tools()` results discovered during `build()`.

Both are bound to the agent's model; the tool-call loop runs until the model
stops requesting tools. Each call is recorded in the run's `used_tools` with its
`provider` (`"local"` or `"mcp"`), so the origin is tracked for tracing even
though it is hidden from the model.

The engine is driven as an async context manager: `build()` connects MCP servers
and discovers tools; `close()` (on context exit) releases them. `run()` does not
connect MCP servers on its own — `build()` must run first.

```python
async with LangGraphEngine(base_dir) as engine:
    await engine.build(spec)   # connects MCP servers, discovers tools
    result = await engine.run(message)
```

## Runtime Tool Usage Summary

Every run collects deterministic tool-usage records (`RunResult.used_tools`) on
the runtime tool-execution path — in call order, not inferred from the final
answer or requested from the model. Records from tools called by nested agents
are merged up into the top-level result.

Rendering these records in `agentctl run` is ⏳ **planned** (not yet wired into
the CLI output). The intended format:

```text
tools used:

* ask_question [mcp: deepwiki] succeeded
* read_wiki_structure [mcp: deepwiki] succeeded
```

Local plugin tools are shown as `[local]`:

```text
tools used:

* book_flight [local] succeeded
```

If no tool was called, the CLI prints:

```text
tools used: none
```

Failed calls are shown with a concise error, without full tracebacks or tool
arguments:

```text
* ask_question [mcp: deepwiki] failed: request timed out
```

Every actual tool call is printed in call order. Repeated calls to the same
tool are printed repeatedly rather than collapsed into a count.

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
- create remote MCP clients from `mcps.<id>.url` via `langchain-mcp-adapters` (✅ implemented);
- discover MCP tool metadata during `build()` (✅ implemented);
- hide local-vs-MCP origin by presenting both as LangChain tools, while tracking
  the origin in `used_tools.provider` (✅ implemented);
- bind discovered MCP tools into LangGraph/LangChain tool-calling (✅ implemented);
- pass trusted request context through `ctx` into tool calls (⏳ planned —
  resolvers receive `ctx`, tools do not yet);
- redact secrets from traces (⏳ planned, task 0011);
- keep prompt wording out of the enforcement path.

Future per-tool access control should be added deliberately to the schema and
docs before implementation.

---

## Manual Smoke Test: DeepWiki Remote MCP

`examples/deepwiki_mcp_agents.yml` is a richer manual smoke-test configuration
for a real public remote MCP server. It demonstrates the intended user
experience for remote MCP: declare a server URL, grant an agent access with
`agent.mcps`, and let the platform create the generic MCP client automatically.

DeepWiki is used only as a public remote MCP example for validating runtime
integration. It is not part of `make check`, and automated tests do not call the
real service.

The MCP declaration is URL-only:

```yaml
mcps:
  deepwiki:
    url: "https://mcp.deepwiki.com/mcp"
```

The `deepwiki_agent` declares `mcps: [deepwiki]`, so its model may call tools
discovered from the DeepWiki MCP server. There is no stdio configuration,
command/args, authentication, custom client code, or DeepWiki-specific client
class. The MCP client handles connection and discovery during `build()`.

Validate the example offline, without contacting DeepWiki:

```bash
agentctl validate --config examples/deepwiki_mcp_agents.yml
```

Run the manual smoke test when provider dependencies and credentials are
available:

```bash
agentctl run --config examples/deepwiki_mcp_agents.yml \
  --message "Use DeepWiki to ask what the public GitHub repository modelcontextprotocol/python-sdk is about"
```

To stream the final assistant answer as it is generated, add `--stream`:

```bash
agentctl run --config examples/deepwiki_mcp_agents.yml --stream \
  --message "Use DeepWiki to explain what the public GitHub repository modelcontextprotocol/python-sdk is about."
```

Additional useful prompts (pass each via `--message`):

```bash
agentctl run --config examples/deepwiki_mcp_agents.yml \
  --message "Use DeepWiki to inspect the wiki structure for modelcontextprotocol/python-sdk."

agentctl run --config examples/deepwiki_mcp_agents.yml \
  --message "Use DeepWiki to explain the main modules in langchain-ai/langchain."
```

The current sample model uses Anthropic via LangChain, so install the optional
provider dependency (for example `langchain-anthropic`) and configure the
required provider credentials before running. This DeepWiki call is a manual
integration smoke test, not a unit test or CI requirement; automated tests stay
offline and deterministic.
