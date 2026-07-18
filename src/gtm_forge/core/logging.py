"""Structured JSON logging to stderr. Machine-parseable by default."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime

_EXTRA_KEYS = ("run_id", "skill", "event", "duration_ms", "cost_usd", "model", "status")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key in _EXTRA_KEYS:
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class _StderrHandler(logging.StreamHandler):  # type: ignore[type-arg]
    """StreamHandler that re-resolves sys.stderr on every emit.

    Binding the stream once breaks under test runners and embedded interpreters
    that swap sys.stderr between invocations (the cached stream gets closed).
    """

    def emit(self, record: logging.LogRecord) -> None:
        self.stream = sys.stderr
        super().emit(record)


def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = _StderrHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.propagate = False
    logger.setLevel(level.upper())
    return logger
