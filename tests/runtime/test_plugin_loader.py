"""Runtime plugin loader behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentplatform.runtime import ExecutionContext
from agentplatform.runtime.plugin_loader import PluginLoader, ResolverPluginError


def _write_resolver_plugin(
    base_dir: Path,
    *,
    agent_body: str,
    base_body: str = "class BaseResolver:\n    pass\n",
    base_class_path: str = "plugins.resolvers.base.BaseResolver",
    agent_class_path: str = "plugins.resolvers.domestic_flights_agent.DomesticFlightsAgentResolver",
    dependencies: str = "",
) -> None:
    resolvers_dir = base_dir / "plugins" / "resolvers"
    resolvers_dir.mkdir(parents=True)
    (resolvers_dir / "__init__.py").write_text('"""Resolvers."""\n', encoding="utf-8")
    (resolvers_dir / "base.py").write_text(
        f"from agentplatform.runtime import ExecutionContext\n\n{base_body}",
        encoding="utf-8",
    )
    (resolvers_dir / "domestic_flights_agent.py").write_text(
        "from agentplatform.runtime import ExecutionContext\n"
        "from plugins.resolvers.base import BaseResolver\n\n"
        f"{agent_body}",
        encoding="utf-8",
    )
    (resolvers_dir / "resolvers.toml").write_text(
        f'[resolvers]\nbase_class = "{base_class_path}"\n'
        f"{dependencies}"
        "[resolvers.agents.domestic_flights_agent]\n"
        f'class = "{agent_class_path}"\n',
        encoding="utf-8",
    )


def test_load_resolver_imports_instantiates_and_invokes_configured_class(tmp_path: Path) -> None:
    _write_resolver_plugin(
        tmp_path,
        base_body=(
            "class BaseResolver:\n"
            "    def __init__(self, rest_client: object | None = None) -> None:\n"
            "        self.rest_client = rest_client\n"
            "    def current_date(self, ctx: ExecutionContext) -> str:\n"
            "        return f'{self.rest_client}:{ctx.message}'\n"
        ),
        agent_body=("class DomesticFlightsAgentResolver(BaseResolver):\n    pass\n"),
        dependencies='[resolvers.dependencies]\nrest_client = "internal_rest_client"\n',
    )
    loader = PluginLoader(tmp_path)

    resolver = loader.load_resolver("domestic_flights_agent", "current_date")
    result = resolver(ExecutionContext(message="hello", state={}))

    assert result == "internal_rest_client:hello"


def test_load_resolver_rejects_missing_toml(tmp_path: Path) -> None:
    loader = PluginLoader(tmp_path)

    with pytest.raises(ResolverPluginError, match="Resolver TOML config not found"):
        loader.load_resolver("domestic_flights_agent", "current_date")


def test_load_resolver_rejects_missing_class_configuration(tmp_path: Path) -> None:
    resolvers_dir = tmp_path / "plugins" / "resolvers"
    resolvers_dir.mkdir(parents=True)
    (resolvers_dir / "resolvers.toml").write_text("[resolvers]\n", encoding="utf-8")

    with pytest.raises(ResolverPluginError, match=r"must define resolvers\.base_class"):
        PluginLoader(tmp_path).load_resolver("domestic_flights_agent", "current_date")


def test_load_resolver_rejects_invalid_class_import_path(tmp_path: Path) -> None:
    _write_resolver_plugin(tmp_path, agent_body="", base_class_path="BaseResolver")

    with pytest.raises(ResolverPluginError, match="Invalid base resolver class import path"):
        PluginLoader(tmp_path).load_resolver("domestic_flights_agent", "current_date")


def test_load_resolver_rejects_unimportable_base_class(tmp_path: Path) -> None:
    _write_resolver_plugin(tmp_path, agent_body="", base_class_path="missing.module.BaseResolver")

    with pytest.raises(ResolverPluginError, match="could not be imported"):
        PluginLoader(tmp_path).load_resolver("domestic_flights_agent", "current_date")


def test_load_resolver_rejects_missing_agent_resolver_config(tmp_path: Path) -> None:
    _write_resolver_plugin(
        tmp_path,
        agent_body=(
            "class DomesticFlightsAgentResolver(BaseResolver):\n"
            "    def current_date(self, ctx: ExecutionContext) -> str:\n"
            "        return 'today'\n"
        ),
    )

    with pytest.raises(
        ResolverPluginError,
        match=r"no \[resolvers\.agents\.super_agent\] class",
    ):
        PluginLoader(tmp_path).load_resolver("super_agent", "current_date")


def test_load_resolver_rejects_unimportable_agent_class(tmp_path: Path) -> None:
    _write_resolver_plugin(
        tmp_path,
        agent_body="",
        agent_class_path="missing.module.DomesticFlightsAgentResolver",
    )

    with pytest.raises(ResolverPluginError, match="could not be imported"):
        PluginLoader(tmp_path).load_resolver("domestic_flights_agent", "current_date")


def test_load_resolver_rejects_agent_class_that_does_not_inherit_base(tmp_path: Path) -> None:
    _write_resolver_plugin(
        tmp_path,
        agent_body=(
            "class DomesticFlightsAgentResolver:\n"
            "    def current_date(self, ctx: ExecutionContext) -> str:\n"
            "        return 'today'\n"
        ),
    )

    with pytest.raises(ResolverPluginError, match="must inherit from base resolver class"):
        PluginLoader(tmp_path).load_resolver("domestic_flights_agent", "current_date")


def test_load_resolver_rejects_uninstantiable_class(tmp_path: Path) -> None:
    _write_resolver_plugin(
        tmp_path,
        agent_body=(
            "class DomesticFlightsAgentResolver(BaseResolver):\n"
            "    def __init__(self, required: object) -> None:\n"
            "        self.required = required\n"
            "    def current_date(self, ctx: ExecutionContext) -> str:\n"
            "        return 'never'\n"
        ),
    )

    with pytest.raises(ResolverPluginError, match="could not be instantiated"):
        PluginLoader(tmp_path).load_resolver("domestic_flights_agent", "current_date")


def test_load_resolver_rejects_missing_method(tmp_path: Path) -> None:
    _write_resolver_plugin(
        tmp_path,
        agent_body=("class DomesticFlightsAgentResolver(BaseResolver):\n    pass\n"),
    )

    with pytest.raises(ResolverPluginError, match="was not found"):
        PluginLoader(tmp_path).load_resolver("domestic_flights_agent", "current_date")


def test_load_resolver_rejects_non_callable_method_attribute(tmp_path: Path) -> None:
    _write_resolver_plugin(
        tmp_path,
        agent_body=(
            "class DomesticFlightsAgentResolver(BaseResolver):\n    current_date = 'not callable'\n"
        ),
    )

    with pytest.raises(ResolverPluginError, match="exists but is not callable"):
        PluginLoader(tmp_path).load_resolver("domestic_flights_agent", "current_date")


def test_load_resolver_rejects_signature_mismatch(tmp_path: Path) -> None:
    _write_resolver_plugin(
        tmp_path,
        agent_body=(
            "class DomesticFlightsAgentResolver(BaseResolver):\n"
            "    def current_date(self) -> str:\n"
            "        return 'today'\n"
        ),
    )

    with pytest.raises(ResolverPluginError, match="must accept exactly one ctx argument"):
        PluginLoader(tmp_path).load_resolver("domestic_flights_agent", "current_date")
