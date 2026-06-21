"""Tests for the offline ``agentctl inspect`` command / diagnostics."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from agentctl.diagnostics import inspect_spec
from agentctl.main import cli

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = REPO_ROOT / "examples"


def _ex(name: str) -> str:
    return str(EXAMPLES / name)


def test_inspect_shows_mcp_server_ids() -> None:
    out = inspect_spec(_ex("local_mcp_agent.yml"))
    assert "mcp_servers: 1" in out
    assert "- local_demo" in out
    assert "url: http://127.0.0.1:8765/mcp" in out


def test_inspect_shows_tool_tags() -> None:
    out = inspect_spec(_ex("local_mcp_agent_invoices.yml"))
    assert "tool_tags: invoices" in out


def test_inspect_shows_default_header_transport() -> None:
    # invoices example uses no explicit transport -> default header is shown.
    out = inspect_spec(_ex("local_mcp_agent_invoices.yml"))
    assert "tool_tag_transport: header X-MCP-Tool-Tag (default)" in out


def test_inspect_shows_query_param_override() -> None:
    out = inspect_spec(_ex("local_mcp_agent_docs_query.yml"))
    assert "tool_tag_transport: query_param tag (override)" in out


def test_inspect_shows_hook_points_and_config_keys_only() -> None:
    out = inspect_spec(_ex("hooks_mcp_auth_agents.yml"))
    assert "hooks: 5" in out
    assert "before_mcp_request: plugin=mcp_auth method=before_mcp_request" in out
    # Config KEYS are shown...
    assert "config_keys: ['credential_env']" in out
    # ...but the VALUE (an env var name in this example) is NOT printed.
    assert "INTERNAL_MCP_CREDENTIAL" not in out


def test_inspect_does_not_print_token_like_values(tmp_path: Path) -> None:
    # A hook config whose key does not trip the YAML secret scanner, with a
    # non-secret-looking value; inspect must still print the key only.
    spec = tmp_path / "spec.yml"
    spec.write_text(
        "system: {name: t}\nagents: {a: {description: d}}\ngraph: {a: }\n"
        "hooks:\n  on_run_start:\n    - ref: company.x:f\n"
        "      config: {audience: my-private-value-123}\n",
        encoding="utf-8",
    )
    out = inspect_spec(str(spec))
    assert "config_keys: ['audience']" in out
    assert "my-private-value-123" not in out


def test_inspect_handles_no_hooks_and_no_tags() -> None:
    out = inspect_spec(_ex("deepwiki_mcp_agents.yml"))
    assert "hooks: 0" in out
    assert "tool_tags: (none)" in out
    assert "no hooks configured" in out


def test_inspect_shows_import_roots_resolved() -> None:
    out = inspect_spec(_ex("hooks_mcp_auth_agents.yml"))
    assert "import_roots:" in out
    assert str(REPO_ROOT) in out  # ".." resolved to the repo root


def test_inspect_shows_plugins_manifest() -> None:
    out = inspect_spec(_ex("local_mcp_agent.yml"))
    assert "plugins_manifest:" in out
    assert "exists: true" in out


def test_cli_inspect_exit_zero() -> None:
    runner = CliRunner()
    res = runner.invoke(cli, ["--log-level", "WARNING", "inspect", _ex("local_mcp_agent.yml")])
    assert res.exit_code == 0
    assert "system: Local MCP Demo" in res.output


def test_cli_inspect_missing_file_exits_nonzero() -> None:
    runner = CliRunner()
    res = runner.invoke(cli, ["--log-level", "WARNING", "inspect", "/no/such/spec.yml"])
    assert res.exit_code != 0


def test_cli_has_all_commands() -> None:
    # Regression: existing commands remain registered alongside validate/inspect.
    assert {"validate", "inspect", "run", "generate", "serve"} <= set(cli.commands)
