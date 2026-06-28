"""Model layer — build provider-agnostic chat models from ``ModelSpec``."""

from agent_engine.models.factory import ModelConfigurationError, build_chat_model

__all__ = ["ModelConfigurationError", "build_chat_model"]
