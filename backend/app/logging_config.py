"""Structured logging setup.

Every pipeline stage call logs one JSON line via the `pipeline` logger with a
consistent set of fields (lead_id, stage, prompt_version, latency_ms,
success). This is the basic observability surface for the project: greppable,
parseable, and enough to answer "what did stage X do for lead Y and how long
did it take" without a tracing backend.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

_RESERVED = set(logging.LogRecord(None, 0, "", 0, "", (), None).__dict__.keys())


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Include any extra= fields the caller attached.
        for key, value in record.__dict__.items():
            if key not in _RESERVED:
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root.addHandler(handler)


def get_pipeline_logger() -> logging.Logger:
    return logging.getLogger("pipeline")
