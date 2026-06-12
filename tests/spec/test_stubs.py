"""Plugin stub generation."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentplatform.spec.models import AgentEngineSpec, AgentSpec, ResolverSpec, SystemSpec
from agentplatform.spec.stubs import ResolverGenerateMode, generate_stubs
from agentplatform.utils import ProjectPaths


def _spec_with_resolver_agents() -> AgentEngineSpec:
    return AgentEngineSpec(
        system=SystemSpec(name="demo"),
        graph={"worker": None},
        resolvers={
            "current_date": ResolverSpec(scope="shared", return_type="str"),
            "user_name": ResolverSpec(scope="shared", return_type="str"),
            "domestic_specific": ResolverSpec(scope="agent", return_type="str"),
            "subscription": ResolverSpec(scope="agent", return_type="str"),
        },
        agents={
            "domestic_flights_agent": AgentSpec(
                description="Domestic flights.",
                resolvers=["current_date", "user_name", "domestic_specific", "current_date"],
            ),
            "international_flights_agent": AgentSpec(
                description="International flights.",
                resolvers=["current_date", "user_name"],
            ),
            "super_agent": AgentSpec(
                description="Supermarket.",
                resolvers=["user_name", "subscription"],
            ),
            "admin_agent": AgentSpec(description="Admin."),
        },
    )


def test_generate_stubs_emits_split_base_and_agent_resolver_files(tmp_path: Path) -> None:
    spec = _spec_with_resolver_agents()

    result = generate_stubs(tmp_path, spec)
    paths = ProjectPaths(tmp_path)

    assert ProjectPaths.resolver_init_rel() in result.created
    assert ProjectPaths.resolver_base_rel() in result.created
    assert ProjectPaths.resolver_agent_rel("domestic_flights_agent") in result.created
    assert ProjectPaths.resolver_agent_rel("super_agent") in result.created
    assert ProjectPaths.resolver_config_rel() in result.created
    assert paths.resolver_init.is_file()
    assert paths.resolver_base.is_file()
    assert paths.resolver_agent("domestic_flights_agent").is_file()
    assert paths.resolver_agent("super_agent").is_file()
    assert not paths.resolver_agent("admin_agent").exists()
    assert not (paths.resolvers_dir / "generated.py").exists()
    assert not (paths.resolvers_dir / "current_date.py").exists()

    base = paths.resolver_base.read_text(encoding="utf-8")
    assert "class BaseResolver(ABC):" in base
    assert "def current_date(self, ctx: ExecutionContext) -> str:" in base
    assert "def user_name(self, ctx: ExecutionContext) -> str:" in base
    assert "Customer must implement shared resolver current_date" in base

    domestic = paths.resolver_agent("domestic_flights_agent").read_text(encoding="utf-8")
    assert "class DomesticFlightsAgentResolver(BaseResolver):" in domestic
    assert "def current_date(" not in domestic
    assert "def user_name(" not in domestic
    assert "def domestic_specific(self, ctx: ExecutionContext) -> str:" in domestic
    assert "def subscription(" not in domestic

    super_agent = paths.resolver_agent("super_agent").read_text(encoding="utf-8")
    assert "class SuperAgentResolver(BaseResolver):" in super_agent
    assert "def user_name(" not in super_agent
    assert "def subscription(self, ctx: ExecutionContext) -> str:" in super_agent
    assert "def current_date(" not in super_agent

    international = paths.resolver_agent("international_flights_agent").read_text(encoding="utf-8")
    assert "class InternationalFlightsAgentResolver(BaseResolver):" in international
    assert "def current_date(" not in international
    assert "def user_name(" not in international
    assert "pass" in international

    config = paths.resolver_config.read_text(encoding="utf-8")
    assert '[resolvers]\nbase_class = "plugins.resolvers.base.BaseResolver"' in config
    assert "[resolvers.agents.domestic_flights_agent]" in config
    assert (
        'class = "plugins.resolvers.domestic_flights_agent.DomesticFlightsAgentResolver"' in config
    )
    assert "[resolvers.agents.super_agent]" in config
    assert "[resolvers.agents.international_flights_agent]" in config
    assert "[resolvers.agents.admin_agent]" not in config


def test_generate_stubs_does_not_overwrite_existing_resolver_files(tmp_path: Path) -> None:
    spec = AgentEngineSpec(
        system=SystemSpec(name="demo"),
        graph={"worker": None},
        resolvers={"current_date": ResolverSpec(scope="agent")},
        agents={
            "worker": AgentSpec(
                description="Worker.",
                resolvers=["current_date"],
            ),
        },
    )
    paths = ProjectPaths(tmp_path)
    paths.resolvers_dir.mkdir(parents=True)
    paths.resolver_base.write_text("# customer base\n", encoding="utf-8")
    paths.resolver_agent("worker").write_text("# customer implementation\n", encoding="utf-8")
    paths.resolver_config.write_text(
        '[resolvers]\nbase_class = "custom.BaseResolver"\n',
        encoding="utf-8",
    )

    result = generate_stubs(tmp_path, spec)

    assert ProjectPaths.resolver_base_rel() not in result.created
    assert ProjectPaths.resolver_agent_rel("worker") not in result.created
    assert ProjectPaths.resolver_config_rel() not in result.created
    assert paths.resolver_base.read_text(encoding="utf-8") == "# customer base\n"
    assert "# customer implementation\n" in paths.resolver_agent("worker").read_text(
        encoding="utf-8"
    )
    assert paths.resolver_config.read_text(encoding="utf-8").startswith(
        '[resolvers]\nbase_class = "custom.BaseResolver"\n'
    )


def test_generate_stubs_adds_missing_method_to_existing_agent_file(tmp_path: Path) -> None:
    spec = AgentEngineSpec(
        system=SystemSpec(name="demo"),
        graph={"worker": None},
        resolvers={
            "current_date": ResolverSpec(scope="agent"),
            "user_name": ResolverSpec(scope="agent"),
        },
        agents={
            "worker": AgentSpec(
                description="Worker.",
                resolvers=["current_date", "user_name"],
            ),
        },
    )
    paths = ProjectPaths(tmp_path)
    paths.resolvers_dir.mkdir(parents=True)
    paths.resolver_agent("worker").write_text(
        "from agentplatform.runtime import ExecutionContext\n"
        "from plugins.resolvers.base import BaseResolver\n\n\n"
        "class WorkerResolver(BaseResolver):\n"
        "    def current_date(self, ctx: ExecutionContext) -> str:\n"
        "        return 'implemented'\n",
        encoding="utf-8",
    )

    result = generate_stubs(tmp_path, spec)

    assert ProjectPaths.resolver_agent_rel("worker") in result.updated
    content = paths.resolver_agent("worker").read_text(encoding="utf-8")
    assert "return 'implemented'" in content
    assert "def user_name(self, ctx: ExecutionContext) -> str:" in content


def test_generate_stubs_children_mode_does_not_touch_base(tmp_path: Path) -> None:
    spec = _spec_with_resolver_agents()
    paths = ProjectPaths(tmp_path)
    paths.resolvers_dir.mkdir(parents=True)
    paths.resolver_base.write_text("# hand edited base\n", encoding="utf-8")

    result = generate_stubs(
        tmp_path,
        spec,
        resolver_mode=ResolverGenerateMode.CHILDREN,
    )

    assert ProjectPaths.resolver_base_rel() not in result.created
    assert ProjectPaths.resolver_base_rel() not in result.updated
    assert paths.resolver_base.read_text(encoding="utf-8") == "# hand edited base\n"
    assert ProjectPaths.resolver_agent_rel("domestic_flights_agent") in result.created
    assert ProjectPaths.resolver_agent_rel("super_agent") in result.created


def test_generate_stubs_specific_child_only_updates_selected_agent(tmp_path: Path) -> None:
    spec = _spec_with_resolver_agents()
    paths = ProjectPaths(tmp_path)

    result = generate_stubs(
        tmp_path,
        spec,
        resolver_mode=ResolverGenerateMode.CHILD,
        resolver_agent_id="super_agent",
    )

    assert ProjectPaths.resolver_agent_rel("super_agent") in result.created
    assert not paths.resolver_agent("domestic_flights_agent").exists()
    assert not paths.resolver_base.exists()
    assert "[resolvers.agents.super_agent]" in paths.resolver_config.read_text(encoding="utf-8")
    assert "[resolvers.agents.domestic_flights_agent]" not in paths.resolver_config.read_text(
        encoding="utf-8"
    )


def test_generate_stubs_reports_stale_resolver_files(tmp_path: Path) -> None:
    spec = _spec_with_resolver_agents()
    paths = ProjectPaths(tmp_path)
    paths.resolvers_dir.mkdir(parents=True)
    (paths.resolvers_dir / "old_agent.py").write_text("# old\n", encoding="utf-8")

    result = generate_stubs(tmp_path, spec)

    assert "plugins/resolvers/old_agent.py" in result.stale


def test_generate_stubs_reports_stale_duplicated_shared_child_method(tmp_path: Path) -> None:
    spec = _spec_with_resolver_agents()
    paths = ProjectPaths(tmp_path)
    paths.resolvers_dir.mkdir(parents=True)
    paths.resolver_agent("domestic_flights_agent").write_text(
        "from agentplatform.runtime import ExecutionContext\n"
        "from plugins.resolvers.base import BaseResolver\n\n\n"
        "class DomesticFlightsAgentResolver(BaseResolver):\n"
        "    def current_date(self, ctx: ExecutionContext) -> str:\n"
        "        return 'duplicate'\n",
        encoding="utf-8",
    )

    result = generate_stubs(tmp_path, spec)

    assert (
        "plugins/resolvers/domestic_flights_agent.py::current_date duplicates shared resolver"
    ) in result.stale


def test_generate_stubs_preserves_existing_base_implementation(tmp_path: Path) -> None:
    spec = _spec_with_resolver_agents()
    paths = ProjectPaths(tmp_path)
    paths.resolvers_dir.mkdir(parents=True)
    paths.resolver_base.write_text(
        "from agentplatform.runtime import ExecutionContext\n\n"
        "class BaseResolver:\n"
        "    def current_date(self, ctx: ExecutionContext) -> str:\n"
        "        return 'implemented'\n",
        encoding="utf-8",
    )

    result = generate_stubs(tmp_path, spec)

    content = paths.resolver_base.read_text(encoding="utf-8")
    assert "return 'implemented'" in content
    assert "def user_name(self, ctx: ExecutionContext) -> str:" in content
    assert ProjectPaths.resolver_base_rel() in result.updated


def test_generate_stubs_rejects_invalid_agent_resolver_class_name(tmp_path: Path) -> None:
    spec = AgentEngineSpec(
        system=SystemSpec(name="demo"),
        graph={"123": None},
        resolvers={"current_date": ResolverSpec(scope="agent")},
        agents={
            "123": AgentSpec(
                description="Invalid class name.",
                resolvers=["current_date"],
            ),
        },
    )

    with pytest.raises(ValueError, match="Cannot generate resolver class name"):
        generate_stubs(tmp_path, spec)
