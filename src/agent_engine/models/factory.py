"""Build a chat model from resolved model config (see ADR 0008).

This is the single chokepoint that translates provider + name + temperature
into a LangChain ``BaseChatModel``. The runtime depends only on
``BaseChatModel`` and this factory — never on a specific provider SDK.
Provider integration packages (``langchain-anthropic``, ``langchain-openai``,
…) are imported lazily by ``init_chat_model`` based on ``provider``.
"""

from __future__ import annotations

import logging

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from agent_engine.logging_config import log

logger = logging.getLogger(__name__)


def build_chat_model(
    provider: str,
    name: str,
    temperature: float | None = None,
) -> BaseChatModel:
    """Construct a chat model from flat config fields.

    Switching providers is a configuration change, not a code change.
    """
    log(
        logger,
        logging.INFO,
        "llm configured",
        provider=provider,
        model=name,
        temperature=temperature,
    )
    if temperature is None:
        return init_chat_model(name, model_provider=provider)
    return init_chat_model(name, model_provider=provider, temperature=temperature)
