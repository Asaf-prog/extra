from __future__ import annotations


def test_package_imports() -> None:
    import agent_engine

    assert isinstance(agent_engine.__version__, str)
    assert agent_engine.__version__


def test_cli_imports() -> None:
    from agentctl.main import cli

    assert cli is not None
