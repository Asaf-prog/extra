from __future__ import annotations

import logging
import os

from langchain_core.callbacks import BaseCallbackHandler

from agent_engine.logging_config import log
from agent_engine.observability.provider import CallbackProvider

logger = logging.getLogger(__name__)


class LangfuseProvider(CallbackProvider):
    name = "langfuse"

    def is_enabled(self) -> bool:
        return bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))

    def build(self) -> BaseCallbackHandler | None:
        try:
            try:
                from langfuse.callback import CallbackHandler  # v2
            except ImportError:
                from langfuse.langchain import CallbackHandler  # v3+
            return CallbackHandler()
        except Exception as exc:
            log(logger, logging.WARNING, "langfuse build failed", error=str(exc))
            return None
