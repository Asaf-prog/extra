from __future__ import annotations

import logging
import sys
import types
from typing import Any, ClassVar

import pytest

from agent_engine.models import factory as factory_mod
from agent_engine.models.factory import ModelConfigurationError, build_chat_model


class _FakeAnthropicModel:
    pass


class _FakeBedrockModel:
    instances: ClassVar[list[_FakeBedrockModel]] = []

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.instances.append(self)


def _install_fake_langchain_aws(monkeypatch: pytest.MonkeyPatch, cls: type[Any]) -> None:
    module = types.ModuleType("langchain_aws")
    monkeypatch.setattr(module, "ChatBedrockConverse", cls, raising=False)
    monkeypatch.setitem(sys.modules, "langchain_aws", module)


def test_anthropic_provider_still_uses_langchain_init_chat_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []
    model = _FakeAnthropicModel()

    def fake_init_chat_model(name: str, **kwargs: Any) -> _FakeAnthropicModel:
        calls.append((name, kwargs))
        return model

    monkeypatch.setattr(factory_mod, "init_chat_model", fake_init_chat_model)

    result = build_chat_model("anthropic", "claude-haiku-4-5", temperature=0.0)

    assert result is model
    assert calls == [
        (
            "claude-haiku-4-5",
            {"model_provider": "anthropic", "temperature": 0.0},
        )
    ]


def test_bedrock_provider_creates_chat_bedrock_converse_with_yaml_region(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _FakeBedrockModel.instances.clear()
    _install_fake_langchain_aws(monkeypatch, _FakeBedrockModel)

    result = build_chat_model(
        "bedrock",
        "anthropic.claude-3-5-haiku-20241022-v1:0",
        temperature=0.0,
        region="us-east-1",
        max_tokens=512,
        top_p=0.8,
    )

    assert result is _FakeBedrockModel.instances[0]
    assert _FakeBedrockModel.instances[0].kwargs == {
        "model": "anthropic.claude-3-5-haiku-20241022-v1:0",
        "region_name": "us-east-1",
        "temperature": 0.0,
        "max_tokens": 512,
        "top_p": 0.8,
    }


def test_bedrock_region_can_come_from_aws_region(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _FakeBedrockModel.instances.clear()
    _install_fake_langchain_aws(monkeypatch, _FakeBedrockModel)
    monkeypatch.setenv("AWS_REGION", "us-west-2")
    monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)

    build_chat_model("bedrock", "anthropic.claude-3-5-haiku-20241022-v1:0")

    assert _FakeBedrockModel.instances[0].kwargs["region_name"] == "us-west-2"


def test_bedrock_region_can_come_from_aws_default_region(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _FakeBedrockModel.instances.clear()
    _install_fake_langchain_aws(monkeypatch, _FakeBedrockModel)
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-central-1")

    build_chat_model("bedrock", "anthropic.claude-3-5-haiku-20241022-v1:0")

    assert _FakeBedrockModel.instances[0].kwargs["region_name"] == "eu-central-1"


def test_bedrock_missing_region_fails_clearly(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_langchain_aws(monkeypatch, _FakeBedrockModel)
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)

    with pytest.raises(ModelConfigurationError, match="requires an AWS region"):
        build_chat_model("bedrock", "anthropic.claude-3-5-haiku-20241022-v1:0")


def test_bedrock_construction_failure_mentions_aws_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class RaisingBedrockModel:
        def __init__(self, **kwargs: Any) -> None:
            raise RuntimeError("Unable to locate credentials")

    _install_fake_langchain_aws(monkeypatch, RaisingBedrockModel)

    with pytest.raises(ModelConfigurationError, match="AWS credentials"):
        build_chat_model(
            "bedrock",
            "anthropic.claude-3-5-haiku-20241022-v1:0",
            region="us-east-1",
        )


def test_unsupported_provider_is_rejected_clearly() -> None:
    with pytest.raises(ModelConfigurationError, match="Unsupported model provider 'openai'"):
        build_chat_model("openai", "gpt-4o-mini")


def test_model_factory_does_not_log_aws_secrets(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    _FakeBedrockModel.instances.clear()
    _install_fake_langchain_aws(monkeypatch, _FakeBedrockModel)
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIA_TEST_SECRET")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "super-secret-value")

    with caplog.at_level(logging.INFO):
        build_chat_model(
            "bedrock",
            "anthropic.claude-3-5-haiku-20241022-v1:0",
            region="us-east-1",
        )

    assert "AKIA_TEST_SECRET" not in caplog.text
    assert "super-secret-value" not in caplog.text
