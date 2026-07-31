"""Logging estruturado em JSON (seção 19.1 da proposta)."""
import json
import logging
import os
import sys
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": os.getenv("OTEL_SERVICE_NAME", os.getenv("WORKER_DOMAIN", "factory")),
            "logger": record.name,
            "event": record.getMessage(),
        }
        for key in (
            "correlation_id",
            "workflow_run_id",
            "task_id",
            "agent_id",
            "duration_ms",
            "event",
        ):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: str | None = None) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level or os.getenv("LOG_LEVEL", "INFO"))


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
