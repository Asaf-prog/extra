from __future__ import annotations

import logging

from langchain_core.callbacks import BaseCallbackHandler

from agent_engine.logging_config import log
from agent_engine.observability.provider import CallbackProvider
from agent_engine.observability.providers.langfuse import LangfuseProvider
from agent_engine.observability.providers.logging import LoggingProvider

logger = logging.getLogger(__name__)

# Every backend is a CallbackProvider here. The logging trace is always on
# (is_enabled() -> True); external backends self-enable from env.
# Add a backend: write a CallbackProvider, append it here.
PROVIDERS: list[CallbackProvider] = [
    LoggingProvider(),
    LangfuseProvider(),
]


def build_callbacks() -> list[BaseCallbackHandler]:
    """Handlers for every enabled provider. Host calls this; injects into engine."""
    callbacks: list[BaseCallbackHandler] = []
    for provider in PROVIDERS:
        if not provider.is_enabled():
            continue
        handler = provider.build()
        if handler is None:
            continue
        log(logger, logging.INFO, "observability enabled", backend=provider.name)
        callbacks.append(handler)
    return callbacks
