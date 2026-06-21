# Local demo MCP server

A small, dependency-light MCP server for **end-to-end smoke testing** of the
agent platform without relying on a public MCP server. It verifies:

- a real (local) remote MCP connection and **tool discovery**;
- optional **`tool_tags`** — tools are listed *per request* from the
  `X-MCP-Tool-Tag` header or a `?tag=` query param;
- **`before_mcp_request` / auth header injection** — `server_info` and `echo`
  report a *safe* summary of the received auth/identity headers (presence only).

It uses the MCP SDK's low-level `Server` + `StreamableHTTPSessionManager`
(already pulled in via `mcp` / `langchain-mcp-adapters`) — no new dependencies,
no Docker.

## Tools

| Group | Tools |
|-------|-------|
| `invoices` | `list_invoices`, `get_invoice`, `invoice_summary` |
| `customers` | `list_customers`, `get_customer`, `customer_summary` |
| `docs` | `search_docs`, `get_doc` |
| `debug` (always exposed) | `echo`, `server_info` |

All data is deterministic and in-memory.

## 1. Start the server

```bash
poetry run python -m examples.local_mcp_server.server
```

Serves Streamable HTTP at **`http://127.0.0.1:8765/mcp`**. Override with env vars:
`LOCAL_MCP_HOST`, `LOCAL_MCP_PORT`, `LOCAL_MCP_PATH`.

## 2. Run the agent against it

In a second terminal (set your model key, e.g. `ANTHROPIC_API_KEY`, first):

```bash
# No tags — discovers ALL tools
agentctl run --config examples/local_mcp_agent.yml --message "What tools do you have?"

# invoices tag (default header transport X-MCP-Tool-Tag: invoices)
agentctl run --config examples/local_mcp_agent_invoices.yml --message "List the invoices"

# customers tag
agentctl run --config examples/local_mcp_agent_customers.yml --message "List the customers"

# docs tag via the query_param transport override (?tag=docs)
agentctl run --config examples/local_mcp_agent_docs_query.yml --message "Search docs for billing"
```

Add `--log-level DEBUG` **before** the subcommand to see detail:

```bash
agentctl --log-level DEBUG run --config examples/local_mcp_agent_invoices.yml --message "List the invoices"
```

## 3. Verifying tag behavior

| Config | `X-MCP-Tool-Tag` / `?tag=` | Tools discovered |
|--------|----------------------------|------------------|
| `local_mcp_agent.yml` | (none) | all 10 |
| `local_mcp_agent_invoices.yml` | `invoices` | 3 invoice + `echo`, `server_info` |
| `local_mcp_agent_customers.yml` | `customers` | 3 customer + `echo`, `server_info` |
| `local_mcp_agent_docs_query.yml` | `?tag=docs` | 2 docs + `echo`, `server_info` |

Multiple tags (e.g. `tool_tags: ["invoices", "customers"]`) return the **union**.
Selection is **server-side**: the server reads the selector and advertises the
matching tools; the platform does no local filtering.

## 4. Verifying auth / header injection (hooks)

Wire a `before_mcp_request` hook (see [docs/RUNTIME_HOOKS.md](../../docs/RUNTIME_HOOKS.md))
to inject an `Authorization` header, then ask the agent to call `server_info` or
`echo`. The returned `received_auth` shows e.g.:

```json
{ "authorization_present": true, "auth_scheme": "Bearer",
  "organization_id": "org-7", "correlation_id": null, "tool_tag": "invoices" }
```

The **token value is never returned or logged** — only presence and scheme.

Optional strict mode: start the server with `LOCAL_MCP_REQUIRE_AUTH=true` to make
it reject requests that arrive without an `Authorization` header.

## 5. Logs to expect

Server (safe by design — never logs tokens/secrets/payloads):

```
INFO local_mcp_server: starting local-mcp-demo v0.1.0 on http://127.0.0.1:8765/mcp
INFO local_mcp_server: list_tools request: tags=1 tools=5 auth_present=True scheme=Bearer org=org-7
INFO local_mcp_server: call_tool: invoice_summary
```

Platform side (`--log-level DEBUG`): `mcp tool_tags configured ... default_transport=...`,
`mcp discovery started`, `mcp connected server=local_demo tools=N`.

## 6. Known limitations

- **Per-request tool listing** relies on the MCP SDK exposing the Starlette
  request in the server's `request_context` (true for Streamable HTTP). If a
  future transport does not, `list_tools` falls back to returning **all** tools
  and the `echo`/`server_info` tools still report the received metadata.
- The server runs in **stateless** Streamable HTTP mode (`json_response=True`) —
  fine for request/response tools; it does not keep MCP sessions or stream
  partial results.
- Tag → tool-group mapping is server-defined here; a real server decides its own
  grouping. This demo treats unknown tags as "no group" (only debug tools shown).
