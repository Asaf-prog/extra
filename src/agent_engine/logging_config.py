from __future__ import annotations

import contextvars
import logging
import os

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")

_NOISY = ("httpx", "httpcore", "anthropic", "openai", "urllib3")


def _kv(key: str, value: object) -> str:
    if isinstance(value, str) and any(c in value for c in ' ="'):
        return f'{key}="{value}"'
    return f"{key}={value}"


class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        pairs: list[str] = []
        rid = request_id_var.get()
        if rid:
            pairs.append(_kv("request_id", rid))
        fields = getattr(record, "fields", None)
        if isinstance(fields, dict):
            pairs.extend(_kv(k, v) for k, v in fields.items())
        return f"{base} {' '.join(pairs)}" if pairs else base


def log(logger: logging.Logger, level: int, event: str, **fields: object) -> None:
    logger.log(level, event, extra={"fields": fields})


def configure_logging(level: str | None = None) -> None:
    name = (level or os.getenv("LOG_LEVEL") or "INFO").upper()
    resolved = getattr(logging, name, logging.INFO)
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredFormatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        root.addHandler(handler)
    root.setLevel(resolved)
    for noisy in _NOISY:
        logging.getLogger(noisy).setLevel(logging.WARNING)


def current_request_id() -> str:
    return request_id_var.get()
