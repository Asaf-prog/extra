"""Tests for the local demo MCP server example.

Pure tag/auth logic and YAML parsing run in-process. A real Streamable HTTP
integration test starts the server on a free localhost port and connects via the
platform's MCP client; it skips cleanly if the server does not come up and never
touches the external network.
"""

from __future__ import annotations

import asyncio
import socket
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from examples.local_mcp_server.tags import (
    DEFAULT_TAG_HEADER,
    auth_summary,
    parse_tags,
    select_tool_names,
)

from agent_engine.engine.langgraph.helpers import collect_mcp_specs
from agent_engine.parsers.yaml.parser import YAMLParser

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = REPO_ROOT / "examples"


# -- pure logic --------------------------------------------------------------


def test_server_module_imports() -> None:
    from examples.local_mcp_server import server

    srv = server.build_server()
    assert srv.name == "local-mcp-demo"


def test_parse_tags_from_header() -> None:
    assert parse_tags("invoices", None) == ("invoices",)


def test_parse_tags_from_query() -> None:
    assert parse_tags(None, "customers") == ("customers",)


def test_parse_tags_multiple_deduped() -> None:
    assert parse_tags("invoices, customers , invoices", None) == ("invoices", "customers")


def test_no_tag_returns_all_tools() -> None:
    names = select_tool_names(())
    assert "list_invoices" in names
    assert "list_customers" in names
    assert "search_docs" in names
    assert "server_info" in names
    assert len(names) == 10


def test_invoices_tag_returns_group_plus_debug() -> None:
    names = select_tool_names(("invoices",))
    assert set(names) == {"list_invoices", "get_invoice", "invoice_summary", "echo", "server_info"}


def test_unknown_tag_returns_only_debug() -> None:
    assert set(select_tool_names(("nope",))) == {"echo", "server_info"}


def test_auth_summary_never_exposes_token() -> None:
    summary = auth_summary(
        {"Authorization": "Bearer super-secret-token-xyz", "X-Organization-Id": "org-7"}
    )
    assert summary["authorization_present"] is True
    assert summary["auth_scheme"] == "Bearer"
    assert summary["organization_id"] == "org-7"
    # The token value appears nowhere in the summary.
    assert "super-secret-token-xyz" not in str(summary)


def test_auth_summary_missing_authorization() -> None:
    summary = auth_summary({})
    assert summary["authorization_present"] is False
    assert summary["auth_scheme"] is None


def test_default_tag_header_constant() -> None:
    assert DEFAULT_TAG_HEADER == "X-MCP-Tool-Tag"


# -- example YAML parsing ----------------------------------------------------


@pytest.mark.parametrize(
    "name,tags",
    [
        ("local_mcp_agent.yml", ()),
        ("local_mcp_agent_invoices.yml", ("invoices",)),
        ("local_mcp_agent_customers.yml", ("customers",)),
        ("local_mcp_agent_docs_query.yml", ("docs",)),
    ],
)
def test_example_yaml_parses(name: str, tags: tuple[str, ...]) -> None:
    spec = YAMLParser().parse(str(EXAMPLES / name))
    assert collect_mcp_specs(spec.graph)["local_demo"].tool_tags == tags


def test_query_param_example_uses_override_transport() -> None:
    spec = YAMLParser().parse(str(EXAMPLES / "local_mcp_agent_docs_query.yml"))
    transport = collect_mcp_specs(spec.graph)["local_demo"].tool_tag_transport
    assert transport is not None
    assert transport.type == "query_param"
    assert transport.param_name == "tag"


def test_deepwiki_example_still_parses() -> None:
    spec = YAMLParser().parse(str(EXAMPLES / "deepwiki_mcp_agents.yml"))
    assert collect_mcp_specs(spec.graph)["deepwiki"].tool_tags == ()


# -- in-process Streamable HTTP integration ---------------------------------


@pytest.fixture(scope="module")
def server_url() -> Iterator[str]:
    """Start the demo server on a free localhost port; skip if it won't come up."""
    import uvicorn
    from examples.local_mcp_server.server import build_app

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    # ws="none": HTTP-only server — skip uvicorn's websockets protocol (and its
    # third-party deprecation warnings) since it is never used here.
    config = uvicorn.Config(
        build_app(), host="127.0.0.1", port=port, log_level="critical", ws="none"
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    ready = False
    for _ in range(50):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                ready = True
                break
        except OSError:
            time.sleep(0.1)
    if not ready:
        server.should_exit = True
        pytest.skip("local MCP server did not start")

    try:
        yield f"http://127.0.0.1:{port}/mcp"
    finally:
        server.should_exit = True
        thread.join(timeout=5)


async def _discover(url: str, *, headers: dict | None = None) -> list[str]:
    from langchain_mcp_adapters.client import MultiServerMCPClient

    config: dict = {"url": url, "transport": "streamable_http"}
    if headers:
        config["headers"] = headers
    client = MultiServerMCPClient({"local": config})  # type: ignore[dict-item]
    tools = await asyncio.wait_for(client.get_tools(), timeout=15)
    return sorted(t.name for t in tools)


async def test_discovery_no_tag_returns_all(server_url: str) -> None:
    names = await _discover(server_url)
    assert len(names) == 10
    assert "list_invoices" in names and "list_customers" in names


async def test_discovery_with_invoices_header(server_url: str) -> None:
    names = await _discover(server_url, headers={"X-MCP-Tool-Tag": "invoices"})
    assert set(names) == {"echo", "get_invoice", "invoice_summary", "list_invoices", "server_info"}


async def test_discovery_with_query_param(server_url: str) -> None:
    names = await _discover(server_url + "?tag=customers")
    assert "list_customers" in names
    assert "list_invoices" not in names  # other group excluded


async def test_tool_call_returns_deterministic_data(server_url: str) -> None:
    from langchain_mcp_adapters.client import MultiServerMCPClient

    client = MultiServerMCPClient(
        {
            "local": {
                "url": server_url,
                "transport": "streamable_http",
                "headers": {"X-MCP-Tool-Tag": "invoices"},
            }
        }
    )
    tools = await asyncio.wait_for(client.get_tools(), timeout=15)
    summary = next(t for t in tools if t.name == "invoice_summary")
    result = await asyncio.wait_for(summary.ainvoke({}), timeout=15)
    assert "total_amount" in str(result)
